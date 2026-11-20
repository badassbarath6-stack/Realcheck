#!/usr/bin/env python3
"""Independent, research-only Impulse Retracer sweep.

One invocation processes exactly one symbol/timeframe pair. No live-worker imports.
Raw input is Binance USD-M monthly M1 klines (CSV or ZIP); outputs are deterministic.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math, os, sys, urllib.request, zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

START = "2024-11-20T00:00:00+00:00"
END = "2026-11-20T00:00:00+00:00"
BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
TIMEFRAMES = {"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240}
ATR_PERIODS=(10,14,20,28)
THRESHOLDS=(2.0,2.2,2.4,2.6,2.8,3.0)
RETRACEMENTS=(.618,.667,.707,.75,.786,.82)
BUFFERS=(0.,.2,.4,.6,.8,1.)
RRS=(1.2,1.5,2.,2.5,3.,4.)
FEE_BPS=5.0

@dataclass(frozen=True)
class Config:
    atr_period:int; impulse_atr:float; retracement:float; sl_buffer:float; rr:float

def configurations():
    return [Config(*x) for x in itertools.product(ATR_PERIODS,THRESHOLDS,RETRACEMENTS,BUFFERS,RRS)]

def sha256(path:Path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def month_range():
    # Include one month of warmup before the requested two-year evaluation.
    return [(2024,10)] + [(y,m) for y in (2024,2025,2026) for m in range(1,13)
                          if (y,m)>=(2024,11) and (y,m)<=(2026,10)]

def download_month(symbol,year,month,out):
    name=f"{symbol}-1m-{year}-{month:02d}.zip"
    url=f"{BASE}/{symbol}/1m/{name}"
    target=out/name
    if target.exists(): return target
    target.parent.mkdir(parents=True,exist_ok=True)
    req=urllib.request.Request(url,headers={"User-Agent":"ImpulseRetracerResearch/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=90) as r, target.open("wb") as f:
            while True:
                b=r.read(1<<20)
                if not b: break
                f.write(b)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target

def load_klines(files):
    rows={}
    for path in files:
        opener=zipfile.ZipFile(path).open if path.suffix==".zip" else open
        with (opener(path.name) if path.suffix==".zip" else path.open()) as stream:
            for row in csv.reader((x.decode() if isinstance(x,bytes) else x for x in stream)):
                if not row or not row[0].isdigit(): continue
                ts=int(row[0]); o,h,l,c=map(float,row[1:5])
                if not all(map(math.isfinite,(o,h,l,c))) or min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or h<l:
                    raise ValueError(f"Invalid OHLC row in {path}: {row[:6]}")
                rows[ts]=(o,h,l,c)
    return sorted((t,*v) for t,v in rows.items())

def atr_wilder(bars,period):
    tr=[0.0]*len(bars)
    for i,(t,o,h,l,c) in enumerate(bars):
        prev=bars[i-1][4] if i else c
        tr[i]=max(h-l,abs(h-prev),abs(l-prev))
    out=[float("nan")]*len(bars)
    if len(bars)<=period: return out
    out[period-1]=sum(tr[:period])/period
    for i in range(period,len(bars)):
        out[i]=(out[i-1]*(period-1)+tr[i])/period
    return out

def resample_m1(rows,minutes):
    step=minutes*60_000; grouped={}
    for t,o,h,l,c in rows:
        bucket=t//step*step
        if bucket not in grouped: grouped[bucket]=[o,h,l,c,1]
        else:
            x=grouped[bucket]; x[1]=max(x[1],h); x[2]=min(x[2],l); x[3]=c; x[4]+=1
    return [(t,*x[:4],x[4]) for t,x in sorted(grouped.items())]

def metrics(trades):
    if not trades: return {"trades":0,"wins":0,"losses":0,"win_rate":0.0,"pf":0.0,"net_bps":0.0,"expectancy_bps":0.0,"max_drawdown_bps":0.0}
    pnls=[x["net_bps"] for x in trades]; wins=sum(x>0 for x in pnls)
    gp=sum(x for x in pnls if x>0); gl=-sum(x for x in pnls if x<0)
    eq=peak=dd=0.
    for p in pnls:
        eq+=p; peak=max(peak,eq); dd=max(dd,peak-eq)
    return {"trades":len(pnls),"wins":wins,"losses":len(pnls)-wins,"win_rate":wins/len(pnls),
            "pf":gp/gl if gl else (float("inf") if gp else 0.0),"net_bps":sum(pnls),
            "expectancy_bps":sum(pnls)/len(pnls),"max_drawdown_bps":dd}

def run_pair(symbol,tf,data_dir,out_dir):
    if tf not in TIMEFRAMES: raise ValueError(tf)
    files=[]
    for y,m in month_range():
        p=download_month(symbol,y,m,data_dir); files.append(p)
    rows=load_klines(files)
    if len(rows)<1000: raise RuntimeError("Insufficient M1 history")
    step=60_000
    gaps=sum(1 for a,b in zip(rows,rows[1:]) if b[0]-a[0]!=step)
    start=int(datetime.fromisoformat(START).timestamp()*1000)
    end=int(datetime.fromisoformat(END).timestamp()*1000)
    rows=[r for r in rows if r[0]<end]
    if not rows or rows[-1][0]<end-60_000: raise RuntimeError("M1 archive does not cover requested end")
    bars=resample_m1(rows,TIMEFRAMES[tf])
    configs=configurations()
    if len(configs)!=5184: raise AssertionError("Search grid changed")
    # Event extraction is deliberately separate from config evaluation: detector
    # variants are only ATR-period x impulse-threshold, not 5,184 duplicated scans.
    events=[]
    for period in ATR_PERIODS:
        atr=atr_wilder(bars,period)
        for threshold in THRESHOLDS:
            for i in range(period,len(bars)):
                t,o,h,l,c,count=bars[i]
                if count!=TIMEFRAMES[tf]: continue
                a=atr[i-1]  # prior completed candle only
                if not math.isfinite(a) or a<=0: continue
                direction=1 if c>o else (-1 if c<o else 0)
                if direction and abs(c-o)>=threshold*a:
                    events.append((t,i,direction,o,h,l,c,a,period,threshold))
    manifest={"symbol":symbol,"timeframe":tf,"period_start":START,"period_end_exclusive":END,
              "config_count":len(configs),"atr_periods":ATR_PERIODS,"thresholds":THRESHOLDS,
              "retracements":RETRACEMENTS,"buffers":BUFFERS,"rrs":RRS,
              "m1_rows":len(rows),"timeframe_bars":len(bars),"m1_gaps":gaps,
              "source_files":[{"name":p.name,"sha256":sha256(p)} for p in files],
              "status":"DATA_AND_IMPULSE_EXTRACTION_ONLY"}
    out_dir.mkdir(parents=True,exist_ok=True)
    (out_dir/f"{symbol}_{tf}_manifest.json").write_text(json.dumps(manifest,indent=2))
    with (out_dir/f"{symbol}_{tf}_impulses.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["bar_open_ms","bar_index","direction","open","high","low","close","prior_atr","atr_period","threshold"])
        w.writerows(events)
    print(json.dumps(manifest,indent=2))
    print("NOTE: trade simulation and ranking are not yet enabled; this output is not a backtest result.")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",required=True,choices=["BTCUSDT","ETHUSDT"])
    p.add_argument("--timeframe",required=True,choices=sorted(TIMEFRAMES))
    p.add_argument("--data-dir",default="research-data")
    p.add_argument("--output-dir",default="research-output")
    a=p.parse_args()
    run_pair(a.symbol,a.timeframe,Path(a.data_dir),Path(a.output_dir))

if __name__=="__main__": main()
