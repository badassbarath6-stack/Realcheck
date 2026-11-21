# Source Audit — Batch 12

Scope: inspect the Apache-2.0 Mefai strategy implementations for grid trading, volume profile, DCA and related execution logic. This batch counts only distinct, source-defined entry hypotheses; generic feature names and composite bundles are not inflated into extra engines.

## New distinct mechanisms accepted at source/mechanism level

| Mechanism | Inspected source | Exact rule observed | Decision / platform boundary |
|---|---|---|---|
| Adaptive arithmetic/geometric range grid | [grid_trading.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/grid_trading.py) | Build a grid inside a rolling range chosen as the wider of Bollinger Bands and a ±ATR multiple. Grid spacing is either equal-price (arithmetic) or equal-percentage (geometric). A crossed lower-half level emits a buy; a crossed upper-half level emits a sell/short in futures mode. Opposite paired levels realize grid profit. EMA20/EMA50 trend changes shift the range by 25% after a cooldown; ATR percentage adjusts grid count (fewer levels in high volatility, more in low volatility). | PASS as a distinct range-harvesting inventory/grid mechanism. NOT IMPORTED: the source mutates level state when generating a signal, before a confirmed fill; pair reset and P&L must be reconciled to actual fills, and the futures short-side inventory/margin model is not fully specified. Needs a stateful event/fill adapter and range-trend risk controls. |
| Volume-profile POC proximity reversion | [volume_profile.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/volume_profile.py) | Construct a rolling price-bin volume profile; POC is the highest-volume bin. When price is within the configured proximity of POC, go long from below POC and short from above POC; the POC is also the dynamic mean-reversion target. | PASS as a distinct profile-auction / POC magnet hypothesis. Source-faithful label is POC proximity reversion, not a confirmed bounce: it does not require a rejection candle or touch-and-reclaim. Profile approximation spreads each candle's volume evenly across every price bin it spans; it is not true tick-level volume-at-price. |
| Value-area re-entry fade | [volume_profile.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/volume_profile.py) | If the previous close was above value-area high and the current close returns below it, enter short; if the previous close was below value-area low and returns above it, enter long. | PASS as a separate value-acceptance / failed-auction re-entry mechanism. Requires a causally frozen or rolling point-in-time value area and next-bar execution. |
| Low-volume-node traversal breakout | [volume_profile.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/volume_profile.py) | Enter long when price crosses upward from below an LVN's lower boundary to at least its midpoint; enter short on the mirrored downward cross. The source treats low-volume zones as areas of faster price travel. | PASS as a separate volume-profile liquidity-vacuum continuation mechanism. It is not the same as value-area re-entry or POC mean reversion. Requires a stable, point-in-time profile and execution at the next tradable quote. |

## Audited but not counted

| Candidate | Source | Decision | Reason |
|---|---|---|---|
| Multi-trigger DCA accumulation | [dca.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/dca.py) | NOT COUNTED AS AN ALPHA ENGINE | The code buys on a schedule, a dip from its rolling reference high, or an RSI oversold trigger; purchase size is increased by dip depth/RSI and reduced by volatility, with staged profit-taking and an investment cap. This is a capital-deployment / averaging overlay, not an independently specified directional edge. It also calls wall-clock `time.time()` in signal generation and mutates average-cost/position state before confirmed fills; historical simulation would need an injected simulation clock and fill-committed state. |
| Order-flow composite | [order_flow.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/order_flow.py) | REJECT AS A DISTINCT SOURCE ENGINE | Combines CVD, absorption, exhaustion and price/CVD divergence already audited in other sources. More importantly, when trade data is absent it invents buy/sell volume from candle body direction and body size; those estimates are not observed aggressor flow and cannot validate an order-flow engine. |
| Smart-money concepts composite | [smart_money.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/smart_money.py) | DEDUPLICATED / TIMING BLOCKED | Bundles order blocks, FVG, BOS/ChoCH, liquidity sweeps and premium/discount/Fibonacci confluence already represented by prior mechanisms. Swing pivots require right-side confirmation; a batch-vectorized port must not signal at the pivot's historical bar. |
| Elliott-wave pattern recognizer | [elliott_wave.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/elliott_wave.py) | CONDITIONAL REJECT / NOT COUNTED | The source counts alternating confirmed swing points and validates 5-wave/3-wave structures with Fibonacci projections. It is a subjective pattern-composite rather than a clearly separable causal alpha rule; it needs a fully specified pivot confirmation delay and stable deterministic wave-selection rules before it can qualify. |
| Multi-timeframe indicator momentum | [momentum.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/momentum.py) | DEDUPLICATED | Composite RSI/MACD/ROC/EMA/volume score with ADX trend gate and ATR trailing stop; overlaps the existing multi-indicator momentum/confluence family. |
| Arbitrage bundle | [arbitrage.py](https://github.com/mefai-dev/mefai-autotrade/blob/master/src/strategies/arbitrage.py) | DEDUPLICATED / MIXED IMPLEMENTATION | Bundles spot/perp basis, funding carry, cross-exchange spread and triangular spot arbitrage already audited elsewhere; no new single independent mechanism is added by the wrapper. |

## Data and source-quality findings

- Repository licence is Apache-2.0; no source code was copied in this audit batch.
- Volume-profile levels are estimated from OHLCV by distributing each bar's volume equally across all price bins touched. This can smear volume across the full candle range and is not equivalent to tick/footprint volume-at-price.
- The profile is rebuilt from the last `session_bars` candles on each signal call. The inspected code does not itself prove that those bars align to a true exchange session boundary.
- POC, value area and LVN levels can change as the rolling profile changes. A faithful backtest must calculate them from bars available at the signal close and execute no earlier than the next bar/quote.
- The grid's internal level state must only be committed after exchange/backtest fills. The current implementation's pre-fill mutation is a material mismatch risk.

## Batch 12 tally

- 4 new distinct source-reviewed mechanisms accepted at mechanism level.
- DCA was inspected but not counted as independent alpha.
- Order-flow, SMC, Elliott-wave, generic momentum and arbitrage wrappers were rejected or deduplicated.
- No code copied and no historical Realcheck backtest started.
