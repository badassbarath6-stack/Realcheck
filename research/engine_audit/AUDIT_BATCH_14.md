# Source Audit — Batch 14

Scope: inspect the archived information-alpha model in BlackLotus0930/crypto-quant-research, including its neural architecture, data windowing, target construction, training objective, portfolio translation and holdout execution selector.

## New distinct mechanism accepted conditionally

| Mechanism | Inspected source | Exact model/portfolio structure | Decision |
|---|---|---|---|
| Dual-axis cross-sectional temporal-attention quantile alpha model | [net.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/model/net.py), [head.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/model/head.py), [train.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/model/train.py), [dataset.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/pipeline/dataset.py), [backtest.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/eval/backtest.py), [exec_select.py](https://github.com/BlackLotus0930/crypto-quant-research/blob/main/archive/info-alpha/exec_select.py) | Input is a rolling 64-day × N-asset panel of five causal normalized OHLCV channels. Each encoder block applies permutation-equivariant masked attention across assets at each timestamp, then causal attention through time for each asset, followed by an MLP. The anchor-day token is passed to a Δt-FiLM quantile head that emits a monotonic 21-quantile distribution per asset. Training combines cross-sectional Pearson-IC loss with quantile pinball loss; validation IC selects checkpoints. The prediction mean becomes a dollar-neutral cross-sectional portfolio using risk-equalized signal/volatility or top/bottom-third ranking. Execution is a separate cadence/rebalance/no-trade-band overlay, selected on validation and applied to holdout with explicit costs. | CONDITIONAL PASS as a distinct learned multi-asset alpha engine, not a hand-built indicator blend. README reports cross-sectional IC around 0.025 and says the edge survives leak/cost checks but is compressed close to breakeven at 5 bps taker fees at current scope. It is explicitly paused. Source repository has no declared licence; no code copied. Reproduction requires the exact point-in-time panel, masks, split metadata, trained checkpoint and model configuration; no claim of tradable net profitability is justified. |

## Causality and implementation audit

- `PanelDataset` builds input windows only through the anchor date; the temporal attention uses a causal mask. Labels use anchor-to-future returns, and the split helper embargoes samples whose maximum label horizon crosses into the next split.
- The normalization helper uses trailing per-asset rolling means/standard deviations and records the contemporaneous return scale. It does not use a global full-sample fit.
- The model's cross-asset attention is permutation-equivariant over the asset axis (no asset positional embedding), which is a materially different hypothesis class from single-asset indicator rules.
- The execution selector tunes cadence, rebalance fraction and no-trade band on validation, then applies fixed settings to holdout. This is a separate execution overlay, not an additional alpha engine.
- The README's IC ~0.025 is a research summary, not a Realcheck result. The same README explicitly notes that 5 bps taker friction compresses the signal close to breakeven. No code, weights or model outputs were imported.

## Import boundary

- No declared upstream licence: do not copy the source implementation. An independent reimplementation would require a clean-room architecture specification and separate approval of the input feature schema and training target.
- This is a multi-asset daily model, not a candle-level signal function. Realcheck would need a point-in-time universe panel, model-training pipeline, checkpoint versioning, inference runner, portfolio construction and a proper OOS execution simulator.
- CPU-only GitHub Actions is suitable for unit tests and small inference smoke tests, not for claiming a full training reproduction. Training feasibility must be measured separately.
- Keep this engine isolated from the existing impulse-retracement runner and from the small directional CSV runner.

## Other related modules

The inspected archive also contains funding, OI and netflow probes. These are factor diagnostics rather than independent trained strategies and were already covered in Batches 01/04/13. They are not counted again.

## Batch 14 tally

- 1 new conditional source-reviewed model family accepted.
- No source code or weights copied; no historical Realcheck backtest started.
