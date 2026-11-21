#!/usr/bin/env python3
"""Build causal Binance M1 OHLCV + taker-flow + funding feature CSV.

Kline row format follows Binance UM monthly/daily archives:
open_time, open, high, low, close, volume, close_time, quote_volume,
trade_count, taker_buy_base_volume, taker_buy_quote_volume, ignore.

Funding data accepts Binance Vision funding archives (calc_time, interval,
last_funding_rate) or CSV headers containing fundingTime/fundingRate.
Funding observations are backward-as-of joined at each candle close time:
a rate is never exposed before its funding timestamp. The directional engine
then uses its own one-bar lag, adding another conservative delay.
"""
from __future__ import annotations
import argparse, csv, json, math, zipfile
from bisect import bisect_right
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
    for path in sorted(paths):
        for line,row in enumerate(_csv_rows(path),1):
            if not row or len(row)<2:
                continue
            # Ignore header lines; Binance Vision commonly stores
            # calc_time, funding_interval_hours, last_funding_rate.
            if not row[0].strip().lstrip("-").isdigit():
                continue
            try:
                ts=int(row[0])
                if len(row)>=3:
                    rate=float(row[2])
                else:
                    rate=float(row[1])
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


def build_feature_csv(klines, funding, output: Path, *, strict_continuity=True):
    if strict_continuity:
        gaps=[(a[0],b[0]) for a,b in zip(klines,klines[1:]) if b[0]-a[0]!=60000]
        if gaps:
            raise ValueError(f"M1 continuity failed: {len(gaps)} gaps; first gap {gaps[0]}")
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
        for open_ms,close_ms,o,h,l,c,volume,taker in klines:
            if funding:
                while funding_idx<len(funding_times) and funding_times[funding_idx]<=close_ms:
                    last_rate=funding_values[funding_idx]
                    funding_idx+=1
                if funding_idx:
                    age=close_ms-funding_times[funding_idx-1]
                    max_funding_age=max(max_funding_age,age)
            ratio=taker/volume if volume>0 else 0.5
            row={"timestamp":open_ms,"close_timestamp":close_ms,"open":o,"high":h,
                 "low":l,"close":c,"volume":volume,"taker_buy_base_volume":taker,
                 "buy_ratio":ratio}
            if funding:
                row["funding_rate"]=last_rate
            writer.writerow(row)
    return {"bars":len(klines),"first_open_ms":klines[0][0],"last_open_ms":klines[-1][0],
            "m1_gaps":sum(1 for a,b in zip(klines,klines[1:]) if b[0]-a[0]!=60000),
            "funding_observations":len(funding),"max_funding_age_ms":max_funding_age,
            "output":str(output)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--klines-dir",type=Path,required=True)
    p.add_argument("--funding-dir",type=Path)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--allow-gaps",action="store_true")
    a=p.parse_args()
    kline_paths=list(a.klines_dir.glob("*.zip"))+list(a.klines_dir.glob("*.csv"))
    funding_paths=[]
    if a.funding_dir:
        funding_paths=list(a.funding_dir.glob("*.zip"))+list(a.funding_dir.glob("*.csv"))
    klines=load_klines(kline_paths)
    funding=load_funding(funding_paths) if funding_paths else []
    print(json.dumps(build_feature_csv(klines,funding,a.output,
        strict_continuity=not a.allow_gaps),indent=2))
if __name__=="__main__": main()
