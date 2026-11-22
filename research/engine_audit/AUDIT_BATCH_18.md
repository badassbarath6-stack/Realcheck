# Source Audit — Batch 18: multi-signal Binance futures bot

Date: 2026-11-22

## Scope

Deep source inspection of `Nikhilperr/binance-futures-trading-bot`:
- `README.md`
- `modules/signals.py`
- `main.py`
- `modules/trade_manager.py`
- `modules/learning_engine.py`

A further 11 candidate repositories from the catalogue were queried for source files matching strategy/signal/entry/exit/funding. The repository search returned no relevant indexed source excerpts for those candidates in this pass; they remain **unassessed**, not rejected.

## Candidate decision: Nikhilperr Binance Futures Trading Bot

| Claimed strategy | Inspected rule | Decision |
|---|---|---|
| Trend following | 15m EMA 9/21 relationship, MACD histogram direction and ADX >25, aligned with 1h EMA50/EMA200 macro trend | DEDUPLICATED — conventional trend-following |
| Mean reversion | RSI divergence plus Bollinger extreme, VWAP location and 1m StochRSI confirmation | DEDUPLICATED — price/RSI divergence and band mean-reversion families already represented |
| Volume breakout | 15m volume >2× prior 20-bar average, ATR expansion, 20-bar high/low breakout and OBV direction | DEDUPLICATED — conventional volume-confirmed breakout |
| Funding-rate fade | Long when funding <−0.15%, short when funding >+0.15%, with rising OI confirmation | DEDUPLICATED — funding-extreme contrarian fade / OI-confirmed positioning family already represented |

The repository adds useful integration evidence: it fetches Binance USD-M futures klines, funding and OI, records per-signal outcomes, and uses a 3× isolated setting with exchange symbol filters. The learning module updates temporal signal weights by hour after trade outcomes. These are execution, risk, and adaptive-weight features around the four existing signal families; they do not create a fifth independent alpha mechanism.

## Futures execution and validation caveats

- The source calls Binance futures endpoints and records fees, but the inspected paper/live trade path does not establish complete historical funding cash-flow attribution per position.
- The README's claimed 10× compounding objective and performance claims are not evidence of robust net expectancy.
- The learning layer updates weights from observed trade outcomes; this is an adaptation overlay, not an independent entry hypothesis.
- The inspected RSI fallback compares extrema over a rolling window and should receive a dedicated prefix-invariance test before any port. The centered local-pivot loop excludes the last two bars, but this does not by itself validate the full fallback path.
- No code copied or imported.

## Other candidates queried

`s-brez/trading-server`, `AbdullaE100/perp-quant-lab`, `Henrikmatos/futures-app`, `hongmin78/futures-app`, `eggyuu5/tracequant`, `sohan-shingade/flintstrats`, `goodeyesniper/Binance-Futures-Trading-Bot`, `CryptGodSon/Trading-Bot-Binance-Futures`, `simoncampos1022/profitable-futures-trading-strategy-crypto-forex-stock`, `WickHunter/Wick-Hunter`, `ZorClawAI/ZorClawAI-Trading-Bot`, and `Afinnn954/Bot-Futures-Binance-With-Gemini-AI`.

The indexed search returned no relevant source excerpts for these 12 repositories in this pass (including Nikhilperr as the one subsequently inspected). A no-result search is not a source audit and is not used as a reject decision. They remain queued for repository-tree/README or direct-source retrieval.

## Batch 18 tally

- 1 repository deeply inspected.
- 0 new distinct mechanisms accepted.
- 11 additional candidates queried but not source-audited due to unavailable indexed source results.
- Cumulative accepted/conditional unique mechanism count remains 47 of 100.
- No historical Realcheck backtest started.
