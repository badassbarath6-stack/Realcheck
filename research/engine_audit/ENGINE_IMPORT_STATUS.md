# Audited Mechanism Import — Research Branch

This branch is isolated from the approved Impulse Retracer runner and production deployment.

## Imported source-derived mechanisms

| Engine | Core rule preserved | Required fields | Status |
|---|---|---|---|
| Funding-rate mean reversion | Lagged funding extreme + lagged EMA trend context + lagged taker buy-ratio confirmation | OHLCV-derived buy ratio, point-in-time funding | Imported and registered for directional adapter; awaits historical feature feed |
| Taker-buy-pressure momentum | Lagged rolling taker-buy share, consecutive bar confirmation, ATR activity filter | Taker-buy volume / total volume | Imported and registered for directional adapter; awaits feature feed |
| Spot/perpetual funding carry | Positive funding threshold creates matched spot-long/perp-short sleeve | Spot close, perp funding, realized volatility | Imported as a matched hedge sleeve; spot feed and settlement cashflows required |
| Avellaneda–Stoikov funding-aware market making | Inventory-skewed reservation price, funding tilt, book-imbalance tilt, A-S spread and inventory caps | L1/L2 book, timestamps, fills, inventory, funding | Quote model imported; requires event-driven queue/fill simulation |
| Dated-futures cash-and-carry | Annualized delivery basis net of financing and both-leg fees | Spot, dated futures mark, expiry, borrow APR, contract specs | Economics module imported; requires expiry-aware execution/rehedge adapter |
| RSI pivot divergence | Confirmed price pivot divergence against RSI; signal only after right-side pivot confirmation | OHLC | Imported and registered; needs next-bar fill and pivot-confirmation delay preserved |
| Volume/range exhaustion | Large directional move followed by cooling volume and candle range | OHLCV | Imported and registered; needs volume feed and next-bar fill |

## Conditional / rejected / held out

- OI/price quadrants: conditional module only. It uses lagged price/OI changes and labels falling-OI reversal directions as hypotheses, not observed trader intent. A regression test guards against current-bar look-ahead.
- Naive fixed-spread market maker: baseline only, not an independent alpha mechanism.
- Fixed funding threshold and funding z-score fade: variants of the same funding-extreme fade; deduplicated.
- Cross-exchange funding-adjusted OU: held out because inspected source uses rolling median backward-fill (future leakage) and full-sample ADF diagnostics. No import until corrected.
- Compression-conditioned breakout: held out pending evidence that it differs from Donchian/Turtle breakout already in the candidate set.

## Execution contract

- Directional bar engines emit a signal at bar close.
- The generic adapter enters at the next bar open, uses pessimistic stop-first resolution, and charges both-side fees and slippage.
- Its fixed fractional stop/target is an adapter-level evaluation policy, not a claim that the upstream engine used those exits. Reports must label this distinction.
- Market-making and cross-venue engines must never use the candle adapter. They require event-driven book/trade/fill/venue clocks.
- Carry sleeves are portfolio hedges, not naked directional trades. They require matched quantities and funding settlement cashflows.

## Data gap versus current Realcheck runner

The existing runner's M1 parser currently keeps OHLC only. It does not persist total volume, taker-buy volume, OI, taker long/short ratio, spot OHLC, L1/L2 depth, queue position, or dated-futures marks/expiry. The new modules therefore have explicit data contracts and are not silently routed into the old impulse/retracement simulator.

## Validation

The dedicated GitHub Actions workflow compiles the imported modules and runs the existing research regression suite plus audit-specific tests. The previous source-audit commit completed that workflow successfully. The OI lag correction in the current commit is covered by a new no-look-ahead regression test; its workflow result is pending.

## Audit count

Six Python strategy modules currently exist in the isolated package. The directional registry includes five candle engines; the specialist registry includes two L2 detectors and one pairwise detector. Four are registered in the directional CSV runner; the specialist carry, market-making and delivery-basis modules require their own portfolio or event-driven execution adapters. Two additional Batch 02 mechanisms (Climax Fade and Momentum Decay) passed source review but are not imported because their stateful exits/cooldowns are not represented by the generic adapter. Batch 03 adds one source-verified dated-futures calendar-spread mechanism, but it is not imported until dated-curve data and two-leg contract accounting exist. OI remains conditional. These are code-level imports only; no historical backtest or profitability claim is made. The 100-candidate source audit remains incomplete.

## Additional source audit — batch 02

See [AUDIT_BATCH_02.md](AUDIT_BATCH_02.md). Climax Fade and Momentum Decay passed mechanism/source review but are not promoted because the current adapter cannot exactly reproduce their stateful exit and cooldown logic. The BTC-to-alt tick divergence candidate was deduplicated against the already-counted momentum-cascade concept. Conventional trend and envelope-breakout variants were not counted as new independent engines. No new backtest was started.


## Current source audit count (through Batch 03)

- 8 distinct source-reviewed mechanism families accepted at mechanism level: 5 from Batch 01, 2 from Batch 02, and 1 from Batch 03.
- 7 have source-derived research modules in the branch; 4 are registered for directional candle CSV testing.
- 3 accepted mechanisms remain unpromoted pending stateful execution or specialist data/contract accounting: Climax Fade, Momentum Decay, dated-futures calendar spread.
- OI/price quadrant remains conditional; duplicates, defects and out-of-scope options are not counted.
- No 100-mechanism completion claim and no strategy backtest has been started.
- Batch 03 report: [AUDIT_BATCH_03.md](AUDIT_BATCH_03.md).


## Source audit — Batch 04

See [AUDIT_BATCH_04.md](AUDIT_BATCH_04.md). Batch 04 inspected 25 evaluator functions in CShear/crack-the-nut and additional Freqtrade strategy implementations. It added 15 source-reviewed mechanisms at mechanism level: rolling-high proximity, Bollinger/RSI reversion, funding-surface regime, funding term-structure reversion, volatility-squeeze release, realized-volatility term structure, cross-sectional funding relative value, funding-settlement calendar, relative-strength residual breakout, beta-compression trigger, multi-voter consensus fade, disagreement/compression breakout, 3-hour ATR impulse breakout with pyramiding, TD Sequential 9-count exhaustion, and VWAP-band capitulation.

These are not all ready for backtesting. The source evaluators omit native trade state/exits; the Freqtrade examples need their exact ROI/stop/pyramiding behavior and point-in-time timing. No generic fixed-RR adapter is being represented as exact native behavior. GPL-3.0 source is not copied into Realcheck without licence compatibility; CShear's README says MIT but its root LICENSE was not present, so clean-room reimplementation only.

## Current source-audit count (through Batch 04)

- 23 distinct mechanisms have passed or conditionally passed source/mechanism review across Batches 01–04.
- Batch 04 added 15; duplicates, misleading labels, overlays and look-ahead-defective candidates are excluded from the unique count.
- 6 Python strategy modules exist in the branch; 5 are registered in the directional CSV runner, with 3 additional specialist score engines.
- The 100-mechanism source audit is still incomplete. No backtest has been started.


## Source audit — Batch 05

See [AUDIT_BATCH_05.md](AUDIT_BATCH_05.md). Batch 05 adds four source-reviewed mechanisms: hour-of-day seasonal entry/exit, hammer-pattern capitulation with oscillator confluence, ADX-regime stochastic exhaustion reversal, and Donchian-position/Keltner-width ratio regime. Eight additional sources were inspected and rejected or deduplicated as generic frameworks, risk overlays, defective rules or ordinary trend-indicator variants.

## Current source-audit count (through Batch 05)

- 27 distinct mechanisms have passed or conditionally passed source/mechanism review across Batches 01–05.
- 6 Python strategy modules exist in the branch; 5 are registered for the directional CSV runner, with 3 additional specialist score engines.
- 73 more distinct source mechanisms must be audited before the requested 100-mechanism gate is met.
- No historical backtest has started.


## Source audit — Batch 06

See [AUDIT_BATCH_06.md](AUDIT_BATCH_06.md). Batch 06 adds four unique mechanisms: psychological round-number bounce, tested liquidity-wall pull, top-N order-book imbalance z-score, and correlation-break recovery/relative lag. Round-number bounce is added to the candle runner; wall-pull and depth-imbalance are specialist L2 signals; correlation-break recovery is a paired-stream signal. The wall-bounce source is held conditional because its proximity checks do not verify that the wall is on the correct side of price.

## Current source-audit count (through Batch 06)

- 31 distinct mechanisms have passed or conditionally passed source/mechanism review across Batches 01–06.
- 69 more distinct mechanisms must be source-audited before the requested 100-mechanism gate is met.
- 6 Python strategy modules exist; 5 candle engines are registered in the CSV runner and 3 specialist score engines are registered separately.
- No historical backtest has started.


## Source audit — Batch 07

See [AUDIT_BATCH_07.md](AUDIT_BATCH_07.md). Batch 07 adds two conditional mechanisms: three-scale momentum confluence with slow-scale exits, and an ADX-switched trend-following/mean-reversion state machine. Both require the external Flint indicator library and stateful execution semantics before exact import. Other inspected files were deduplicated into existing momentum, squeeze, residual-stat-arb, mean-reversion, lead-lag and climax families.

## Current source-audit count (through Batch 07)

- 33 distinct mechanisms have passed or conditionally passed source/mechanism review across Batches 01–07.
- 67 more distinct mechanisms must be audited before the requested 100-mechanism gate is met.
- No historical backtest has started.


## Source audit — Batch 08

See [AUDIT_BATCH_08.md](AUDIT_BATCH_08.md). Batch 08 adds one conditional mechanism: ETF-flow / stablecoin-supply liquidity regime. It is not imported because the notebook's flow fixture is synthetic and needs real point-in-time flow histories. A distinct DXY/rates macro filter is rejected on the notebook's own multiple-testing and after-cost results; liquidation stress is deduplicated with volume-climax; remaining notebooks are duplicates or outside perpetual-futures scope.

## Current source-audit count (through Batch 08)

- 34 distinct mechanisms have passed or conditionally passed source/mechanism review across Batches 01–08.
- 66 more distinct mechanisms must be audited before the requested 100-mechanism gate is met.
- No historical backtest has started.


## Backtest infrastructure preparation (not a backtest run)

A separate source-style research path is now implemented:

- \`prepare_binance_feature_csv.py\`: reads Binance M1 archives, validates OHLCV/taker-buy fields and continuity, resamples to native 5m/15m/30m/1h/2h/4h bars, recomputes buy ratio from summed taker-buy and total base volume, and backward-as-of joins funding at the resampled candle OPEN.
- \`prepare_metrics_features.py\`: backward-as-of joins OI and taker long/short volume ratio metrics at candle OPEN and retains independent observation-age columns.
- \`source_backtest.py\`: next-open entries, hold-bar exits, stop-first SL/TP, long-only source exit flags, conservative gap handling or source-compatible fills, and train-only walk-forward selection. Signal grids are compressed to one byte per bar to avoid excessive memory on multi-asset grids.
- \`run_walk_forward.py\`: native source timeframes and parameter grids for funding mean reversion (81 configs, 15m), taker-buy momentum (108 valid configs, 5m), and OI/price quadrants (216 configs, 15m). It checks prefix invariance for every parameter set before walk-forward.
- Funding history older than 24 hours and OI/taker metrics older than 15 minutes are rejected by default. OI backtesting therefore requires continuous historical metrics; a short recent API window must not be forward-filled over a multi-year sample.

The upstream taker notebook selects SL/TP by comparing OOS Sharpe across separate walk-forward runs. That is OOS leakage. The Realcheck runner includes SL/TP in the training parameter grid and selects them on training data only. It also offers source-compatible fills for comparison, while defaulting to the user's existing conservative 5 bps fee + 2 bps slippage per side and conservative stop-gap handling.

The earlier \`run_csv_backtest.py\` is a smoke/adapter runner, not the final source-style walk-forward benchmark. No backtest has been started; the 100-mechanism audit gate remains in force.


## Source audit — Batch 09

See [AUDIT_BATCH_09.md](AUDIT_BATCH_09.md). Batch 09 adds two distinct OI-confirmed crash mechanisms: liquidation-wick reversal on falling OI and crash continuation on rising OI. Both require point-in-time delayed OI, 1m quote volume and stateful event execution; the upstream repository has no declared licence, so no code was copied. The fast L2 imbalance taker, passive maker and simulator quoting rules were inspected but deduplicated into existing order-book imbalance and market-making families. The cumulative accepted/conditional source-review count is 36 of 100. No historical Realcheck backtest has started.

## Source audit — Batch 10

See [AUDIT_BATCH_10.md](AUDIT_BATCH_10.md). Batch 10 adds one conditional options-implied-volatility complacency regime (low trailing 90-observation Deribit DVOL percentile predicts underperformance over a 60-day horizon). Its source reports five of five walk-forward periods confirming the direction on both BTC and ETH, but it is not a costed futures trade simulation and requires point-in-time DVOL publication timestamps. The source's CVD absorption and spot/perpetual CVD leadership mechanisms were separately audited and rejected for promotion on their own negative test results; funding velocity and flow-conditioned sweep/breakout variants were deduplicated. The cumulative accepted/conditional source-review count is 37 of 100; 63 remain. No historical Realcheck backtest has started.


## Source audit — Batch 11

See [AUDIT_BATCH_11.md](AUDIT_BATCH_11.md). Batch 11 adds volatility-scaled cross-sectional price momentum: rank a point-in-time multi-perpetual universe by lagged 14-day return divided by lagged 30-day volatility, then hold equal-weight top-30% longs and bottom-30% shorts as a dollar-neutral portfolio. This is distinct from time-series momentum and from the funding-ranked evaluator previously rejected as mislabeled. Source is MIT-licensed. The source's own OOS Sharpe claim is not accepted as our result; survivorship bias, missing funding/slippage and an unstable final OOS third remain material limitations. It needs a separate portfolio-level adapter, not the single-symbol candle runner. Cumulative accepted/conditional source-review count: 38 of 100; 62 remain. No historical Realcheck backtest has started.


## Source audit — Batch 12

See [AUDIT_BATCH_12.md](AUDIT_BATCH_12.md). Batch 12 adds four distinct profile/grid mechanisms: adaptive arithmetic/geometric range grid; POC proximity reversion; value-area re-entry fade; and low-volume-node traversal breakout. All four passed source/mechanism review but remain unpromoted pending exact event/fill state, rolling profile timing, and realistic OHLCV/L2 profile limitations. The source is Apache-2.0; no code was copied. DCA accumulation was inspected but not counted as independent alpha; order-flow, SMC, Elliott-wave, indicator-momentum and arbitrage bundles were rejected or deduplicated. Cumulative accepted/conditional source-review count: 42 of 100; 58 remain. No historical Realcheck backtest has started.


## Source audit — Batch 13

See [AUDIT_BATCH_13.md](AUDIT_BATCH_13.md). Batch 13 adds two conditional mechanisms: lagged seven-day DeFiLlama stablecoin-supply growth as a macro liquidity regime filter, and lagged seven-day Dune ERC-20 exchange netflow ranked cross-sectionally as a long/short futures factor. Both require point-in-time source timestamps and additional OOS verification; the ETF-flow input was a synthetic fixture, the macro DXY filter failed its own cost-adjusted risk test, and the liquidation proxy was deduplicated with the OI-confirmed crash family. No code copied. Cumulative accepted/conditional source-review count: 44 of 100; 56 remain. No historical Realcheck backtest has started.


## Source audit — Batch 14

See [AUDIT_BATCH_14.md](AUDIT_BATCH_14.md). Batch 14 adds one conditional model family: a dual-axis cross-sectional temporal-attention transformer with a monotonic quantile head, trained on causal normalized OHLCV panels and translated into dollar-neutral, risk-equalized long/short weights. The upstream README reports IC around 0.025 but explicitly says 5 bps taker friction compresses it near breakeven; no weights or code were copied because the repository has no declared licence. It requires a full multi-asset model pipeline and is not suitable for the candle-only runner. Cumulative accepted/conditional source-review count: 45 of 100; 55 remain. No historical Realcheck backtest has started.


## Source audit — Batch 15

See [AUDIT_BATCH_15.md](AUDIT_BATCH_15.md). Batch 15 adds one conditional mechanism: volume-clock VPIN toxicity-percentile regime switching. The inspected Binance implementation uses adaptive volume buckets, a lagged historical CDF excluding the current bucket, and next-open long/cash execution with fees, slippage and a two-day cooldown. It is not promoted to BTC/ETH perpetual testing yet: the upstream run manifest records 2,347 missing 1m candles across 15 intervals in its requested 2020–2026 spot history, with zero completed parameter trials, and the implementation is spot rather than perpetual-specific. No code copied. Cumulative accepted/conditional source-review count: 46 of 100; 54 remain. No historical Realcheck backtest has started.


## Broad crypto-futures source discovery — 2026-11-22

Added [CRYPTO_FUTURES_100_SOURCE_CATALOG.md](CRYPTO_FUTURES_100_SOURCE_CATALOG.md), a discovery scan of **109 unique GitHub repositories** returned by 26 targeted searches spanning perpetual-futures bots, funding/basis, order flow, liquidation, market making, statistical arbitrage, ML/RL, grid, breakout, mean reversion and backtesting. This exceeds the requested 100-source discovery breadth.

Important distinction: 109 is the number of unique candidate repositories catalogued, **not** the number of audited or accepted engines. Candidate repositories can be duplicates, forks, generic bot shells, spot-only implementations, or unverified. They must be source-inspected and deduplicated by mechanism. No source is accepted merely because its search title or README advertises a strategy. The catalogue defines a crypto-perpetual-native eligibility gate: funding cashflows, mark/index, fees/slippage, leverage/margin, liquidation and causal fills as applicable.

The user's instruction is to complete the remaining mechanism audit as one coherent research pass, with no artificial stopping after a handful of sources. The next audit work must use this broad candidate pool and additional academic/data/platform sources, inspect actual source files and retain ACCEPT / CONDITIONAL / REJECT outcomes. It must not label the 54 remaining mechanisms complete until source evidence is recorded. No five-year BTC/ETH backtest is claimed started by this discovery scan.
