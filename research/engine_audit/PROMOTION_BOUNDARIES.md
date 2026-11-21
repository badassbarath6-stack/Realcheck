# Promotion boundaries

Only `funding_rate_mean_reversion` and `taker_buy_pressure_momentum` are registered for the generic directional candle adapter. OI quadrants are explicitly conditional and absent from the active registry. Spot/perpetual carry, Avellaneda–Stoikov market making, and dated-futures cash-and-carry are specialized mechanisms and are not eligible for the candle adapter. They require their own hedge accounting or event-driven fill simulators.
