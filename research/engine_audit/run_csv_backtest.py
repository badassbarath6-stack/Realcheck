#!/usr/bin/env python3
"""Run audited directional mechanisms on a feature-enriched OHLCV CSV.

Signal is computed using completed bar i; entry is next bar i+1 open.
The fixed stop/target is an explicit common evaluation overlay, not the
upstream strategy's native exit rule. Specialist two-leg and L2 engines are
intentionally excluded from this candle-only runner.
"""
from __future__ import annotations
import argparse, csv, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from engines import funding_rate_mean_reversion, taker_buy_pressure_momentum
from price_action_engines import rsi_pivot_divergence, volume_range_exhaustion
from adapter import run_directional_signals

ENGINES={
    "funding_rate_mean_reversion": funding_rate_mean_reversion,
    "taker_buy_pressure_momentum": taker_buy_pressure_momentum,
    "rsi_pivot_divergence": rsi_pivot_divergence,
    "volume_range_exhaustion": volume_range_exhaustion,
}
REQUIRED=("timestamp","open","high","low","close")

def load_rows(path: Path):
    with path.open(newline="") as f:
        rows=list(csv.DictReader(f))
    if not rows: raise ValueError("input CSV is empty")
    missing=[x for x in REQUIRED if x not in rows[0]]
    if missing: raise ValueError(f"missing required columns: {missing}")
    parsed=[]
    for n,r in enumerate(rows,2):
        ts_field="timestamp" if r.get("timestamp","") not in ("",None) else "open_time"\n        if r.get(ts_field,"") in ("",None): raise ValueError(f"missing timestamp/open_time at CSV line {n}")\n        item={"timestamp":int(float(r[ts_field]))}
        for k in ("open","high","low","close"):
            item[k]=float(r[k])
        for k in ("funding_rate","buy_ratio","open_interest","taker_ls_vol_ratio",
                  "realized_vol_30d","volume"):
            if r.get(k,"") not in ("",None): item[k]=float(r[k])
        if min(item["open"],item["high"],item["low"],item["close"])<=0:
            raise ValueError(f"non-positive OHLC at CSV line {n}")
        if "buy_ratio" not in item:\n            taker=item.get("taker_buy_base_volume",item.get("taker_buy_base_asset_volume"))\n            if taker is not None and item.get("volume",0)>0:\n                item["buy_ratio"]=taker/item["volume"]\n        if "buy_ratio" in item and not 0.0<=item["buy_ratio"]<=1.0:\n            raise ValueError(f"buy_ratio must be in [0,1] at CSV line {n}")\n        if item["low"]>min(item["open"],item["close"]) or item["high"]<max(item["open"],item["close"]):
            raise ValueError(f"invalid OHLC envelope at CSV line {n}")
        parsed.append(item)
    if any(b["timestamp"]<=a["timestamp"] for a,b in zip(parsed,parsed[1:])):
        raise ValueError("timestamps must be strictly increasing")
    return parsed

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--engine",required=True,choices=sorted(ENGINES))
    p.add_argument("--stop-fraction",type=float,default=.01)
    p.add_argument("--target-r",type=float,default=2.)
    p.add_argument("--fee-bps",type=float,default=5.)
    p.add_argument("--slippage-bps",type=float,default=2.)
    a=p.parse_args()
    rows=load_rows(a.input)
    if a.engine=="volume_range_exhaustion" and any("volume" not in r for r in rows):
        raise ValueError("volume_range_exhaustion requires volume in every row")
    if a.engine=="taker_buy_pressure_momentum" and any("buy_ratio" not in r for r in rows):
        raise ValueError("taker_buy_pressure_momentum requires buy_ratio in every row")
    if a.engine=="funding_rate_mean_reversion" and any("funding_rate" not in r for r in rows):
        raise ValueError("funding_rate_mean_reversion requires point-in-time funding_rate")
    trades=run_directional_signals(rows,ENGINES[a.engine],stop_fraction=a.stop_fraction,
        target_r=a.target_r,fee_bps_per_side=a.fee_bps,slippage_bps_per_side=a.slippage_bps)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    fields=["signal_timestamp","entry_timestamp","exit_timestamp","direction","entry","exit",
            "exit_reason","gross_bps","net_bps","exit_model"]
    with a.output.open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(trades)
    gp=sum(max(0,x["net_bps"]) for x in trades); gl=-sum(min(0,x["net_bps"]) for x in trades)
    summary={"engine":a.engine,"bars":len(rows),"trades":len(trades),
        "wins":sum(x["net_bps"]>0 for x in trades),"net_bps":sum(x["net_bps"] for x in trades),
        "profit_factor":gp/gl if gl else (999. if gp else 0.),
        "expectancy_bps":sum(x["net_bps"] for x in trades)/len(trades) if trades else 0.,
        "exit_model":"adapter_fixed_fractional_stop_target",
        "not_native_exit_fidelity":True}
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
