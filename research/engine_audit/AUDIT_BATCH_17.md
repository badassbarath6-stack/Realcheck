# Source Audit — Batch 17: strategy frameworks and time-series momentum

Date: 2026-11-22

## Scope

Inspected implementation/documentation from five candidates in the 109-repository discovery catalogue:

- `zihhn/Kairos-v2`: `detailed_documentation.md`, `chien_luoc/json_strategy.py`
- `jicheolha/crypto-trading-bot`: `README.md` and documented project structure
- `86maid/trading-maid`: `examples/strategy_horizon_long.rs`
- `keptaduona/wickline`: `README.md`, strategy API and backtest execution contract
- `Lumiwealth/lumibot-strategies`: candidate search results; no qualifying perpetual-specific mechanism source identified in the inspected result

## Decisions

| Candidate | Source-level finding | Decision |
|---|---|---|
| KAIROS v2 | Documentation describes a five-way ensemble of conventional breakout, squeeze, trend-following, mean-reversion and scalping strategies, gated by an MLP regime classifier. The inspected JSON strategy is a generic indicator/configuration interpreter. No separate, independently specified perpetual-futures alpha mechanism is evidenced. The documented data layer mentions funding and liquidations, but its execution section does not establish funding cash-flow, mark-price, liquidation or margin accounting for each strategy. | FRAMEWORK / OVERLAY; NOT A NEW ENGINE |
| Keltrader | README describes a Bollinger squeeze/volatility-expansion strategy with ATR exits and claims leveraged results. Core signal generator, live trader, backtest runner and diagnostics are explicitly redacted. The available evidence is insufficient to reconstruct or audit the actual signal and execution rules. Promotional performance figures are not source-verified. | REJECT AS UNVERIFIABLE |
| Trading Maid — TSMOM long | The Rust example implements a distinct time-series momentum rule: compare current close with the close 168 hourly bars earlier; enter long on positive momentum; exit after two consecutive momentum reversals, a 336-hour maximum holding horizon, or a 6×ATR disaster stop; impose a 24-hour cooldown. It also provides a local exchange simulation with BTCUSDT metadata, maker/taker fees and maintenance margin. | CONDITIONAL PASS — NEW MECHANISM |
| Wickline | The inspected repository is a general charting/backtesting platform. Its API allows user-written strategies and documents close-signal/next-open fills, but the repository evidence inspected here does not specify one original trading hypothesis. Platform capability is not an engine. | FRAMEWORK; NOT A NEW ENGINE |
| Lumiwealth strategy catalogue | The inspected candidate result did not establish a source-backed, crypto-perpetual-native strategy with a distinct trade policy. | NO ACCEPTANCE; MORE SOURCE EVIDENCE REQUIRED |

## TSMOM futures-compatibility limitations

The TSMOM example is materially distinct from the previously audited cross-sectional momentum and momentum-decay mechanisms: it uses a fixed historical return sign as the entry state and a two-confirmation reversal/finite-horizon exit policy. It is not counted as a profitable or production-ready strategy.

Before BTC/ETH perpetual backtesting, a clean implementation must add:
- point-in-time funding payments over the full holding period;
- mark/index-price and contract-specification handling;
- realistic taker entry/exit costs and slippage;
- liquidation and maintenance-margin path checks, including intrabar ambiguity;
- a causal order/fill model and explicit treatment of the source example's local-exchange assumptions;
- long-only limitation clearly retained unless a separately sourced short rule is found.

The example's local simulator includes maker/taker fee and maintenance metadata, but the inspected strategy path does not show funding cash-flow accounting. It therefore remains conditional rather than fully futures-validated. The source repository's licence must be checked before any code reuse; this audit copies no code.

## Batch 17 tally

- 1 new distinct mechanism accepted conditionally: time-series momentum with fixed horizon and reversal confirmation.
- 4 other candidates did not add a distinct source-auditable engine.
- No code copied or imported.
- No historical Realcheck backtest started.
