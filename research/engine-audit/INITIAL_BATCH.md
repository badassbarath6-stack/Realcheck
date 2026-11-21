# Initial 100-Mechanism Audit

Branch: `research/100-mechanism-audit-import` (based on `research/mtf-top100-two-year`).

This is a source audit, not a profitability claim. No new backtests have started.

## Source audit ledger

| Mechanism | Source | Audit | Platform status / blocker |
|---|---|---|---|
| Funding-rate mean-reversion fade | [signals.py](https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_1_funding_mr/signals.py) | PASS mechanism | Independently implemented in `strategies.py`. Requires funding + buy-ratio columns. Upstream root had no visible licence, so no verbatim source copied. |
| Taker-buy-pressure momentum | [signals.py](https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_2_taker_momentum/signals.py) | PASS mechanism | Independently implemented in `strategies.py`. Requires aggressor buy volume / total volume, which must be ingested by a future data adapter. |
| OI/price quadrants | [signals.py](https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_3_oi_divergence/signals.py) | CONDITIONAL | Independently implemented as a research candidate, not promoted. OI falling cannot identify which side is closing; reversal labels remain hypotheses. Requires OI + taker long/short volume ratio. |
| Avellaneda–Stoikov funding-aware market making | [source](https://github.com/ib2003dev/market-making-sim/blob/main/src/market_making_sim/strategies/avellaneda_stoikov.py) | PASS mechanism | Not imported into bar runner. Needs timestamped L1/L2, trades/fills, funding and event-driven queue simulation. Source repo uses WTFPL. |
| Naive constant-spread maker | [source](https://github.com/ib2003dev/market-making-sim/blob/main/src/market_making_sim/strategies/naive.py) | REJECT as duplicate | Baseline/control for market making, not an independent alpha mechanism. |
| Funding-adjusted cross-venue OU spread | [signal source](https://github.com/yoho369/crypto-perpetual-arbitrage/blob/main/src/statistical_eng.py), [execution source](https://github.com/yoho369/crypto-perpetual-arbitrage/blob/main/src/backtest_eng.py) | CONDITIONAL / current code fails | Requires synchronized multi-venue BBO and funding. `liquidity_toll.rolling(...).median().bfill()` leaks future values; full-sample ADF cannot be used for live selection. Must be corrected before import. |
| Spot/perp delta-neutral funding carry | [source](https://github.com/idreesm18/crypto-perp-funding-carry/blob/main/src/2_signal.py) | PASS mechanism | Not imported into directional bar runner. Needs spot + perp prices, funding settlement schedule and matched hedge accounting. |
| Dated-futures cash-and-carry basis with TWAP hedge | [scanner](https://github.com/tkwsean/SpotFuturesArbitrage/blob/main/scanner.py), [replay](https://github.com/tkwsean/SpotFuturesArbitrage/blob/main/backtest_replay.py) | PASS mechanism; replay fidelity limited | Not imported into directional bar runner. Needs spot + dated futures, expiry and inverse-contract accounting. Existing replay's always-fill assumptions are not execution-grade. |
| Funding z-score fade / fixed funding threshold | [z-score](https://github.com/xy3293/crypto-strategy-backtest/blob/main/backtest/strategies/funding_zscore_fade.py), [threshold](https://github.com/xy3293/crypto-strategy-backtest/blob/main/backtest/strategies/funding_extreme_threshold.py) | REJECT as two separate engines | Same funding-extreme contrarian family; count once, not twice. |
| Compression-conditioned swing breakout | [source](https://github.com/xy3293/crypto-strategy-backtest/blob/main/backtest/strategies/jlaw_swing_breakout_4h.py) | CONDITIONAL pending deduplication | 30-bar range compression + trend-aligned break; compare with Donchian/Turtle before counting as distinct. |

## Imported platform files

- `research/engine-audit/strategies.py`: pure-Python signal adapters for funding fade, taker-buy pressure momentum and conditional OI/price quadrants.
- `research/engine-audit/ADAPTER_CONTRACT.md`: required point-in-time input/output contract and promotion boundaries.
- `tests/research/test_audited_strategies.py`: unit tests for lagging, warmup, missing inputs and OI quadrants.
- `.github/workflows/audit-strategy-adapters.yml`: isolated Python test workflow for this branch.

All imported strategies emit a signal at bar close with `execution_rule=next_bar_open`. They do not place orders or modify the existing impulse-retracement engine.

## Realcheck compatibility

The existing `research/impulse_retracer_backtest.py` remains unchanged. It is a dedicated impulse/retracement runner, not a general strategy-plugin runner. Its Binance kline parser retains OHLC only; it does not preserve taker-buy volume, OI, long/short ratios, order-book depth, trade queue or synchronized multi-venue BBO.

The new adapters therefore define their own normalized feature contract and are not yet wired to the impulse runner. Market making and cross-venue strategies need separate event-driven execution adapters. Do not approximate these with candle highs/lows.

## Current verified status

- 8 distinct candidates passed or conditionally passed at mechanism/source level (the 30-bar compression breakout remains pending deduplication).
- 2 passed directional signal engines independently implemented in the platform.
- 1 conditional OI strategy independently implemented for research only.
- 2 other mechanism classes (market making and cross-venue OU) remain blocked by execution/data contracts or source defects.
- 2 carry/basis classes remain separate portfolio-leg strategies, not directional signals.
- 1 duplicate family rejected as multiple engines.
- No backtests launched. The agreed gate remains: complete and deduplicate the 100-mechanism source audit before backtesting.
