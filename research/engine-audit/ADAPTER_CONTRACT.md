# Strategy adapter contract

The audit import is intentionally separate from the production/live strategy code and from the existing impulse-retracement runner.

## Input contract

Each input row is one closed bar with a monotonically increasing UTC timestamp. Feature fields must be point-in-time aligned and must never be forward-filled across a period longer than the source cadence without an explicit policy.

| Field | Used by |
|---|---|
| `timestamp` | All |
| `open`, `high`, `low`, `close` | Taker-pressure ATR; all relevant price signals |
| `funding_rate` | Funding fade |
| `buy_ratio` | Funding fade and taker pressure; aggressor buy volume / total volume |
| `open_interest` | OI quadrants |
| `taker_ls_vol_ratio` | OI quadrants |

## Output contract

Each strategy emits one row per input bar: timestamp, integer signal (-1/0/+1), engine identifier and `execution_rule=next_bar_open`. The OI strategy also emits its observable quadrant and an interpretation warning.

Signals are evaluated at the close of their timestamped bar. The earliest permitted simulated entry is the next bar open. No signal is a trade by itself: the shared portfolio simulator must apply position lifecycle, stop/target, fees, funding cashflows, leverage/margin, liquidation, and symbol-level concurrency rules consistently.

## Audit promotion boundaries

- Funding-rate fade and taker-buy-pressure momentum passed source-level mechanism audit and are independently reimplemented in `strategies.py`.
- OI/price quadrants are retained as a conditional research candidate. The code preserves the upstream four-quadrant mapping but explicitly does not treat “OI down” as proof of long or short liquidation.
- Funding carry, dated-futures basis, Avellaneda–Stoikov market making, and cross-venue OU spread are not coerced into this bar adapter. They require spot/perp or dated-futures legs, event-level order-book/fill simulation, or synchronized multi-venue quotes. Their proper execution adapters are separate work.
- The existing impulse-retracement runner and its configs/data/results are unchanged.
- No backtests are launched until the full 100-mechanism source audit and deduplication is complete, per the agreed research gate.
