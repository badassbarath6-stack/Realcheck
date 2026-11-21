"""Audited, point-in-time crypto-perpetual strategy adapters.

These adapters emit a direction at the signal bar close. A backtester MUST
execute no earlier than the next bar open. Inputs are normalized, timestamp-
aligned rows; this module deliberately does not fetch data or place orders.

No upstream source files are copied verbatim. The formulas below are an
independent implementation of the audited signal rules.
"""
from __future__ import annotations

from math import isfinite
from typing import Iterable, Mapping, Any


def _number(row: Mapping[str, Any], key: str, default=None):
    value = row.get(key, default)
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    return value if isfinite(value) else None


def _ffill(values):
    out, last = [], None
    for value in values:
        if value is not None:
            last = value
        out.append(last)
    return out


def _ema(values, span):
    alpha = 2.0 / (span + 1.0)
    out, prev = [], None
    for value in values:
        if value is None:
            out.append(prev)
            continue
        prev = value if prev is None else alpha * value + (1.0 - alpha) * prev
        out.append(prev)
    return out


def _rolling_mean(values, window, min_periods=None):
    if min_periods is None:
        min_periods = window
    out = []
    for i in range(len(values)):
        chunk = [x for x in values[max(0, i-window+1):i+1] if x is not None]
        out.append(sum(chunk) / len(chunk) if len(chunk) >= min_periods else None)
    return out


def _pct_change(values, periods):
    out = [None] * len(values)
    for i in range(periods, len(values)):
        a, b = values[i], values[i-periods]
        if a is not None and b not in (None, 0):
            out[i] = a / b - 1.0
    return out


def _tr_and_atr(rows, period):
    tr = []
    previous_close = None
    for row in rows:
        high, low, close = (_number(row, k) for k in ("high", "low", "close"))
        if high is None or low is None or close is None:
            tr.append(None)
        else:
            tr.append(max(high-low,
                          abs(high-previous_close) if previous_close is not None else 0.0,
                          abs(low-previous_close) if previous_close is not None else 0.0))
            previous_close = close
    return _ema(tr, period)


def _emit(rows, directions, engine):
    return [
        {"timestamp": row.get("timestamp"), "signal": int(direction),
         "engine": engine, "execution_rule": "next_bar_open"}
        for row, direction in zip(rows, directions)
    ]


def funding_rate_fade(rows: Iterable[Mapping[str, Any]], params=None):
    """Funding-extremity contrarian signal with lagged funding/flow confirmation.

    Required: close, funding_rate, buy_ratio. Defaults mirror audited source:
    EMA 50, high funding 0.0005, low funding 0.0001, buy-ratio gates 0.45/0.55.
    """
    rows = list(rows); p = params or {}
    span = int(p.get("ema_period", 50))
    high_thr = float(p.get("threshold_high", 0.0005))
    low_thr = float(p.get("threshold_low", 0.0001))
    if span < 2 or high_thr < 0 or low_thr < 0:
        raise ValueError("Invalid funding-fade parameters")
    close = [_number(r, "close") for r in rows]
    funding = _ffill([_number(r, "funding_rate") for r in rows])
    buy = [0.5 if _number(r, "buy_ratio") is None else _number(r, "buy_ratio") for r in rows]
    ema = _ema(close, span)
    dirs = [0] * len(rows)
    for i in range(span + 1, len(rows)):
        prior_ema = ema[i-1]
        prior_funding = funding[i-1]
        prior_buy = buy[i-1]
        if None in (close[i], prior_ema, prior_funding):
            continue
        if prior_funding < -low_thr and close[i] < prior_ema and prior_buy > 0.45:
            dirs[i] = 1
        elif prior_funding > high_thr and close[i] > prior_ema and prior_buy < 0.55:
            dirs[i] = -1
    return _emit(rows, dirs, "funding_rate_fade")


def taker_buy_pressure_momentum(rows: Iterable[Mapping[str, Any]], params=None):
    """Aggressor-buy dominance momentum with consecutive confirmation + ATR gate.

    Required: high, low, close, buy_ratio. Signals are calculated at bar close;
    buy-flow averages/confirmation are lagged one full bar, as in source.
    """
    rows = list(rows); p = params or {}
    ma_period = int(p.get("ma_period", 15))
    confirm = int(p.get("confirm_bars", 3))
    threshold = float(p.get("threshold_high", 0.62))
    atr_period = int(p.get("atr_period", 14))
    if min(ma_period, confirm, atr_period) < 1 or not 0.5 < threshold < 1:
        raise ValueError("Invalid taker-pressure parameters")
    buy = [0.5 if _number(r, "buy_ratio") is None else _number(r, "buy_ratio") for r in rows]
    ma = _rolling_mean(buy, ma_period)
    atr = _tr_and_atr(rows, atr_period)
    atr_ma = _rolling_mean(atr, 50, min_periods=20)
    dirs = [0] * len(rows)
    warmup = max(ma_period, atr_period, 50) + confirm + 1
    for i in range(warmup, len(rows)):
        if ma[i-1] is None or atr[i] is None or atr_ma[i] in (None, 0):
            continue
        if atr[i] <= atr_ma[i] * 0.8:
            continue
        prior = buy[i-confirm:i]
        if len(prior) != confirm:
            continue
        if ma[i-1] > threshold and all(x > 0.5 for x in prior):
            dirs[i] = 1
        elif ma[i-1] < 1.0-threshold and all(x < 0.5 for x in prior):
            dirs[i] = -1
    return _emit(rows, dirs, "taker_buy_pressure_momentum")


def oi_price_quadrants(rows: Iterable[Mapping[str, Any]], params=None):
    """Price/OI quadrant strategy; continuation is flow-confirmed, MR is not.

    Required: close, open_interest, taker_ls_vol_ratio. Reversal labels are
    deliberately treated as hypotheses: OI alone cannot identify which side
    closed. The raw four-quadrant observation is retained in each output row.
    """
    rows = list(rows); p = params or {}
    lookback = int(p.get("lookback_bars", 12))
    price_thr = float(p.get("price_thresh", 0.005))
    oi_thr = float(p.get("oi_thresh", 0.01))
    use_mr = bool(p.get("use_mr", 1))
    if lookback < 1 or price_thr < 0 or oi_thr < 0:
        raise ValueError("Invalid OI-divergence parameters")
    close = [_number(r, "close") for r in rows]
    oi = _ffill([_number(r, "open_interest") for r in rows])
    ls = _ffill([_number(r, "taker_ls_vol_ratio") for r in rows])
    pc = _pct_change(close, lookback)
    oc = _pct_change(oi, lookback)
    dirs = [0] * len(rows)
    out = []
    for i, row in enumerate(rows):
        # source uses pct_change(...).shift(1)
        j = i - 1
        quadrant = "unknown"
        if j >= 0 and pc[j] is not None and oc[j] is not None:
            pu, pdn = pc[j] > price_thr, pc[j] < -price_thr
            ou, odn = oc[j] > oi_thr, oc[j] < -oi_thr
            if pu and ou:
                quadrant = "price_up_oi_up"
                if ls[j] is not None and ls[j] > 1.0: dirs[i] = 1
            elif pdn and ou:
                quadrant = "price_down_oi_up"
                if ls[j] is not None and ls[j] < 1.0: dirs[i] = -1
            elif pu and odn:
                quadrant = "price_up_oi_down"
                if use_mr: dirs[i] = -1
            elif pdn and odn:
                quadrant = "price_down_oi_down"
                if use_mr: dirs[i] = 1
            elif not (pu or pdn or ou or odn):
                quadrant = "neutral"
        if i < lookback + 2:
            dirs[i] = 0
        out.append({"timestamp": row.get("timestamp"), "signal": int(dirs[i]),
                    "engine": "oi_price_quadrants", "quadrant": quadrant,
                    "execution_rule": "next_bar_open",
                    "interpretation_warning": "OI direction does not identify which side is closing"})
    return out


STRATEGIES = {
    "funding_rate_fade": funding_rate_fade,
    "taker_buy_pressure_momentum": taker_buy_pressure_momentum,
    "oi_price_quadrants": oi_price_quadrants,
}
