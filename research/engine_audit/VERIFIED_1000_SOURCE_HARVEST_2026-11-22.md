# Verified 1,000-Source Strategy Harvest

Date: 2026-11-22

## Run verification

- GitHub Actions run: [45023349418](https://github.com/badassbarath6-stack/Realcheck/actions/runs/45023349418)
- Workflow: Harvest 1000 Strategy Implementations
- Result: SUCCESS
- Workflow commit: 0a30c22c60f70c0e14151aeeb6105667e30d24c4
- Harvested artifact: strategy-source-harvest-1000
- Artifact ID: 14754249843
- Artifact size: 3,975,811 bytes
- Manifest entries: 1,000
- Exact SHA-256 unique source files: 1,000
- Workflow verification checked every copied file exists and its SHA-256 matches the manifest.

## Harvest composition

| Language/source family | Count | Source repository |
|---|---:|---|
| TradingView Pine strategy scripts | 384 | https://github.com/theonetrade/pynecore-strategies |
| Freqtrade IStrategy implementations | 429 | https://github.com/PeetCrypto/freqtrade-stuff and https://github.com/freqtrade/freqtrade-strategies |
| MetaTrader 5 Expert Advisors | 187 | https://github.com/GeneralTradingSarl/expert-mt5 |
| **Total** | **1,000** | |

The Freqtrade count is 381 from PeetCrypto and 48 from the official Freqtrade strategy examples repository. The Python static filter required an IStrategy subclass and a populate_entry_trend or populate_buy_trend method. The Pine filter required a strategy() declaration. The MQL5 filter required OnInit and OnTick functions.

## Source pinning and files

The artifact includes:
- 1,000 original source files, preserved byte-for-byte
- manifest.csv with source URL, original path, repository commit SHA, SHA-256, byte count, language, and audit status
- repository license files where present, plus explicit notices where a root license file was not found
- README with harvest scope and caveats

Pinned source commits:
- pynecore-strategies: 13f6388d7d95144bb828f8881bede77cf2008ea7
- freqtrade-stuff: f6c38def0b2fe01d8d42e47740cdeab53511527b
- expert-mt5: 54915406328289767819175bf2e24e714aef4b85
- freqtrade-strategies: f3340ce11f5bdf62f598522e64d1f5638eaa13f5
- HUGE_FreqTrade_Strategy_Collection fallback clone: 0bd980ffe4f09063256a1df3d9c1250b2acda1a7

## Scope boundary

This completes the requested first stage: harvesting 1,000 actual strategy source-code files, with 1,000 distinct exact-file SHA-256 hashes and reproducible provenance.

It does not yet mean there are 1,000 semantically distinct trading mechanisms. Similar implementations, ports, forks, renamed scripts, shared templates, parameter-only variants, and strategy families still need source-level semantic deduplication. The source code has not yet been normalized into Realcheck adapters, independently audited for lookahead/repainting, or backtested. No performance claims are made.

Do not redistribute or use any harvested source in a product until its individual repository license and applicable upstream terms have been checked.
