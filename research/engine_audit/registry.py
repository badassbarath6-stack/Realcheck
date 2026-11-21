"""Promotion registry for audited mechanism ports."""
from engines import funding_rate_mean_reversion, taker_buy_pressure_momentum

DIRECTIONAL_ENGINES = {
    "funding_rate_mean_reversion": funding_rate_mean_reversion,
    "taker_buy_pressure_momentum": taker_buy_pressure_momentum,
}
SPECIALIZED_NOT_CANDLE_BACKTESTABLE = (
    "spot_perp_funding_carry",
    "avellaneda_stoikov_market_making",
    "dated_futures_cash_and_carry",
)
CONDITIONAL_NOT_PROMOTED = ("oi_price_quadrants",)
REJECTED_OR_HELD_OUT = (
    "naive_fixed_spread_market_making_baseline",
    "funding_zscore_and_fixed_threshold_fade_duplicate",
    "cross_venue_ou_with_lookahead_defect",
    "compression_breakout_pending_deduplication",
)
