"""Clean-room, dependency-free ports of audited external bar-signal mechanisms.

These are research signal generators only. They do not place orders and do not
choose fills, stops, targets, leverage, or position sizing. The backtest adapter
must execute a signal no earlier than the next bar.

Source provenance and fidelity:
- funding_rate_mean_reversion: independently reimplemented from the publicly
  inspected signal specification in Gotodataru/binance-futures-backtest. That
  repository exposed no license at audit time, so no source code is copied.
- taker_buy_pressure_momentum: same provenance and clean-room treatment.
- oi_price_divergence: same provenance; kept behind an explicit opt-in because
  open-interest changes alone do not identify which side is closing.

Input is a sequence of dictionaries with timestamp, close, high, low and the
strategy-specific fields. Timestamps must be strictly increasing.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Dict, Iterable, List, Sequence


def _column(rows: Sequence[dict], key: str, default=None) -> List[Any]:
    return [r.get(key, default) for r in rows]


def _ffill(values: Sequence[Any], default: float) -> List[float]:
    out: List[float] = []
    last = default
    for value in values:
        if value is not None:
            try:
                x = float(value)
                if isfinite(x):
                    last = x
            except (TypeError, ValueError):
                pass
        out.append(last)
    return out


def _ema(values: Sequence[float], span: int) -> List[float]:
    if span < 1:
        raise ValueError("span must be >= 1")
    alpha = 2.0 / (span + 1.0)
    out: List[float] = []
    current = None
    for x in values:
        current = x if current is None else alpha * x + (1.0 - alpha) * current
        out.append(current)
    return out


def _rolling_mean(values: Sequence[float], window: int, min_periods: int | None = None) -> List[float | None]:
    if window < 1:
        raise ValueError("window must be >= 1")
    need = window if min_periods is None else min_periods
    out: List[float | None] = []
    running = 0.0
    queue: List[float] = []
    for x in values:
        queue.append(float(x))
        running += float(x)
        if len(queue) > window:
            running -= queue.pop(0)
        out.append(running / len(queue) if len(queue) >= need else None)
    return out


def _atr_ewm(rows: Sequence[dict], period: int) -> List[float]:
    highs = [float(r["high"]) for r in rows]
    lows = [float(r["low"]) for r in rows]
    closes = [float(r["close"]) for r in rows]
    tr = []
    for i, (h, l, c) in enumerate(zip(highs, lows, closes)):
        prev = closes[i - 1] if i else None
        tr.append(h - l if prev is None else max(h - l, abs(h - prev), abs(l - prev)))
    return _ema(tr, period)


def _validate(rows: Sequence[dict]) -> None:
    previous = None
    for i, row in enumerate(rows):
        for key in ("timestamp", "close", "high", "low"):
            if key not in row:
                raise ValueError(f"row {i} missing required field: {key}")
        ts = row["timestamp"]
        if previous is not None and ts <= previous:
            raise ValueError("timestamps must be strictly increasing")
        previous = ts
        if not all(isfinite(float(row[k])) for k in ("close", "high", "low")):
            raise ValueError(f"row {i} has non-finite OHLC")
        if float(row["low"]) > float(row["high"]):
            raise ValueError(f"row {i} has low > high")


def funding_rate_mean_reversion(rows: Sequence[dict], params: dict | None = None) -> List[int]:
    """Funding-extreme fade with EMA price filter and lagged taker buy-ratio check.

    Required extra columns: funding_rate, buy_ratio.
    Returns +1 long, -1 short, 0 flat. Signals use only lagged funding/flow
    features and the source's current-close-vs-prior-EMA condition.
    """
    _validate(rows)
    p = params or {}
    ema_period = int(p.get("ema_period", 50))
    threshold_high = float(p.get("threshold_high", 0.0005))
    threshold_low = float(p.get("threshold_low", 0.0001))
    if ema_period < 1 or threshold_high < 0 or threshold_low < 0:
        raise ValueError("invalid funding mean-reversion parameters")

    close = [float(r["close"]) for r in rows]
    funding = _ffill(_column(rows, "funding_rate"), 0.0)
    buy_ratio = _ffill(_column(rows, "buy_ratio"), 0.5)
    ema = _ema(close, ema_period)
    signals = [0] * len(rows)
    for i in range(ema_period + 1, len(rows)):
        prior_funding = funding[i - 1]
        prior_buy = buy_ratio[i - 1]
        prior_ema = ema[i - 1]
        if prior_funding < -threshold_low and close[i] < prior_ema and prior_buy > 0.45:
            signals[i] = 1
        elif prior_funding > threshold_high and close[i] > prior_ema and prior_buy < 0.55:
            signals[i] = -1
    return signals


def taker_buy_pressure_momentum(rows: Sequence[dict], params: dict | None = None) -> List[int]:
    """Aggressive buyer/seller dominance with consecutive confirmation and ATR gate.

    Required extra column: buy_ratio = taker_buy_volume / total_volume.
    """
    _validate(rows)
    p = params or {}
    ma_period = int(p.get("ma_period", 15))
    confirm_bars = int(p.get("confirm_bars", 3))
    threshold_high = float(p.get("threshold_high", 0.62))
    atr_period = int(p.get("atr_period", 14))
    if min(ma_period, confirm_bars, atr_period) < 1 or not 0.5 < threshold_high < 1:
        raise ValueError("invalid taker-pressure parameters")
    buy_ratio = _ffill(_column(rows, "buy_ratio"), 0.5)
    ma = _rolling_mean(buy_ratio, ma_period)
    atr = _atr_ewm(rows, atr_period)
    atr_ma = _rolling_mean(atr, 50, min_periods=20)
    signals = [0] * len(rows)
    warmup = max(ma_period, atr_period, 50) + confirm_bars + 1
    low_threshold = 1.0 - threshold_high
    for i in range(warmup, len(rows)):
        # The rolling mean and confirmation windows end on the previous bar.
        if i < ma_period or ma[i - 1] is None or i < confirm_bars:
            continue
        confirm = buy_ratio[i-confirm_bars:i]
        confirm_long = all(x > 0.5 for x in confirm)
        confirm_short = all(x < 0.5 for x in confirm)
        vol_ok = atr_ma[i] is not None and atr[i] > float(atr_ma[i]) * 0.8
        if not vol_ok:
            continue
        if float(ma[i - 1]) > threshold_high and confirm_long:
            signals[i] = 1
        elif float(ma[i - 1]) < low_threshold and confirm_short:
            signals[i] = -1
    return signals


def oi_price_divergence(rows: Sequence[dict], params: dict | None = None) -> List[int]:
    """Price/OI quadrant strategy. Explicitly experimental; not promoted by default.

    Required extra columns: open_interest, taker_ls_vol_ratio. The source's
    four-quadrant interpretation is reproduced as a hypothesis, not as proof
    of which trader cohort is opening/closing.
    """
    _validate(rows)
    p = params or {}
    lookback = int(p.get("lookback_bars", 12))
    price_thr = float(p.get("price_thresh", 0.005))
    oi_thr = float(p.get("oi_thresh", 0.01))
    use_mr = bool(int(p.get("use_mr", 1)))
    if lookback < 1 or price_thr < 0 or oi_thr < 0:
        raise ValueError("invalid OI divergence parameters")
    close = [float(r["close"]) for r in rows]
    oi = _ffill(_column(rows, "open_interest"), 0.0)
    ls = _ffill(_column(rows, "taker_ls_vol_ratio"), 1.0)
    signals = [0] * len(rows)
    for i in range(lookback + 2, len(rows)):
        # pct_change(lookback).shift(1): compare close/OI at i-1 with i-1-lookback.
        prev = i - 1
        base = prev - lookback
        if base < 0 or close[base] == 0 or oi[base] == 0:
            continue
        pc = close[prev] / close[base] - 1.0
        oc = oi[prev] / oi[base] - 1.0
        ls_lag = ls[i - 1]
        price_up, price_down = pc > price_thr, pc < -price_thr
        oi_up, oi_down = oc > oi_thr, oc < -oi_thr
        if price_up and oi_up and ls_lag > 1.0:
            signals[i] = 1
        elif price_down and oi_up and ls_lag < 1.0:
            signals[i] = -1
        elif use_mr and price_down and oi_down:
            signals[i] = 1
        elif use_mr and price_up and oi_down:
            signals[i] = -1
    return signals


def spot_perp_funding_carry(funding_rows: Sequence[dict], threshold: float = 0.0001) -> List[int]:
    """Binary long-spot/short-perp carry eligibility at funding timestamps.

    Returns 1 when funding exceeds threshold, else 0. This is not a directional
    perp-only signal. A valid backtest must hold matched spot/perp notionals,
    account for both legs' fees/slippage, borrow/capital cost and actual
    settlement cashflows. Volatility sizing is deliberately left to portfolio
    risk, not embedded in this signal.
    """
    out = []
    previous = None
    for i, row in enumerate(funding_rows):
        if "timestamp" not in row or "funding_rate" not in row:
            raise ValueError(f"funding row {i} needs timestamp and funding_rate")
        ts = row["timestamp"]
        if previous is not None and ts <= previous:
            raise ValueError("funding timestamps must be strictly increasing")
        previous = ts
        rate = float(row["funding_rate"])
        out.append(1 if isfinite(rate) and rate > threshold else 0)
    return out
