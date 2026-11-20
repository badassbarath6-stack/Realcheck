# Impulse Retracer

Independent implementation. The prior model source is not a dependency or design reference.

## Minute execution
- Cloudflare Cron is configured as `* * * * *`: one scheduled invocation each minute.
- On **every successful minute poll**, inspect the currently forming H1 candle for each enabled configuration. The first qualifying live H1 snapshot is frozen once per symbol/config/hour.
- ATR is calculated from completed H1 history only; the current forming H1 candle is the impulse candidate.
- On the same poll, process completed M1 candles. Only M1 bars after the detection minute can trigger a retracement.
- There is no five-minute batch and no wait for H1 close.
- A setup remains active until its impulse boundary is breached; no fixed 3/6-candle expiry.
- A trigger reference is not a fill. Any execution must use a fresh quote after the alert.

## Initial candidate configurations
The five entries IR-A01 through IR-A05 are **starter parameter variants**, not the earlier Top-100 configurations and not proven profitable. They vary ATR period, impulse range/body thresholds, retracement depth and confirmation level. Each currently specifies a 1.0x structural stop multiplier and a 5R target for the planned historical outcome simulation. The PF registry remains empty until a reproducible backtest establishes actual results.

## Cloudflare
Cron is best-effort and executes in UTC; exact wall-clock delivery is not guaranteed. A missed invocation can still leave an M1 history gap if the outage exceeds the worker's fetched candle window. Add GitHub secrets `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`; add Worker secrets `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. Vars: `SYMBOLS` (default BTCUSDT,ETHUSDT) and `BINANCE_API_BASE`.

## Research rules
Public `Realcheck` is the only backtesting workspace. The private repository is a code mirror only. Do not add PF rankings without actual out-of-sample evidence. No exchange orders are submitted by this worker.
