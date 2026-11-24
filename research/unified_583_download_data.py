#!/usr/bin/env python3
"""Build checksum-verified, three-year Binance USD-M multi-timeframe OHLCV."""
import csv, hashlib, io, json, re, urllib.request, zipfile
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BASE="https://data.binance.vision/data/futures/um"
START=datetime(2023,11,24,tzinfo=timezone.utc)
# Binance daily archive for 2026-11-23 was not yet published at run time.
# Use all verified archives through 2026-11-22; this is the latest complete day.
END=datetime(2026,11,23,tzinfo=timezone.utc)
START_MS,END_MS=int(START.timestamp()*1000),int(END.timestamp()*1000)
SYMBOLS=("BTCUSDT","ETHUSDT")
TFS={"5m":"5min","15m":"15min","30m":"30min","1h":"1h","4h":"4h"}
ROOT=Path("user_data/data/binance/futures")
CACHE=Path("/tmp/binance-vision-archives")

def digest(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def verified(url):
    p=CACHE/url.rsplit("/",1)[-1];p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():
        req=urllib.request.Request(url,headers={"User-Agent":"RealcheckHistoricalResearch/1.0"})
        with urllib.request.urlopen(req,timeout=180) as r,p.open("wb") as o:
            while True:
                b=r.read(1<<20)
                if not b:break
                o.write(b)
    with urllib.request.urlopen(url+".CHECKSUM",timeout=60) as r:raw=r.read().decode("utf-8","replace")
    m=re.search(r"\b([0-9a-fA-F]{64})\b",raw)
    if not m or digest(p).lower()!=m.group(1).lower():
        p.unlink(missing_ok=True);raise RuntimeError(f"Checksum verification failed: {url}")
    return p

def urls(symbol):
    out=[];y,m=2023,11
    while (y,m)<=(2026,10):
        name=f"{symbol}-1m-{y}-{m:02d}.zip"
        out.append(f"{BASE}/monthly/klines/{symbol}/1m/{name}")
        m+=1
        if m==13:y,m=y+1,1
    for day in range(1,23):
        name=f"{symbol}-1m-2026-11-{day:02d}.zip"
        out.append(f"{BASE}/daily/klines/{symbol}/1m/{name}")
    return out

def build(symbol):
    frames=[]
    archive_urls=urls(symbol)
    for n,url in enumerate(archive_urls,1):
        p=verified(url)
        with zipfile.ZipFile(p) as z:
            csvname=next(x for x in z.namelist() if x.lower().endswith(".csv"))
            with z.open(csvname) as raw:
                for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8")):
                    if not row or not row[0].isdigit():continue
                    ts=int(row[0])
                    if ts<START_MS or ts>=END_MS:continue
                    o,h,l,c,v=map(float,row[1:6])
                    if min(o,h,l,c)<=0 or l>min(o,c) or h<max(o,c) or h<l or v<0:
                        raise RuntimeError(f"Invalid candle {symbol}: {row[:6]}")
                    frames.append((ts,o,h,l,c,v))
        print(f"{symbol}: checksum-verified archive {n}/{len(archive_urls)}",flush=True)
    minute=pd.DataFrame(frames,columns=["timestamp","open","high","low","close","volume"])
    minute=minute.drop_duplicates("timestamp").sort_values("timestamp")
    minute.index=pd.to_datetime(minute.pop("timestamp"),unit="ms",utc=True)
    minute=minute[~minute.index.duplicated(keep="last")]
    expected_minutes=(END_MS-START_MS)//60_000
    if len(minute)!=expected_minutes:
        raise RuntimeError(f"{symbol}: expected {expected_minutes} one-minute candles, got {len(minute)}; missing archive/candle coverage")
    ROOT.mkdir(parents=True,exist_ok=True);counts={}
    for tf,rule in TFS.items():
        bars=minute.resample(rule,origin="epoch",label="left",closed="left").agg(
            {"open":"first","high":"max","low":"min","close":"last","volume":"sum"})
        bars=bars.dropna()
        mins={"5m":5,"15m":15,"30m":30,"1h":60,"4h":240}[tf]
        expected=(END_MS-START_MS)//(mins*60_000)
        if len(bars)!=expected:raise RuntimeError(f"{symbol} {tf}: expected {expected} bars, got {len(bars)}")
        bars.reset_index(names="date").to_feather(ROOT/f"{symbol[:-4]}_USDT-{tf}-futures.feather")
        # Freqtrade futures pair notation BTC/USDT:USDT maps to BTC_USDT_USDT.
        bars.reset_index(names="date").to_feather(ROOT/f"{symbol[:-4]}_USDT_USDT-{tf}-futures.feather")
        counts[tf]=len(bars);print(f"{symbol} {tf}: {len(bars):,} complete bars",flush=True)
    return counts

if __name__=="__main__":
    counts={s:build(s) for s in SYMBOLS}
    Path("three-year-results").mkdir(exist_ok=True)
    Path("three-year-results/data_manifest.json").write_text(json.dumps({
      "source":"Binance Vision USD-M 1m monthly/daily archives","sha256_verified":True,
      "start_inclusive":START.isoformat(),"end_exclusive":END.isoformat(),
      "coverage_note":"Latest complete UTC day available when prepared; 2026-11-23 daily archive was not yet published.",
      "symbols":list(SYMBOLS),"timeframes":counts},indent=2))
