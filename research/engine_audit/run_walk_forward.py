#!/usr/bin/env python3
"""Run source-faithful, train-only walk-forward backtests for audited engines.

This runner is not dispatched until the 100-mechanism audit gate is met.
Input CSV must already be resampled to the strategy's native timeframe by
prepare_binance_feature_csv.py.
"""
from __future__ import annotations
import argparse, csv, itertools, json, sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from run_csv_backtest import load_rows
from engines import funding_rate_mean_reversion, taker_buy_pressure_momentum, oi_price_quadrants
from source_backtest import walk_forward

def _grid(mapping):
    keys=list(mapping)
    return [dict(zip(keys,values)) for values in itertools.product(*(mapping[k] for k in keys))]

def strategy_spec(name):
    if name=="funding_mr":
        grid=_grid({
            "ema_period":[20,50,100],
            "threshold_high":[0.0003,0.0005,0.0007],
            "threshold_low":[0.00005,0.0001,0.0002],
            "hold_bars":[8,16,32],
        })
        def signal(rows,p):
            return funding_rate_mean_reversion(rows,ema_period=p["ema_period"],
                threshold_high=p["threshold_high"],threshold_low=p["threshold_low"])
        return "15m",grid,signal,("funding_rate","buy_ratio")
    if name=="taker_momentum":
        grid=_grid({
            "ma_period":[5,15,30],
            "confirm_bars":[2,4],
            "threshold_high":[0.58,0.62,0.68],
            "atr_period":[14],
            "hold_bars":[8,16],
            "sl_pct":[0.01,0.02],
            "tp_pct":[0.02,0.035],
        })
        def signal(rows,p):
            return taker_buy_pressure_momentum(rows,ma_period=p["ma_period"],
                confirm_bars=p["confirm_bars"],threshold_high=p["threshold_high"],
                atr_period=p["atr_period"])
        return "5m",grid,signal,("buy_ratio","volume")
    if name=="oi_divergence":
        grid=_grid({
            "lookback_bars":[4,8,16,24],
            "price_threshold":[0.003,0.007,0.015],
            "oi_threshold":[0.005,0.015,0.03],
            "hold_bars":[8,16,24],
            "use_mr":[0,1],
        })
        def signal(rows,p):
            return oi_price_quadrants(rows,lookback_bars=p["lookback_bars"],
                price_threshold=p["price_threshold"],oi_threshold=p["oi_threshold"],
                use_mr=bool(p["use_mr"]))
        return "15m",grid,signal,("open_interest","taker_ls_vol_ratio")
    raise ValueError(f"unknown strategy: {name}")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--strategy",choices=("funding_mr","taker_momentum","oi_divergence"),required=True)
    p.add_argument("--symbol",required=True)
    p.add_argument("--input",type=Path,required=True)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--timeframe",choices=("5m","15m","30m","1h","4h"))
    p.add_argument("--train-months",type=int,default=6)
    p.add_argument("--test-months",type=int,default=2)
    p.add_argument("--step-months",type=int,default=2)
    p.add_argument("--min-train-trades",type=int,default=10)
    p.add_argument("--fee-bps",type=float,default=5.0)
    p.add_argument("--slippage-bps",type=float,default=2.0)
    p.add_argument("--fill-model",choices=("conservative","source_compatible"),default="conservative")
    a=p.parse_args()
    native_tf,grid,signal_fn,required=strategy_spec(a.strategy)
    timeframe=a.timeframe or native_tf
    if timeframe!=native_tf:
        raise ValueError(f"{a.strategy} source timeframe is {native_tf}; got {timeframe}")
    rows=load_rows(a.input)
    missing=[k for k in required if any(k not in r for r in rows)]
    if missing:
        raise ValueError(f"{a.strategy} requires point-in-time columns: {missing}")
    if a.strategy=="taker_momentum" and any("volume" not in r for r in rows):
        raise ValueError("taker_momentum requires total base volume")
    result=walk_forward(rows,signal_fn,grid,timeframe=timeframe,
        train_months=a.train_months,test_months=a.test_months,step_months=a.step_months,
        min_train_trades=a.min_train_trades,fee_bps_per_side=a.fee_bps,
        slippage_bps_per_side=a.slippage_bps,fill_model=a.fill_model,check_prefix=True)
    a.output_dir.mkdir(parents=True,exist_ok=True)
    summary={**result["summary"],"strategy":a.strategy,"symbol":a.symbol,
        "timeframe":timeframe,"input":str(a.input),"parameter_combinations":len(grid),
        "bars":len(rows),"first_timestamp":rows[0]["timestamp"],
        "last_timestamp":rows[-1]["timestamp"],
        "parameter_selection":"training-window Sharpe only; SL/TP included in training grid",
        "signal_causality":"prefix-invariance checked for every parameter set"}
    (a.output_dir/"summary.json").write_text(json.dumps(summary,indent=2))
    (a.output_dir/"windows.json").write_text(json.dumps(result["windows"],indent=2))
    trade_fields=["window_index","signal_timestamp","entry_timestamp","exit_timestamp",
        "exit_bar_close_timestamp","exit_time_precision","entry_bar_index","exit_bar_index",
        "exit_bar_index_global","direction","entry_price","exit_price","gross_bps",
        "commission_bps","net_bps","exit_reason","hold_actual","fill_model","params"]
    with (a.output_dir/"trades.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=trade_fields,extrasaction="ignore"); w.writeheader()
        for trade in result["trades"]:
            row=dict(trade); row["params"]=json.dumps(row.get("params",{}),sort_keys=True); w.writerow(row)
    with (a.output_dir/"equity.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(["timestamp","close_timestamp","oos_equity_fraction"])
        for row,equity in zip(rows,result["equity"]):
            w.writerow([row["timestamp"],row.get("close_timestamp"),equity])
    print(json.dumps(summary,indent=2))

if __name__=="__main__": main()
