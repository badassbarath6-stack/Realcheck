# Impulse Retracer

Independent implementation. The previous model source is not a dependency or design reference.

## Architecture
- Every successful one-minute Cloudflare poll checks the latest completed 1-hour candle for a new strong impulse, across every enabled configuration. Hourly candle checks are deduplicated by symbol, config and candle close time.
- The same poll processes completed 1-minute candles to monitor retracement and setup invalidation.
- Cloudflare Worker cron: every minute. Durable Object persists setups, cursors, candidate queue, deduplication and alert history.
- Every poll immediately ranks all configurations triggered in that poll by validated out-of-sample PF, then trade count, and emits at most one alert. There is no five-minute batch.
- One configuration is sufficient; no multi-configuration confirmation is required.
- No fixed 3/6-candle expiry. A setup stays active until its invalidation boundary: long below impulse low; short above impulse high.
- A retracement trigger is a candidate, not a fill. Any execution must use a fresh quote after the alert; no pre-alert backfill.
- Configurations without positive, explicitly validated PF are not eligible.

## Cloudflare
GitHub Actions deploys the Worker. Add repository secrets CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID. Add Worker secrets TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. Vars: SYMBOLS (default BTCUSDT,ETHUSDT) and BINANCE_API_BASE.

Cron is best-effort; Cloudflare does not guarantee exact wall-clock execution. The worker checks for the latest closed hourly bar on every poll, so a missed poll does not make it wait for the next hour, provided the API history covers the missed minute candles.

## Research
The five starter configurations are unproven candidates. PF registry is intentionally empty until real out-of-sample backtesting establishes valid rankings. Public repository is the sole backtesting workspace; the private repository mirrors the code. No exchange orders are submitted by this worker.
