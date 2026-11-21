# Source Audit — Batch 11

Scope: inspect the cross-sectional portfolio research in AbdullaE100/perp-quant-lab, including its signal construction, portfolio weights, OOS evaluation and live preview implementation.

## New distinct mechanism accepted

| Mechanism | Inspected source | Exact structure | Decision |
|---|---|---|---|
| Volatility-scaled cross-sectional momentum long/short | [backtest2.py](https://github.com/AbdullaE100/perp-quant-lab/blob/main/research/backtest2.py), [backtest3.py](https://github.com/AbdullaE100/perp-quant-lab/blob/main/research/backtest3.py), [fetch.py](https://github.com/AbdullaE100/perp-quant-lab/blob/main/research/fetch.py), [robust.py](https://github.com/AbdullaE100/perp-quant-lab/blob/main/research/robust.py) | On a multi-perpetual daily panel, compute each asset's trailing 14-day price return ending at t-1 and divide by its trailing 30-day daily-return volatility known at t-1. Rank the cross-section; allocate equal-weight long positions to the top 30% and equal-weight shorts to the bottom 30%, with dollar-neutral long/short exposure. Hold weights over the next daily return; turnover-based taker fees are charged. | PASS mechanism/source. This is cross-sectional *price* momentum with volatility scaling, distinct from time-series momentum and distinct from CShear's similarly named evaluator, which actually ranks cumulative funding rather than price returns and was rejected as mislabeled. The source is MIT-licensed. |

## Reproduction / quality audit

- The source's 14-day momentum formula is lagged: `px.shift(1) / px.shift(15) - 1`; the volatility denominator is also lagged with `vol.shift(1)`. Portfolio return is aligned to the next day's price return. No direct future-price reference was found in the inspected signal construction.
- The portfolio ranks assets cross-sectionally and constructs separate long and short baskets; it is not a collection of independent single-symbol entries. Realcheck needs a portfolio-level rebalance/ledger adapter, matched notional accounting and delisting-aware point-in-time universe membership.
- The repository's README reports OOS Sharpe 1.62 for the vol-scaled variant over 2022–2026, with 5 bps/side taker fees. Treat this as an upstream claim, not our result.
- Important source limitations: current survivor universe (survivorship bias), only 6 names in the live script versus a broader research candidate list, no funding cashflows, no slippage/market impact for thinner alts, and regime split of OOS thirds (0.34, 3.00, -0.97) shows a material recent drawdown. The README itself flags the regime dependence.
- The source's 70/30 split is chronological but its robustness helper also reports full-sample cross-coin results. Our port must freeze the universe by historical listing/liquidity data, use funding and slippage, and reserve an untouched OOS period. The top/bottom fraction and 14/30-day windows must be preserved as source defaults rather than silently optimized.

## Deduplication

- CShear's `make_xsection_momentum` is not this mechanism: despite its name, it ranks cumulative funding, not price return. That implementation was rejected in Batch 04 as a mislabeled/ambiguous funding-positioning proxy.
- Time-series momentum, BTC-to-alt lead-lag and residual relative-strength breakout are distinct hypotheses; they do not rank the whole cross-section by risk-adjusted trailing price return and construct dollar-neutral long/short baskets.
- Alternative lookbacks, top/bottom basket fractions and volatility windows within this implementation are parameter variants, not extra engines.

## Import boundary

- MIT permits clean-room reimplementation with attribution.
- Do not route this through the current single-symbol candle adapter. It requires a synchronized multi-asset daily panel, point-in-time universe, cross-sectional ranking at each rebalance, two-sided portfolio weights, turnover costs and funding accrual.
- Candidate is accepted for the 100-mechanism audit count, but no code has yet been copied into Realcheck and no backtest has started.

## Batch 11 tally

- 1 new distinct source-reviewed mechanism accepted.
- No duplicates counted and no source code copied.
- No historical Realcheck backtest started.
