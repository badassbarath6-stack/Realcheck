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
    previous=None
    for i,row in enumerate(rows):
        if "timestamp" not in row:
            raise ValueError(f"row {i} missing timestamp")
        if previous is not None and row["timestamp"]<=previous:
            raise ValueError("timestamps must be strictly increasing")
        previous=row["timestamp"]
        for key in required:
            if _num(row,key) is None:
                raise ValueError(f"row {i} missing or invalid {key}")


def _rolling_max(values: Sequence[float | None], window: int, min_periods: int=1) -> list[float | None]:
    q: deque[int]=deque()
    out=[]
    valid=0
    for i,value in enumerate(values):
        expired=i-window
        if expired>=0 and values[expired] is not None:
            valid-=1
        while q and q[0]<=expired:
            q.popleft()
        if value is not None:
            valid+=1
            while q and values[q[-1]] is not None and values[q[-1]]<=value:
                q.pop()
            q.append(i)
        out.append(values[q[0]] if valid>=min_periods and q else None)
    return out


def _rolling_mean_std(values: Sequence[float | None], window: int, min_periods: int):
    q: deque[float]=deque()
    total=0.0
    total_sq=0.0
    means=[]; stds=[]
    for value in values:
        if value is not None:
            x=float(value)
            q.append(x); total+=x; total_sq+=x*x
        else:
            q.append(float("nan"))
        if len(q)>window:
            old=q.popleft()
            if old==old:
                total-=old; total_sq-=old*old
        count=sum(1 for x in q if x==x) if len(q)<=window else 0
        if count<min_periods:
            means.append(None); stds.append(None); continue
        mean=total/count
        means.append(mean)
        if count<2:
            stds.append(None)
        else:
            variance=max(0.0,(total_sq-total*total/count)/(count-1))
            stds.append(variance**0.5)
    return means,stds


def round_number_bounce(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Psychological round-level support bounce / resistance rejection."""
    _validate(rows,("close","low","high"))
    p=params or {}
    frac=float(p.get("level_step_frac",0.05))
    touch=float(p.get("touch_threshold",0.003))
    if frac<=0 or touch<0 or any(float(r["close"])<=0 for r in rows):
        raise ValueError("invalid round-number parameters or non-positive close")
    out=[]
    for row in rows:
        close=float(row["close"])
        step=10.0**round(log10(close*frac))
        support=floor(close/step)*step
        resistance=support+step
        tolerance=close*touch
        bounce_up=float(row["low"])<=support+tolerance and close>support+tolerance
        bounce_down=float(row["high"])>=resistance-tolerance and close<resistance-tolerance
        direction=1 if bounce_up else (-1 if bounce_down else 0)
        out.append({"timestamp":row["timestamp"],"direction":direction,"score":float(direction),
                    "mechanism":"round_number_bounce"})
    return out


def wall_pull_detector(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Detect a recently tested large bid/offer wall being pulled.

    Offer wall removal scores +1 (upward breakout hypothesis); bid wall
    removal scores -1. This preserves the upstream event-edge semantics.
    """
    _validate(rows,("close",))
    p=params or {}
    window=int(p.get("lookback",30))
    pull=float(p.get("pull_frac",0.3))
    proximity=float(p.get("prox_frac",0.001))
    if window<5 or not 0<pull<1 or proximity<0:
        raise ValueError("invalid wall-pull parameters")
    sides={}
    for side,sign in (("offer",1),("bid",-1)):
        quantities=[_num(row,f"{side}_wall_qty") for row in rows]
        prices=[_num(row,f"{side}_wall_price") for row in rows]
        peaks=_rolling_max(quantities,window,min_periods=5)
        near=[]
        for i,row in enumerate(rows):
            close=float(row["close"])
            distance=None if prices[i] is None or close<=0 else ((prices[i]-close)*sign)/close
            near.append(distance is not None and abs(distance)<proximity)
        near_rolling=[]
        near_count=0
        for i,flag in enumerate(near):
            near_count+=int(flag)
            if i>=window:
                near_count-=int(near[i-window])
            near_rolling.append(near_count>0)
        event=[]
        for i in range(len(rows)):
            qty=quantities[i]; peak=peaks[i]
            event.append(qty is not None and peak is not None and qty<pull*peak and near_rolling[i])
        edge=[event[i] and (i==0 or not event[i-1]) for i in range(len(rows))]
        sides[side]=(sign,edge)
    out=[]
    for i,row in enumerate(rows):
        score=0
        for sign,edge in sides.values():
            if edge[i]:
                score=sign
        out.append({"timestamp":row["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":float(score),"mechanism":"wall_pull"})
    return out


def book_imbalance_zscore(rows: Sequence[Mapping[str, Any]], params: dict | None=None) -> list[dict[str, Any]]:
    """Rolling z-score of log(top-N bid depth / ask depth)."""
    _validate(rows,())
    p=params or {}
    window=int(p.get("window",240))
    max_z=float(p.get("max_z",3.0))
    if window<2 or max_z<=0:
        raise ValueError("invalid book-imbalance parameters")
    ratio=[]
    for row in rows:
        bid=_num(row,"bid_total"); ask=_num(row,"offer_total")
        ratio.append(log(bid/ask) if bid is not None and ask is not None and bid>0 and ask>0 else None)
    mean,std=_rolling_mean_std(ratio,window,min_periods=min(60,window))
    out=[]
    for i,row in enumerate(rows):
        z=None if mean[i] is None or std[i] in (None,0) or ratio[i] is None else (ratio[i]-mean[i])/std[i]
        score=0.0 if z is None else max(-1.0,min(1.0,z/max_z))
        out.append({"timestamp":row["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":score,"mechanism":"book_imbalance_zscore"})
    return out


def correlation_break_recovery(rows: Sequence[Mapping[str, Any]], pair_rows: Sequence[Mapping[str, Any]],
                                params: dict | None=None) -> list[dict[str, Any]]:
    """Signal on recovery of a previously broken rolling return correlation.

    The lagging asset is identified by the relative cumulative return over the
    same lookback. Pair observations are forward-filled by timestamp only.
    """
    _validate(rows,("close",)); _validate(pair_rows,("close",))
    p=params or {}
    window=int(p.get("window",30))
    break_thr=float(p.get("break_thr",0.4))
    recovery=float(p.get("recovery_thr",0.7))
    scale=float(p.get("rel_scale",0.10))
    if window<2 or scale<=0 or not -1<=break_thr<=1 or not -1<=recovery<=1:
        raise ValueError("invalid correlation-break parameters")
    aligned=[]
    j=0; last=None
    for row in rows:
        while j<len(pair_rows) and pair_rows[j]["timestamp"]<=row["timestamp"]:
            last=float(pair_rows[j]["close"]); j+=1
        aligned.append(last)
    close_x=[float(row["close"]) for row in rows]
    ret_x=[None]+[close_x[i]/close_x[i-1]-1 if close_x[i-1]>0 else None for i in range(1,len(rows))]
    ret_y=[None]+[
        aligned[i]/aligned[i-1]-1
        if i>0 and aligned[i-1] is not None and aligned[i] is not None and aligned[i-1]>0
        else None for i in range(1,len(rows))
    ]
    corr=[None]*len(rows)
    pair_window: deque[tuple[float,float] | None]=deque()
    sx=sy=sxx=syy=sxy=0.0
    count=0
    for i,(a,b) in enumerate(zip(ret_x,ret_y)):
        item=(a,b) if a is not None and b is not None else None
        pair_window.append(item)
        if item is not None:
            ax,by=item; sx+=ax; sy+=by; sxx+=ax*ax; syy+=by*by; sxy+=ax*by; count+=1
        if len(pair_window)>window:
            old=pair_window.popleft()
            if old is not None:
                ax,by=old; sx-=ax; sy-=by; sxx-=ax*ax; syy-=by*by; sxy-=ax*by; count-=1
        if len(pair_window)==window and count==window:
            vx=sxx-sx*sx/count; vy=syy-sy*sy/count
            if vx>0 and vy>0:
                cov=sxy-sx*sy/count
                corr[i]=cov/(vx*vy)**0.5
    min_q: deque[int]=deque()
    corr_count=0
    out=[]; conditions=[]
    for i,row in enumerate(rows):
        expired=i-window
        if expired>=0 and corr[expired] is not None:
            corr_count-=1
        while min_q and min_q[0]<=expired:
            min_q.popleft()
        value=corr[i]
        if value is not None:
            corr_count+=1
            while min_q and corr[min_q[-1]]>=value:
                min_q.pop()
            min_q.append(i)
        was_broken=(len(min_q)>0 and corr_count==window and corr[min_q[0]]<break_thr)
        recovering=value is not None and value>recovery
        condition=was_broken and recovering
        edge=condition and (i==0 or not conditions[-1])
        conditions.append(condition)
        if i>=window and aligned[i] is not None and aligned[i-window] is not None and aligned[i-window]>0:
            relative=(close_x[i]/close_x[i-window]-1)-(aligned[i]/aligned[i-window]-1)
        else:
            relative=None
        score=0.0 if not edge or relative is None else max(-1.0,min(1.0,-relative/scale))
        out.append({"timestamp":row["timestamp"],"direction":1 if score>0 else (-1 if score<0 else 0),
                    "score":score,"mechanism":"correlation_break_recovery"})
    return out
