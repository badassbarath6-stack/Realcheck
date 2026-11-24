#!/usr/bin/env python3
"""Three-year checksum-verified Binance USD-M 1m download; aggregate complete MTF candles."""
import csv, hashlib, io, json, re, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BASE = "https://data.binance.vision/data/futures/um"
START = datetime(2023, 11, 24, tzinfo=timezone.utc)
END = datetime(2026, 11, 24, tzinfo=timezone.utc)
START_MS, END_MS = int(START.timestamp()*1000), int(END.timestamp()*1000)
SYMBOLS = ("BTCUSDT", "ETHUSDT")
TFS = {"5m":5, "15m":15, "30m":30, "1h":60, "4h":240}
ROOT = Path("user_data/data/binance/futures")
CACHE = Path("/tmp/binance-vision-archives")

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()

def verified(url):
    p=CACHE/url.rsplit("/",1)[-1]; p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        req=urllib.request.Request(url,headers={"User-Agent":"RealcheckHistoricalResearch/1.0"})
        with urllib.request.urlopen(req,timeout=180) as r,p.open("wb") as o:
            while True:
                b=r.read(1<<20)
                if not b: break
                o.write(b)
    with urllib.request.urlopen(url+".CHECKSUM",timeout=60) as r:
        raw=r.read().decode("utf-8","replace")
    m=re.search(r"\b([0-9a-fA-F]{64})\b",raw)
    if not m or digest(p).lower()!=m.group(1).lower():
        p.unlink(missing_ok=True); raise RuntimeError(f"Checksum verification failed: {url}")
    return p

def urls(symbol):
    out=[]
    y,m=2023,11
    while (y,m)<=(2026,10):
        name=f"{symbol}-1m-{y}-{m:02d}.zip"
        out.append(f"{BASE}/monthly/klines/{symbol}/1m/{name}")
        m+=1
        if m==13:y,m=y+1,1
    for day in range(1,24):
        name=f"{symbol}-1m-2026-11-{day:02d}.zip"
        out.append(f"{BASE}/daily/klines/{symbol}/1m/{name}")
    return out

def build(symbol):
    current={}
    for n,url in enumerate(urls(symbol),1):
        p=verified(url)
        with zipfile.ZipFile(p) as z:
            csvname=next(x for x in z.namelist() if x.lower().endswith(".csv"))
            with z.open(csvname) as raw:
                for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8")):
                    if not row or not row[0].isdigit(): continue
                    ts=int(row[0])
                    if ts<START_MS or ts>=END_MS: continue
                    o,h,l,c,v=map(float,row[1:6])
                    if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or h<l or v<0:
                        raise RuntimeError(f"Invalid candle {symbol}: {row[:6]}")
                    for tf,mins in TFS.items():
                        step=mins*60_000; bucket=ts//step*step; key=(tf,bucket)
                        x=current.get(key)
                        if x is None: current[key]=[o,h,l,c,v,1]
                        else: x[1]=max(x[1],h); x[2]=min(x[2],l); x[3]=c; x[4]+=v; x[5]+=1
        print(f"{symbol}: verified {n}/{len(urls(symbol))} archives",flush=True)
    ROOT.mkdir(parents=True,exist_ok=True); counts={}
    for tf,mins in TFS.items():
        rows=[(ts,*x[:5]) for (t,ts),x in current.items() if t==tf and x[5]==mins]
        rows.sort(key=lambda x:x[0])
        frame=pd.DataFrame(rows,columns=["date","open","high","low","close","volume"])
        frame["date"]=pd.to_datetime(frame.date,unit="ms",utc=True)
        expected=(END_MS-START_MS)//(mins*60_000)
        if len(frame)!=expected: raise RuntimeError(f"{symbol} {tf}: expected {expected} complete bars, got {len(frame)}")
        frame.to_feather(ROOT/f"{symbol[:-4]}_USDT-{tf}-futures.feather")
        counts[tf]=len(frame)
        print(f"{symbol} {tf}: {len(frame):,} bars",flush=True)
    return counts

if __name__=="__main__":
    counts={s:build(s) for s in SYMBOLS}
    Path("three-year-results").mkdir(exist_ok=True)
    Path("three-year-results/data_manifest.json").write_text(json.dumps({
        "source":"Binance Vision USD-M 1m monthly/daily archives","sha256_verified":True,
        "start_inclusive":START.isoformat(),"end_exclusive":END.isoformat(),
        "symbols":list(SYMBOLS),"timeframes":counts
    },indent=2))
