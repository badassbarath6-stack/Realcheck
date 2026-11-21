"""Causal walk-forward trade simulator for audited signal engines.

The implementation is an independent, standard-library reimplementation of
the inspected source backtest contract: signal at completed bar i, entry at
open i+1, one position at a time, hold-bar exits and optional intrabar SL/TP.
The original source's taker fee/slippage assumptions can be selected; the
Realcheck conservative cost model is also supported.

The OOS parameter selector chooses every parameter, including SL/TP, on the
training window only. This deliberately fixes the upstream taker runner's
selection of SL/TP by comparing OOS Sharpe across separate runs.
"""
from __future__ import annotations
import calendar
import math
from datetime import datetime, timezone
from statistics import mean, stdev
from typing import Any, Callable, Mapping, Sequence


def _signal_record(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {"direction": int(value)}


def _side(value: Any) -> int:
    try:
        side=int(_signal_record(value).get("direction",0))
    except (TypeError,ValueError):
        return 0
    return side if side in (-1,1) else 0


def validate_prefix_invariance(signal_fn: Callable, bars: Sequence[Mapping[str, Any]], params: dict,
                                prefix_length: int | None=None) -> None:
    """Reject signals whose earlier outputs change when future rows are removed."""
    if len(bars)<3:
        return
    cut=prefix_length if prefix_length is not None else max(2,int(len(bars)*0.7))
    cut=min(max(2,cut),len(bars)-1)
    full=list(signal_fn(bars,params))
    prefix=list(signal_fn(bars[:cut],params))
    if len(full)!=len(bars) or len(prefix)!=cut:
        raise ValueError("signal function returned an invalid length during prefix-causality check")
    if full[:cut]!=prefix:
        raise ValueError("look-ahead detected: prefix signals changed after future rows were removed")


def run_trades(
    bars: Sequence[Mapping[str, Any]],
    signals: Sequence[Any],
    *,
    hold_bars: int=16,
    sl_pct: float | None=None,
    tp_pct: float | None=None,
    fee_bps_per_side: float=5.0,
    slippage_bps_per_side: float=2.0,
    fill_model: str="conservative",
) -> list[dict[str, Any]]:
    """Simulate source-style next-open entries and hold/SL/TP/signal exits.

    fill_model='source_compatible' uses the inspected upstream behavior:
    entry and time-exit slippage, but SL/TP fills exactly at the level and no
    explicit gap improvement/worsening. 'conservative' additionally handles
    stop gaps at the open and applies adverse slippage to all level exits.
    """
    n=len(bars)
    if len(signals)!=n:
        raise ValueError("signals must align one-to-one with bars")
    if hold_bars<1 or fee_bps_per_side<0 or slippage_bps_per_side<0:
        raise ValueError("invalid hold/cost parameters")
    if sl_pct is not None and not 0<sl_pct<1:
        raise ValueError("sl_pct must be between 0 and 1")
    if tp_pct is not None and not 0<tp_pct<1:
        raise ValueError("tp_pct must be between 0 and 1")
    if fill_model not in ("source_compatible","conservative"):
        raise ValueError("unknown fill_model")
    slip=slippage_bps_per_side/10000.0
    trades=[]
    last_exit_bar=-1
    for signal_i in range(n):
        side=_side(signals[signal_i])
        if side==0 or signal_i<=last_exit_bar:
            continue
        entry_i=signal_i+1
        if entry_i>=n:
            break
        raw_entry=float(bars[entry_i]["open"])
        if raw_entry<=0:
            continue
        entry=raw_entry*(1+slip if side==1 else 1-slip)
        stop=entry*(1-sl_pct) if side==1 and sl_pct is not None else (
            entry*(1+sl_pct) if side==-1 and sl_pct is not None else None)
        target=entry*(1+tp_pct) if side==1 and tp_pct is not None else (
            entry*(1-tp_pct) if side==-1 and tp_pct is not None else None)

        exit_i=None
        exit_price=None
        reason=None
        exit_precision=None
        last_blocked_bar=None

        # Native signal exits (e.g. the long-only round-level source) are
        # evaluated at the next bar open, not on the signal bar close.
        for j in range(entry_i,n):
            row=bars[j]
            op=float(row["open"]); hi=float(row["high"]); lo=float(row["low"])
            if fill_model=="conservative" and stop is not None:
                if side==1 and op<=stop:
                    exit_i=j; exit_price=op*(1-slip); reason="stop_gap"; exit_precision="bar_open"
                elif side==-1 and op>=stop:
                    exit_i=j; exit_price=op*(1+slip); reason="stop_gap"; exit_precision="bar_open"
            if exit_i is not None:
                last_blocked_bar=j
                break

            if j>entry_i:
                prior=_signal_record(signals[j-1])
                exit_flag=bool(prior.get("exit_long")) if side==1 else bool(prior.get("exit_short"))
                if exit_flag:
                    exit_i=j
                    exit_price=op*(1-slip if side==1 else 1+slip)
                    reason="signal_exit_long" if side==1 else "signal_exit_short"
                    exit_precision="bar_open"
                    last_blocked_bar=j-1
                    break

            # Conservative stop-first handling for bars touching both levels.
            stop_hit=(stop is not None and ((side==1 and lo<=stop) or (side==-1 and hi>=stop)))
            if stop_hit:
                exit_i=j
                exit_price=stop*(1-slip if side==1 and fill_model=="conservative" else
                                 1+slip if side==-1 and fill_model=="conservative" else 1.0)
                reason="stop"; exit_precision="bar_interval"; last_blocked_bar=j
                break

            target_hit=(target is not None and ((side==1 and hi>=target) or (side==-1 and lo<=target)))
            if target_hit:
                exit_i=j
                exit_price=target*(1-slip if side==1 and fill_model=="conservative" else
                                   1+slip if side==-1 and fill_model=="conservative" else 1.0)
                reason="take_profit"; exit_precision="bar_interval"; last_blocked_bar=j
                break

            # Source hold horizon: the position is closed at open(entry+hold).
            if j>=min(entry_i+hold_bars-1,n-2):
                exit_i=min(entry_i+hold_bars,n-1)
                exit_price=float(bars[exit_i]["open"])*(1-slip if side==1 else 1+slip)
                reason="hold"; exit_precision="bar_open"
                last_blocked_bar=exit_i-1
                break

        if exit_i is None:
            exit_i=n-1
            exit_price=float(bars[exit_i]["open"])*(1-slip if side==1 else 1+slip)
            reason="end_of_data"; exit_precision="bar_open"
            last_blocked_bar=exit_i-1

        gross=side*(exit_price-entry)/entry*10000.0
        fees=2.0*fee_bps_per_side
        net=gross-fees
        signal_close=bars[signal_i].get("close_timestamp",bars[signal_i].get("timestamp"))
        trades.append({
            "signal_timestamp":signal_close,
            "entry_timestamp":bars[entry_i].get("timestamp"),
            "exit_timestamp":bars[exit_i].get("timestamp"),
            "exit_bar_close_timestamp":bars[exit_i].get("close_timestamp"),
            "exit_time_precision":exit_precision,
            "entry_bar_index":entry_i,
            "exit_bar_index":exit_i,
            "direction":side,
            "entry_price":entry,
            "exit_price":exit_price,
            "gross_bps":gross,
            "commission_bps":fees,
            "net_bps":net,
            "exit_reason":reason,
            "hold_actual":max(0,exit_i-entry_i+(1 if exit_precision=="bar_interval" else 0)),
            "fill_model":fill_model,
        })
        last_exit_bar=last_blocked_bar if last_blocked_bar is not None else exit_i
    return trades


def trades_to_equity(n_bars: int, trades: Sequence[Mapping[str, Any]]) -> list[float]:
    """Add each trade's net return at its exit bar, matching source equity logic."""
    changes=[0.0]*n_bars
    for trade in trades:
        i=int(trade["exit_bar_index"])
        if 0<=i<n_bars:
            changes[i]+=float(trade["net_bps"])/10000.0
    equity=[]; running=0.0
    for value in changes:
        running+=value
        equity.append(running)
    return equity


def _sharpe(equity: Sequence[float], periods_per_year: float) -> float:
    changes=[equity[i]-equity[i-1] for i in range(1,len(equity))]
    if len(changes)<2:
        return -999.0
    sd=stdev(changes)
    if sd==0:
        return -999.0
    return mean(changes)/sd*math.sqrt(periods_per_year)


def _add_months(dt: datetime, months: int) -> datetime:
    month0=dt.month-1+months
    year=dt.year+month0//12
    month=month0%12+1
    day=min(dt.day,calendar.monthrange(year,month)[1])
    return dt.replace(year=year,month=month,day=day)


def _timestamp(dt: datetime) -> int:
    return int(dt.timestamp()*1000)


def make_walk_forward_windows(
    bars: Sequence[Mapping[str, Any]], *, train_months: int=6,
    test_months: int=2, step_months: int=2,
) -> list[dict[str,int]]:
    if not bars:
        return []
    start=datetime.fromtimestamp(int(bars[0]["timestamp"])/1000,tz=timezone.utc)
    end=datetime.fromtimestamp(int(bars[-1]["timestamp"])/1000,tz=timezone.utc)
    windows=[]
    cursor=start
    while True:
        train_end=_add_months(cursor,train_months)
        test_end=_add_months(train_end,test_months)
        if test_end>end:
            break
        windows.append({"train_start":_timestamp(cursor),"train_end":_timestamp(train_end),
                        "test_start":_timestamp(train_end),"test_end":_timestamp(test_end)})
        cursor=_add_months(cursor,step_months)
    return windows


def walk_forward(
    bars: Sequence[Mapping[str, Any]],
    signal_fn: Callable[[Sequence[Mapping[str, Any]],dict],Sequence[Any]],
    parameter_grid: Sequence[dict[str,Any]],
    *,
    timeframe: str,
    train_months: int=6,
    test_months: int=2,
    step_months: int=2,
    min_train_trades: int=10,
    fee_bps_per_side: float=5.0,
    slippage_bps_per_side: float=2.0,
    fill_model: str="conservative",
    check_prefix: bool=True,
) -> dict[str,Any]:
    """Train-only parameter selection with contiguous out-of-sample windows.

    Signal arrays are calculated once on the full chronological dataset per
    parameter set. Every signal remains causal; this retains indicator warm-up
    across walk-forward boundaries without using future observations.
    """
    if timeframe not in {"1m","5m","15m","30m","1h","2h","4h"}:
        raise ValueError("unsupported timeframe")
    if any(b["timestamp"]<=a["timestamp"] for a,b in zip(bars,bars[1:])):
        raise ValueError("bar timestamps must be strictly increasing")
    if not parameter_grid:
        raise ValueError("parameter_grid cannot be empty")
    periods={"1m":252*24*60,"5m":252*24*12,"15m":252*24*4,
             "30m":252*24*2,"1h":252*24,"2h":252*12,"4h":252*6}[timeframe]
    all_signals=[]
    for params in parameter_grid:
        sig=list(signal_fn(bars,params))
        if len(sig)!=len(bars):
            raise ValueError("signal_fn output length does not match bars")
        if check_prefix:
            validate_prefix_invariance(signal_fn,bars,params)
        all_signals.append(sig)

    windows=make_walk_forward_windows(bars,train_months=train_months,
        test_months=test_months,step_months=step_months)
    if not windows:
        raise ValueError("not enough history for a complete walk-forward window")
    times=[int(row["timestamp"]) for row in bars]
    import bisect
    all_oos_trades=[]
    oos_changes=[0.0]*len(bars)
    oos_bar_indices=[]
    window_rows=[]
    for wi,window in enumerate(windows):
        tr0=bisect.bisect_left(times,window["train_start"])
        tr1=bisect.bisect_left(times,window["train_end"])
        te0=bisect.bisect_left(times,window["test_start"])
        te1=bisect.bisect_left(times,window["test_end"])
        train_bars=bars[tr0:tr1]
        test_bars=bars[te0:te1]
        best_score=-999.0
        best_params=parameter_grid[0]
        best_pi=0
        best_train_trades=[]
        for pi,params in enumerate(parameter_grid):
            train_signals=all_signals[pi][tr0:tr1]
            hold=int(params.get("hold_bars",16))
            sl=params.get("sl_pct")
            tp=params.get("tp_pct")
            trades=run_trades(train_bars,train_signals,hold_bars=hold,sl_pct=sl,tp_pct=tp,
                fee_bps_per_side=fee_bps_per_side,slippage_bps_per_side=slippage_bps_per_side,
                fill_model=fill_model)
            if len(trades)<min_train_trades:
                score=-999.0
            else:
                eq=trades_to_equity(len(train_bars),trades)
                score=_sharpe(eq,periods)
            if score>best_score:
                best_score=score; best_params=params; best_pi=pi; best_train_trades=trades
        pi=best_pi
        test_signals=all_signals[pi][te0:te1]
        test_trades=run_trades(test_bars,test_signals,
            hold_bars=int(best_params.get("hold_bars",16)),
            sl_pct=best_params.get("sl_pct"),tp_pct=best_params.get("tp_pct"),
            fee_bps_per_side=fee_bps_per_side,slippage_bps_per_side=slippage_bps_per_side,
            fill_model=fill_model)
        oos_bar_indices.extend(range(te0,te1))
        for trade in test_trades:
            trade["window_index"]=wi
            trade["params"]=dict(best_params)
            global_exit=te0+int(trade["exit_bar_index"])
            if 0<=global_exit<len(oos_changes):
                oos_changes[global_exit]+=float(trade["net_bps"])/10000.0
            trade["exit_bar_index_global"]=global_exit
        all_oos_trades.extend(test_trades)
        window_rows.append({
            **window,"train_bars":len(train_bars),"test_bars":len(test_bars),
            "best_train_sharpe":best_score,"best_params":dict(best_params),
            "train_trades":len(best_train_trades),"oos_trades":len(test_trades),
            "oos_net_bps":sum(x["net_bps"] for x in test_trades),
        })
    oos_equity=[]; running=0.0
    for x in oos_changes:
        running+=x; oos_equity.append(running)
    net=[float(x["net_bps"]) for x in all_oos_trades]
    gp=sum(x for x in net if x>0); gl=-sum(x for x in net if x<0)
    peak=0.0; running=0.0; max_dd=0.0
    for x in oos_changes:
        running+=x; peak=max(peak,running); max_dd=max(max_dd,peak-running)
    oos_series=[]; oos_running=0.0
    for index in oos_bar_indices:
        oos_running+=oos_changes[index]
        oos_series.append(oos_running)
    summary={
        "sharpe":_sharpe(oos_series,periods),
        "trades":len(net),"wins":sum(x>0 for x in net),"losses":sum(x<=0 for x in net),
        "win_rate":sum(x>0 for x in net)/len(net) if net else 0.0,
        "gross_profit_bps":gp,"gross_loss_bps":gl,
        "profit_factor":gp/gl if gl else (999.0 if gp else 0.0),
        "net_bps":sum(net),"expectancy_bps":sum(net)/len(net) if net else 0.0,
        "max_drawdown_bps":max_dd,"oos_windows":len(window_rows),
        "annualization_periods":periods,"fee_bps_per_side":fee_bps_per_side,
        "slippage_bps_per_side":slippage_bps_per_side,"fill_model":fill_model,
    }
    return {"summary":summary,"trades":all_oos_trades,"windows":window_rows,
            "equity":oos_equity}
