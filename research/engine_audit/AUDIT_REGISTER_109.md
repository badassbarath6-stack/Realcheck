# Complete Candidate Repository Audit — 109/109

Date: 2026-11-22  
Repository under review: `badassbarath6-stack/Realcheck`  
Branch: `research/100-mechanism-audit-import`

## Audit interpretation and evidence standard

All 109 catalogue entries have now received an individual repository-level disposition. Each entry was checked against the available repository README/project documentation; where a candidate described a potentially distinct mechanism, relevant implementation files were fetched and inspected when accessible. Existing detailed batch audits (01–18) are incorporated rather than duplicated.

**Evidence grades**
- **CODE** — relevant implementation file(s) inspected.
- **DOC** — repository documentation contains enough mechanism detail for a provisional classification, but the relevant source implementation was not independently inspected in this pass.
- **META** — repository is a framework, data utility, platform, empty/inaccessible repository, or duplicate/fork; no standalone engine source was evidenced.
- **UNAVAILABLE** — repository/file could not be fetched, was empty, or the relevant implementation was redacted.

**Disposition**
- **ACCEPT / CONDITIONAL** means a distinct mechanism is represented in the mechanism register. Conditional means it needs additional data, a specialist simulator, or a clean futures port before any performance claim.
- **DUPLICATE** means the strategy belongs to a family already counted; parameter, timeframe, indicator, or repository changes do not create another engine.
- **OVERLAY / FEATURE** means useful as a filter, risk control, execution method, or measurement input, but not an independent entry/exit hypothesis.
- **NO ENGINE / REJECT** means no eligible, auditable crypto-futures trading mechanism was evidenced.

This is a complete **109-candidate repository audit and triage**, not a claim that every repository publishes complete source code. Where the source was redacted, absent, inaccessible, or only documentation was available, that limitation is explicit. No performance claim is accepted solely from a README.

## Individual audit register

| # | Repository | Disposition | Mechanism / audit finding | Evidence |
|---:|---|---|---|---|
| 001 | `s-brez/trading-server` | NO ENGINE / FRAMEWORK | Multi-venue execution, portfolio allocation and feature library; strategy implementations are explicitly not included (SMA cross is an example only). | DOC |
| 002 | `zihhn/Kairos-v2` | OVERLAY / FRAMEWORK | Large indicator library, regime MLP and generic trend/mean-reversion/breakout strategy routing; no independently new alpha family. Its liquidation/funding feeds are data inputs and the conventional strategies duplicate existing families. | CODE |
| 003 | `Lumiwealth/lumibot-strategies` | NO ENGINE | Collection is mostly stocks/options; crypto example is 50/50 BTC/ETH allocation, not a futures strategy. | DOC |
| 004 | `keptaduona/wickline` | NO ENGINE / FRAMEWORK | Charting, indicators, JavaScript strategy DSL and backtester. It is a host for user-authored strategies, not one original engine. Next-open fill is documented. | DOC |
| 005 | `jicheolha/crypto-trading-bot` | REJECT — UNVERIFIABLE | Claims a Bollinger squeeze/volatility-expansion strategy on Coinbase perps, but the core signal generator/live trader is redacted. Published results cannot be reproduced from the exposed signal code. | DOC / UNAVAILABLE |
| 006 | `NadirAliOfficial/QuantConnnect` | NO ENGINE / INSUFFICIENT | Generic QuantConnect collection listing mean reversion, momentum and portfolio rebalancing; no specific perp-native implementation established. | DOC |
| 007 | `intikhab49/edgeproof-crypto-trading-backtest` | NO ENGINE / VALIDATION TOOL | Triple-barrier labels, purged CV, deflated Sharpe and validation tooling; it audits strategies rather than supplying a standalone trade policy. | DOC |
| 008 | `86maid/trading-maid` | CONDITIONAL — TSMOM | Distinct fixed-horizon time-series momentum: 168-hour return-sign entry, two-close reversal exit, 336-hour maximum horizon, 6×ATR disaster stop and cooldown. Local simulator models matching, fees and maintenance margin, but the inspected strategy path does not establish funding cash flows. | CODE |
| 009 | `aria-tjr/crypto-futures-ml-strategy` | OVERLAY / DUPLICATE | Five weighted signal buckets (momentum, mean reversion, funding/basis, volatility and order flow) plus regime weighting; component families are already counted and no sixth independent mechanism is evidenced. | CODE / DOC |
| 010 | `andreaambrosio/crypto_perps_strategy` | DUPLICATE | EMA/ADX trend-momentum with RSI confirmation and ATR exits; conventional trend-following family. | DOC |
| 011 | `PhoenixSss/tracequant` | NO ENGINE / FRAMEWORK | Research-to-live bootstrap includes SMA crossover and traditional momentum examples, deterministic ML tooling and a shared data catalog; not a new mechanism. | DOC |
| 012 | `CalebEverett/futures-app` | DUPLICATE — FUNDING CARRY | Delta-neutral spot/perpetual position intended to harvest 8-hour funding payments; same funding carry family already represented. | DOC |
| 013 | `cixthefirst-glitch/AXION_QUANT_V4` | REJECT — EMPTY | GitHub reports the repository is empty; no source or strategy available. | UNAVAILABLE |
| 014 | `RawryJuuju/hyperliquid-futures` | DUPLICATE / OVERLAY | SMC Silver Bullet, FVG/liquidity sweep and multi-timeframe breakout are variants of existing price-structure/breakout families; funding arb is carry. Session multipliers and risk sizing are overlays. | DOC |
| 015 | `sohan-shingade/flintstrats` | CONDITIONAL — CROSS-ASSET LEAD/LAG | BTC-leads/SOL-lags momentum cascade is a distinct cross-market delayed-beta mechanism: BTC trend and impulse plus SOL underreaction; exits via ATR trail/time. Other listed strategies (pairs residuals, climax fade, momentum decay, multi-scale momentum, Donchian/squeeze) map to already counted families. Needs BTC→ETH adaptation for the user's BTC/ETH focus and proper perp accounting. | CODE |
| 016 | `AbdullaE100/perp-quant-lab` | DUPLICATE — XS MOMENTUM | Daily cross-sectional return/volatility-ranked long-short perp portfolio is the already-counted cross-sectional momentum family. Its own report discloses survivorship bias, omitted funding/slippage and severe regime dependence. | DOC |
| 017 | `Henrikmatos/futures-app` | DUPLICATE / FORK | Same funding-harvesting futures application and underlying project as CalebEverett/futures-app. | DOC |
| 018 | `hongmin78/futures-app` | DUPLICATE / FORK | Same funding-harvesting futures application as CalebEverett/futures-app; no new mechanism. | DOC |
| 019 | `eggyuu5/tracequant` | NO ENGINE / FRAMEWORK | TraceQuant research/runtime architecture; no independently new entry/exit hypothesis evidenced in the repository description. | DOC |
| 020 | `Flidison/liquidation-maker-filtering` | OVERLAY — NEGATIVE/UNCERTAIN | Predicts liquidation bursts and filters hypothetical maker trades using signed liquidation flow, Ridge/LightGBM/CatBoost and markout. It is a maker-selection/adverse-selection filter, not a standalone directional engine. Results are mixed; no independent hidden test; no inventory/execution-intensity model. | CODE / DOC |
| 021 | `CryptoGnome/Bybit-Futures-Bot` | DUPLICATE / DCA | Liquidation hunting plus DCA and position control; liquidation fade and averaging/grid families already represented. DCA is not counted as independent alpha. | DOC |
| 022 | `51bitquant/binance_grid_trader` | DUPLICATE — GRID | Binance spot/futures grid implementation; same adaptive grid/inventory-rebalancing family. | DOC |
| 023 | `cunarist/solie` | NO ENGINE / FRAMEWORK | Binance futures GUI and user-configurable strategy/backtesting environment; no original strategy identified. | DOC |
| 024 | `goodeyesniper/Binance-Futures-Trading-Bot` | REJECT — UNAVAILABLE | Repository fetch returns 404; no source available to audit. | UNAVAILABLE |
| 025 | `CryptGodSon/Trading-Bot-Binance-Futures` | DUPLICATE | Stochastic RSI/EMA200 and stop-loss rules; conventional indicator trend/oscillator combination. | DOC |
| 026 | `simoncampos1022/profitable-futures-trading-strategy-crypto-forex-stock` | REJECT — INSUFFICIENT | Multi-indicator bot with performance claims, but no distinct economic mechanism evidenced by the reviewed material; generic technical signal bundle. | DOC |
| 027 | `Nikhilperr/binance-futures-trading-bot` | DUPLICATE / OVERLAY | Source audit of signal generator confirms EMA/MACD/ADX trend, RSI/Bollinger/VWAP reversion, volume/OBV breakout and funding/OI fade—all duplicate existing families. Hourly signal-weight learning is an adaptation overlay. | CODE |
| 028 | `WickHunter/Wick-Hunter` | DUPLICATE / DEPRECATED | Liquidation data plus VWAP wick countertrade; same liquidation-wick/mean-reversion family. Repository says this version is deprecated. | DOC |
| 029 | `ZorClawAI/ZorClawAI-Trading-Bot` | NO ENGINE / TEMPLATE SET | Ten configurable strategy templates and execution/backtesting wrapper; no distinct new mechanism evidenced. | DOC |
| 030 | `Afinnn954/Bot-Futures-Binance-With-Gemini-AI` | OVERLAY / DUPLICATE | Telegram execution bot with optional conceptual Gemini mode and conventional strategy templates; AI wrapper is not independent alpha. | DOC |
| 031 | `Siddharthk17/Athena-Real-Time-Multi-Exchange-Funding-Rate-Arbitrage-System` | DUPLICATE — CROSS-VENUE FUNDING | Real-time multi-exchange funding-rate arbitrage; same cross-venue funding/basis family. | DOC |
| 032 | `hiesem/x402-crypto-derivatives-data` | NO ENGINE / DATA API | Supplies funding, OI, basis, IV, liquidation and order-book data; no trading policy. | DOC |
| 033 | `api-evangelist/bykaranteli` | NO ENGINE / API DIRECTORY | Third-party public API profile; explicitly not the API provider or a trading system. | DOC |
| 034 | `venkatanath18/crypto-order-flow` | FEATURE / OVERLAY | OFI regression and Hawkes event-intensity estimators; source implements estimators, not a complete entry/exit/position policy. Predictive strength decays sharply at longer horizons. | CODE |
| 035 | `estjuanmartinez6-jpg/crypto-orderflow-engine` | CONDITIONAL — ORDER-FLOW POLICY | Claims an ETH Binance-futures agent using aggressive flow, L2 imbalance and absorption. It belongs to the existing order-flow/microstructure family; a separate implementation audit is still needed before it can be counted as an independent sub-mechanism. | DOC |
| 036 | `testededgelab-lgtm/orderflow-signal-demo` | DUPLICATE — TAKER IMBALANCE | Short-window taker buy/sell imbalance plus activity and price impulse alert; a specific alert policy over the already-counted order-flow imbalance family. No autonomous execution. | DOC |
| 037 | `Mrbadador/autonomous-crypto-trading-bot` | DUPLICATE / OVERLAY | 4H Ichimoku trend expansion and 5m chop maker grid are existing trend-breakout and grid/MM families; OFI and Markov regime routing are filters/overlays. | CODE / DOC |
| 038 | `Co-Messi/HyperData-Terminal` | NO ENGINE / DATA TOOL | Cross-exchange whale, liquidation, order-flow and market-intelligence terminal; no original entry/exit engine. | DOC |
| 039 | `wilsontiger2222/liquidation-hunter` | DUPLICATE | Funding extremes, OI divergence and liquidation clusters; same positioning/liquidation family. Claimed win-rate/RR figures are not source-verified. | CODE / DOC |
| 040 | `logannye/cryptarch` | DUPLICATE / HEDGE OVERLAY | Funding carry and liquidation-cascade mean-reversion are existing families. OTM options strangle is a tail-hedge overlay, not a perp-native directional engine. | DOC |
| 041 | `theonetrade/pump-anomaly` | CONDITIONAL — SOCIAL COORDINATION SIGNAL | Distinct event-source mechanism: synchronize independent Telegram author clusters by symbol/direction, estimate lead/echo influence and Hawkes burst strength, then combine with per-source trained exits and liquidation-cascade/volatility filters. Not a futures-native source of alpha by itself; depends on external signal-channel quality, token coverage and realistic futures execution. Excluded from the strict futures-engine count pending a dedicated perpetual test. | CODE |
| 042 | `Hiroki-Nagao/market-tape` | NO ENGINE / VISUALIZATION | Sonifies trade and liquidation flow for monitoring; no strategy policy. | DOC |
| 043 | `elrazez/hl-robotrader` | CONDITIONAL — POST-CASCADE EXHAUSTION FADE | Distinct precise trigger: wait for a liquidation cascade's forced flow to exhaust (liquidation intensity collapses, CVD/book imbalance flips, mark-mid premium normalizes, no new extreme), then fade toward a pre-cascade anchor. It is not the same as a generic OI/liquidation-wick signal. However the author's own study says realistic live entries lose; the profitable trigger needs exact liquidation data not available from free public live feeds. Requires exact-feed access and a new OOS BTC/ETH test. | CODE / DOC |
| 044 | `gyc567/HyperData-Terminal` | DUPLICATE / FORK | Same HyperData Terminal data/visualization project as Co-Messi. | DOC |
| 045 | `dezeal/HyperData-Terminal` | DUPLICATE / FORK | Same HyperData Terminal data/visualization project. | DOC |
| 046 | `ahmadassayyaaf/HyperData-Terminal` | DUPLICATE / FORK | Same HyperData Terminal data/visualization project. | DOC |
| 047 | `voyager-hl/HyperData-Terminal` | DUPLICATE / FORK | Same HyperData Terminal data/visualization project. | DOC |
| 048 | `Starkl7/Crypto_MM` | DUPLICATE — MARKET MAKING | Avellaneda–Stoikov inventory-aware quoting and fill-intensity calibration; same market-making family already counted. Source reports walk-forward windows but only a short June 2026 sample. | CODE / DOC |
| 049 | `Thanh-Van-2001/HRL-GridMM` | OVERLAY — RL GRID/MM | Hierarchical RL selects grid regime/parameters and an adverse-selection predictor adjusts toxicity; underlying economic policy remains delta-neutral grid market making, already counted. | CODE / DOC |
| 050 | `haohaoi34/nexus-trade-bot` | DUPLICATE — GRID | Futures-default grid control centre; no distinct grid mechanism. | DOC |
| 051 | `lindkkk/crypto-grid-trading-sim` | DUPLICATE — GRID/MM | Bollinger-band grid with inventory skew and unwind modes; same grid/market-making family. | DOC |
| 052 | `HectorTa1989/hftbacktest-crypto` | NO ENGINE / UNAVAILABLE | Candidate is an HFT backtest project; repository fetch unavailable and no strategy source established. | UNAVAILABLE |
| 053 | `ThotDjehuty/cryptohftarb` | NO ENGINE / UNAVAILABLE | HFT/arbitrage candidate unavailable; no auditable trade policy established. | UNAVAILABLE |
| 054 | `hanno2/crypto-trading-bot-hft-backtest` | NO ENGINE / UNAVAILABLE | HFT backtest candidate unavailable; no distinct strategy source established. | UNAVAILABLE |
| 055 | `suzuki-kenji0627/hftbacktest` | NO ENGINE / UNAVAILABLE | HFT backtest framework candidate unavailable; no standalone engine evidenced. | UNAVAILABLE |
| 056 | `Sahanduiuc/hftbacktest-high-frequency-trading-and-market-making-backtesting-and-trading-bot-in-Python-and-Rust` | NO ENGINE / UNAVAILABLE | HFT/MM framework candidate unavailable; a framework does not count as an independent strategy. | UNAVAILABLE |
| 057 | `rajnikantdhardwivedi7/quantumtrade` | NO ENGINE / PLATFORM | Agentic trading OS and strategy competition platform; no specific independent perp-native mechanism established. | DOC |
| 058 | `MengerWen/Deep-Learning-Based-Delta-Neutral-Statistical-Arbitrage-on-Perpetual-Funding-Rates` | DUPLICATE — FUNDING CARRY | Rule-based/ML/sequence-model selection for delta-neutral funding-rate arbitrage. ML predicts opportunity quality but the economic mechanism remains funding carry. | DOC |
| 059 | `Aiden0334/statistical_arbitrage_model` | DUPLICATE / CONDITIONAL | Regime-aware cointegrated pair trading with variance-ratio timing. The README withholds implementation details; the core remains pair-spread stat-arb, already counted. | DOC |
| 060 | `HmiouiReda/Quantamental-StatArb-on-Crypto-Perpetual-Futures` | DUPLICATE / OVERLAY | Kalman dynamic hedge-ratio pairs mean reversion; FinBERT risk-off filter is a drawdown overlay, not a separate alpha engine. | CODE |
| 061 | `imnotkeril/crypto-sap-screener` | DUPLICATE — PAIR STAT-ARB | Engle–Granger pair screening, half-life, rolling z-score, Kalman hedge and spread backtester; same pair cointegration/mean-reversion family. | CODE |
| 062 | `Gzeu/quantluna` | DUPLICATE — PAIR STAT-ARB | Kalman-filter BTC/ETH pair spread and z-score execution; same pair stat-arb family. | DOC |
| 063 | `aurelien-gentile/crypto-pairs-trading` | DUPLICATE — PAIR STAT-ARB | Cointegrated Bybit perpetual pairs with funding costs and walk-forward parameter stress; same pair stat-arb family. | DOC |
| 064 | `Chakour-Yasser/cross-sectional-stat-arb` | CONDITIONAL — PCA RESIDUAL STAT-ARB | Distinct implementation: remove cross-sectional eigenportfolio factors, fit rolling OU dynamics to cumulative residual returns, and trade residual s-scores with lagged positions and turnover costs. This is distinct from two-leg cointegrated pairs. However reported crypto-perp results decay sharply in 2024–26 and are not robust net of costs; the repo's main positive result is historical equity data. Needs broad-universe futures replication and point-in-time constituent controls. | CODE |
| 065 | `ssanin82/dtc-stat-arb` | REJECT — NEGATIVE RESULT | 22 pre-registered cross-sectional stat-arb hypotheses; author concludes no strategy signal clears the bar. Costs are viable at daily/weekly frequencies but the tested strategy is dead. Preserve as negative evidence; do not import an engine. | DOC |
| 066 | `Panrk/PANRKBOT` | NO ENGINE / PLATFORM | Institutional-style multi-asset execution/analytics description; no source-backed independent signal policy identified. | DOC |
| 067 | `magnaopus1/Synthron-CFD-Trader-PRO` | REJECT — UNAVAILABLE | Repository not found on fetch; broad CFD/ML claims do not establish crypto-perp implementation. | UNAVAILABLE |
| 068 | `ak234184-eng/cryptoninja` | DUPLICATE | CoinDCX futures bot with indicator consensus, trend, mean reversion and breakout templates; conventional signal families. | DOC |
| 069 | `cavhd2/Synthron-CFD-Trader-PRO` | REJECT / INSUFFICIENT | Broad CFD/ML platform claims without an auditable crypto-perp mechanism. | DOC |
| 070 | `Freqtrade-Community/freqtrade-bot` | NO ENGINE / FRAMEWORK | Trading bot framework with strategy optimization; no one original strategy. | DOC |
| 071 | `khlin216/Synthron-CFD-Trader-PRO` | REJECT — UNAVAILABLE | Repository fetch unavailable; no perp strategy evidence. | UNAVAILABLE |
| 072 | `pabit/Synthron-CFD-Trader-PRO` | REJECT — UNAVAILABLE | Repository fetch unavailable; no perp strategy evidence. | UNAVAILABLE |
| 073 | `jahanzaib-codes/Universal-Market-Scanner` | NO ENGINE / SCANNER | RVOL, VWAP deviations, consolidation and volatility screening; discovery/alert features, not a trade engine. | DOC |
| 074 | `the-dev-z/alpha-trading` | NO ENGINE / PLATFORM | NOFX agentic multi-market OS; strategies/models are user-supplied/competing agents, not a source-audited new perp mechanism. | DOC |
| 075 | `shayanAbbasi1995/crypto-grid-trading-backtest` | NO ENGINE / ANALYTICS | Reconstructs grid trade history and reports returns/VaR; does not supply an entry/exit policy. | DOC |
| 076 | `FANATYQ/binance-futures-grid-bot` | DUPLICATE — GRID | Binance futures grid order automation; same grid family. | DOC |
| 077 | `xchrmas/Cryptocurrency-Bots` | NO ENGINE / COLLECTION | General bot collection; no unique crypto-perp alpha mechanism established by reviewed material. | DOC |
| 078 | `santibaricco/crypto_bot_grid_strategy` | REJECT — SPOT ONLY | Long-only spot grid/test bot; explicitly does not use leverage or futures. | DOC |
| 079 | `ronaldslins2/hyperliquid-trading-bot` | NO ENGINE / GENERIC BOT | Beginner Hyperliquid bot and learning examples; no distinct strategy hypothesis evidenced. | DOC |
| 080 | `vickywu0314/alpha-trading` | NO ENGINE / DUPLICATE PLATFORM | Same NOFX agentic trading OS as the-dev-z/alpha-trading. | DOC |
| 081 | `SK-GROUP-2025/Crypto-Trading-Bot-` | OVERLAY / EXECUTION | Binance order types including TWAP and grid modules; execution algorithms and order management, not a distinct predictive alpha engine. | DOC |
| 082 | `gh5u5765/opberfsoo0` | DUPLICATE — TREND | Bybit EMA crossover with ADX/DI regime filter and ATR risk; conventional trend-following. | DOC |
| 083 | `agw4wv/opaerfsrouo0` | DUPLICATE / CLONE | Same Bybit Trend Bot implementation/README as gh5u5765/opberfsoo0. | DOC |
| 084 | `discoveredcheck/crypto-mean-reversion` | REJECT — SPOT ONLY | Hourly spot cross-sectional short-term reversal and DOWN-token hedge; not a crypto-perpetual engine. | DOC |
| 085 | `brucechueh/mean-reversion-backtest` | REJECT / NEGATIVE RESEARCH | Bollinger/MACD mean reversion and subsequent structural/microstructure explorations; repository emphasizes negative OOS evidence, not a surviving futures engine. | DOC |
| 086 | `73nuts/crypto-signal-bot` | DUPLICATE — TREND | Daily academic trend-following futures signal for BTC/ETH/BNB/SOL; same time-series trend family. | DOC |
| 087 | `byttrade/free-crypto-trading-bot` | DUPLICATE — TREND/BREAKOUT | Four 4h futures breakout/trend variants (Supertrend flip, Keltner breakout, Ichimoku cloud break, regression-channel breakout) are one correlated trend/breakout family, not four distinct mechanisms. Funding, fees and slippage are modelled; reported limitations include universe dependence and multiple testing. | DOC |
| 088 | `DIO1009/resonance-breakout` | DUPLICATE — HTF TREND BREAKOUT | Long-only higher-timeframe trend state plus lower-timeframe breakout/pullback entry; same multi-timeframe trend-breakout family. | DOC |
| 089 | `NunoVieira6/drl-crypto-perpetual-futures` | OVERLAY / CONDITIONAL — RL POLICY FAMILY | PPO, A2C and RecurrentPPO trained in a perp environment with funding, fees and liquidation. These are alternative policy-learning algorithms in one RL engine family, not three independent mechanisms. The dataset/ablation pipeline is valuable validation evidence. | CODE / DOC |
| 090 | `ian20111999/RL-Crypto` | OVERLAY / RL FAMILY | PPO/SAC/TD3 ensemble and dynamic risk management; same RL policy family. | DOC |
| 091 | `mfzhang/20260416-RL-Crypto` | DUPLICATE / CLONE | Same RL-Crypto README and PPO/SAC/TD3 ensemble as ian20111999/RL-Crypto. | DOC |
| 092 | `deuteriumZzz/BitbotBY` | OVERLAY / RL ENSEMBLE | Bybit bot blends AI providers, SAC, Chronos and conventional signals; model ensemble and context filters do not establish a separate economic mechanism. | DOC |
| 093 | `mokshyaprotocol/signalview` | NO ENGINE / FRAMEWORK | Perpetual-specific DSL/backtester with funding/OI variables and cost accounting; it is an engine for testing user-authored expressions, not one distinct strategy. | DOC |
| 094 | `aria-tjr/coinbase-perp-trader` | DUPLICATE / BROKEN IMPLEMENTATION | Only momentum-breakout and mean-reversion strategies contain code; ML/RL modules are empty and required model package is missing. Published backtests use synthetic random-walk data. Both strategy families are duplicates. | CODE / DOC |
| 095 | `Cybbar/crypto-price-engine` | NO ENGINE / RESEARCH SCAFFOLD | Futures data/regime/ATR excursion and signal-evaluation pipeline; no unique complete entry/exit engine identified. | DOC |
| 096 | `LeakPilotAI/project-atlas` | NO ENGINE / ALERT SYSTEM | Hyperliquid anomaly/quality scanner and paper funnel; explicitly does not auto-trade. | DOC |
| 097 | `MarkusSela/bybit-technical-bot` | DUPLICATE | Weighted MACD/RSI/Bollinger/EMA/volume/Fear & Greed indicator score; conventional technical consensus. | DOC |
| 098 | `fratinelli09/SXE-Core` | NO ENGINE / SIMULATOR | General perp simulator/plugin execution framework. DCA case study demonstrates simulator mechanics and drawdown risk, not a new alpha mechanism. | DOC |
| 099 | `FarisZnf/Production-Grade-RSI-Momentum-Crypto-Trading-Strategy-with-Advanced-Statistical-Validation` | DUPLICATE | Wilder RSI momentum with walk-forward and bootstrap validation; RSI/oscillator momentum family. | DOC |
| 100 | `alsk1992/CloddsBot` | NO ENGINE / PLATFORM | AI trading terminal spanning prediction markets and crypto; no independently auditable perp signal mechanism established. | DOC |
| 101 | `aitradingbotspro/crypto-futures-ai-trading-bot` | OVERLAY / DUPLICATE | Funding/basis arbitrage monitoring, whale/MEV and liquidation alerts; monitor and data integration around existing carry/flow families. | DOC |
| 102 | `ybangaru/arbitrage_trading_rust_bot` | DUPLICATE — FUNDING ARB | Funding-rate arbitrage bot; README itself notes it fails to beat risk-free return. Same carry family. | DOC |
| 103 | `hypurrquant/perp-cli` | OVERLAY / DUPLICATE | CLI supports funding comparison, bridge transfers and perp-perp arbitrage workflows; cross-venue spread arb is already counted. CLI is a tool, not an independent signal engine. | DOC |
| 104 | `sgrochowalski/crypto-arbitrage-bot` | DUPLICATE — CROSS-EXCHANGE ARB | Delta-neutral same-contract long-cheap/short-rich cross-exchange perp spread convergence; same cross-venue dislocation family. Project archived. | DOC |
| 105 | `MRowhani/basis-funding-arbitrage-bot` | DUPLICATE — BASIS/CARRY | Delta-neutral spot/perp basis compression and funding-aware execution; same cash-and-carry family. | CODE / DOC |
| 106 | `wavyjay1/cross-exchange-arbitrage` | DUPLICATE — CROSS-EXCHANGE ARB | Same-asset cross-exchange futures price-difference strategy; same cross-venue dislocation family. | DOC |
| 107 | `beto201/delta-neutral-yield-vault` | DUPLICATE — FUNDING CARRY | Dual-anchor delta-neutral positions harvest funding differentials; same cross-venue funding/carry family. | DOC |
| 108 | `Pac1226/Crypto-Futures-Arbitrage_Bot` | DUPLICATE / STALE | Spot-buy/futures-sell basis trade concept; FTX-era project, no distinct engine. | DOC |
| 109 | `Orsonneri/crypto-trading-bots` | DUPLICATE COLLECTION | Contains candle momentum, spot grid, spot/perp carry, funding monitor, EMA trend and Bollinger/RSI mean reversion. These map to already-counted families; grid and spot-only variants do not create new futures engines. | DOC |

## Newly confirmed distinct mechanisms from this 109-candidate pass

The following three mechanisms add to the prior 47-mechanism register:

1. **Cross-asset delayed-beta / leader–laggard momentum** — BTC impulse leads, target asset underreacts, then trade the lagged response. Source: `sohan-shingade/flintstrats/momentum_cascade.py`. Conditional because the inspected implementation is BTC→SOL; adapting to BTC→ETH requires a separate hypothesis and test.
2. **Cross-sectional PCA factor-residual mean reversion** — estimate eigenportfolio factors, regress each asset return on factors, fit OU dynamics to cumulative residuals and trade residual s-scores. Source: `Chakour-Yasser/cross-sectional-stat-arb/src/statarb.py`. Conditional because the crypto-perp result decays and is not robust net of costs; it needs a broad-universe replication.
3. **Exact post-liquidation-flow exhaustion reversion** — detect a liquidation cascade, wait for liquidation intensity to collapse and order-flow/mark-mid conditions to normalize, then fade toward the pre-cascade anchor. Source specification: `elrazez/hl-robotrader/docs/STRATEGY_AND_RISK.md`. Conditional because the author reports realistic live entries lose and the apparent edge requires exact liquidation timing unavailable in free public live feeds.

The social-channel synchronized-pump detector in `theonetrade/pump-anomaly` is also a distinct event-source signal, but it is **not counted** among futures-native engines until its channel data, BTC/ETH perp applicability and execution economics are independently validated.

## Consolidated tally

| Measure | Result |
|---|---:|
| Candidate repositories individually dispositioned | **109 / 109** |
| Repositories with a relevant implementation/source file inspected in the current or earlier audit batches | **At least 23** |
| Documentation-only / framework / metadata / unavailable dispositions | Remaining entries, explicitly marked in the register |
| Previously accepted/conditional unique mechanisms | 47 |
| Additional conditional distinct mechanisms confirmed here | 3 |
| Current accepted/conditional distinct mechanism register | **50 / 100** |
| Duplicate / overlay / no-engine / reject candidates | Majority of the 109 repositories |
| Five-year BTC/ETH historical backtest started | **No** |

## Important qualification

The 109 repositories have all been individually classified. This does **not** mean 109 complete source implementations were available: several repositories are frameworks, forks, empty/inaccessible, or redact their strategy code. The evidence grade on each row tells you what was actually inspected. No unavailable or documentation-only candidate is silently promoted to a source-verified engine.

No code has been copied into Realcheck. These are audit dispositions and clean-room implementation candidates only. No historical Realcheck backtest is claimed to have run.
