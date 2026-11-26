# Volume Explosion MTF Research

Isolated research branch: `research/volume-explosion-mtf`. This work does not modify the live Impulse Retracer, the existing Top-100 research, or any previously approved engine.

## Scope
- Binance USD-M perpetual futures: BTCUSDT and ETHUSDT.
- Three years: 2023-11-25 through 2026-11-24 UTC.
- All six timeframes: 1m, 5m, 15m, 30m, 1h, 4h.
- Ten standalone volume mechanisms plus all valid execution-timeframe / higher-timeframe directional-confirmation pairs.
- Base-asset traded volume and taker-buy base volume are retained from Binance USD-M kline archives.

## Core rule
For each completed candle, calculate `volume / mean(previous 20 completed candle volumes)`; the current candle is excluded from its baseline. A bullish signal requires a bullish candle; bearish requires a bearish candle. Entry is at the next candle open, never at the already-closed signal candle price.

## Engine families
V01-V05: volume ratios 1.5x, 2x, 2.5x, 3x, 4x.
V06: 2x + body/range >= 0.60.
V07: 2x + candle range >= 1.20 ATR(14).
V08: 2x + 20-bar high/low breakout.
V09: 2x + taker-buy volume pressure aligned with candle direction.
V10: 2x + body/range >= 0.55 + range >= 1 ATR.
MTF models: 2x volume trigger on each execution timeframe, confirmed by the latest fully completed candle on each strictly higher timeframe. No forming higher-timeframe candle is read.

## Risk and execution assumptions
- ATR(14) structural distance: 1.0x and 1.5x.
- Targets: 1.2R, 2R, 3R.
- Fees: 5 bps per side; slippage: 2 bps per side.
- Next-bar open entry. Stop-first when stop and target are both touched in one candle.
- One position at a time per model/configuration.
- Chronological train, validation and untouched OOS periods are reported separately.

## Known research limitation
Funding payments are not yet included in the first pass. The results must therefore be labelled fee/slippage-adjusted, not fully net of all perpetual-futures costs. Funding-rate integration is a required next validation step before promoting any engine. No profitability is assumed and no engine is deployed.
