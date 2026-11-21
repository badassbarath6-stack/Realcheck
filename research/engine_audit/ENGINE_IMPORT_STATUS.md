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
