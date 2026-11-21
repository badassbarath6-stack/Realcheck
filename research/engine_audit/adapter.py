"""Causal next-bar adapter for directional audit engines.

Does not simulate queue priority, maker fills, or two-venue hedge execution.
"""
from typing import Any, Callable, Mapping


def run_directional_signals(bars: list[Mapping[str, Any]], signal_fn: Callable[..., list[dict[str, Any]]],
        *, signal_kwargs: dict[str, Any] | None=None, stop_fraction: float=0.01,
        target_r: float=2.0, fee_bps_per_side: float=5.0,
        slippage_bps_per_side: float=2.0) -> list[dict[str, Any]]:
    """Signal on close, enter next bar open, stop-first on ambiguous bars.

    Long-only strategies may emit exit_long on bar i; it closes at bar i+1 open.
    Fixed fractional exits are an adapter-level evaluation policy, not a claim
    about the upstream strategy's native exit logic.
    """
    if stop_fraction<=0 or target_r<=0 or fee_bps_per_side<0 or slippage_bps_per_side<0:
        raise ValueError("invalid adapter risk/cost parameters")
    signals=signal_fn(bars,**(signal_kwargs or {}))
    if len(signals)!=len(bars):
        raise ValueError("signal function must return one record per input bar")
    trades=[]; i=0
    while i+1<len(bars):
        direction=int(signals[i].get("direction",0))
        if direction not in (-1,1):
            i+=1; continue
        entry_i=i+1; entry=float(bars[entry_i]["open"])
        if entry<=0:
            i+=1; continue
        stop=entry*(1-direction*stop_fraction)
        target=entry+direction*(entry-stop)*target_r
        exit_i=exit_price=reason=None
        for j in range(entry_i,len(bars)):
            row=bars[j]; o,h,l=float(row["open"]),float(row["high"]),float(row["low"])
            # A stop/target gap at the open takes precedence over a signal exit.
            if direction==1 and o<=stop:
                exit_i,exit_price,reason=j,o,"stop_gap"
            elif direction==-1 and o>=stop:
                exit_i,exit_price,reason=j,o,"stop_gap"
            elif direction==1 and o>=target:
                exit_i,exit_price,reason=j,o,"target_gap"
            elif direction==-1 and o<=target:
                exit_i,exit_price,reason=j,o,"target_gap"
            elif j>entry_i and (
                (direction==1 and bool(signals[j-1].get("exit_long",False))) or
                (direction==-1 and bool(signals[j-1].get("exit_short",False)))
            ):
                exit_i,exit_price,reason=j,o,"signal_exit_long" if direction==1 else "signal_exit_short"
            elif direction==1 and l<=stop:
                exit_i,exit_price,reason=j,stop,"stop"
            elif direction==-1 and h>=stop:
                exit_i,exit_price,reason=j,stop,"stop"
            elif direction==1 and h>=target:
                exit_i,exit_price,reason=j,target,"target"
            elif direction==-1 and l<=target:
                exit_i,exit_price,reason=j,target,"target"
            if exit_i is not None:
                break
        if exit_i is None:
            exit_i=len(bars)-1; exit_price=float(bars[exit_i]["close"]); reason="end_of_data"
        gross=direction*(exit_price-entry)/entry*10000
        costs=2*(fee_bps_per_side+slippage_bps_per_side)
        exit_open_ts=bars[exit_i].get("timestamp")
        exit_close_ts=bars[exit_i].get("close_timestamp")
        if reason=="end_of_data" and exit_close_ts is not None:
            exit_timestamp=exit_close_ts; precision="bar_close"
        elif reason in ("signal_exit_long","signal_exit_short"):
            exit_timestamp=exit_open_ts; precision="bar_open"
        else:
            exit_timestamp=exit_open_ts; precision="bar_interval"
        trades.append({"signal_timestamp":bars[i].get("close_timestamp",bars[i].get("timestamp")),
            "entry_timestamp":bars[entry_i].get("timestamp"),"exit_timestamp":exit_timestamp,
            "exit_bar_open_timestamp":exit_open_ts,"exit_bar_close_timestamp":exit_close_ts,
            "exit_time_precision":precision,"direction":direction,"entry":entry,"exit":exit_price,
            "exit_reason":reason,"gross_bps":gross,"net_bps":gross-costs,
            "exit_model":"adapter_fixed_fractional_stop_target"})
        i=exit_i+1
    return trades
