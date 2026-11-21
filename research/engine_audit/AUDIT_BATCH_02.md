# Source Audit — Batch 02

Scope: inspect implementation files from FlintStrats, xy3293/crypto-strategy-backtest and H4wkQuant. This batch extends the 100-mechanism inventory; it does not start backtesting.

## New source-reviewed candidates

| Candidate | Source | Finding | Distinctness | Platform decision |
|---|---|---|---|---|
| Climax Fade — panic capitulation | [climax_fade.py](https://github.com/sohan-shingade/flintstrats/blob/main/climax_fade.py) | Implements a long after a large down bar, abnormal volume and oversold RSI, with a long-term trend/meltdown guard. The actual exit state machine uses hard stop, fixed target, giveback trail, trade-type-specific max hold and loss cooldown. | Distinct event-driven capitulation/reversal hypothesis; not the same as funding fade, ordinary RSI mean reversion, or the prior liquidity-sweep family. | PASS mechanism/source; NOT YET PROMOTED. Must port its stateful exits and verify Flint history/candle timing before an exact import. |
| Climax Fade — streak exhaustion | Same source | Implements a short after at least four consecutive up candles, cumulative gain threshold, elevated RSI and a 15% long-term EMA extension guard. Separate trade-type max hold and same stateful risk logic. | A distinct overextension/streak exhaustion short hypothesis; separate signal mechanism from panic capitulation, but packaged in the same strategy class. Count as one engine package with two entry modes, not two engines. | PASS mechanism/source; NOT YET PROMOTED for same stateful-exit/timing reason. |
| Momentum Decay | [momentum_decay.py](https://github.com/sohan-shingade/flintstrats/blob/main/momentum_decay.py) | Compares ROC at three spaced checkpoints; shorts positive-but-decelerating momentum and buys negative-but-decelerating momentum, RSI-gated and optionally checked against BTC momentum acceleration. Uses hard stop, TP, trailing, max hold and loss-dependent cooldown. | Distinct momentum-curvature / trend-transition hypothesis, not a simple trend-following crossover. | PASS mechanism/source; NOT YET PROMOTED. Needs exact stateful exit port and aligned BTC history. Audit note: `vol_decline_ratio` is configured but not used in the inspected entry logic; do not claim volume-decline confirmation. |
| BTC-to-alt momentum divergence | [momentum_div.py](https://github.com/H4wkCode/H4wkQuant/blob/main/strategies/momentum_div.py) | Source implements BTC sharp move, beta-scaled alt underreaction, taker-cost edge gate and a 30-second timeout. | Same core BTC-leads/alt-lags concept as FlintStrats Momentum Cascade; do not count a second time. | REJECT as duplicate for unique count; also requires synchronized tick data and sub-minute execution. |

## Deduplication / rejection notes

| Source candidates | Decision | Reason |
|---|---|---|
| Keltner breakout and Bollinger breakout in xy3293 | One volatility-envelope breakout family, not two engines | Both enter on close outside a volatility envelope and exit around the channel midpoint. This overlaps the already researched volatility-expansion/breakout family. |
| Supertrend, RSI-ATR trend, ADX trend, EMA ribbon, Ichimoku, MACD-EMA trend | Do not add as separate unique mechanisms | These are conventional trend-state / trend-continuation variants, not independent economic hypotheses for the 100 count. |
| H4wkQuant statistical arbitrage | REJECT as duplicate | Cointegrated pair spread z-score and reversion are already represented by the pair/stat-arb family. |
| H4wkQuant funding arbitrage | REJECT as duplicate | Same funding-carry / delta-neutral funding family already in batch 01. |
| H4wkQuant cross-exchange price spread | REJECT as duplicate | Generic cross-venue price dislocation is already represented by the cross-venue arbitrage family; this source adds no independent signal hypothesis. |
| FlintStrats adaptive residual / dual residual / cross-asset reversion | REJECT as duplicate variants | Same beta-hedged residual / cointegrated spread mean-reversion family with parameter and regression-model variants. |
| FlintStrats Cascade Climax / Inflection Trader | REJECT as separate engines | Composite strategies combine panic, trend, and momentum-decay signals already counted or represented; do not inflate the unique count by counting a bundle as another mechanism. |

## Import gate

The existing directional adapter uses a generic fixed-fractional stop/target. That is not an exact reproduction of the Flint strategy state machines. Therefore the two new source-reviewed mechanisms are not copied into the promoted registry yet. They will only be imported after a stateful adapter can reproduce their entry, stop, target, trailing, time-exit, cooldown and position-state behavior without changing the signal.

## Batch 02 tally

- 2 source-verified mechanism families newly identified: Climax Fade (two independent entry modes packaged as one engine) and Momentum Decay.
- 2 pass mechanism/source review but remain unpromoted pending exact stateful execution support.
- 1 duplicate BTC-to-alt momentum divergence candidate rejected.
- Multiple trend and envelope variants rejected from the unique count as duplicates.
- No backtest started.

The 100-engine source audit remains incomplete. No profitability claim is made.
