"""Clean-room ports of MIT-licensed order-book and relative-market detectors.

Sources: stooq1/strategy-graveyard (MIT):
- trading_analyzer/detectors/walls.py
- trading_analyzer/detectors/satellite.py
- trading_analyzer/strategies/round_numbers.py

These are point-in-time score generators, not order/fill simulators. The
signal timestamp is the completed observation timestamp; a bar adapter must
execute no earlier than the next bar. L2 strategies require actual timestamped
book snapshots, not candle volume approximations.
"""
from __future__ import annotations
from collections import deque
from math import floor, isfinite, log, log10
from typing import Any, Mapping, Sequence


def _num(row: Mapping[str, Any], key: str) -> float | None:
    try:
        x=float(row[key])
        return x if isfinite(x) else None
    except (KeyError,TypeError,ValueError):
        return None


def _validate(rows: Sequence[Mapping[str, Any]], required: Sequence[str]) -> None:
    prev=None
    for i,r in enumerate(rows):
        if "timestamp" not in r:
            raise ValueError(f"row {i} missing timestamp")
        if prev is not None and r["timestamp"]<=prev:
            raise ValueError("timestamps must be strictly increasing")
        prev=r["timestamp"]
        for k in required:
            if _num(r,k) is None:
                raise ValueError(f"row {i} missing or invalid {k}")


def _rolling_max(values: Sequence[float | None], window: int, min_periods: int=1) -> list[float | None]:
    q: deque[int]=deque()
    out=[]
    valid=0
    for i,x in enumerate(values):
        while q and q[0] <= i-window:
            q.popleft()
        if x is not None:
            while q and values[q[-1]] is not None and values[q[-1]] <= x:
                q.pop()
            q.append(i)
        start=max(0,i-window+1)
        valid=sum(1 for j in range(start,i+1) if values[j] is not None)
        out.append(values[q[0]] if valid>=min_periods and q else None)
    return out


def _rolling_mean_std(values: Sequence[float | None], window: int, min_periods: int) -> tuple[list[float | None],list[float | None]]:
    means=[]; stds=[]
    for i in range(len(values)):
        xs=[float(x) for x in values[max(0,i-window+1):i+1] if x is not None]
        if len(xs)<min_periods:
            means.append(None); stds.append(None); continue
        m=sum(xs)/len(xs)
        means.append(m)
        if len(xs)<2:
            stds.append(None)
        else:
            var=sum((x-m)**2 for x in xs)/(len(xs)-1)
            stds.append(var**0.5)
    return means,stds


def round_number_bounce(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Psychological round-level support bounce / resistance rejection."""
    _validate(rows,("close","low","high"))
    p=params or {}
    frac=float(p.get("level_step_frac",0.05))
    touch=float(p.get("touch_threshold",0.003))
    if frac<=0 or touch<0:
        raise ValueError("invalid round-number parameters")
    out=[]
    for r in rows:
        close=float(r["close"])
        raw=close*frac
        step=10.0**round(log10(max(raw,1e-12)))
        support=floor(close/step)*step
        resistance=support+step
        tol=close*touch
        up=float(r["low"])<=support+tol and close>support+tol
        down=float(r["high"])>=resistance-tol and close<resistance-tol
        direction=1 if up else (-1 if down else 0)
        out.append({"timestamp":r["timestamp"],"direction":direction,"score":float(direction),
                    "mechanism":"round_number_bounce"})
    return out


def wall_pull_detector(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Detect a recently tested large bid/offer wall being pulled.

    Offer wall removal scores +1 (upward breakout hypothesis); bid wall
    removal scores -1. This preserves the upstream event-edge semantics.
    """
    keys=("close","bid_wall_price","bid_wall_qty","offer_wall_price","offer_wall_qty")
    _validate(rows,("close",))
    p=params or {}
    window=int(p.get("lookback",30))
    pull=float(p.get("pull_frac",0.3))
    prox=float(p.get("prox_frac",0.001))
    if window<5 or not 0<pull<1 or prox<0:
        raise ValueError("invalid wall-pull parameters")
    sides={}
    for side,sign in (("offer",1),("bid",-1)):
        qty=[_num(r,f"{side}_wall_qty") for r in rows]
        price=[_num(r,f"{side}_wall_price") for r in rows]
        peak=_rolling_max(qty,window,min_periods=5)
        was_near=[]
        for i,r in enumerate(rows):
            close=float(r["close"])
            d=None if price[i] is None else ((price[i]-close)*sign)/close
            near=d is not None and abs(d)<prox
            was_near.append(near)
        near_rolling=[]
        for i in range(len(rows)):
            near_rolling.append(any(was_near[max(0,i-window+1):i+1]))
        event=[]
        for i in range(len(rows)):
            q=qty[i]; pk=peak[i]
            event.append(q is not None and pk is not None and q < pull*pk and near_rolling[i])
        edge=[event[i] and (i==0 or not event[i-1]) for i in range(len(rows))]
        sides[side]=(sign,edge)
    out=[]
    for i,r in enumerate(rows):
        score=0
        for side,(sign,edge) in sides.items():
            if edge[i]: score=sign
        out.append({"timestamp":r["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":float(score),"mechanism":"wall_pull"})
    return out


def book_imbalance_zscore(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Rolling z-score of log(top-N bid depth / ask depth)."""
    _validate(rows,("timestamp",))
    p=params or {}
    window=int(p.get("window",240))
    max_z=float(p.get("max_z",3.0))
    if window<2 or max_z<=0:
        raise ValueError("invalid book-imbalance parameters")
    ratio=[]
    for r in rows:
        bid=_num(r,"bid_total"); ask=_num(r,"offer_total")
        ratio.append(log(bid/ask) if bid is not None and ask is not None and bid>0 and ask>0 else None)
    mean,std=_rolling_mean_std(ratio,window,min_periods=min(60,window))
    out=[]
    for i,r in enumerate(rows):
        z=None if mean[i] is None or std[i] in (None,0) or ratio[i] is None else (ratio[i]-mean[i])/std[i]
        score=0.0 if z is None else max(-1.0,min(1.0,z/max_z))
        out.append({"timestamp":r["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":score,"mechanism":"book_imbalance_zscore"})
    return out


def correlation_break_recovery(
    rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    params: dict | None=None,
) -> list[dict[str, Any]]:
    """Signal on recovery of a previously broken rolling return correlation.

    The lagging asset is identified by the relative cumulative return over the
    same lookback. Pair observations are forward-filled by timestamp only.
    """
    _validate(rows,("close",))
    _validate(pair_rows,("close",))
    p=params or {}
    window=int(p.get("window",30))
    break_thr=float(p.get("break_thr",0.4))
    recovery=float(p.get("recovery_thr",0.7))
    scale=float(p.get("rel_scale",0.10))
    if window<2 or scale<=0 or not -1<=break_thr<=1 or not -1<=recovery<=1:
        raise ValueError("invalid correlation-break parameters")
    aligned=[]
    j=0; last=None
    for r in rows:
        while j<len(pair_rows) and pair_rows[j]["timestamp"]<=r["timestamp"]:
            last=float(pair_rows[j]["close"]); j+=1
        aligned.append(last)
    x=[float(r["close"]) for r in rows]
    ret_x=[None]+[x[i]/x[i-1]-1 if x[i-1]>0 else None for i in range(1,len(x))]
    ret_y=[None]+[aligned[i]/aligned[i-1]-1 if i>0 and aligned[i-1] is not None and aligned[i] is not None and aligned[i-1]>0 else None for i in range(1,len(x))]
    corr=[None]*len(rows)
    for i in range(window,len(rows)):
        xs=ret_x[i-window+1:i+1]; ys=ret_y[i-window+1:i+1]
        pairs=[(a,b) for a,b in zip(xs,ys) if a is not None and b is not None]
        if len(pairs)<window:
            continue
        mx=sum(a for a,_ in pairs)/len(pairs); my=sum(b for _,b in pairs)/len(pairs)
        vx=sum((a-mx)**2 for a,_ in pairs); vy=sum((b-my)**2 for _,b in pairs)
        if vx<=0 or vy<=0: continue
        cov=sum((a-mx)*(b-my) for a,b in pairs)
        corr[i]=cov/(vx*vy)**0.5
    out=[]; cond_hist=[]
    for i,r in enumerate(rows):
        lo=max(0,i-window+1)
        hist=[v for v in corr[lo:i+1] if v is not None]
        was_broken=len(hist)>=window and min(hist)<break_thr
        recovering=corr[i] is not None and corr[i]>recovery
        condition=was_broken and recovering
        edge=condition and (i==0 or not cond_hist[-1])
        cond_hist.append(condition)
        if i>=window and aligned[i] is not None and aligned[i-window] is not None and aligned[i-window]>0:
            rel=(x[i]/x[i-window]-1)-(aligned[i]/aligned[i-window]-1)
        else:
            rel=None
        score=0.0 if not edge or rel is None else max(-1.0,min(1.0,-rel/scale))
        out.append({"timestamp":r["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":score,"mechanism":"correlation_break_recovery"})
    return out
