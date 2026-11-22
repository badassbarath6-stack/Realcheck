# Source Audit — Batch 15

Scope: inspect the Binance 1-minute VPIN research implementation in djienne/VPIN_PYTHON_CRYPTO, including volume-bucket construction, causal percentile calculation, position rules, execution timing, costs, validation tests and the retained run manifest.

## New distinct mechanism accepted conditionally

| Mechanism | Inspected source | Exact mechanism | Decision |
|---|---|---|---|
| Volume-clock VPIN toxicity percentile regime switch | [vpin_calculator.py](https://github.com/djienne/VPIN_PYTHON_CRYPTO/blob/main/vpin_calculator.py), [vpin_backtest.py](https://github.com/djienne/VPIN_PYTHON_CRYPTO/blob/main/vpin_backtest.py), [config.json](https://github.com/djienne/VPIN_PYTHON_CRYPTO/blob/main/config.json), [run manifest](https://github.com/djienne/VPIN_PYTHON_CRYPTO/blob/main/docs/vpin_guide_assets/run_manifest.json) | Estimate buy/sell volume from Binance taker-buy base volume, split each 1m candle proportionally across adaptive volume buckets calibrated from the preceding 90 complete UTC days, compute rolling VPIN as summed absolute buy-minus-sell volume divided by total volume across the last N buckets, then calculate a rolling historical CDF that excludes the current bucket. The strategy is long/cash: enter at the next candle open when the known CDF is below 0.99 and flat, exit at the next open when CDF is at/above 0.99, then apply a two-day cooldown. It uses a shared cash/quantity simulator and explicit per-side fee/slippage. | CONDITIONAL PASS as a distinct volume-clock order-flow-toxicity regime strategy. The volume-synchronized bucketing and lagged historical toxicity rank are materially different from ordinary candle-volume exhaustion, taker-ratio momentum, and OI/liquidation signals. Not imported or counted as BTC/ETH futures-ready: inspected implementation is configured for Binance spot candles and a long-or-cash portfolio, and its run manifest records a failed 2020–2026 coverage validation (2,347 missing 1m candles over 15 intervals; no grid or Optuna trials completed). Repository metadata reports no declared licence. |

## Causality and execution audit

- Adaptive bucket targets are calculated from rolling ADV of preceding complete UTC days and shifted by one day; incomplete days are excluded.
- Buy/sell volume is allocated proportionally using the candle's taker-buy base volume. This is an approximation to trade-level volume bucketing, not exact tick-level VPIN.
- Bucket timestamps are the source candle close plus 1 ms. The CDF reference excludes the current bucket, and the strategy joins the latest available CDF backward to candle open before deciding an action.
- Orders are modeled at the next candle open with adverse slippage and fees on both entry and exit. The strategy's rule is long/cash, not a directional short/long engine.
- The source tests cover numerical examples, candle coverage, causality, execution, costs and train-only selection. The run manifest reports 33 tests passing, but zero completed grid trials and zero completed Optuna trials because the requested history failed coverage validation.
- The guide explicitly rejects replacing the failed 2020-start study with a shorter interval without treating that as a separate study choice. No profitability result is imported or inferred.

## Realcheck import boundary

- This is a unique mechanism family, but promotion to a BTC/ETH perpetual-futures backtest is blocked until a futures-specific version is justified and tested. Spot taker flow and futures taker flow are not interchangeable by assumption.
- A valid port must preserve volume-clock buckets, lagged ADV calibration, partial-bucket carry, CDF history excluding the current observation, next-open execution, cooldown, and long/cash portfolio accounting. Do not replace it with a candle-volume threshold or a fixed-timeframe proxy.
- Use point-in-time BTCUSDT and ETHUSDT perpetual trade/taker-buy data. Validate completeness and exchange archive checksums; the 1m candle feed alone does not recover true trade-level bucket ordering.
- The upstream repository has no declared licence. Do not copy its code; any later implementation must be clean-room and separately tested.

## Batch 15 tally

- 1 new distinct source-inspected mechanism accepted conditionally.
- No code copied or imported; no historical Realcheck backtest started.
