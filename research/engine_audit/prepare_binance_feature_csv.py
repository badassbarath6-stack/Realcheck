#!/usr/bin/env python3
"""Build causal Binance OHLCV/taker-flow/funding feature CSV.

Binance UM M1 kline fields:
open_time, open, high, low, close, volume, close_time, quote_volume,
trade_count, taker_buy_base_volume, taker_buy_quote_volume, ignore.

Funding observations are backward-as-of joined to the OPEN time of each
resampled candle, matching the inspected source data_loader's merge_asof
semantics. The funding signal engine applies its own one-bar lag.
"""
from __future__ import annotations
import argparse, csv, json, math, zipfile
from pathlib import Path
from typing import Iterable


def _csv_rows(path: Path):
    if path.suffix.lower()==".zip":
        with zipfile.ZipFile(path) as z:
            members=[n for n in z.namelist() if n.lower().endswith(".csv")]
            if len(members)!=1:
                raise ValueError(f"{path}: expected exactly one CSV member, found {len(members)}")
            with z.open(members[0]) as raw:
                import io
                with io.TextIOWrapper(raw,encoding="utf-8-sig",newline="") as f:
                    yield from csv.reader(f)
    else:
        with path.open(encoding="utf-8-sig",newline="") as f:
            yield from csv.reader(f)


def load_klines(paths: Iterable[Path]):
    rows={}
    for path in sorted(paths):
        for line,row in enumerate(_csv_rows(path),1):
            if not row or len(row)<10 or not row[0].strip().lstrip("-").isdigit():
                continue
            try:
                open_ms=int(row[0]); o,h,l,c,volume=map(float,row[1:6])
                close_ms=int(row[6]) if len(row)>6 and row[6].strip().isdigit() else open_ms+59999
                taker=float(row[9])
            except (ValueError,IndexError) as exc:
                raise ValueError(f"{path}:{line}: malformed Binance kline row") from exc
            if not all(math.isfinite(x) for x in (o,h,l,c,volume,taker)):
                raise ValueError(f"{path}:{line}: non-finite kline value")
            if min(o,h,l,c)<=0 or volume<0 or taker<0 or taker>volume+1e-9:
                raise ValueError(f"{path}:{line}: invalid OHLCV/taker volume")
            if l>min(o,c) or h<max(o,c) or h<l or close_ms<open_ms:
                raise ValueError(f"{path}:{line}: invalid OHLC envelope/time")
            item=(open_ms,close_ms,o,h,l,c,volume,taker)
            old=rows.get(open_ms)
            if old is not None and old!=item:
                raise ValueError(f"conflicting duplicate kline at {open_ms}")
            rows[open_ms]=item
    if not rows:
        raise ValueError("no Binance M1 kline rows were found")
    return [rows[t] for t in sorted(rows)]


def load_funding(paths: Iterable[Path]):
    rates={}
    timestamp_names={"fundingtime","funding_time","calc_time","timestamp","time"}
    rate_names={"fundingrate","funding_rate","last_funding_rate","rate"}
    for path in sorted(paths):
        ts_idx=rate_idx=None
        for line,row in enumerate(_csv_rows(path),1):
            if not row:
                continue
            names=[x.strip().lower() for x in row]
            if ts_idx is None:
                ti=next((i for i,x in enumerate(names) if x in timestamp_names),None)
                ri=next((i for i,x in enumerate(names) if x in rate_names),None)
                if ti is not None and ri is not None:
                    ts_idx,rate_idx=ti,ri
                    continue
            if ts_idx is None:
                ts_idx,rate_idx=0,(2 if len(row)>=3 else 1)
            if max(ts_idx,rate_idx)>=len(row) or not row[ts_idx].strip().lstrip("-").isdigit():
                continue
            try:
                ts=int(row[ts_idx]); rate=float(row[rate_idx])
            except (ValueError,IndexError):
                continue
            if not math.isfinite(rate):
                raise ValueError(f"{path}:{line}: non-finite funding rate")
            if ts in rates and rates[ts]!=rate:
                raise ValueError(f"conflicting funding rates at timestamp {ts}")
            rates[ts]=rate
    if not rates:
        raise ValueError("funding files were supplied but no valid funding observations were found")
    return sorted(rates.items())


def resample_klines(klines, timeframe_minutes: int, *, strict=True):
    if timeframe_minutes not in (1,5,15,30,60,120,240):
        raise ValueError("unsupported timeframe_minutes")
    width=timeframe_minutes*60000
    groups={}
    for row in klines:
        bucket=(row[0]//width)*width
        groups.setdefault(bucket,[]).append(row)
    out=[]
    for bucket,group in sorted(groups.items()):
        group.sort(key=lambda x:x[0])
        if strict:
            if len(group)!=timeframe_minutes:
                raise ValueError(f"incomplete {timeframe_minutes}m bucket at {bucket}: {len(group)} M1 bars")
            expected=[bucket+i*60000 for i in range(timeframe_minutes)]
            if [x[0] for x in group]!=expected:
                raise ValueError(f"non-contiguous M1 bars inside bucket {bucket}")
        first,last=group[0],group[-1]
        out.append((bucket,last[1],first[2],max(x[3] for x in group),
            min(x[4] for x in group),last[5],sum(x[6] for x in group),sum(x[7] for x in group)))
    return out


def build_feature_csv(klines, funding, output: Path, *, timeframe_minutes=1, strict_continuity=True):
    if strict_continuity:
        gaps=[(a[0],b[0]) for a,b in zip(klines,klines[1:]) if b[0]-a[0]!=60000]
        if gaps:
            raise ValueError(f"M1 continuity failed: {len(gaps)} gaps; first gap {gaps[0]}")
    bars=resample_klines(klines,timeframe_minutes,strict=strict_continuity)
    funding_times=[x[0] for x in funding]
    funding_values=[x[1] for x in funding]
    fields=["timestamp","close_timestamp","open","high","low","close","volume",
            "taker_buy_base_volume","buy_ratio"]
    if funding:
        fields.append("funding_rate")
    output.parent.mkdir(parents=True,exist_ok=True)
    funding_idx=0
    last_rate=0.0
    max_funding_age=0
    with output.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields)
        writer.writeheader()
        for open_ms,close_ms,o,h,l,c,volume,taker in bars:
            if funding:
                while funding_idx<len(funding_times) and funding_times[funding_idx]<=open_ms:
                    last_rate=funding_values[funding_idx]
                    funding_idx+=1
                if funding_idx:
                    age=open_ms-funding_times[funding_idx-1]
                    max_funding_age=max(max_funding_age,age)
            ratio=taker/volume if volume>0 else 0.5
            row={"timestamp":open_ms,"close_timestamp":close_ms,"open":o,"high":h,
                 "low":l,"close":c,"volume":volume,"taker_buy_base_volume":taker,
                 "buy_ratio":ratio}
            if funding:
                row["funding_rate"]=last_rate
            writer.writerow(row)
    return {"m1_rows":len(klines),"bars":len(bars),"timeframe_minutes":timeframe_minutes,
            "first_open_ms":bars[0][0],"last_open_ms":bars[-1][0],
            "m1_gaps":sum(1 for a,b in zip(klines,klines[1:]) if b[0]-a[0]!=60000),
            "funding_observations":len(funding),"max_funding_age_ms":max_funding_age,
            "output":str(output)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--klines-dir",type=Path,required=True)
    p.add_argument("--funding-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--timeframe",choices=("1m","5m","15m","30m","1h","2h","4h"),default="1m")
    p.add_argument("--allow-gaps",action="store_true")
    a=p.parse_args()
    kline_paths=list(a.klines_dir.glob("*.zip"))+list(a.klines_dir.glob("*.csv"))
    funding_paths=[]
    if a.funding_dir:
        funding_paths=list(a.funding_dir.glob("*.zip"))+list(a.funding_dir.glob("*.csv"))
    klines=load_klines(kline_paths)
    funding=load_funding(funding_paths) if funding_paths else []
    minutes={"1m":1,"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240}[a.timeframe]
    print(json.dumps(build_feature_csv(klines,funding,a.output,
        timeframe_minutes=minutes,strict_continuity=not a.allow_gaps),indent=2))
if __name__=="__main__": main()
