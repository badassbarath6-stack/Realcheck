# Source Audit — Batch 10

Scope: inspect the executable hypothesis code and validation records in pavel-shkliar/Trading-research and the signal estimators/results in jshekhawat/quant_experiments. The repositories contain research scripts rather than reusable production engines; only the source-defined hypothesis is audited.

## New distinct mechanism

| Mechanism | Inspected source | Exact rule / evidence | Decision |
|---|---|---|---|
| Deribit implied-volatility complacency regime | [compute_indicators.py](https://github.com/pavel-shkliar/Trading-research/blob/master/compute_indicators.py), [backtest_h6b_walkforward.py](https://github.com/pavel-shkliar/Trading-research/blob/master/backtests/backtest_h6b_walkforward.py), [HYPOTHESES.md](https://github.com/pavel-shkliar/Trading-research/blob/master/HYPOTHESES.md) | Compute a trailing 90-observation percentile of Deribit DVOL. When the percentile is below 5%, treat the options market as unusually complacent and take a bearish / underperformance exposure over the 60-day horizon. The author reports 5/5 walk-forward periods confirming the negative relative-return hypothesis on both BTC and ETH; the reported 60-day edge is -6.83% BTC (n=85) and -10.06% ETH (n=71), with Welch and Mann–Whitney p-values below 0.02. | CONDITIONAL PASS as a genuinely distinct options-implied-volatility state signal for perpetual-futures direction. It is not an options trade. The source's evidence is forward-return event analysis, not a fully costed perpetual trade simulation; it has only BTC/ETH DVOL coverage, and the repo has no declared licence. Do not import or claim tradable profitability until we run an independent execution-aware backtest using point-in-time DVOL observations and a publication/close timestamp. |

## Distinct source mechanisms audited but rejected for promotion

| Mechanism | Inspected source | Exact rule | Decision |
|---|---|---|---|
| Aggressive-flow absorption / price-impact residual | [absorption.py](https://github.com/jshekhawat/quant_experiments/blob/main/src/quant_lab/analytics/absorption.py), [findings](https://github.com/jshekhawat/quant_experiments/blob/main/reports/cvd_absorption_findings.md) | Normalize signed taker quote flow by trailing activity; fit a trailing rolling OLS of return on flow; use the signed residual as an absorption score, where aggressive selling with unusually small negative impact predicts a long and vice versa. | DISTINCT MECHANISM, REJECTED FOR PROMOTION. The source's own design/test shows test IC -0.0187 with 95% block-bootstrap CI [-0.0379, +0.0007], negative in all 18 robustness cells, and a near-zero control-regression coefficient. This is a valuable negative result, not an engine to import. |
| Spot-versus-perpetual CVD leadership | [divergence.py](https://github.com/jshekhawat/quant_experiments/blob/main/src/quant_lab/analytics/divergence.py), [results](https://github.com/jshekhawat/quant_experiments/blob/main/reports/spot_cvd_divergence_results.md) | Separately normalize rolling spot and perp taker flow, then use the difference between their trailing z-scores as a cross-market leadership signal. | DISTINCT MECHANISM, REJECTED FOR PROMOTION. Test IC is -0.0040, bootstrap CI [-0.0239, +0.0170], design-to-test sign reversal, non-monotonic deciles and negative leave-one-symbol-out results. Requires spot/perp synchronization even if reconsidered later. |

## Deduplicated / not counted

- Funding-rate velocity (pavel H7) splits extreme negative funding into a sudden transition versus a chronic state. This is a temporal refinement of the existing funding-extremity / funding-momentum family, not a separate economic mechanism.
- The spot–perp CVD project's price-versus-CVD divergence sub-hypothesis is not separately counted: it is a price/flow divergence variant of the already audited flow-divergence family.
- Flow-confirmed breakout and failed-sweep studies in jshekhawat/quant_experiments reuse prior-range breakout/sweep events and add taker-flow filters. They are incremental conditioning tests, not new standalone mechanisms. Their own reports also show no stable incremental edge.
- The source's rolling CVD absorption and spot/perp divergence reports cover 2026 only; the authors explicitly label them exploratory / single-regime. Their negative findings are not universal proof of no edge, but are sufficient to reject promotion from this evidence.

## Licence / timing boundary

- pavel-shkliar/Trading-research has no declared repository licence. No code copied.
- jshekhawat/quant_experiments has no declared repository licence in repository metadata. No code copied.
- The DVOL percentile calculation is trailing-only, but the historical feed's timestamp semantics and the exact moment the daily DVOL close becomes public must be confirmed before any backtest. A daily value must not be forward-filled into bars before publication.

## Batch 10 tally

- 1 new conditional mechanism accepted at source/mechanism level (DVOL complacency).
- 2 distinct source mechanisms audited and rejected for promotion on the source's own test results (CVD absorption; spot/perp CVD leadership).
- Funding-velocity and flow-conditioned sweep/breakout candidates deduplicated.
- No code copied and no Realcheck historical backtest started.
