#!/usr/bin/env python3
"""Backward-as-of merge of Binance 5m derivatives metrics into candle CSV.

Accepted headers mirror the inspected source data_loader:
create_time, sum_open_interest, sum_taker_long_short_vol_ratio
(or normalized open_interest / taker_ls_vol_ratio names).
Each candle receives only the latest metrics observation whose timestamp is
<= that candle's OPEN time. No forward fill from future metrics is allowed.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path


def load_metrics(paths):
    rows={}
    ts_names=("create_time","timestamp","time")
    oi_names=("sum_open_interest","open_interest","sumOpenInterest")
    ls_names=("sum_taker_long_short_vol_ratio","taker_ls_vol_ratio","takerlongshortRatio")
    for path in sorted(paths):
        with path.open(encoding="utf-8-sig",newline="") as f:
            reader=csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError(f"{path}: metrics CSV needs a header")
            for line,row in enumerate(reader,2):
                lower={k.strip().lower():v for k,v in row.items() if k}
                def find(names):
                    return next((lower[n.lower()] for n in names if n.lower() in lower),None)
                ts_raw=find(ts_names); oi_raw=find(oi_names); ls_raw=find(ls_names)
                if ts_raw in (None,""):
                    continue
                try:
                    ts=int(float(ts_raw))
                    oi=float(oi_raw) if oi_raw not in (None,"") else None
                    ls=float(ls_raw) if ls_raw not in (None,"") else None
                except (TypeError,ValueError) as exc:
                    raise ValueError(f"{path}:{line}: malformed metrics row") from exc
                if oi is not None and (not math.isfinite(oi) or oi<=0):
                    raise ValueError(f"{path}:{line}: invalid open_interest")
                if ls is not None and (not math.isfinite(ls) or ls<=0):
                    raise ValueError(f"{path}:{line}: invalid taker_ls_vol_ratio")
                if oi is None and ls is None:
                    continue
                value=(oi,ls)
                if ts in rows and rows[ts]!=value:
                    raise ValueError(f"conflicting metrics at timestamp {ts}")
                rows[ts]=value
    if not rows:
        raise ValueError("no valid open-interest / taker-ratio metrics found")
    return sorted((ts,*value) for ts,value in rows.items())


def merge_metrics(candle_csv: Path, metrics, output: Path):
    with candle_csv.open(encoding="utf-8-sig",newline="") as f:
        candles=list(csv.DictReader(f))
    if not candles:
        raise ValueError("candle CSV is empty")
    if "timestamp" not in candles[0]:
        raise ValueError("candle CSV must contain timestamp")
    metric_times=[x[0] for x in metrics]
    oi_values=[]; ls_values=[]
    mi=0; last_oi=last_ls=""
    fields=list(candles[0])
    for col in ("open_interest","taker_ls_vol_ratio"):
        if col not in fields: fields.append(col)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields); writer.writeheader()
        for row in candles:
            ts=int(float(row["timestamp"]))
            while mi<len(metrics) and metric_times[mi]<=ts:
                _,oi,ls=metrics[mi]
                if oi is not None: last_oi=oi
                if ls is not None: last_ls=ls
                mi+=1
            row["open_interest"]=last_oi
            row["taker_ls_vol_ratio"]=last_ls
            writer.writerow(row)
            oi_values.append(last_oi!="")
            ls_values.append(last_ls!="")
    return {"bars":len(candles),"metrics_rows":len(metrics),
            "oi_coverage":sum(oi_values)/len(oi_values),
            "taker_ls_coverage":sum(ls_values)/len(ls_values),
            "output":str(output)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--metrics-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    paths=list(a.metrics_dir.glob("*.csv"))
    metrics=load_metrics(paths)
    print(json.dumps(merge_metrics(a.input,metrics,a.output),indent=2))
if __name__=="__main__": main()
