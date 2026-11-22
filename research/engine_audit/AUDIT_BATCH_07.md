# Source Audit — Batch 07

Scope: inspect strategy implementations in sohan-shingade/flintstrats, beyond the previously audited Climax Fade and Momentum Decay files. The repository has no root LICENSE file in the inspected tree, so no source code is copied.

## New distinct mechanisms

| # | Mechanism | Source | Exact structure observed | Decision / blocker |
|---:|---|---|---|---|
| 1 | Three-scale momentum confluence with slow-scale exit | [fractal_momentum.py](https://github.com/sohan-shingade/flintstrats/blob/main/fractal_momentum.py) | Require fast/medium/slow ROC all to agree, fast-vs-medium and medium-vs-slow EMA trend confirmation, volume ratio gate and RSI band. Exit via ATR trail (tightens after a profit threshold), or early exit when fast and medium momentum reverse while trade is profitable; max-hold and loss-adaptive cooldown are also stateful. | CONDITIONAL PASS. Distinct from single-horizon trend momentum. Requires exact Flint indicator definitions and event timing, persistent strategy state, partial/variable position sizing and ATR trailing-exit simulation. No stateless signal-only port. |
| 2 | ADX-switched trend-following / mean-reversion engine | [regime_momentum.py](https://github.com/sohan-shingade/flintstrats/blob/main/regime_momentum.py) | If ADX exceeds a threshold, use fast/slow EMA + ROC + RSI trend entries and trend-reversal exits. Otherwise use rolling price z-score + RSI extremes for mean-reversion entries and z-score reversion exits. Position size scales inversely with realized volatility; ATR trailing stops and max-hold apply in both regimes. | CONDITIONAL PASS. This is a genuine two-mode state machine, not a simple indicator overlay. Requires exact Flint ADX/EMA/ROC/RSI/z-score/volatility/ATR definitions and stateful position sizing/trailing exits. |

## Deduplication and source-quality findings

- [inflection_trader.py](https://github.com/sohan-shingade/flintstrats/blob/main/inflection_trader.py) combines momentum deceleration, volume-climax capitulation and reversal confirmation, with BTC regime checks. Its constituent entry mechanisms overlap the previously audited Momentum Decay and Climax Fade families; the BTC checks and risk rules are overlays, so it is not counted as a third independent mechanism.
- [volatility_breakout.py](https://github.com/sohan-shingade/flintstrats/blob/main/volatility_breakout.py) is a squeeze/volatility release breakout with volume and BTC filters; deduplicated with Batch 04's volatility-squeeze release.
- [donchian_surfer.py](https://github.com/sohan-shingade/flintstrats/blob/main/donchian_surfer.py) is a Donchian trend breakout variant; deduplicated with the existing channel-breakout family.
- [adaptive_residual.py](https://github.com/sohan-shingade/flintstrats/blob/main/adaptive_residual.py), [dual_residual.py](https://github.com/sohan-shingade/flintstrats/blob/main/dual_residual.py) and [cross_asset_reversion.py](https://github.com/sohan-shingade/flintstrats/blob/main/cross_asset_reversion.py) are rolling-beta / pair-residual / cross-asset mean-reversion variants, deduplicated with the existing residual-stat-arb family.
- [mean_revert_pure.py](https://github.com/sohan-shingade/flintstrats/blob/main/mean_revert_pure.py), [rsi_extremes.py](https://github.com/sohan-shingade/flintstrats/blob/main/rsi_extremes.py) and [alpha_reversion.py](https://github.com/sohan-shingade/flintstrats/blob/main/alpha_reversion.py) are variants of the existing price mean-reversion family.
- [eth_alpha.py](https://github.com/sohan-shingade/flintstrats/blob/main/eth_alpha.py) is asset-specific parameterization/feature selection, not a new mechanism. [sol_eth_spread.py](https://github.com/sohan-shingade/flintstrats/blob/main/sol_eth_spread.py) is a pair-spread variant.
- [momentum_cascade.py](https://github.com/sohan-shingade/flintstrats/blob/main/momentum_cascade.py) is a leader/follower momentum catch-up variant, deduplicated with cross-asset lead-lag. [cascade_climax.py](https://github.com/sohan-shingade/flintstrats/blob/main/cascade_climax.py) is a volume-climax variant, deduplicated with Climax Fade.
- The source imports indicator functions from the external Flint package. Those exact indicator implementations and the framework's order-fill timing were not part of the inspected strategy files; this prevents exact platform import until that dependency is audited.
- The README's performance claims are not treated as evidence. No backtest results from this repository are accepted without independent reproduction.

## Batch 07 tally

- 2 new distinct mechanisms accepted conditionally at source/mechanism level.
- 8 additional strategy files were inspected and deduplicated against already counted families.
- No source code copied; no historical backtest started.
