# Top-10 engine live integration (research branch)

This branch starts the first ten-engine integration without changing any source strategy.

## Engine identity and qualification

The exact ten source IDs, original names, source file paths, and the prior stress-cost pooled PF are in `config/top10-engine-registry.json`. The preliminary 1.30 stress-PF screen passes six engines; four remain in the registry but are research-only. Pooled PF is not sufficient for production approval.

## Minimum target-distance rule

The shared gate is `cloudflare/src/min-target-gate.js`. It accepts the native target produced by an engine adapter and rejects a candidate unless the **net target distance after estimated round-trip fees and slippage** is at least 8 pips. It does not alter the engine's native target or exits. Unknown symbols or missing pip sizes fail closed.

Initial configurable crypto pip convention:
- BTCUSDT: 1 pip = $1.00
- ETHUSDT: 1 pip = $0.10
- Minimum net target = 8 pips
- Cost defaults = 7.5 bps fee + 2.5 bps slippage per side

This is a project convention, not a Binance-defined pip standard. Override with `PIP_SIZE_BTCUSDT`, `PIP_SIZE_ETHUSDT`, and related Worker vars if the convention changes.

## Critical implementation boundary

This commit provides the source registry and tested shared gate only. It does **not** claim the ten original strategy adapters are implemented, the Worker is connected to them, or live alerts are active. Several engines have native DCA/ROI/trailing/MTF behavior that must be preserved rather than approximated.

## Backtesting requirement

The next validation must replay each source-equivalent adapter on Binance USD-M BTCUSDT and ETHUSDT candles, with the 8-pip gate applied **before** trade entry. It must report baseline vs gated trades, net PF, win rate, net PnL, drawdown, target-distance distribution, and symbol/timeframe/year breakdown under baseline and stress costs. Filtering already-closed trades by realized move is not a valid substitute for this pre-entry replay.
