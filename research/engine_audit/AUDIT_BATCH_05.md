# Source Audit — Batch 05

Scope: additional source-level inspection of Freqtrade's official strategy examples. The source repository is GPL-3.0; this audit records algorithm behavior but does not copy its code into Realcheck.

## New distinct mechanisms

| # | Mechanism | Source | Exact rule observed | Decision |
|---:|---|---|---|---|
| 1 | Hour-of-day seasonal entry/exit | [HourBasedStrategy.py](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/HourBasedStrategy.py) | On a 1-hour timeframe, enter whenever UTC candle hour is in a configurable buy-hour interval and exit in a configurable sell-hour interval. It contains no price indicator or direction signal; its entire edge hypothesis is intraday seasonality. | PASS as a distinct time-of-day seasonality mechanism; CONDITIONAL pending timezone/venue clock definition, survivorship-free pair selection and strict walk-forward hour-window selection. |
| 2 | Hammer-pattern capitulation with oscillator confluence | [Strategy002.py](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/Strategy002.py) | Long when TA-Lib hammer pattern is +100, RSI <30, slow stochastic K <20 and close is below the lower Bollinger band. Exit when PSAR is above close and inverse-Fisher RSI >0.3. | PASS as a distinct candlestick-pattern confirmation entry. Long-only source; preserve its native PSAR/Fisher exit rather than imposing a generic fixed-RR exit. |
| 3 | ADX-regime stochastic exhaustion reversal | [Strategy004.py](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/Strategy004.py) | Require ADX >50 or slow ADX >26, CCI <-100, fast and slow stochastic oversold; enter on fast stochastic K crossing above D. Exit when slow ADX <25 and fast stochastic has recovered above 70 with close above EMA5. | PASS mechanism, long-only. The source comment warns about global mean-volume look-ahead, but the inspected implementation uses a rolling 12-bar volume mean; preserve rolling behavior and audit the threshold/units. |
| 4 | Donchian-position / Keltner-width ratio regime | [Heracles.py](https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/Heracles.py) | Compute Donchian channel percent-B and Keltner channel width; compare values from separately lagged bars through a configurable ratio band to trigger long entry. Source uses a fixed ROI/stop and no signal exit. | CONDITIONAL PASS as a distinct normalized channel-state ratio. Needs exact indicator definitions, timestamp alignment and a reasonableness audit of its parameter ranges; source's reported optimization sample is not evidence of edge. |

## Deduplication and defects

- TD Sequential in the root strategy collection and the berlinguyinca subfolder is the same 9-count implementation; it remains one mechanism from Batch 04.
- Strategy001 is an EMA20/EMA50 crossover confirmed by Heikin-Ashi candle direction, with EMA50/EMA100 + opposite Heikin-Ashi exit. This is a conventional trend-following crossover variant and is not counted separately.
- PowerTower uses exponentiation of raw close prices against lagged closes with a tunable exponent. The rule is scale-dependent and dimensionally unstable across assets/prices; reject.
- Diamond is a generic configurable field-to-field crossover template (including price, volume or user-added indicators), not a concrete independent mechanism; reject as a framework/template.
- GodStra is a genetic indicator-condition generator, not a single strategy mechanism; reject as a generic strategy-generation framework.
- BreakEven is an exit-only ROI/stoploss profile with no entry mechanism; reject as an independent strategy.
- FixedRiskRewardLoss is a risk/exit overlay with an always-enter placeholder. Its inspected stop calculations mix current_rate and trade.open_rate in the break-even/initial-risk calculations; do not import it as a complete engine.
- CustomStoplossWithPSAR is an exit-only PSAR trailing-stop example with a deliberately nonsensical placeholder entry; do not count as an independent alpha mechanism.
- Ichimoku, Supertrend, Alligator, OTT, EMA and MA-ribbon examples remain trend-indicator variants under the deduplication rule. Keltner-only breakout remains a volatility-envelope breakout variant.
- The same official Freqtrade strategy source family is GPL-3.0. Clean-room mathematical reimplementation only unless Realcheck's distribution licence is confirmed GPL-compatible.

## Batch 05 tally

- 4 new source-reviewed mechanisms accepted or conditionally accepted at mechanism level.
- 8 additional source files were inspected and rejected/deduplicated as templates, overlays, indicator variants or defective implementations.
- No historical backtest started.
