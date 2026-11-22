# External strategy discovery — 2026-11-22

## Scope and evidence standard

Target market for Realcheck: BTCUSDT and ETHUSDT perpetual futures first. This is a discovery catalogue, not a claim that 100 strategies have already been implemented or passed backtests. A mechanism is counted separately only when its causal hypothesis, required inputs, entry/exit state, and economic payoff are materially different. Indicators, filters, parameter variants, and different names for the same rule are not separate engines.

The initial public-source sweep located several unusually large discovery pools:
- **The Quant Trading Vault** claims 5,806 strategy specifications/code algorithms/indicators. Treat this as a lead index, not 5,806 verified independent engines.
- **crack-the-nut** describes 63 backtestable strategies and walk-forward/exit simulation.
- **FlintStrats** describes 20 crypto-perpetual strategies.
- **Freqtrade strategies** is a public strategy repository; its own README warns that strategies are starting points and results depend on pair, timeframe, and costs.
- **Algorithmic-Trading-Projects** describes 20+ crypto strategies across Binance, Phemex and Hyperliquid.
- **crypto-ml-trading-research** documents a point-in-time universe, HMM regimes, tree/transformer models, walk-forward folds, and cost stress.
- **crypto-perps-research** documents funding/basis, structural-break, order-flow and L1-book research, including mechanisms killed by look-ahead or realistic-fill tests.
- **crypto_systematic_research** documents a BTC/ETH-oriented walk-forward pipeline and failed-strategy kill list.
- **Cryptocurrency market microstructure: a systematic literature review** provides an academic map of microstructure research.
- **Momentum in the Cryptocurrency Market: A Comprehensive Analysis under Realistic Assumptions** reports stronger time-series momentum evidence than cross-sectional momentum, while warning about tail risk and data-snooping.

These sources are discovery inputs only. Repository README claims and author-reported returns are not accepted as Realcheck performance evidence. Source code, license, data, execution semantics and out-of-sample results must be inspected independently before import.

## Candidate consolidation: 100 distinct mechanism hypotheses

Status for every item below: **DISCOVERY CANDIDATE — NOT YET SOURCE-VERIFIED OR BACKTESTED IN REALCHECK**. Required data notes indicate the minimum viable research feed, not a guarantee that historical coverage exists.

### A. Directional trend and breakout (1–15)
1. Donchian channel breakout — rolling high/low breach; OHLCV.
2. Turtle dual-channel breakout — separate entry/exit channel lengths; OHLCV.
3. Time-series momentum (TSMOM) — signed trailing return with fixed holding/exit rule; OHLCV.
4. Moving-average trend state — fast/slow average state transition; OHLCV.
5. Moving-average slope persistence — slope sign and persistence rather than crossover; OHLCV.
6. Price-channel volatility expansion — channel breach conditioned on range expansion; OHLCV.
7. Opening-range breakout — session range break; timestamped OHLCV.
8. Volatility-compression release — squeeze then directional expansion; OHLCV.
9. Multi-timeframe impulse continuation — higher-timeframe impulse with lower-timeframe trigger; multi-TF OHLCV.
10. Trend pullback continuation — retracement into a trend reference then resumption; OHLCV.
11. ADX trend-strength transition — directional entry on trend-strength state change; OHLCV.
12. Parabolic SAR trend reversal/continuation — SAR state flip; OHLCV.
13. Ichimoku cloud breakout/state — cloud structure and conversion/base relationship; OHLCV.
14. Linear-regression channel breakout — regression residual/channel escape; OHLCV.
15. Price acceleration breakout — acceleration in returns/price velocity; OHLCV.

### B. Mean reversion and exhaustion (16–30)
16. Bollinger-band re-entry — close back inside an outer band; OHLCV.
17. RSI extreme reversal — threshold exit from oversold/overbought; OHLCV.
18. RSI pivot divergence — price/oscillator swing divergence; OHLCV.
19. Stochastic exhaustion cross — oscillator turn from extreme; OHLCV.
20. CCI extreme snapback — CCI excursion and reversal; OHLCV.
21. VWAP deviation reversion — deviation from session/anchored VWAP; OHLCV with volume.
22. VWAP band capitulation — extreme volume-weighted deviation and reclaim; OHLCV with volume.
23. Volume/range climax fade — abnormal volume and range exhaustion; OHLCV.
24. Momentum-decay reversal — deceleration after extended directional move; OHLCV.
25. Streak-exhaustion reversal — unusually long same-direction return sequence; OHLCV.
26. Climax capitulation wick fade — extreme wick/volume with reclaim confirmation; OHLCV.
27. Value-area re-entry fade — auction returns into prior value area; volume profile/trades.
28. Point-of-control reversion — migration back toward volume POC; trade/volume profile.
29. Psychological round-number rejection — level test, rejection and follow-through; tick trades/OHLCV.
30. Fibonacci retracement reaction — pre-defined swing retracement reaction; OHLCV.

### C. Volatility, range and path-dependent (31–40)
31. ATR expansion breakout — range expansion relative to trailing ATR; OHLCV.
32. ATR contraction-to-expansion — low-volatility state transition; OHLCV.
33. Realized-volatility regime switch — realized variance state controls entry/position; OHLCV.
34. Parkinson/Garman–Klass volatility shock — range-based volatility shock; OHLCV.
35. Volatility risk-premium capture — implied versus realized volatility; options surface plus realized vol.
36. Volatility carry/dispersion — relative implied/realized or cross-asset vol pricing; options surface.
37. Hurst/variance-ratio persistence switch — persistence versus anti-persistence state; OHLCV.
38. Range-bound adaptive grid — inventory-aware grid in bounded regimes; tick/quote and fill simulation.
39. Arithmetic/geometric adaptive grid — grid spacing and inventory process; tick/quote and fill simulation.
40. Volatility-targeted trend allocation — trend exposure scaled to realized volatility; OHLCV.

### D. Perpetual futures funding, basis and derivatives (41–55)
41. Funding-rate extreme mean reversion — extreme funding followed by convergence; funding history.
42. Funding momentum/continuation — persistent funding changes as directional positioning signal; funding history.
43. Funding term-structure reversion — cross-maturity funding curve dislocation; multi-venue/maturity funding.
44. Cross-sectional funding relative value — long/short funding spread across assets; universe funding.
45. Funding settlement calendar effect — behavior around scheduled settlement; timestamped funding and trades.
46. Spot-perpetual cash-and-carry — delta-neutral basis plus funding; matched spot/perp prices and funding.
47. Perpetual basis convergence — mark/index/spot basis normalization; mark, index, spot.
48. Perpetual basis momentum — basis change predicts subsequent return; mark/index/spot.
49. Open-interest price quadrant — price/OI joint state; OI and OHLCV.
50. OI-confirmed liquidation-wick reversal — forced deleveraging plus OI collapse and reclaim; OI, liquidation feed, trades.
51. OI-confirmed crash continuation — price/OI expansion during breakdown; OI and OHLCV.
52. Liquidation cascade exhaustion — forced-flow intensity decays and imbalance flips; liquidation events, trades, L1.
53. Dated-futures cash-and-carry — expiry-aware basis and financing; dated contracts, spot, expiry/roll.
54. Dated-futures calendar-spread convergence — inter-expiry spread convergence; full futures curve.
55. Cross-venue funding/basis arbitrage — matched instruments across venues; synchronized order books, fees, borrow/transfer constraints.

### E. Order flow, liquidity and market microstructure (56–70)
56. Taker buy/sell imbalance momentum — aggressive flow imbalance; aggregate trades.
57. Cumulative-volume-delta divergence — CVD versus price disagreement; signed trades.
58. Order-flow imbalance (OFI) — quote/trade event imbalance; L1 event stream.
59. Top-N order-book depth imbalance — multi-level bid/ask depth skew; L2 snapshots/events.
60. Queue depletion / replenishment — depth consumption and refill asymmetry; L2 event stream.
61. Liquidity-wall pull detector — large displayed liquidity cancels before price reaches it; L2 event stream.
62. Liquidity-wall absorption/bounce — aggressive flow absorbed at persistent depth; L2 plus trades.
63. VPIN volume-clock toxicity — volume-bucket signed-flow toxicity regime; trade-level data.
64. Amihud illiquidity shock — price impact per dollar volume; OHLCV/trades.
65. Spread widening/narrowing regime — quoted spread state and subsequent movement; L1 quotes.
66. Microprice imbalance — size-weighted best bid/ask microprice; L1 quotes.
67. Trade-sign autocorrelation — persistence in aggressor direction; trade-level data.
68. Large-trade impact decay — post-block-trade transient impact/reversion; trade-level data.
69. Sweep-and-reclaim order-flow confirmation — liquidity sweep followed by aggressive-flow reversal; trades plus L1/L2.
70. Passive maker spread capture — quote placement with queue-position/fill probability; event-level L2 and queue model.

### F. Cross-asset, statistical arbitrage and relative value (71–82)
71. Cointegration pairs mean reversion — stationary price spread; synchronized multi-asset prices.
72. Rolling hedge-ratio pairs trading — dynamic beta spread; synchronized prices.
73. PCA factor-residual mean reversion — residual z-score after common factors; multi-asset panel.
74. Cross-sectional momentum ranking — rank assets by trailing return; point-in-time universe.
75. Cross-sectional volatility-scaled momentum — momentum rank normalized by volatility; point-in-time OHLCV.
76. Relative-strength residual breakout — idiosyncratic return residual breakout; market/sector factor panel.
77. BTC-led delayed beta cascade — leader impulse and lagged follower response; synchronized BTC/ETH and target prices.
78. Correlation-break recovery — transient correlation dislocation; synchronized multi-asset prices.
79. Beta-compression expansion — compressed rolling beta followed by expansion; synchronized prices.
80. Cross-asset lead-lag reversal — leader/follower return reversal after lead-lag shock; synchronized trades/bars.
81. Cross-sectional dispersion convergence — abnormal dispersion mean reversion; broad point-in-time universe.
82. Basket/stat-arb residual momentum — directional trade in factor-neutral residual; multi-asset panel.

### G. Calendar, session and structural behavior (83–90)
83. Hour-of-day seasonality — conditional intraday return distribution; timestamped OHLCV.
84. Day-of-week/month-end effect — calendar-conditioned return behavior; OHLCV.
85. Funding-time pre/post event drift — event-window price/flow behavior; funding timestamps and trades.
86. Weekend liquidity regime — weekend-specific spread/volatility/return behavior; timestamped quotes/trades.
87. Session handover volatility impulse — regional session transition; timestamped OHLCV.
88. Post-listing / new-contract lifecycle — listing-age conditional trend/liquidity; point-in-time listings.
89. Volatility shock after macro event — scheduled event response; timestamped macro calendar and market data.
90. Exchange outage/depeg dislocation recovery — venue/asset-specific dislocation; venue status, prices, order books.

### H. Options, on-chain, sentiment and machine learning (91–100)
91. Implied-volatility skew reversal — options skew extreme and normalization; options surface.
92. IV term-structure regime — maturity curve state; options surface.
93. Dealer gamma / gamma exposure positioning — gamma concentration and spot response; options OI/greeks.
94. On-chain exchange netflow signal — exchange inflow/outflow shock; point-in-time on-chain data.
95. Stablecoin supply/liquidity regime — stablecoin supply/flow changes; on-chain supply/flow.
96. Social coordination / attention shock — abnormal social attention and flow; timestamped social data.
97. News/sentiment event drift — text-derived event score and post-event returns; timestamped news corpus.
98. HMM/Markov regime-conditioned strategy — forward-filtered latent state gates a separately specified base rule; causal features.
99. Gradient-boosted cross-sectional return ranker — point-in-time features, nested walk-forward; broad panel.
100. Sequence/attention quantile forecaster — temporal model forecasts conditional return quantiles; point-in-time panel and nested validation.

## De-duplication and promotion rules

- Items 1–100 are hypothesis families, not 100 already-proven engines. Some may collapse after exact source-code comparison; for example, several indicator threshold variants are parameterizations of the same causal rule.
- A filter/model (e.g., HMM regime detector) is not an independent trading engine unless paired with a fully specified entry, exit, sizing and execution policy. It remains an overlay component.
- Market making, carry, cross-venue arbitrage, options, liquidation-flow and order-book strategies require their own event-driven simulators. They must not be approximated by candle-only backtests.
- Missing native feed => **NOT TESTABLE**, never proxy performance.
- Every imported candidate must record original source URL, author, commit/version/date, license, exact code/spec hash, market, timeframe, inputs, entry, exit, sizing, fees, funding, slippage, fill assumptions, look-ahead tests and known limitations.
- Require prefix invariance, point-in-time universe, chronological walk-forward, untouched holdout, realistic costs and adverse cost stress. Record failed tests and rejected candidates.
- Performance is measured only by Realcheck runs with reproducible artifacts. Third-party advertised returns are not imported as facts.

## Public discovery leads

1. https://github.com/brainbrick-trades/The-Quant-Trading-Vault
2. https://github.com/CShear/crack-the-nut
3. https://github.com/sohan-shingade/flintstrats
4. https://github.com/freqtrade/freqtrade-strategies
5. https://github.com/pranay123-stack/Algorithmic-Trading-Projects
6. https://github.com/cengizmandros/crypto-ml-trading-research
7. https://github.com/rsipavan/crypto-perps-research
8. https://github.com/EstebanSP23/crypto_systematic_research
9. https://github.com/akoiralaa/statistical-arbitrage
10. https://github.com/CryptoQuantix/CryptoQuantix
11. https://github.com/WallStreetPete/awesome-open-source-trading
12. https://link.springer.com/article/10.1007/s10479-023-05627-5
13. https://academic.oup.com/raps/advance-article/doi/10.1093/rapstu/raag011/8914819
14. https://onlinelibrary.wiley.com/doi/full/10.1002/fut.22425

## Current disposition

- Consolidated candidate families in this file: 100.
- Claims that 1,000 distinct engines have been source-inspected: **NO**.
- Claims that these 100 are all independently source-verified: **NO**.
- Claims that these 100 are implemented or backtested in Realcheck: **NO**.
- Next research operation: enumerate source-level strategy artifacts from the large discovery pools, fingerprint logic, merge duplicates into these families, then promote only source-verified and data-testable implementations.
