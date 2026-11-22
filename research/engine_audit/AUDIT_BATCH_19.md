# Source Audit — Batch 19: complete 109-repository candidate register

Date: 2026-11-22

## Scope

Completed an individual repository-level disposition for all 109 entries in `CRYPTO_FUTURES_100_SOURCE_CATALOG.md`. Every candidate has a row in [AUDIT_REGISTER_109.md](AUDIT_REGISTER_109.md), with disposition, mechanism/family mapping, and evidence grade (CODE, DOC, META, UNAVAILABLE).

This is a repository-by-repository audit/triage, not a claim that every candidate published usable source code. Frameworks, forks, empty repositories, unavailable projects and redacted strategy implementations are explicitly identified rather than treated as verified engines. Earlier detailed batches 01–18 remain the deeper source audits for their inspected mechanisms.

## New distinct mechanisms confirmed

### 1. Cross-asset delayed-beta / leader–laggard momentum — CONDITIONAL

Source: `sohan-shingade/flintstrats/momentum_cascade.py`.

The implementation uses BTC fast/slow trend alignment, a minimum BTC impulse, and a lagging SOL return threshold to trade the delayed beta response. It includes directionally symmetric entries, ATR trailing exits, a maximum holding horizon and cooldown. This is distinct from single-asset time-series momentum and cross-sectional ranking. The source is BTC→SOL; adapting it to BTC→ETH is a separate hypothesis and must not be assumed equivalent.

### 2. Cross-sectional PCA factor-residual mean reversion — CONDITIONAL

Source: `Chakour-Yasser/cross-sectional-stat-arb/src/statarb.py`, with `src/regime.py` and `src/backtest.py`.

The code estimates eigenportfolio factors using a correlation-matrix PCA and Marchenko–Pastur factor count, regresses each asset return on the factors, accumulates residuals, fits OU dynamics and trades s-scores. Positions are lagged one period and turnover costs are included. This is distinct from two-leg cointegrated pairs. However, the repository's crypto-perp findings show pronounced 2024–2026 decay and weak/negative post-cost robustness; keep conditional and require a fresh broad-universe OOS replication.

### 3. Exact post-liquidation-flow exhaustion reversion — CONDITIONAL

Source specification: `elrazez/hl-robotrader/docs/STRATEGY_AND_RISK.md`.

The rule detects a forced-flow cascade, waits for liquidation intensity to collapse, CVD/book imbalance to reverse, mark-mid dislocation to normalize and price to stop making new extremes, then fades toward a pre-cascade anchor. This precise post-exhaustion trigger is distinct from generic OI/liquidation-wick reversal. The source author's own report states realistic live entries lose; the profitable hindsight timing requires exact liquidation events that free public live feeds do not provide. It is conditional on a suitable exact feed and a new independent OOS test.

### Excluded from the strict futures-native count

`theonetrade/pump-anomaly` implements a distinct social-channel coordination detector: independent author clusters, event-window synchronization, lead/echo influence, Hawkes burst intensity and per-source trained exits. It is not counted in the strict futures-native engine tally pending validation of signal-source quality, BTC/ETH applicability, and futures-specific execution/cost economics.

## Major deduplication outcomes

- HyperData Terminal forks/clones collapse to one data/visualization tool, not engines.
- Futures-app clones collapse to the same delta-neutral funding-carry implementation.
- NOFX and RL-Crypto clones do not create additional mechanisms.
- Multiple grid, pair-stat-arb, cross-venue funding/basis, trend, RSI, breakout and market-making repositories map to existing families.
- HFT backtest frameworks, screeners, dashboards, data APIs and execution hosts are not engines.
- Negative or redacted projects are preserved as reject/conditional evidence; marketing metrics are not accepted.

## Batch 19 tally

- 109/109 candidate repositories individually dispositioned.
- 3 additional distinct mechanisms conditionally accepted.
- Current unique accepted/conditional mechanism register: **50/100**.
- No code copied or imported.
- No historical Realcheck BTC/ETH backtest started.
