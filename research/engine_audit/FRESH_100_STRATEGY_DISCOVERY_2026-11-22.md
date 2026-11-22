# Fresh 100 strategy-engine discovery shortlist
Date: 2026-11-22
Status: research shortlist compiled from public strategy ecosystems and quantitative-method literature. These are 100 separately specified candidate mechanisms; they are NOT represented as 100 source-code-audited implementations or as Realcheck backtest results.

## Discovery-pool evidence and limits

The source sweep found public pools large enough to support a 1,000+ candidate harvesting programme:
- The Algo Catalog advertises 3,200+ published strategies and 6,500+ tested strategy runs, with rerunnable RealTest files. It explicitly warns that backtests are selection-biased and requires forward records before sale.
- PyneCore Strategies advertises 449 TradingView community strategies ported to Python, plus 471 indicators and 85 libraries.
- The MQL5 CodeBase is a large public source library; the search result showed 217 pages of MT5 code.
- GeneralD/calgo reports 75+ cTrader cBots and 200+ indicators.
- WallStreetPete/awesome-open-source-trading maps 450+ open-source projects and 110+ quant strategy papers.
- TradingView's public script library is described by a public-source search tool as containing hundreds of thousands of community scripts.
- QuantConnect LEAN provides an event-driven multi-asset algorithm platform; crypto bot ecosystems include Freqtrade, Hummingbot, Jesse, OctoBot and others.

These counts establish that the discovery pool is large. They do NOT establish that 1,000 individual strategies have been fetched, parsed, de-duplicated and audited in this pass. This document therefore does not make that false claim. Each item below is a fresh candidate mechanism definition for subsequent source-level matching. A strategy is distinct only if its causal signal, trade construction, exit/payoff or required market mechanism is materially different; cosmetic indicator substitutions are not counted.

## 100 fresh candidate engines

### 1. Trend structure and directional systems
1. **Vortex directional-cross system** — enter on positive/negative vortex-line dominance; exit on opposite dominance or structural stop.
2. **Aroon trend-age system** — trade new high/low recency dominance; exit when trend age decays.
3. **Chande momentum oscillator zero-line regime** — enter on signed momentum regime transition; exit on zero-line loss.
4. **Kaufman adaptive moving-average efficiency trend** — use price-path efficiency to switch adaptive trend exposure.
5. **Fractal breakout continuation** — enter on confirmed Bill Williams fractal level break; invalidate on opposite fractal.
6. **Linear-regression slope reversal** — trade statistically significant slope sign changes, not channel breakouts.
7. **Moving-average ribbon compression expansion** — trade ribbon compression resolving into ordered directional separation.
8. **Range-filter directional state** — use a volatility-scaled range filter's state flip as the sole direction trigger.
9. **Supertrend flip-and-retest** — require a Supertrend state flip followed by a successful retest before entry.
10. **Elder Triple Screen** — weekly trend filter, daily oscillator pullback, intraday trigger as a three-stage rule.

### 2. Auction, price formation and market profile
11. **Initial balance extension** — trade acceptance beyond the initial balance with a measured extension target.
12. **Prior-day value-area acceptance** — enter only after sustained acceptance outside prior value area, targeting next profile node.
13. **Poor-high / poor-low repair** — trade revisit and completion of a weak auction extreme.
14. **Single-print auction continuation** — trade directional continuation through a single-print region, invalidated by full repair.
15. **Excess-tail rejection** — fade a completed auction tail only after price fails to re-enter the extreme.
16. **Volume-profile composite migration** — trade persistent POC migration as directional auction repricing.
17. **Anchored VWAP reclaim after event** — enter after reclaim/loss of event-anchored VWAP, with event anchor fixed ex ante.
18. **VWAP slope plus dispersion expansion** — trade directional VWAP slope only when dispersion expands in the same direction.
19. **Market-profile day-type transition** — classify trend/balance/neutral day from opening development, then apply distinct entry logic.
20. **Auction rotation failure** — fade a failed rotation at value edge after opposing initiative flow appears.

### 3. Candlestick and swing-structure systems
21. **Outside-bar failure reversal** — trade failed continuation after an outside bar closes back through its midpoint.
22. **Inside-bar volatility resolution** — enter break of mother-bar range after compression; cancel stale orders after fixed bars.
23. **NR7 volatility breakout** — trade expansion after the narrowest range of the recent seven-bar window.
24. **Three-bar play continuation** — impulse, controlled pause, then break of pause in impulse direction.
25. **Gap-and-go continuation** — trade opening gap continuation only after opening-range acceptance (market/session-specific).
26. **Gap-fill rejection reversal** — trade failed gap fill with risk beyond the gap extreme.
27. **Swing-failure pattern** — take prior swing liquidity then close back inside; entry on confirmation break.
28. **Break-of-structure retest** — enter only on retest of a confirmed swing break level.
29. **Change-of-character reversal** — require a prior trend, opposing structural break, then lower-timeframe confirmation.
30. **Measured-move completion reversal** — fade a completed pre-defined measured move after momentum failure.

### 4. Oscillator, cycle and signal-processing methods
31. **Ehlers Roofing Filter cycle turn** — trade band-pass filtered cycle turns with a trend-state veto.
32. **Ehlers MESA phase crossover** — trade dominant-cycle phase transitions with adaptive cycle period.
33. **Hilbert instantaneous trend mode** — switch between trend and cycle rules using instantaneous trendline state.
34. **Fisher transform extreme reversal** — trade Fisher transform turning from statistically extreme values.
35. **Connors RSI pullback system** — combine short RSI, streak length and percentile rank of one-bar return.
36. **Williams %R failure swing** — enter after oscillator failure swing confirms a reversal.
37. **DeMarker exhaustion system** — trade DeMarker extreme reversal with price confirmation.
38. **Know Sure Thing signal-line transition** — trade multi-horizon rate-of-change composite cross.
39. **DPO cycle reversion** — trade detrended-price-oscillator cycle extremes with explicit cycle invalidation.
40. **Wavelet denoised trend trigger** — extract multi-scale denoised trend component; trade only stable scale agreement.

### 5. Portfolio, allocation and cross-sectional engines
41. **Dual momentum allocation** — require positive absolute momentum and rank assets by relative momentum; allocate to strongest eligible assets.
42. **Volatility-managed momentum portfolio** — scale momentum portfolio risk by forecast variance and correlation.
43. **Minimum-variance crypto rotation** — rebalance to inverse-covariance weights with turnover constraints.
44. **Risk-parity trend basket** — allocate by marginal risk contribution, then apply a separate trend eligibility rule.
45. **Hierarchical risk-parity portfolio** — cluster return correlations and allocate recursively; portfolio engine, not a single-asset signal.
46. **Maximum-diversification portfolio** — optimize diversification ratio subject to liquidity and concentration constraints.
47. **Tail-risk parity allocation** — size assets by expected shortfall contribution rather than variance.
48. **Volatility breakout breadth thrust** — trade market basket when fraction of assets breaking volatility bands crosses a breadth threshold.
49. **Cross-sectional reversal after extreme dispersion** — rank-reverse recent winners/losers only when dispersion is abnormally high.
50. **Residual momentum after sector/market neutralization** — trade residual trend after factor regression, distinct from residual mean reversion.

### 6. Statistical arbitrage and econometric systems
51. **Kalman-filter dynamic spread hedge** — estimate time-varying hedge ratio and trade standardized residual with filter uncertainty gate.
52. **Error-correction model (VECM) convergence** — trade deviations from cointegrated long-run equilibrium using estimated adjustment coefficients.
53. **Ornstein–Uhlenbeck optimal stopping spread** — derive entry/exit thresholds from estimated mean-reversion speed and transaction costs.
54. **Fractional cointegration spread** — trade a spread stationary only after fractional differencing / long-memory diagnostics.
55. **Copula tail-dependence relative value** — enter pair trades when joint-tail dependence deviates from calibrated copula.
56. **Variance-ratio statistical trend/reversion switch** — use multi-horizon variance ratio to select trend or reversion exposure.
57. **CUSUM mean-shift detector strategy** — detect persistent return mean shift and trade only after sequential change confirmation.
58. **Bayesian online change-point strategy** — update probability of regime change and reset/close positions when posterior hazard rises.
59. **Hawkes self-exciting event-flow strategy** — trade clustering in signed trade or liquidation event intensity.
60. **Kalman fair-value deviation strategy** — trade deviations from a dynamic fair-value state estimate with uncertainty-scaled sizing.

### 7. Execution, order book and liquidity strategies
61. **Order-book queue imbalance next-tick strategy** — predict short-horizon mid-price move from queue imbalance; event-driven fills required.
62. **Microprice fair-value market making** — quote around size-weighted microprice rather than mid-price.
63. **Optimal execution schedule (Almgren–Chriss)** — schedule parent-order execution minimizing impact/variance; execution engine, not alpha.
64. **Adaptive POV execution** — participate at a target fraction of market volume with urgency adaptation.
65. **Implementation-shortfall execution** — dynamically trade off market impact and opportunity cost against arrival price.
66. **Iceberg replenishment detection** — infer hidden liquidity from repeated executions and displayed-size replenishment.
67. **Stop-run cascade continuation** — detect clustered stop-triggered aggressive flow and trade continuation before exhaustion.
68. **Spread capture with inventory skew** — market-make while shifting quotes by inventory risk and adverse-selection estimate.
69. **Latency-arbitrage stale-quote protection** — cancel/avoid quoting when cross-venue reference price moves ahead.
70. **Cross-venue order-book dislocation capture** — trade temporary executable best-price differences after fees, latency and inventory costs.

### 8. Futures, carry, options and volatility surface
71. **Calendar-spread seasonal roll strategy** — trade historically persistent calendar spread seasonality with contract-roll-aware execution.
72. **Butterfly curvature convergence** — trade relative mispricing of adjacent futures maturities using fly structure.
73. **Perpetual-vs-quarterly basis switch** — rotate exposure between perp and dated future based on net basis/funding economics.
74. **Funding-neutral directional overlay** — retain directional exposure only when expected alpha exceeds funding and basis drag.
75. **Options put-call skew risk reversal** — trade changes in risk-reversal skew with delta-hedged option legs.
76. **Options calendar volatility spread** — trade relative implied volatility between maturities with vega/delta hedging.
77. **Options butterfly volatility curvature** — trade curvature of implied volatility across strikes.
78. **Variance risk premium short-vol strategy** — sell variance exposure only under explicit crash-risk and margin constraints.
79. **Gamma scalping around realized-volatility divergence** — dynamically delta hedge long gamma when realized movement justifies option decay.
80. **Volatility surface arbitrage constraint repair** — identify and trade executable violations of static-arbitrage surface constraints.

### 9. On-chain, network, event and information systems
81. **Exchange reserve shock strategy** — trade abnormal changes in exchange-held balances with entity-adjusted, point-in-time data.
82. **Stablecoin exchange inflow deployment signal** — detect stablecoin inflow to exchanges and condition on actual market buying pressure.
83. **Miner/validator distribution pressure** — model entity-labelled distribution flow, not raw address transfers.
84. **Realized-cap / MVRV regime allocation** — adjust long-horizon exposure by valuation regime with survivorship-safe chain data.
85. **Network activity acceleration** — trade changes in active entities/transaction activity after seasonality adjustment.
86. **Liquid staking / unlock supply event strategy** — trade scheduled token supply unlocks with actual vesting and venue liquidity data.
87. **Governance proposal event strategy** — event-window strategy around material protocol governance decisions.
88. **Exchange incident recovery strategy** — model price/liquidity dislocation around outage, withdrawal halt and reopening events.
89. **News surprise drift** — score event novelty and surprise relative to expectations, then trade post-publication drift.
90. **Funding/positioning crowding unwind** — combine crowded positioning with catalyst/flow reversal; not simply a funding threshold.

### 10. Machine learning, ensembles and risk-control engines
91. **Random-forest meta-labeler** — filter independently generated primary entries using triple-barrier labels and purged validation.
92. **Gradient-boosted triple-barrier classifier** — predict probability of upper/lower/vertical barrier first-touch.
93. **Purged-CV feature-selection ensemble** — ensemble only features stable across purged folds; nested out-of-sample selection.
94. **Conformal prediction position filter** — abstain or reduce size when predictive interval is too wide or coverage degrades.
95. **Online logistic-regression adaptive signal** — update coefficients sequentially with drift monitoring and strict delayed labels.
96. **Contextual bandit execution selector** — select among execution policies using context and realized implementation shortfall.
97. **Mixture-of-experts market-state model** — distinct expert policies for trend, range, stress and illiquid regimes with probabilistic gating.
98. **Ensemble disagreement abstention** — do not trade when independent model predictions diverge beyond a calibrated threshold.
99. **Drawdown-state capital allocator** — scale portfolio risk based on drawdown, volatility and recovery state, without altering signal labels.
100. **Sequential probability-ratio trade confirmation** — accumulate evidence after setup formation and enter only when likelihood ratio crosses a pre-registered boundary.

## Provenance and discovery references

### Strategy and code pools
- The Algo Catalog (3,200+ published strategies; exact .rts source files and methodology): https://algo-catalog.com/
- PyneCore ports of 449 TradingView strategies: https://github.com/theonetrade/pynecore-strategies
- TradingView public strategy/source discovery tool: https://github.com/daviddme/tradingview-indicator-search-mcp-server
- MQL5 CodeBase (Expert Advisors, indicators and scripts): https://www.mql5.com/en/code/mt5
- cTrader/cAlgo collection with 75+ cBots: https://github.com/GeneralD/calgo
- 450+ project / 110+ research-paper index: https://github.com/WallStreetPete/awesome-open-source-trading
- Systematic futures research index: https://github.com/ngeorgj/Awesome-Systematic-Trading
- QuantConnect LEAN event-driven engine: https://github.com/QuantConnect/Lean
- Crypto bot ecosystem map: https://github.com/starkdcc/awesome-crypto-bots
- YouTube strategy distillation workflow with transcript provenance: https://github.com/mostlyerror/yt-trade-distill

### Research integrity and Realcheck admission gate

1. The candidate is not counted as source-verified until its actual source/specification is inspected and archived with URL, author, version/commit, date, license and SHA-256.
2. Reconcile source code into a canonical rule card: market, universe, timeframe, input feeds, signal, entry, exit, sizing, state, fees, funding, slippage, fill assumptions and known failure modes.
3. Cluster duplicates by code fingerprint and normalized rule semantics. Indicator substitutions, parameter sweeps, timeframes and long/short mirrors do not automatically qualify as distinct engines.
4. A filter, feature, portfolio allocator or execution algorithm is not mislabeled as a standalone alpha engine. It is separately typed.
5. Require native data. Candle-only backtests cannot validate queue, market-making, liquidation-event, options, on-chain or cross-venue strategies.
6. Require point-in-time data, no-lookahead/prefix-invariance tests, chronological walk-forward, purged validation where applicable, untouched holdout, realistic fees/slippage/funding, adverse-cost stress and reproducible artifacts.
7. Record **NOT TESTABLE** where historical data or execution fidelity is unavailable. Do not fill gaps with proxy data.
8. No performance claim is accepted from an author's marketing page as Realcheck evidence.

## Honest completion ledger

- Public catalogues/repositories discovered: YES.
- Public catalogues include pools with several thousand strategy entries: YES (catalogue claims; not independently recounted here).
- 1,000 individual strategy source files harvested and inspected in this pass: NO.
- 100 fresh candidate mechanisms consolidated in this document: YES.
- 100 candidate source implementations individually audited: NO.
- 100 engines implemented or backtested in Realcheck: NO.
