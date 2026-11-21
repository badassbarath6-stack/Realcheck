"""Promotion registry for source-audited mechanism ports."""
from engines import funding_rate_mean_reversion, taker_buy_pressure_momentum
from price_action_engines import rsi_pivot_divergence, volume_range_exhaustion

DIRECTIONAL_ENGINES = {
    "funding_rate_mean_reversion": funding_rate_mean_reversion,
    "taker_buy_pressure_momentum": taker_buy_pressure_momentum,
    "rsi_pivot_divergence": rsi_pivot_divergence,
    "volume_range_exhaustion": volume_range_exhaustion,
}
SPECIALIZED_NOT_CANDLE_BACKTESTABLE = (
    "spot_perp_funding_carry",
    "avellaneda_stoikov_market_making",
    "dated_futures_cash_and_carry",
    "orderbook_wall_bounce",
    "orderbook_wall_pull",
    "orderbook_imbalance",
    "cross_asset_lead_lag",
)
CONDITIONAL_NOT_PROMOTED = (
    "oi_price_quadrants",
    "round_number_reaction_long_only_exit_semantics",
)
REJECTED_OR_HELD_OUT = (
    "naive_fixed_spread_market_making_baseline",
    "funding_zscore_and_fixed_threshold_fade_duplicate",
    "cross_venue_ou_with_lookahead_defect",
    "compression_breakout_pending_deduplication",
    "lead_lag_full_sample_optimal_lag_selection",
)
