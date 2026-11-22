# Source Audit — Batch 06

Scope: inspect additional order-book, relative-market and round-level implementations in stooq1/strategy-graveyard, and inspect the strategy implementations in mengrenman/microstructure-lab. The stooq1 and microstructure-lab projects expose MIT licences. This batch adds source-derived specialist signal ports and one candle-compatible engine.

## New distinct mechanisms

| # | Mechanism | Inspected source | Rule and data | Decision / import |
|---:|---|---|---|---|
| 1 | Psychological round-number support/resistance bounce | [round_numbers.py](https://github.com/stooq1/strategy-graveyard/blob/main/trading_analyzer/strategies/round_numbers.py) | Dynamic decimal grid step from price × 5%; long when low touches support within tolerance and close recovers above it; short/exit when high touches resistance and close fails below it. | PASS. Imported as round_number_bounce into the directional CSV runner; next-bar execution required. |
| 2 | Tested liquidity-wall pull | [walls.py — WallPullDetector](https://github.com/stooq1/strategy-graveyard/blob/main/trading_analyzer/detectors/walls.py) | A bid/offer wall's displayed quantity collapses below 30% of its recent rolling maximum after price has recently traded near it. Offer removal scores upward; bid removal scores downward; signal only on the event edge. | PASS detector. Imported into the specialist registry; requires timestamped L2 wall price/quantity snapshots and next-observation execution. |
| 3 | Top-N order-book depth imbalance z-score | [walls.py — ImbalanceDetector](https://github.com/stooq1/strategy-graveyard/blob/main/trading_analyzer/detectors/walls.py) | Rolling z-score of log(cumulative bid depth / cumulative ask depth), clipped to [-1,+1]. | PASS detector. Imported into specialist registry; requires synchronized multi-level depth, not candle volume or taker-buy ratio. |
| 4 | Correlation-break recovery / relative lag | [satellite.py — CorrBreakDetector](https://github.com/stooq1/strategy-graveyard/blob/main/trading_analyzer/detectors/satellite.py) | When rolling return correlation was below a break threshold and recovers above a higher threshold, signal toward the asset that lagged over the break window. Signal only on the first recovery bar. | PASS pairwise detector. Imported into a separate pairwise specialist registry; requires synchronized paired asset histories and a two-leg or explicitly documented single-leg execution model. |

## Defects and deduplication

- WallBounceDetector is NOT promoted: its proximity tests only check distance < threshold, without requiring the wall to be on the correct side of price. A wall on the wrong side can therefore be classified as nearby. The original behavior is documented, but no silent correction is made; it remains conditional pending a source-faithful defect fix and regression tests.
- RoundLevelDetector is the same round-level touch/bounce rule as RoundNumberStrategy with coarse-level weighting; deduplicated, not counted twice.
- CorrelationStrategy uses a rolling log-spread z-score and correlation gate, but it only buys/sells the primary asset and does not create a matched hedge leg. It is deduplicated into the existing pairs/stat-arb family and must not be described as a full pair-trade backtest.
- FairPriceDetector is rolling OLS residual mean reversion, already represented by the beta-adjusted residual/stat-arb family.
- LeadLagDetector is a generic leader/follower catch-up rule, already represented by the cross-asset lead-lag family.
- RSI divergence and volume/range exhaustion detectors duplicate the already imported price-action mechanisms.
- The microstructure-lab MomentumStrategy is simple rolling mid-price momentum executed as taker; it duplicates the time-series momentum family. DoNothingStrategy is a zero-PnL control, TWAPStrategy is execution scheduling rather than alpha, and InventorySkewMM is an inventory-skewed market-making baseline rather than an independent alpha source. The Avellaneda–Stoikov market-making family remains the single distinct quoting mechanism.
- The microstructure-lab code uses synthetic order-book scenarios; its simulation tests do not establish real-market profitability or queue-position realism.

## Platform import details

- round_number_bounce is registered for the candle-compatible directional runner.
- wall_pull_detector and book_imbalance_zscore are registered only as specialist L2 score engines; they are not routed through the OHLCV runner.
- correlation_break_recovery is registered only as a pairwise specialist score engine; it requires an explicit paired data stream.
- The order-book ports preserve source scoring/event structure. The runner must not synthesize L2 snapshots from OHLCV or assume queue fills.

## Batch 06 tally

- 4 new distinct source-reviewed mechanisms accepted at mechanism level.
- 3 specialist signal mechanisms were imported into isolated specialist/directional registries; only round-number bounce is candle-backtestable.
- 1 wall-bounce defect is held conditional and not imported.
- Several overlapping detectors and execution-only strategies were deduplicated.
- No historical backtest started.
