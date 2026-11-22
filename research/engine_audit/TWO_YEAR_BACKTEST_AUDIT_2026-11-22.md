# Two-Year Backtest Audit — 2026-11-22

## Verified execution

- Repository: `badassbarath6-stack/Realcheck`
- Branch used by the runner: `research/mtf-top100-two-year`
- Workflow: [Impulse Retracer Full Two-Year Backtest](https://github.com/badassbarath6-stack/Realcheck/actions/runs/44860180033)
- Run ID: `44860180033`
- Runner commit: `e4682fb7c62dff292b2ba1675aebae1fd76e2f15`
- Workflow result: success; validation, all 12 symbol/timeframe jobs, and aggregation succeeded.
- Window: 2024-11-20 00:00 UTC inclusive to 2026-11-20 00:00 UTC exclusive.
- Instruments: Binance USD-M perpetual BTCUSDT and ETHUSDT.
- Timeframes: 5m, 15m, 30m, 1h, 2h, 4h.
- Search space: 4 ATR periods × 6 impulse thresholds × 6 retracements × 6 stop buffers × 6 reward/risk values = 5,184 configurations per symbol/timeframe; 62,208 configuration/timeframe evaluations across the 12 jobs.
- Data checks: M1 gap count was zero in every manifest; funding history was included (2,283 funding rows reported per pair/timeframe summary).
- Method: forming-timeframe impulse scan on M1; next-M1-open entry; 60% train / 20% validation / 20% OOS; funding included; baseline and higher-slippage stress results emitted. The run generated per-config metrics, selected trades, validation rankings, manifests, and combined comparisons.

## OOS results

The aggregate ranks the best validation-qualified configuration in each symbol/timeframe cell and reports that configuration's OOS result. Blank values mean no configuration passed the minimum validation-trade qualification.

| Instrument | TF | Qualified configs | OOS trades | OOS win rate | OOS PF | OOS net |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 5m | 8 | 98 | 19.39% | 0.4905 | -1,289.10 bps |
| BTCUSDT | 15m | 2 | 35 | 42.86% | 0.6987 | -394.44 bps |
| BTCUSDT | 30m | 0 | — | — | — | — |
| BTCUSDT | 1h | 0 | — | — | — | — |
| BTCUSDT | 2h | 0 | — | — | — | — |
| BTCUSDT | 4h | 0 | — | — | — | — |
| ETHUSDT | 5m | 7 | 44 | 27.27% | 0.4533 | -818.76 bps |
| ETHUSDT | 15m | 2 | 62 | 19.35% | 1.0395 | +146.96 bps |
| ETHUSDT | 30m | 0 | — | — | — | — |
| ETHUSDT | 1h | 0 | — | — | — | — |
| ETHUSDT | 2h | 0 | — | — | — | — |
| ETHUSDT | 4h | 0 | — | — | — | — |

Only 19 of 62,208 configuration/timeframe evaluations produced a configuration with at least 30 validation trades. Only ETHUSDT 15m showed a positive OOS net result at baseline costs. That result was not robust to the higher-slippage stress: OOS PF fell to 0.8878 and OOS net became -473.04 bps. The other populated OOS cells were already negative at baseline costs.

## Critical scope boundary

This is a completed two-year backtest of **one Impulse Retracer mechanism family** across 5,184 parameter configurations per symbol/timeframe. It is **not** a source-based backtest of 1,000 independently discovered engines, and it does not establish a shortlist of 100 distinct engines. Parameter combinations are not distinct engines. The requested 1,000-source harvest, source-code audit, deduplication into 100 independent engines, and source-faithful backtests of those engines remain uncompleted.

Do not treat the single positive baseline ETH 15m cell as a validated tradable edge: it has only 62 OOS trades and fails the higher-slippage stress test.
