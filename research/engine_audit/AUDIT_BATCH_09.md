# Source Audit — Batch 09

Scope: inspect the event-driven crash strategies in gahitchi/trading, the fast L2 imbalance strategy in the same repository, and the event-driven maker implementation in lucaspaulien/crypto-market-making. This is source-level mechanism review only.

## New distinct mechanisms accepted

| Mechanism | Inspected source | Exact signal and trade structure | Decision |
|---|---|---|---|
| Open-interest-confirmed liquidation-wick reversal | [crash_study.py](https://github.com/gahitchi/trading/blob/main/src/lab/crash_study.py) | On 1-minute bars, require a decline of at least `drop_pct` over `window_min`, quote volume at least `vol_mult` times the trailing 7-day median baseline, and OI down at least `oi_pct` over the same window. Enter long after the signal at the next open plus configured delay; exit on stop, target or max hold; one trade per crash with cooldown; volatility-targeted sizing uses pre-event volatility. OI snapshots are delayed five minutes before becoming available and stale snapshots fail closed. | PASS as a distinct OI-confirmed forced-deleveraging reversal mechanism. It is not the same as price/volume climax fade because OI contraction is a required independent event condition. NOT IMPORTED: source repository has no declared licence; do not copy code. Requires historical OI snapshots with publication delay, 1m quote volume and a stateful event runner. |
| Open-interest-confirmed crash continuation | [crash_study.py](https://github.com/gahitchi/trading/blob/main/src/lab/crash_study.py) | Same extreme price decline and abnormal quote-volume event, but require OI to rise over the event window (new positions being added into the fall). Enter short after a delay; stop/target/time exits and volatility targeting are explicit. The source interprets this as potential continuing deleveraging pressure, not as an observed identity of the trader opening the position. | PASS as a distinct conditional crash-continuation mechanism: OI expansion during a high-volume sell-off differs economically from the OI-contraction wick-reversal rule. NOT IMPORTED for the same licence and OI-data constraints. |

## Audited but not counted

| Candidate | Source | Decision | Reason |
|---|---|---|---|
| Five-level book-imbalance taker | [fast.py](https://github.com/gahitchi/trading/blob/main/src/lab/fast.py), [micro.py](https://github.com/gahitchi/trading/blob/main/src/lab/micro.py) | DEDUPLICATED | Takes the touch when five-level weighted book imbalance exceeds a fixed threshold and exits after a fixed five-second hold. This is another implementation of the order-book-imbalance directional family already represented in Batch 06; it is not counted as a second independent alpha family. |
| PassiveMaker | [maker.py](https://github.com/gahitchi/trading/blob/main/src/lab/maker.py) | DEDUPLICATED / EXECUTION VARIANT | Passive quoting with inventory controls is in the same market-making family as the already audited Avellaneda–Stoikov strategy. Different quote placement and fill policy do not create a new directional hypothesis. |
| Touch / fixed spread / Avellaneda–Stoikov simulator strategies | [strategies.py](https://github.com/lucaspaulien/crypto-market-making/blob/main/src/mmsim/strategies.py) | DEDUPLICATED | Touch and fixed spread are baselines; Avellaneda–Stoikov is the same inventory-skewed optimal-quoting family already audited. The queue-position, latency, post-only and trade-through simulator is useful execution infrastructure, not a new signal engine. |
| Multi-level OFI, VPIN-style flow toxicity, Hawkes trade intensity, absorption proxy, Kalman lead-lag | [micro.py](https://github.com/gahitchi/trading/blob/main/src/lab/micro.py) | FEATURE CANDIDATES ONLY | The source implements causal event-time feature estimators, but explicitly does not define calibrated entry/exit thresholds or a standalone strategy for these features. Do not count a feature as a strategy engine. Kalman lead-lag also belongs to the already counted cross-asset lead/lag family. |

## Source defects / data requirements

- The crash study delays OI observations by five minutes and uses a 15-minute staleness limit. A backtest must preserve both; aligning OI to its raw snapshot timestamp would introduce look-ahead.
- The source's event entry is delayed after the event; it must not be backdated to the crash bar.
- The two modes use different hypotheses and different direction/position rules, but share the same event detector framework. Count them as two mechanisms, not as dozens of parameter variants.
- Repository metadata reports no SPDX licence. No source code is copied or ported.
- The source reports that queue position and square-root market impact are not modeled in its crash execution; its slippage assumptions need stress tests. That does not invalidate the mechanism audit, but it blocks profitability claims.
- The L2 fast strategy is short-horizon (five seconds), so it does not fit the current M1 candle runner or the user's swing-oriented objective. It is also a duplicate signal family.

## Batch 09 tally

- 2 new source-reviewed mechanisms accepted at mechanism level.
- 4 additional source components inspected but not counted as distinct mechanisms.
- No code copied.
- No historical backtest started.
