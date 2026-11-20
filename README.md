# Impulse Retracer

## Approved model
- Exactly one model containing the 100 approved configurations in `config/model3_asset_independent_top100_rr2.csv`.
- Live parameters in `config/strategies.js` are checked against that CSV by the backtest runner.
- IDs `IR-T001` through `IR-T100` preserve source ranks 1–100. All rows remain H1, RR 2.0; each retains its own ATR period, impulse threshold, ADX band, RSI mode, retracement and pending-bars value.
- No five-config starter set, no ten-model split, no substitute configurations.

## Live execution
- Cloudflare Cron runs every minute.
- Each minute, the current H1 candle is reconstructed from completed M1 candles plus the current M1 open. It is evaluated against all 100 configurations; H1 impulse detection does not wait for the hour to close.
- ATR is Wilder-smoothed from completed H1 bars and uses the prior completed H1 ATR. ADX(14) and RSI(14) are recalculated from the forming H1 snapshot.
- Impulse condition: directional H1 candle and H1 high-low range at least `impulse_atr × prior ATR`; ADX must be within each configuration's inclusive band.
- RSI `none`: no RSI gate. `exact`: long 50–70, short 30–50. `loose`: long 50–75, short 25–50.
- When a configuration first qualifies in an H1 hour, its impulse high/low/range are frozen for that configuration and impulse.
- `pending_bars=N`: setup remains eligible from its first detection minute until the opening of H1 hour `impulse_open + (N+1) hours`. Thus N=3 includes the rest of the impulse hour plus the next three H1 bars.
- Minute retracement touch completes the entry condition. The alert is generated after that M1 candle closes; a real fill must use a fresh quote after the alert, not the already-completed candle's touch price.
- One configuration can alert alone. If multiple configurations complete on the same M1 candle for the same impulse, choose the highest validated PF. Configurations completing in different minutes are not compared.
- After a successful alert, lock that symbol/H1 impulse across all 100 configurations. A new H1 impulse can alert independently.
- Structural stop is the opposite impulse extreme (1×); target RR comes from the approved row (2R).

## Five-year research
- Runner: `backtest/top100_five_year_h1_m1.py`.
- Period: 2021-11-19 through 2026-11-18 inclusive (end-exclusive 2026-11-19 UTC).
- Assets: BTCUSDT and ETHUSDT Binance USD-M perpetuals.
- Official Binance Vision 1m archives are SHA-256 verified and checked for continuous coverage; hourly candles are aggregated from 1m data.
- Historical detection uses the same minute-by-minute forming-H1 snapshot; entry is alerted at the trigger M1 close and filled at the next M1 open.
- Exits: 1× structural stop, 2R target, stop-first on same-minute stop/target collisions, adverse-gap stop fills, 24-hour maximum hold.
- Costs: 5 bps fee per side; 2 bps/side baseline slippage and 7 bps/side stress; official Binance funding history.
- The first 60% of the five-year window estimates per-configuration PF. The final 40% is the out-of-sample model validation. A separate full-window retrospective stream is explicitly labelled in-sample.
- Outputs include model trades, per-config metrics, yearly OOS metrics, funding coverage, archive checksums and generated PF rankings.

## Verification and deployment boundary
- JavaScript unit tests cover Top-100 loading, forming-H1/M1 timing, ADX/RSI filters, pending expiry, same-minute PF selection and one-alert-per-impulse locking.
- Python unit tests cover next-minute fills, stop-first handling, same-minute PF selection and exact source CSV matching.
- This branch is a draft research implementation. It is not deployed to Cloudflare and does not submit exchange orders.
- Public `Realcheck` is the only backtesting workspace. The private repository remains a code mirror, not a backtest workspace.
