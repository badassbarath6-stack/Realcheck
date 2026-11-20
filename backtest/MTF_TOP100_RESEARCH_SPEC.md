# Impulse Retracer — Two-Year Multi-Timeframe Impulse-Only Research

Status: corrected research specification. No backtest results are claimed until a complete run and artifact verification.

## Objective
Discover the strongest raw impulse/retracement configurations independently on every supported timeframe from 5m through 4h. This is not MTF confirmation: each timeframe has its own impulse detector, setup lifecycle, entries, trades, metrics, and ranked configuration universe.

The old H1 Top-100 file is historical provenance only. Do not use it as a candidate source or seed the new rankings.

## Timeframes and instruments
- Instruments: BTCUSDT and ETHUSDT, Binance USD-M perpetuals.
- Independent impulse timeframes: 5m, 15m, 30m, 1h, 2h, 4h.
- Scan forming impulse candles on the minute execution clock, using only OHLC information available as of each minute.
- Each timeframe uses its own prior completed candles for indicator warmup and its own ATR and impulse calculations. Never use another timeframe as a confirmation/filter.
- M1 is the execution/entry observation stream. A trigger is recognized only after the M1 candle completes; simulated fill is at the next M1 open.
- Do not pool timeframe candidates into a single impulse or ranking universe. Produce separate results and rankings for each timeframe, as well as a cross-timeframe comparison report.

## Deliberately excluded for this discovery phase
This phase isolates impulse/retracement quality. Do not apply or search:
- RSI modes or RSI thresholds.
- ADX filters or ADX ranges.
- MTF confirmation/agreement.
- Candle-body confirmation, volume, EMA, session, news, or other filters.
- Any other signal-quality filter not explicitly listed in the search grid below.

These factors can be assessed only after the raw impulse configurations have been identified.

## Fixed execution/model architecture
- Preserve the live impulse-retracer lifecycle: forming-candle impulse detection, retained pending setups, M1 retracement trigger, next-M1-open simulated fill, and one alert per symbol/timeframe/impulse.
- Candidate configurations remain independently tracked until their setup expires. If several configurations trigger on the same M1 minute for the same symbol/timeframe/impulse, select among only those simultaneous contenders using training-period PF. Never compare candidates that triggered on different minutes. A sole contender bypasses PF gating.
- Pending expiry is three complete bars of that configuration's own impulse timeframe: the impulse candle plus the next three complete timeframe bars; expire at the following timeframe-bar open. This must be tested for every timeframe.
- Stop-loss (SL) is anchored to the opposite extreme of the impulse candle, with a configurable ATR buffer beyond that extreme. Search buffer values: 0.0, 0.2, 0.4, 0.6, 0.8 and 1.0 × the prior completed same-timeframe ATR. For a long, SL is below the impulse low; for a short, SL is above the impulse high.
- Take-profit (TP) is calculated from the actual entry-to-SL risk distance. Search RR targets: 1.2R, 1.5R, 2.0R, 2.5R, 3.0R and 4.0R. Each configuration must use its own SL buffer and RR consistently in candidate geometry, fill validation and trade simulation.
- Reject invalid geometry (non-positive risk, stop on the wrong side of entry, or target on the wrong side of entry). Do not silently substitute a different SL or RR.
- No intrabar look-ahead. If stop and target are touched in the same M1 candle, stop-first. Adverse stop gaps fill at the candle open.
- Apply the existing execution-cost model consistently: 5 bps fee per side, and 2 bps / 7 bps slippage per side stress scenarios. Include official Binance USD-M funding where archive coverage is available; disclose any gaps.
- Correct Wilder SMA seed and recurrence for ATR. ATR is calculated only on the same timeframe as the impulse detector, using prior completed candles. Do not add RSI/ADX calculations to this phase.
- Research branch only. Do not deploy, change the live worker, or publish/update the production PF registry.

## Period, data and split
- UTC start: 2024-11-20 inclusive.
- UTC end: 2026-11-20 exclusive.
- Chronological split separately for each symbol/timeframe: first 60% training, next 20% validation, final 20% untouched OOS.
- No parameter selection using final OOS.
- Fetch sufficient pre-period warmup history for the longest ATR period and highest timeframe.
- Verify archive checksums, M1 timestamp continuity, OHLC sanity, resampled timeframe boundaries, duplicates/gaps, and as-of-time aggregation. Record source URLs and checksums.

## Search factors (only these)
- Same-timeframe ATR period: 10, 14, 20, 28.
- Impulse threshold: 2.0, 2.2, 2.4, 2.6, 2.8, 3.0 × prior completed same-timeframe ATR.
- Retracement level: 61.8%, 66.7%, 70.7%, 75.0%, 78.6%, 82.0%.
- SL buffer beyond the structural opposite impulse extreme: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0 × prior completed same-timeframe ATR.
- TP/RR: 1.2R, 1.5R, 2.0R, 2.5R, 3.0R, 4.0R.
- Pending expiry: fixed at three complete bars of the configuration's own impulse timeframe.

This is 5,184 raw parameter combinations per timeframe (4 × 6 × 6 × 6 × 6), or 31,104 across all six timeframes before symbol-specific performance evaluation. Do not silently add or prune factors. If runtime requires batching, partition the complete grid deterministically and record each batch and its completion status.

## Selection and reporting
- Evaluate configurations independently for training and validation. Apply one-alert-per-impulse selection with same-minute-only PF competition.
- Require at least 30 completed training trades and 30 validation trades for qualified ranking. Report low-sample configurations separately rather than hiding them.
- Rank within each timeframe using validation performance and robustness, including net PF, expectancy, drawdown, sample size, BTC/ETH consistency, long/short split, and monthly/quarterly stability.
- Freeze each timeframe's candidate ranking from validation before running that timeframe's final 20% OOS.
- Do not force 100 qualified configurations. Report the number that actually pass the gates for each timeframe. If a 100-row compatibility export is needed, mark unqualified rows explicitly.
- Run the final OOS once after the validation selection is frozen.

## Deliverables
- Immutable search manifest with exact parameter grid, timeframe definitions, split timestamps, cost assumptions and software revision.
- Source/data checksums and integrity report.
- Full per-configuration metrics and candidate universe for each timeframe.
- Separate validation-ranked configuration CSVs for 5m, 15m, 30m, 1h, 2h and 4h.
- Frozen final OOS trades and summaries per timeframe, plus a cross-timeframe comparison.
- Metrics: trades, wins/losses, win rate, gross/net bps, PF, expectancy, max drawdown, average win/loss, stop/target/time exits, holding time, BTC/ETH splits, long/short splits, monthly/quarterly stability, and 7-bps stress results.
- Reproducibility metadata. No partial run may be labelled complete.

## Acceptance gates
1. Tests prove independent forming-candle impulse detection on all six timeframes, using only information available at each minute.
2. Tests prove same-timeframe ATR, retracement levels, M1 trigger and next-M1-open fill timing.
3. Tests prove no RSI, ADX, MTF confirmation, candle-body, volume, EMA, session or other excluded filter is applied.
4. Tests prove each SL buffer and RR value changes actual stop/target prices and is respected by candidate geometry, fills and trade simulation; also prove separate per-timeframe setup expiry, one-alert-per-impulse, same-minute-only PF competition, single-candidate bypass, stop-first and adverse-gap handling.
5. Wilder ATR initialization and warmup are independently verified.
6. Both assets and all six timeframes complete the full 144-combination grid; no partial output may be labelled complete.
7. Final OOS remains untouched until validation rankings are frozen. No live configuration or production PF registry is changed.
