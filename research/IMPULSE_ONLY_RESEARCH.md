# Impulse Retracer — Clean Impulse-Only Research

Status: scope reset; implementation and backtest are not yet complete.

## Objective
Research only the existing Impulse Retracer concept, starting with a clean configuration search. Preserve the deployed model source and its runtime dependencies. Do not reuse historical Top-100 backtest outputs or rankings as research inputs.

## Instruments and independent timeframes
- BTCUSDT and ETHUSDT, Binance USD-M perpetuals.
- Independent impulse timeframes: 5m, 15m, 30m, 1h, 2h and 4h.
- Each timeframe has its own ATR, forming-candle impulse detection, pending setup lifecycle, M1 trigger, trade simulation and ranking. No cross-timeframe confirmation.
- Use M1 data for as-of-minute forming-candle detection and execution.
- A retracement trigger is known only after its M1 candle completes; fill at the next M1 open.

## Search grid
- ATR period: 10, 14, 20, 28.
- Impulse threshold: 2.0, 2.2, 2.4, 2.6, 2.8, 3.0 × prior completed same-timeframe ATR.
- Retracement: 61.8%, 66.7%, 70.7%, 75.0%, 78.6%, 82.0%.
- Structural SL buffer: 0.0, 0.2, 0.4, 0.6, 0.8, 1.0 × prior completed same-timeframe ATR, beyond the opposite impulse extreme.
- TP/RR: 1.2R, 1.5R, 2.0R, 2.5R, 3.0R, 4.0R.
- Pending expiry: impulse candle plus next three complete bars of that same timeframe; expire at the following timeframe-bar open.
- 5,184 configurations per timeframe; 31,104 total per symbol. Evaluate BTC and ETH separately.

## Exclusions
No RSI, ADX, MTF confirmation, candle-body confirmation, volume, EMA, session, news, or any other extra signal-quality filters. Candle direction is used only to identify long versus short impulse direction; it is not an additional confirmation gate.

## Execution and accounting
- No look-ahead: only information available at each minute may be used.
- Same-minute contenders only: for a given symbol/timeframe/impulse, only configurations triggered in the same M1 minute compete by training-period PF. If multiple trigger minutes exist, the earliest trigger minute owns the impulse; later triggers cannot displace it. A sole contender bypasses PF comparison.
- Stop-loss is opposite impulse extreme plus/minus its own ATR buffer. Target is based on actual entry-to-stop risk and that configuration's RR.
- Invalid geometry is rejected; no silent substitution.
- If SL and TP are touched in one M1 candle, stop-first. Adverse stop gaps fill at candle open.
- Apply 5 bps fee per side and 2 bps / 7 bps slippage-per-side stress tests. Include Binance USD-M funding where complete archive data is available and explicitly report coverage.
- Wilder ATR uses an SMA seed followed by Wilder recurrence; only prior completed same-timeframe candles contribute to the ATR used for impulse detection.

## Period and evaluation
- UTC period: 2024-11-20 inclusive through 2026-11-20 exclusive.
- Obtain sufficient pre-period warmup data.
- Chronological split: 60% training, 20% validation, 20% untouched OOS.
- Freeze validation selections before running OOS once.
- Minimum 30 completed trades in both training and validation for qualified ranking; show low-sample configurations separately.
- Do not force 100 candidates.

## Required outputs
Immutable manifest; data checksums and integrity report; full per-configuration metrics; separate timeframe validation rankings; frozen OOS trades and summaries; cross-timeframe comparison; reproducibility metadata. Report trades, wins/losses, win rate, gross/net bps, PF, expectancy, drawdown, average win/loss, exit reasons, holding time, asset and direction splits, monthly/quarterly stability, and 7-bps stress.

## Safety boundary
Research-only branch. Never deploy research code, modify the live worker, update production PF rankings, or use old Top-100 results as inputs. A partial run must never be labelled complete.
