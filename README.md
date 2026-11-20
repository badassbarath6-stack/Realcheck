# Impulse Retracer

## Model definition
- One model containing exactly the 100 approved configurations from `model3_asset_independent_top100_rr2.csv`.
- Configuration IDs `IR-T001` through `IR-T100` preserve CSV ranks 1–100 and each row's timeframe, ATR period, impulse ATR, ADX range, RSI mode, retracement, RR, and pending-bars value.
- No five-configuration starter set and no ten-model split.

## Execution and alert architecture
- Cloudflare Cron invokes the Worker every minute.
- Every successful minute invocation inspects the currently forming H1 candle against all 100 configurations. ATR history uses completed H1 candles only.
- The Worker evaluates only the latest completed M1 candle. It does not backfill stale entry alerts.
- Every qualifying configuration setup is retained independently; no PF selection occurs at impulse detection.
- When one configuration completes its M1 entry condition, it is eligible to alert immediately.
- If multiple configurations complete during the same M1 execution for the same symbol/H1 impulse, the highest validated PF wins. PF is not compared across different impulses.
- A successful alert locks that symbol/H1 impulse across all 100 configurations. Other configurations cannot emit duplicate alerts from that impulse.
- A new H1 impulse is eligible for a new alert.
- Structural stop multiplier is 1.0x; target RR is read from each approved CSV row (2.0R).
- A single candidate does not require a PF ranking. Multiple same-minute candidates require validated PF values for every competing configuration.

## Current verification boundary
The one-minute scheduling, 100-row loading, latest-completed-M1 processing, same-minute PF selection, and per-impulse duplicate suppression are covered by unit tests.

**The signal-definition work is not yet complete or deployment-ready:** the current impulse detector applies ATR-range strength and the entry evaluator applies the single retracement touch, but ADX/RSI filters and the precise `pending_bars` expiry semantics are not yet wired into live evaluation. The PF registry is also empty, so simultaneous multi-configuration triggers will be withheld until verified PF rankings exist. Do not deploy this branch as a fully validated trading model yet.

## Cloudflare
Cron: `* * * * *`. Default symbols: BTCUSDT, ETHUSDT. No exchange orders are submitted by this Worker.
