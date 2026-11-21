# Promotion boundaries

## Directional candle engines

The following are registered for the isolated CSV runner:

- funding_rate_mean_reversion
- taker_buy_pressure_momentum
- rsi_pivot_divergence
- volume_range_exhaustion
- round_number_bounce

They emit signals on completed bars. The earliest allowed fill is the next bar open. The generic adapter's fixed fractional stop/target is an evaluation overlay, not native-exit fidelity for strategies whose source has ROI, trailing, cooldown, pyramiding or stateful exits.

## Specialist engines

- wall_pull_detector: requires timestamped L2 wall prices and quantities.
- book_imbalance_zscore: requires timestamped cumulative bid/ask depth.
- correlation_break_recovery: requires synchronized primary and paired asset histories.

These are separate score engines and must not be passed through the candle-only adapter as if their required data were present. A dedicated L2/paired-stream adapter and execution assumptions are required.

## Conditional / held out

- OI/price quadrants: conditional because falling OI does not identify which trader cohort is closing.
- WallBounceDetector: conditional because its source proximity checks lack a correct-side condition.
- Avellaneda–Stoikov, funding carry, dated cash-and-carry and calendar spreads require event-driven quotes or matched multi-leg portfolio accounting.
- Cross-venue OU remains held out until the source's rolling backward-fill look-ahead defect is corrected.
- Naive fixed-spread maker, funding-fade parameter variants, trend/MA indicator variants, and execution-only TWAP/Almgren–Chriss examples are not counted as distinct directional alpha engines.

No backtest is started until the 100-mechanism audit gate is satisfied.
