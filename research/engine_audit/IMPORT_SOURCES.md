# Source references and porting notes

The source projects below were inspected at implementation level. Their mathematical behavior was independently ported into `research/engine_audit/engines.py`; upstream files were not copied verbatim.

| Mechanism | Source implementation | Port |
|---|---|---|
| Funding-rate mean reversion | https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_1_funding_mr/signals.py | `funding_rate_mean_reversion` |
| Taker-buy-pressure momentum | https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_2_taker_momentum/signals.py | `taker_buy_pressure_momentum` |
| OI/price quadrants (conditional) | https://github.com/Gotodataru/binance-futures-backtest/blob/main/strategy_3_oi_divergence/signals.py | `oi_price_quadrants` |
| Funding-aware Avellaneda–Stoikov | https://github.com/ib2003dev/market-making-sim/blob/main/src/market_making_sim/strategies/avellaneda_stoikov.py | `avellaneda_stoikov_quotes` |
| Spot/perpetual funding carry | https://github.com/idreesm18/crypto-perp-funding-carry/blob/main/src/2_signal.py | `spot_perp_funding_carry` |
| Dated futures cash-and-carry | https://github.com/tkwsean/SpotFuturesArbitrage/blob/main/scanner.py | `delivery_basis_economics` |

The upstream funding-fade repository did not expose a clear licence in the inspected root listing, so its logic was reimplemented independently. The market-making repository identifies WTFPL. The ports preserve signal/economic structure, not the upstream projects' execution wrappers or risk settings.

The cross-venue OU project was excluded pending correction of a rolling-median backward-fill look-ahead defect. Compression breakout remains uncounted pending deduplication against Donchian/Turtle.
