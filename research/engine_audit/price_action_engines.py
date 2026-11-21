"""Clean-room ports of MIT-licensed price/volume mechanisms.

Source: stooq1/strategy-graveyard (MIT), trading_analyzer/strategies/divergence.py
and trading_analyzer/detectors/exhaustion.py. Original attribution and MIT
notice are retained in THIRD_PARTY_NOTICES.md.

Signals are emitted only on the bar when the pivot is confirmed or the
exhaustion condition is observable. The shared adapter fills at the next bar.
"""
from __future__ import annotations
import math
from typing import Any, Mapping, Sequence


def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _validate(rows: Sequence[Mapping[str, Any]], need_volume: bool = False) -> None:
    previous = None
    for i, r in enumerate(rows):
        for key in ("timestamp", "high", "low", "close"):
            if key not in r:
                raise ValueError(f"row {i} missing {key}")
        if need_volume and "volume" not in r:
            raise ValueError(f"row {i} missing volume")
        if previous is not None and r["timestamp"] <= previous:
            raise ValueError("timestamps must be strictly increasing")
        previous = r["timestamp"]
        if not all(_finite(r[k]) for k in ("high", "low", "close")):
            raise ValueError(f"row {i} has non-finite OHLC")
        if float(r["low"]) > float(r["high"]):
            raise ValueError(f"row {i} has low > high")
        if need_volume and (not _finite(r["volume"]) or float(r["volume"]) < 0):
            raise ValueError(f"row {i} has invalid volume")


def _rsi_ewm(close: Sequence[float], period: int) -> list[float]:
    """Match source Wilder-style EWM RSI (alpha=1/period, adjust=False)."""
    if period < 1:
        raise ValueError("RSI period must be >= 1")
    out = [float("nan")] * len(close)
    avg_gain = avg_loss = None
    alpha = 1.0 / period
    for i in range(1, len(close)):
        delta = float(close[i]) - float(close[i - 1])
        gain, loss = max(delta, 0.0), max(-delta, 0.0)
        if avg_gain is None:
            avg_gain, avg_loss = gain, loss
        else:
            avg_gain = alpha * gain + (1.0 - alpha) * avg_gain
            avg_loss = alpha * loss + (1.0 - alpha) * avg_loss
        if avg_loss and avg_loss > 0:
            rs = avg_gain / avg_loss
            out[i] = 100.0 - 100.0 / (1.0 + rs)
    return out


def rsi_pivot_divergence(rows: Sequence[Mapping[str, Any]], params: dict | None = None) -> list[dict[str, Any]]:
    """Confirmed RSI divergence: lower price low/higher RSI low, or inverse.

    A pivot at j is not used until j + pivot_order. This intentionally avoids
    backdating a centred-window pivot to its historical location.
    """
    _validate(rows)
    p = params or {}
    period = int(p.get("rsi_period", 14))
    order = int(p.get("pivot_order", 5))
    max_gap = int(p.get("max_pivot_gap", 60))
    if period < 1 or order < 1 or max_gap < 1:
        raise ValueError("invalid RSI divergence parameters")
    close = [float(r["close"]) for r in rows]
    rsi = _rsi_ewm(close, period)
    out = [{"timestamp":r["timestamp"],"direction":0,"strength":0.0,"mechanism":"rsi_pivot_divergence"} for r in rows]
    last_low = last_high = None
    for confirm in range(2 * order, len(rows)):
        pivot = confirm - order
        left, right = pivot - order, pivot + order + 1
        window = close[left:right]
        if close[pivot] == min(window):
            if last_low is not None:
                prev_i = last_low
                if pivot - prev_i <= max_gap and _finite(rsi[pivot]) and _finite(rsi[prev_i]):
                    if close[pivot] < close[prev_i] and rsi[pivot] > rsi[prev_i]:
                        out[confirm]["direction"] = 1
                        out[confirm]["strength"] = min(1.0, abs(close[pivot] / close[prev_i] - 1.0))
            last_low = pivot
        if close[pivot] == max(window):
            if last_high is not None:
                prev_i = last_high
                if pivot - prev_i <= max_gap and _finite(rsi[pivot]) and _finite(rsi[prev_i]):
                    if close[pivot] > close[prev_i] and rsi[pivot] < rsi[prev_i]:
                        out[confirm]["direction"] = -1
                        out[confirm]["strength"] = min(1.0, abs(close[pivot] / close[prev_i] - 1.0))
            last_high = pivot
    return out


def _rolling_mean(values: Sequence[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i-window]
        out.append(running / window if i >= window-1 else None)
    return out


def volume_range_exhaustion(rows: Sequence[Mapping[str, Any]], params: dict | None = None) -> list[dict[str, Any]]:
    """Fade a large move only when both volume and candle range are cooling."""
    _validate(rows, need_volume=True)
    p = params or {}
    lookback = int(p.get("lookback", 10))
    roc_threshold = float(p.get("roc_threshold", 0.10))
    vol_fast = int(p.get("vol_fast", 3))
    vol_slow = int(p.get("vol_slow", 10))
    if min(lookback, vol_fast, vol_slow) < 1 or roc_threshold <= 0 or vol_fast >= vol_slow:
        raise ValueError("invalid exhaustion parameters")
    close = [float(r["close"]) for r in rows]
    volume = [float(r["volume"]) for r in rows]
    \n    if any(float(r["close"]) <= 0 for r in rows):\n        raise ValueError("close must be positive for range normalization")\n    ranges = [(float(r["high"])-float(r["low"]))/float(r["close"]) for r in rows]
    vfast, vslow = _rolling_mean(volume, vol_fast), _rolling_mean(volume, vol_slow)
    rfast, rslow = _rolling_mean(ranges, vol_fast), _rolling_mean(ranges, vol_slow)
    out=[]
    for i,row in enumerate(rows):
        direction=0
        if i>=max(lookback,vol_slow-1) and close[i-lookback] > 0:
            roc=close[i]/close[i-lookback]-1.0
            fading=(vfast[i] is not None and vslow[i] is not None and
                    rfast[i] is not None and rslow[i] is not None and
                    vfast[i] < vslow[i] and rfast[i] < rslow[i])
            if fading and roc < -roc_threshold:
                direction=1
            elif fading and roc > roc_threshold:
                direction=-1
        out.append({"timestamp":row["timestamp"],"direction":direction,
                    "mechanism":"volume_range_exhaustion"})
    return out
