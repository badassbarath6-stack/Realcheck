# Source Audit — Batch 16: expanded crypto-perpetual candidate pool

Date: 2026-11-22

## Scope

Source-level inspection was performed on the candidate repositories surfaced by the 109-repository discovery catalogue. Inspected source files included:
- `venkatanath18/crypto-order-flow`: `src/orderflow/ofi.py`, `src/orderflow/hawkes.py`, `analysis/a05_ofi.py`
- `HmiouiReda/Quantamental-StatArb-on-Crypto-Perpetual-Futures`: `src/features/kalman.py`, `src/features/sentiment.py`, strategy and pair-selection modules
- `MRowhani/basis-funding-arbitrage-bot`: `src/ssot/basis.rs`, `src/ssot/candidates.rs`, `src/ssot/funding.rs`
- `wilsontiger2222/liquidation-hunter`: funding, OI divergence and liquidation-cluster signal modules
- `Starkl7/Crypto_MM`: `src/intensity.cpp`, `src/fill_engine.cpp`, walk-forward documentation
- `aria-tjr/crypto-futures-ml-strategy`: funding, mean-reversion, cross-asset and HMM/GMM regime modules
- `51bitquant/binance_grid_trader`, `DIO1009/resonance-breakout`, `aurelien-gentile/crypto-pairs-trading`, `FarisZnf/Production-Grade-RSI-Momentum-Crypto-Trading-Strategy-with-Advanced-Statistical-Validation` README and strategy descriptions.

## Decisions

| Candidate source / apparent strategy | Exact source-level finding | Decision | Why it does or does not add a distinct engine |
|---|---|---|---|
| Crypto-order-flow: OFI regression | Builds normalized order-flow imbalance from book updates, estimates contemporaneous impact and next-interval mid-price response, and tests walk-forward regressions. README reports meaningful 1s forecasting but approximately zero predictive R² at 10s/1m. | FEATURE / RESEARCH ONLY; NOT A COMPLETE ENGINE | No standalone causal entry/exit, position sizing or perpetual trade state machine in inspected files. OFI feature is related to the existing book-imbalance specialist family; don't count a regression feature as a second engine. |
| Crypto-order-flow: exponential Hawkes process | Implements event-time self-exciting intensity with exponential kernel, maximum-likelihood parameters and Python/C++ parity. | FEATURE / RESEARCH ONLY | It estimates event clustering; the inspected module does not specify an independent trade direction, entry/exit or execution policy. Do not count a point-process estimator as a strategy engine. |
| Quantamental StatArb: Kalman hedge-ratio pairs | Online Kalman regression estimates time-varying intercept and hedge ratio; pair strategy trades cointegrated residual mean reversion and uses FinBERT sentiment as a turbulence/risk-off overlay. | DEDUPLICATED; PAIR FAMILY ALREADY COUNTED | Same pair-spread mean-reversion economic mechanism already audited. Kalman hedge-ratio adaptation and FinBERT risk overlay are model/overlay changes, not a separate alpha engine. |
| MRowhani basis/funding bot | Maintains cross-venue basis level/slope state with Kalman estimates; candidate types include reverse-basis and funding-new; compares funding signs across main/hedge venues and uses two-leg execution/repair. | DEDUPLICATED WITH CROSS-VENUE BASIS/FUNDING FAMILY | Valuable implementation of basis/funding state and execution repair, but no new independent economic hypothesis versus the already audited cross-venue basis/funding arbitrage family. |
| Liquidation Hunter: funding/OI/whale liquidation clusters | Funding extremes infer crowded side; OI-price divergence estimates fragile positioning; whale liquidation prices are binned into clusters and nearest dense cluster drives cascade direction. | DEDUPLICATED WITH OI/LIQUIDATION FAMILY | Same liquidation-cascade / forced-deleveraging mechanism already audited. README's claimed 55–65% win rate and 2:1+ R:R are unsupported promotional claims, not verified performance. Its suggested market-nudge tactic is explicitly excluded from any implementation. |
| Crypto_MM: Avellaneda–Stoikov | Fits exponential fill intensity by MLE and replays quotes against order-book snapshots and real trades; reservation price and optimal spread account for inventory and volatility; walk-forward calibration and delayed parameter activation are modelled. | DEDUPLICATED; MARKET-MAKING FAMILY ALREADY COUNTED | Stronger source-level execution detail, but same inventory-skewed optimal-quoting family already audited. The current source reports positive results for one short sample, but this does not establish generalizable net edge; its handoff also records an earlier losing version. |
| aria-tjr funding signal module | Implements funding carry, funding mean reversion, funding momentum, extreme, annualized and z-score signals, then a composite. | DEDUPLICATED WITH FUNDING FAMILY | These are multiple transformations of the same funding input and overlap the already counted funding carry, term-structure and cross-sectional funding families. They are not counted as separate engines merely because the code emits separate columns. |
| aria-tjr mean-reversion module | RSI, Bollinger deviation/reversal, moving-average z-score, gap reversal, VWAP deviation and consecutive-move reversal. | DEDUPLICATED / GENERIC INDICATOR VARIANTS | These are conventional price mean-reversion variants already represented by existing price-reversion engines; no independent market mechanism is added by the bundle. |
| aria-tjr cross-asset module | Rolling BTC beta, sector momentum, correlation regime, PCA factor exposure and lead-lag features. | FEATURE / OVERLAY; PARTLY DEDUPLICATED | Beta/PCA/sector/lead-lag are portfolio features and cross-asset conditioning; the inspected module does not define one independent complete execution strategy. Existing cross-sectional momentum, relative lag and correlation-break mechanisms cover the actual standalone families. |
| aria-tjr HMM/GMM regime detector | Fits a Gaussian HMM (or GMM fallback) to momentum, volatility, correlation, volume and trend-strength features to label trending, mean-reverting, high-vol and low-vol states. | REGIME OVERLAY; NOT A STANDALONE ENGINE | A regime classifier can condition multiple strategies but has no independent directional trade policy in the inspected module. Do not count regime labels as an alpha engine. |
| 51bitquant Binance grid trader | Provides Binance spot/futures grid bot entry point; source description establishes a grid execution approach but not a separate causal alpha beyond grid inventory harvesting. | DEDUPLICATED WITH ADAPTIVE GRID FAMILY | Same range/grid inventory-harvesting mechanism already audited. |
| DIO1009 Trend Resonance | Higher-timeframe channel selects long direction; lower-timeframe breakout waits for a pullback into a tolerance band; source describes costs, funding and stop slippage in a 380-day replay. | DEDUPLICATED WITH HTF TREND/BREAKOUT-PULLBACK FAMILY | A well-specified implementation and useful validation reference, but still a trend-filtered breakout-pullback entry in an already represented family. Do not count another source as another engine. |
| aurelien-gentile pairs trading | Bybit perpetual pairs ranked by correlation, filtered by cointegration, traded on spread mean reversion with funding costs. | DEDUPLICATED WITH COINTEGRATION/PAIR STAT-ARB FAMILY | Same pair residual convergence family. |
| FarisZnf RSI momentum | RSI momentum with adaptive bull-market threshold, 12m/6m walk-forward, block bootstrap and stress testing. | DEDUPLICATED WITH RSI/MOMENTUM FAMILY | Better validation scaffolding, but indicator/threshold variant of an existing momentum family, not a distinct economic mechanism. |

## New distinct engines added by this batch

**Zero.** This is a valid audit outcome: the newly inspected sources mainly strengthen evidence and implementation understanding for already represented mechanism families, or provide features without complete trade policies. Counting them as new engines would violate the user's requirement for genuine mechanism distinctness.

## Important source-quality notes

- Repository names, README performance badges and claimed win rates are not accepted as proof.
- A strategy must have an independently identifiable causal entry/exit hypothesis, not merely a feature estimator or an ensemble wrapper.
- A different venue, timeframe, parameter, model architecture, or source repository does not automatically create a new engine.
- Spot-only source logic is not presumed futures-compatible.
- No code was copied in this batch. No five-year BTC/ETH backtest was started by this audit.

## Result

The 109-source discovery catalogue has now been supplemented by source-level inspection of additional candidate projects. The audited unique count is unchanged by this batch; the candidate sources were deduplicated or classified as research/overlay components. Continue auditing the remaining discovery candidates and the outstanding 54-mechanism target without inflating the count.
