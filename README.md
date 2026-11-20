# Impulse Retracer

A clean, independent implementation. Prior model source is not a dependency or design reference.

## Architecture
- Closed 1-hour candles detect strong impulse candles independently for every configuration.
- Completed 1-minute candles monitor retracement after each impulse.
- Cloudflare Worker runs every minute. A Durable Object serializes setup state, per-config cursors, pending candidates, deduplication and alert history.
- Candidates accumulate through each five-minute UTC window. At minute 00/05/10/... the engine selects the highest validated out-of-sample profit-factor configuration. Trade count breaks PF ties.
- One configuration is sufficient; there is no multi-config vote.
- No fixed 3/6-candle expiry. A setup remains active until the direction-specific boundary breaks: long below impulse low; short above impulse high.
- A retracement trigger is a candidate, not a fill. Execution must use a fresh quote received after the alert. Never backfill a pre-alert price.
- Configurations without positive, explicitly validated PF are not eligible for alert selection.

## Cloudflare deployment
GitHub Actions deploys the Worker. Add repository secrets CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. Add Worker secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Vars: SYMBOLS (default BTCUSDT,ETHUSDT) and BINANCE_API_BASE.

Cloudflare cron is best-effort and may be delayed; a one-minute schedule does not guarantee exact wall-clock delivery.

## Research gates
The five starter configurations in config/strategies.js are parameter candidates, not proven profitable strategies. config/pf-rankings.js is intentionally empty: populate it only with reproducible out-of-sample backtest results. The next engineering stage is a historical replay harness using the same signal rules and realistic fees, slippage, and post-alert fills. No exchange orders are submitted by this Worker.
