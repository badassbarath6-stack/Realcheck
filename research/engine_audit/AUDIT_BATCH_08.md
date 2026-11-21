# Source Audit — Batch 08

Scope: inspect the ten worked strategy notebooks in mikemarshall01/crypto-quant-strategies (MIT licensed). The notebook source and its own after-cost caveats are treated as evidence; README claims alone are not.

## New mechanism

| Mechanism | Source | Rule | Decision |
|---|---|---|---|
| ETF-flow / stablecoin-supply liquidity regime | [09_etf_stablecoin_flows.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/09_etf_stablecoin_flows.py) | Daily BTC long/flat regime uses ETF net flow normalized by AUM and standardized over a rolling window, stablecoin-supply growth as a second liquidity input, a lagged composite flow signal, and a long-term BTC trend gate. | CONDITIONAL PASS as a distinct cross-market liquidity-flow mechanism. The notebook's test fixture is synthetic rather than a verified historical ETF-flow archive; the source itself notes that IC is small/noisy. Do not import it as a completed production strategy or report its synthetic test as market evidence. Requires point-in-time real ETF-flow data, stablecoin supply history, revisions/publication timestamps, and a daily event-driven portfolio adapter. |

## Audited but rejected / deduplicated

- [10_cross_asset_rates_dxy.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/10_cross_asset_rates_dxy.py): a macro headwind filter using DXY, Treasury yields, real yields and rate changes to gate BTC exposure. Distinct macro mechanism, but the notebook's own FDR/multiple-testing analysis finds no robust surviving predictive relationship and its after-cost strategy underperforms the baseline. REJECT for promotion; preserve as a negative-control candidate, not an imported alpha engine.
- [07_liquidation_cascade.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/07_liquidation_cascade.py): the long-history stress score is an absolute-return × positive volume-z proxy, not actual liquidation prints. Its separate OI validation is short-horizon and does not establish a multi-year liquidation feed. The signal overlaps the already counted volume-climax/exhaustion family and is not a distinct, source-verified liquidation engine. DEDUP / DATA BLOCKED.
- [03_cross_sectional_funding_factor.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/03_cross_sectional_funding_factor.py): cross-sectional funding-yield ranking, deduplicated with Batch 04's funding relative-value family.
- [04_triangular_arbitrage.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/04_triangular_arbitrage.py): spot-market triangular arbitrage, outside the perpetual-futures scope.
- [05_leadlag_btc_alts.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/05_leadlag_btc_alts.py): BTC-to-alt lead/lag, deduplicated with cross-asset lead-lag.
- [06_calendar_funding_seasonality.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/06_calendar_funding_seasonality.py): funding-settlement/calendar seasonality, deduplicated with Batch 04's settlement-calendar mechanism.
- [08_variance_risk_premium.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/08_variance_risk_premium.py): options-implied versus realized variance; options strategy rather than a perpetual-futures engine, outside the current scope.
- [02_basis_carry.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/02_basis_carry.py) and [01_funding_carry.py](https://github.com/mikemarshall01/crypto-quant-strategies/blob/main/notebooks/01_funding_carry.py): duplicate existing spot/perp carry and basis convergence families.

## Batch 08 tally

- 1 new conditional mechanism.
- 1 distinct macro mechanism rejected on the source notebook's own after-cost/multiple-testing evidence.
- 1 liquidation proxy deduplicated with the existing volume-climax family.
- Remaining notebooks are duplicates or outside perpetual-futures scope.
- No code copied and no historical backtest started.
