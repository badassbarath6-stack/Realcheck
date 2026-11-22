"""Source-faithful, research-only implementations of audited crypto mechanisms.

Inputs are point-in-time rows sorted ascending by timestamp. No exchange client,
order placement, or live execution is included. Directional signals are emitted
at bar close; the adapter must fill at the next bar open.
"""
from __future__ import annotations
import math
from typing import Iterable, Mapping, Any


def _finite(x: Any) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _ema(values: list[float], span: int) -> list[float]:
    alpha = 2.0 / (span + 1.0)
    out, current = [], float("nan")
    for value in values:
        current = value if not _finite(current) else alpha * value + (1.0-alpha) * current
        out.append(current)
    return out


def _atr_ewm(rows: list[Mapping[str, Any]], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    out, current = [], float("nan")
    for i, row in enumerate(rows):
        high, low, close = float(row["high"]), float(row["low"]), float(row["close"])
        prev = float(rows[i-1]["close"]) if i else close
        tr = max(high-low, abs(high-prev), abs(low-prev))
        current = tr if not _finite(current) else alpha*tr + (1.0-alpha)*current
        out.append(current)
    return out


def funding_rate_mean_reversion(rows: Iterable[Mapping[str, Any]], *,
        ema_period: int = 50, threshold_high: float = 0.0005,
        threshold_low: float = 0.0001) -> list[dict[str, Any]]:
    """Lagged funding extreme + lagged EMA + lagged aggressive-flow confirmation."""
    data = list(rows)
    if ema_period < 2 or threshold_high <= 0 or threshold_low < 0:
        raise ValueError("invalid funding mean-reversion parameters")
    closes = [float(r["close"]) for r in data]
    emas = _ema(closes, ema_period)
    prior_funding, prior_buy, out = None, 0.5, []
    for i, row in enumerate(data):
        lag_funding = prior_funding
        lag_buy = prior_buy
        prior_ema = emas[i-1] if i else float("nan")
        direction = 0
        if i >= ema_period+1 and lag_funding is not None and _finite(prior_ema):
            if lag_funding < -threshold_low and closes[i] < prior_ema and lag_buy > 0.45:
                direction = 1
            elif lag_funding > threshold_high and closes[i] > prior_ema and lag_buy < 0.55:
                direction = -1
        out.append({"timestamp":row.get("timestamp"),"direction":direction,
                    "mechanism":"funding_rate_mean_reversion"})
        if _finite(row.get("funding_rate")):
            prior_funding = float(row["funding_rate"])
        prior_buy = float(row["buy_ratio"]) if _finite(row.get("buy_ratio")) else 0.5
    return out


def taker_buy_pressure_momentum(rows: Iterable[Mapping[str, Any]], *,
        ma_period: int = 15, confirm_bars: int = 3,
        threshold_high: float = 0.62, atr_period: int = 14) -> list[dict[str, Any]]:
    """Lagged taker-buy share, consecutive confirmation, and ATR activity gate."""
    data = list(rows)
    if ma_period < 1 or confirm_bars < 1 or not 0.5 < threshold_high < 1 or atr_period < 2:
        raise ValueError("invalid taker-pressure parameters")
    ratios = [float(r["buy_ratio"]) if _finite(r.get("buy_ratio")) else 0.5 for r in data]
    atr = _atr_ewm(data,atr_period)
    atr_ma = []
    for i in range(len(data)):
        w=atr[max(0,i-49):i+1]
        atr_ma.append(sum(w)/len(w) if len(w)>=20 else float("nan"))
    out=[]; warmup=max(ma_period,atr_period,50)+confirm_bars+1
    for i,row in enumerate(data):
        direction=0
        if i>=warmup and i>=ma_period+confirm_bars:
            ma=sum(ratios[i-ma_period:i])/ma_period
            confirm=ratios[i-confirm_bars:i]
            active=_finite(atr_ma[i]) and atr[i]>atr_ma[i]*0.8
            if active and ma>threshold_high and all(x>0.5 for x in confirm): direction=1
            elif active and ma<1.0-threshold_high and all(x<0.5 for x in confirm): direction=-1
        out.append({"timestamp":row.get("timestamp"),"direction":direction,
                    "mechanism":"taker_buy_pressure_momentum"})
    return out


def oi_price_quadrants(rows: Iterable[Mapping[str, Any]], *,
        lookback_bars: int=12, price_threshold: float=0.005,
        oi_threshold: float=0.01, use_mr: bool=True) -> list[dict[str, Any]]:
    """Conditional OI/price quadrant hypotheses; no claim about which side closes."""
    data=list(rows); out=[]
    oi_values=[]; ls_values=[]
    last_oi=None; last_ls=1.0
    for row in data:
        if _finite(row.get("open_interest")):
            last_oi=float(row["open_interest"])
        if _finite(row.get("taker_ls_vol_ratio")):
            last_ls=float(row["taker_ls_vol_ratio"])
        oi_values.append(last_oi)
        ls_values.append(last_ls)
    for i,row in enumerate(data):
        direction,regime=0,"unknown"
        # Match source warm-up: signals.iloc[:lookback+2] = 0.
        if i>=lookback_bars+2:
            # pct_change(lookback).shift(1): endpoints i-1 and i-1-lookback.
            start_i=i-lookback_bars-1
            end_i=i-1
            p0,p1=float(data[start_i]["close"]),float(data[end_i]["close"])
            o0,o1=oi_values[start_i],oi_values[end_i]
            if o0 is not None and o1 is not None and p0>0 and o0>0:
                pc=p1/p0-1; oc=o1/o0-1
                ls=ls_values[end_i]
                pu,pd=pc>price_threshold,pc < -price_threshold
                ou,od=oc>oi_threshold,oc < -oi_threshold
                if pu and ou and ls>1: direction,regime=1,"price_up_oi_up_continuation"
                elif pd and ou and ls<1: direction,regime=-1,"price_down_oi_up_continuation"
                elif use_mr and pd and od: direction,regime=1,"price_down_oi_down_reversal_hypothesis"
                elif use_mr and pu and od: direction,regime=-1,"price_up_oi_down_reversal_hypothesis"
                else: regime="neutral_or_unconfirmed"
            else:
                regime="missing_oi_history"
        out.append({"timestamp":row.get("timestamp"),"direction":direction,"regime":regime,
                    "mechanism":"oi_price_quadrants",
                    "interpretation":"hypothesis_not_observed_trader_intent"})
    return out


def spot_perp_funding_carry(rows: Iterable[Mapping[str, Any]], *,
        funding_threshold: float=0.0001) -> list[dict[str, Any]]:
    """Positive signal means matched spot-long/perpetual-short, not naked long."""
    if funding_threshold<0: raise ValueError("funding_threshold must be non-negative")
    out=[]
    for row in rows:
        f=row.get("funding_rate"); active=_finite(f) and float(f)>funding_threshold
        vol=row.get("realized_vol_30d")
        out.append({"timestamp":row.get("timestamp"),"active":bool(active),
                    "spot_weight":1.0 if active else 0.0,"perp_weight":-1.0 if active else 0.0,
                    "realized_vol_30d":float(vol) if _finite(vol) else None,
                    "mechanism":"spot_perp_funding_carry"})
    return out


def avellaneda_stoikov_quotes(*, mid: float, inventory: float, funding_rate: float,
        variance_over_horizon: float, book_imbalance: float, gamma: float=0.1,
        kappa: float=1.5, funding_gain: float=1.0, imbalance_gain: float=2.0,
        min_half_spread_bps: float=1.0, max_inventory: float=1.0) -> dict[str, Any]:
    """A-S reservation price, funding and book-imbalance tilts, optimal spread."""
    vals=(mid,inventory,funding_rate,variance_over_horizon,book_imbalance,gamma,kappa,
          funding_gain,imbalance_gain,min_half_spread_bps,max_inventory)
    if not all(_finite(v) for v in vals) or mid<=0 or gamma<=0 or kappa<=0:
        raise ValueError("invalid market-making inputs")
    if variance_over_horizon<0 or not -1<=book_imbalance<=1:
        raise ValueError("variance must be nonnegative and imbalance in [-1, 1]")
    reservation=(mid-inventory*gamma*variance_over_horizon
        -funding_gain*funding_rate*mid+imbalance_gain*book_imbalance*mid*1e-4)
    spread_const=(2/gamma)*math.log(1+gamma/kappa)
    spread=max(gamma*variance_over_horizon+spread_const,
               2*min_half_spread_bps*1e-4*mid)
    return {"reservation_price":reservation,"spread":spread,
            "bid_price":reservation-spread/2,"ask_price":reservation+spread/2,
            "allow_bid":inventory<max_inventory,"allow_ask":inventory>-max_inventory}


def delivery_basis_economics(*, spot_mid: float, futures_mark: float,
        days_to_expiry: float, borrow_apr: float, spot_fee_bps: float=10.,
        futures_fee_bps: float=5., hurdle_annualized: float=0.08,
        contract_size_usd: float=100.) -> dict[str, Any]:
    """Dated futures cash-and-carry basis economics net of fees and financing."""
    vals=(spot_mid,futures_mark,days_to_expiry,borrow_apr,spot_fee_bps,
          futures_fee_bps,hurdle_annualized,contract_size_usd)
    if not all(_finite(v) for v in vals) or spot_mid<=0 or days_to_expiry<=0 or contract_size_usd<=0:
        raise ValueError("invalid delivery-basis inputs")
    basis=(futures_mark-spot_mid)/spot_mid
    annualized=basis*365/days_to_expiry
    fee_drag=(spot_fee_bps+futures_fee_bps)/10000*(365/days_to_expiry)
    net=annualized-fee_drag-borrow_apr
    return {"basis":basis,"annualized_basis":annualized,"fee_drag_annualized":fee_drag,
            "net_annualized":net,"contracts_per_base":spot_mid/contract_size_usd,
            "eligible":net>=hurdle_annualized}
