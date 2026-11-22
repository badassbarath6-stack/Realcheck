"""Promotion registry for source-audited mechanism ports."""
from engines import funding_rate_mean_reversion, taker_buy_pressure_momentum
from price_action_engines import rsi_pivot_divergence, volume_range_exhaustion
from specialist_signal_engines import round_number_bounce, wall_pull_detector, book_imbalance_zscore, correlation_break_recovery

DIRECTIONAL_ENGINES = {
    "funding_rate_mean_reversion": funding_rate_mean_reversion,
    "taker_buy_pressure_momentum": taker_buy_pressure_momentum,
    "rsi_pivot_divergence": rsi_pivot_divergence,
    "volume_range_exhaustion": volume_range_exhaustion,
    "round_number_bounce": round_number_bounce,
}
SPECIALIST_SIGNAL_ENGINES = {
    "wall_pull_detector": wall_pull_detector,
    "book_imbalance_zscore": book_imbalance_zscore,
}
PAIRWISE_SPECIALIST_ENGINES = {
    "correlation_break_recovery": correlation_break_recovery,
}

SPECIALIZED_NOT_CANDLE_BACKTESTABLE = (
    "spot_perp_funding_carry",
    "avellaneda_stoikov_market_making",
    "dated_futures_cash_and_carry",
    "orderbook_wall_bounce",
    "orderbook_wall_pull",
    "orderbook_imbalance",
    "cross_asset_lead_lag",
    "correlation_break_recovery",
)
CONDITIONAL_NOT_PROMOTED = (
    "oi_price_quadrants",
    "wall_bounce_distance_sign_bug",
)
REJECTED_OR_HELD_OUT = (
    "naive_fixed_spread_market_making_baseline",
    "funding_zscore_and_fixed_threshold_fade_duplicate",
    "cross_venue_ou_with_lookahead_defect",
    "compression_breakout_pending_deduplication",
    "lead_lag_full_sample_optimal_lag_selection",
)
