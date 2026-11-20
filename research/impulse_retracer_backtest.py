#!/usr/bin/env python3
"""Independent Impulse Retracer research backtester; never imports or deploys live code."""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, math, urllib.request, urllib.error, zipfile
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

START_MS=int(datetime(2024,11,20,tzinfo=timezone.utc).timestamp()*1000)
END_MS=int(datetime(2026,11,20,tzinfo=timezone.utc).timestamp()*1000)
BASE="https://data.binance.vision/data/futures/um"
TIMEFRAMES={"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240}
ATR_PERIODS=(10,14,20,28); THRESHOLDS=(2.,2.2,2.4,2.6,2.8,3.)
RETRACEMENTS=(.618,.667,.707,.75,.786,.82); BUFFERS=(0.,.2,.4,.6,.8,1.)
RRS=(1.2,1.5,2.,2.5,3.,4.); FEE_BPS=5.

@dataclass(frozen=True)
class Config:
    atr_period:int; impulse_atr:float; retracement:float; sl_buffer:float; rr:float

def configurations():
    return [Config(*x) for x in itertools.product(ATR_PERIODS,THRESHOLDS,RETRACEMENTS,BUFFERS,RRS)]

def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def month_files(symbol):
    out=[]
    y,m=2024,10
    while (y,m)<=(2026,10):
        out.append((y,m)); m+=1
        if m==13: y+=1; m=1
    return out

def fetch_archive(url,target):
    target=Path(target); target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists() and target.stat().st_size: return target
    req=urllib.request.Request(url,headers={"User-Agent":"ImpulseRetracerResearch/1.0"})
    try:
        with urllib.request.urlopen(req,timeout=120) as r, target.open("wb") as f:
            while True:
                b=r.read(1<<20)
                if not b: break
                f.write(b)
    except Exception:
        target.unlink(missing_ok=True); raise
    return target

def download_inputs(symbol,data_dir):
    paths=[]
    for y,m in month_files(symbol):
        name=f"{symbol}-1m-{y}-{m:02d}.zip"
        paths.append(fetch_archive(f"{BASE}/monthly/klines/{symbol}/1m/{name}",Path(data_dir)/name))
    # The current monthly archive is not published until month-end; add daily files.
    for day in range(1,20):
        name=f"{symbol}-1m-2026-11-{day:02d}.zip"
        paths.append(fetch_archive(f"{BASE}/daily/klines/{symbol}/1m/{name}",Path(data_dir)/name))
    return paths

def load_klines(paths):
    rows={}
    for path in paths:
        try:
            with zipfile.ZipFile(path) as z:
                members=[n for n in z.namelist() if n.endswith(".csv")]
                if not members: raise ValueError(f"No CSV in {path}")
                with z.open(members[0]) as f:
                    reader=csv.reader((x.decode("utf-8") for x in f))
                    for row in reader: _add_row(rows,row,path)
        except zipfile.BadZipFile:
            raise ValueError(f"Corrupt Binance archive: {path}")
    return [(t,*v) for t,v in sorted(rows.items())]

def _add_row(rows,row,path):
    if not row or not row[0].isdigit(): return
    t=int(row[0]); o,h,l,c=map(float,row[1:5])
    if not all(math.isfinite(x) for x in (o,h,l,c)) or min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or h<l:
        raise ValueError(f"Invalid OHLC row in {path}: {row[:6]}")
    if t in rows and rows[t]!=(o,h,l,c): raise ValueError(f"Conflicting duplicate M1 timestamp {t}")
    rows[t]=(o,h,l,c)

def resample_m1(rows,minutes):
    step=minutes*60000; out=[]
    for t,o,h,l,c in rows:
        bucket=t//step*step
        if not out or out[-1][0]!=bucket: out.append([bucket,o,h,l,c,1])
        else:
            x=out[-1]; x[2]=max(x[2],h); x[3]=min(x[3],l); x[4]=c; x[5]+=1
    return [tuple(x) for x in out]

def atr_wilder(bars,period):
    tr=[]
    for i,b in enumerate(bars):
        prev=bars[i-1][4] if i else b[4]
        tr.append(max(b[2]-b[3],abs(b[2]-prev),abs(b[3]-prev)))
    out=[float("nan")]*len(bars)
    if len(bars)>=period:
        out[period-1]=sum(tr[:period])/period
        for i in range(period,len(bars)): out[i]=(out[i-1]*(period-1)+tr[i])/period
    return out

def score_metrics(trades):
    p=[x["net_bps"] for x in trades]
    if not p: return {"trades":0,"wins":0,"losses":0,"win_rate":0.,"gross_profit_bps":0.,"gross_loss_bps":0.,"net_bps":0.,"pf":0.,"expectancy_bps":0.,"max_drawdown_bps":0.}
    gp=sum(x for x in p if x>0); gl=-sum(x for x in p if x<0); eq=peak=dd=0.
    for x in p: eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
    wins=[x for x in p if x>0]; losses=[x for x in p if x<=0]
    return {"trades":len(p),"wins":len(wins),"losses":len(losses),
            "win_rate":len(wins)/len(p),"gross_profit_bps":gp,"gross_loss_bps":gl,
            "net_bps":sum(p),"pf":gp/gl if gl else (999. if gp else 0.),
            "expectancy_bps":sum(p)/len(p),"average_win_bps":sum(wins)/len(wins) if wins else 0.,
            "average_loss_bps":sum(losses)/len(losses) if losses else 0.,"max_drawdown_bps":dd}

def _trade_for_setup(m1,trigger_i,direction,entry,stop,target,slip):
    # Entry is next M1 open after trigger candle. Exit begins at that entry candle.
    risk=abs(entry-stop)
    if risk<=0 or not math.isfinite(risk): return None
    for j in range(trigger_i,len(m1)):
        t,o,h,l,c=m1[j]
        if direction==1:
            if o<=stop: exit_px=o; reason="stop_gap"; break
            if l<=stop: exit_px=stop; reason="stop"; break
            if o>=target: exit_px=o; reason="target_gap"; break
            if h>=target: exit_px=target; reason="target"; break
        else:
            if o>=stop: exit_px=o; reason="stop_gap"; break
            if h>=stop: exit_px=stop; reason="stop"; break
            if o<=target: exit_px=o; reason="target_gap"; break
            if l<=target: exit_px=target; reason="target"; break
    else:
        if len(m1)<=trigger_i: return None
        t=m1[-1][0]; exit_px=m1[-1][4]; reason="time"
    gross=direction*(exit_px-entry)/entry*10000
    costs=2*(FEE_BPS+slip)
    return {"entry_ms":m1[trigger_i][0],"exit_ms":t,"entry":entry,"exit":exit_px,
            "reason":reason,"gross_bps":gross,"net_bps":gross-costs,"holding_minutes":(t-m1[trigger_i][0])//60000}

def simulate(m1,tf_bars,tf,slip,funding=()):
    """Scan forming same-timeframe impulse candles on the M1 clock, then simulate M1 retracements."""
    mins=TIMEFRAMES[tf]; tf_ms=mins*60000
    m1_times=[x[0] for x in m1]
    atr_cache={p:atr_wilder(tf_bars,p) for p in ATR_PERIODS}
    completed_index={bar[0]:i for i,bar in enumerate(tf_bars)}
    cfgs=configurations()
    by_key={(p,t):[] for p in ATR_PERIODS for t in THRESHOLDS}
    for cfg in cfgs: by_key[(cfg.atr_period,cfg.impulse_atr)].append(cfg)
    import bisect
    funding_times=[x[0] for x in funding]
    funding_prefix=[0.0]
    for _,rate in funding: funding_prefix.append(funding_prefix[-1]+rate)
    candidates=[]
    # Every detector variant observes the current TF candle as it forms. Its ATR
    # reference is the ATR of the immediately preceding completed TF candle.
    for period in ATR_PERIODS:
        atr=atr_cache[period]
        for threshold in THRESHOLDS:
            matching=by_key[(period,threshold)]
            pos=0
            while pos<len(m1):
                bucket=m1[pos][0]//tf_ms*tf_ms
                end=pos+1
                while end<len(m1) and m1[end][0]//tf_ms*tf_ms==bucket: end+=1
                prior_i=completed_index.get(bucket-tf_ms)
                if prior_i is not None and math.isfinite(atr[prior_i]) and atr[prior_i]>0:
                    open_px=m1[pos][1]; run_hi=open_px; run_lo=open_px
                    for k in range(pos,end):
                        _,mo,mh,ml,mc=m1[k]
                        run_hi=max(run_hi,mh); run_lo=min(run_lo,ml)
                        direction=1 if mc>open_px else (-1 if mc<open_px else 0)
                        if not direction or abs(mc-open_px)<threshold*atr[prior_i]: continue
                        impulse_end=m1[k][0]+60000
                        if impulse_end<START_MS or impulse_end>=END_MS: continue
                        first=k+1
                        expiry=bucket+4*tf_ms
                        last=bisect.bisect_left(m1_times,expiry)
                        if first>=last or first>=len(m1): break
                        rng=run_hi-run_lo
                        if rng<=0: break
                        event_id=f"{bucket}:{period}:{threshold}"
                        for cfg in matching:
                            level=(run_hi-rng*cfg.retracement) if direction==1 else (run_lo+rng*cfg.retracement)
                            stop=(run_lo-cfg.sl_buffer*atr[prior_i]) if direction==1 else (run_hi+cfg.sl_buffer*atr[prior_i])
                            trigger=None
                            for j in range(first,last):
                                _,_,jh,jl,_=m1[j]
                                if (direction==1 and jl<=level) or (direction==-1 and jh>=level):
                                    trigger=j; break
                            if trigger is None or trigger+1>=len(m1): continue
                            entry=m1[trigger+1][1]
                            risk=direction*(entry-stop)
                            if risk<=0: continue
                            target=entry+direction*risk*cfg.rr
                            trade=_trade_for_setup(m1,trigger+1,direction,entry,stop,target,slip)
                            if trade is None: continue
                            lo=bisect.bisect_right(funding_times,trade["entry_ms"])
                            hi=bisect.bisect_right(funding_times,trade["exit_ms"])
                            paid=direction*(funding_prefix[hi]-funding_prefix[lo])*10000
                            trade["funding_bps"]=paid; trade["net_bps"]-=paid
                            trade.update({"config":cfg,"event_id":event_id,"trigger_ms":m1[trigger][0],
                                          "impulse_ms":m1[k][0],"direction":"long" if direction==1 else "short"})
                            candidates.append(trade)
                        # First threshold crossing freezes the impulse candle for this detector.
                        break
                pos=end
    return candidates

def split_bounds():
    span=END_MS-START_MS
    return START_MS+int(span*.60), START_MS+int(span*.80)

def select_period(candidates,period,training_pf=None):
    train_end,val_end=split_bounds()
    lo,hi=(START_MS,train_end) if period=="train" else ((train_end,val_end) if period=="validation" else (val_end,END_MS))
    # Keep both signal and realized exit inside the same chronological partition.
    rows=[x for x in candidates if lo<=x["impulse_ms"]<hi and x["exit_ms"]<hi]
    if period=="train": return rows
    # Earliest trigger minute owns each impulse. Among same-minute contenders choose
    # the highest training PF; one contender bypasses the PF comparison.
    grouped={}
    for x in rows: grouped.setdefault(x["event_id"],[]).append(x)
    selected=[]
    for group in grouped.values():
        earliest=min(x["trigger_ms"] for x in group)
        contenders=[x for x in group if x["trigger_ms"]==earliest]
        if len(contenders)==1: selected.append(contenders[0]); continue
        def rank(x):
            cfg=asdict(x["config"]); key=tuple(cfg[k] for k in ("atr_period","impulse_atr","retracement","sl_buffer","rr"))
            m=(training_pf or {}).get(key,{"pf":0.,"trades":0})
            return (m["pf"] if m["trades"]>=30 else float("-inf"),m["trades"])
        eligible=[x for x in contenders if (training_pf or {}).get(config_key(x["config"]),{"trades":0})["trades"]>=30]
        if eligible: selected.append(max(eligible,key=rank))
    return selected

def config_key(c):
    return tuple(asdict(c)[k] for k in ("atr_period","impulse_atr","retracement","sl_buffer","rr"))

def write_csv(path,rows):
    if not rows: path.write_text(""); return
    keys=list(rows[0])
    with path.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=keys); w.writeheader()
        for r in rows:
            x={k:(json.dumps(asdict(v)) if isinstance(v,Config) else v) for k,v in r.items()}
            w.writerow(x)

def download_funding(symbol,data_dir):
    paths=[]
    def optional(name,url):
        try: paths.append(fetch_archive(url,Path(data_dir)/'funding'/name))
        except urllib.error.HTTPError as exc:
            if exc.code!=404: raise
    for y,m in month_files(symbol):
        name=f'{symbol}-fundingRate-{y}-{m:02d}.zip'
        optional(name,f'{BASE}/monthly/fundingRate/{symbol}/{name}')
    for day in range(1,20):
        name=f'{symbol}-fundingRate-2026-11-{day:02d}.zip'
        optional(name,f'{BASE}/daily/fundingRate/{symbol}/{name}')
    rates={}
    for path in paths:
        with zipfile.ZipFile(path) as z:
            member=next((n for n in z.namelist() if n.endswith('.csv')),None)
            if not member: continue
            with z.open(member) as stream:
                for row in csv.reader((x.decode('utf-8') for x in stream)):
                    if len(row)>=3 and row[1].isdigit():
                        rate=float(row[2])
                        if math.isfinite(rate): rates[int(row[1])]=rate
    return sorted(rates.items()),paths

def run_pair(symbol,tf,data_dir,out_dir):
    files=download_inputs(symbol,data_dir); m1_all=load_klines(files)
    funding,funding_files=download_funding(symbol,data_dir)
    # Exact M1 continuity is audited, not silently forward-filled.
    start=START_MS-35*86400000
    m1=[r for r in m1_all if start<=r[0]<END_MS]
    if not m1 or m1[-1][0]<END_MS-60000: raise RuntimeError("Input archive does not cover through 2026-11-19 23:59 UTC")
    gaps=[(a[0],b[0]) for a,b in zip(m1,m1[1:]) if b[0]-a[0]!=60000]
    tf_bars=resample_m1(m1,TIMEFRAMES[tf])
    # Keep only fully formed bars; incomplete resample buckets are never used.
    tf_bars=[b for b in tf_bars if b[5]==TIMEFRAMES[tf]]
    candidates=simulate(m1,tf_bars,tf,2.,funding)
    train=select_period(candidates,"train")
    train_pf={config_key(c):score_metrics([x for x in train if x["config"]==c]) for c in configurations()}
    validation=select_period(candidates,"validation",train_pf)
    oos=select_period(candidates,"oos",train_pf)
    rows=[]
    for c in configurations():
        row=asdict(c)
        for name,data in (("train",train),("validation",validation),("oos",oos)):
            selected=[x for x in data if x["config"]==c]
            m=score_metrics(selected)
            for k,v in m.items(): row[name+"_"+k]=v
            stress=[dict(x,net_bps=x["net_bps"]-10.) for x in selected]
            sm=score_metrics(stress)
            for k in ("trades","win_rate","pf","net_bps","expectancy_bps","max_drawdown_bps"):
                row[name+"_slippage7_"+k]=sm[k]
        rows.append(row)
    rows.sort(key=lambda x:(x["validation_pf"],x["validation_net_bps"]),reverse=True)
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    write_csv(out/f"{symbol}_{tf}_all_config_metrics.csv",rows)
    write_csv(out/f"{symbol}_{tf}_validation_ranked.csv",[x for x in rows if x["validation_trades"]>=30])
    trade_rows=[]
    for name,data in (("train",train),("validation",validation),("oos",oos)):
        for x in data:
            y={k:v for k,v in x.items() if k!="config"}; y["period"]=name
            y.update({"atr_period":x["config"].atr_period,"impulse_atr":x["config"].impulse_atr,
                      "retracement":x["config"].retracement,"sl_buffer":x["config"].sl_buffer,"rr":x["config"].rr})
            trade_rows.append(y)
    write_csv(out/f"{symbol}_{tf}_selected_trades.csv",trade_rows)
    manifest={"symbol":symbol,"timeframe":tf,"start_utc":"2024-11-20T00:00:00Z","end_utc_exclusive":"2026-11-20T00:00:00Z",
              "configurations":len(configurations()),"m1_rows":len(m1),"m1_gap_count":len(gaps),
              "first_gaps":gaps[:100],"timeframe_bars":len(tf_bars),"candidate_trades":len(candidates),
              "selected_trades":{"train":len(train),"validation":len(validation),"oos":len(oos)},
              "source_files":[{"name":p.name,"sha256":sha256(p)} for p in files],
              "funding_files":[{"name":p.name,"sha256":sha256(p)} for p in funding_files],
              "fees_bps_per_side":FEE_BPS,"slippage_scenarios_bps_per_side":[2.,7.],
              "funding":"Binance USD-M funding rates applied within holding periods; unavailable archives are excluded and inventoried",
              "method":"Completed same-timeframe impulse candles; M1 retracement trigger; next M1 open entry; stop-first; 3 complete timeframe bars expiry",
              "status":"BACKTEST_WITH_AVAILABLE_FUNDING"}
    (out/f"{symbol}_{tf}_manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",required=True,choices=["BTCUSDT","ETHUSDT"])
    p.add_argument("--timeframe",required=True,choices=sorted(TIMEFRAMES))
    p.add_argument("--data-dir",default="/tmp/binance")
    p.add_argument("--output-dir",default="research-output")
    a=p.parse_args(); run_pair(a.symbol,a.timeframe,a.data_dir,a.output_dir)

if __name__=="__main__": main()
