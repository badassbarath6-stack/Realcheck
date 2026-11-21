# Audited strategy ports

This directory contains isolated, clean-room research ports. They are intentionally
not wired into the existing impulse-retracement runner.

## Included

- `funding_rate_mean_reversion`: funding-extreme fade with EMA and lagged taker-flow filters.
- `taker_buy_pressure_momentum`: taker-buy dominance, consecutive confirmation and ATR activity gate.
- `oi_price_divergence`: price/OI quadrant logic, explicitly experimental and not approved as a causal interpretation of trader positioning.
- `spot_perp_funding_carry`: funding carry eligibility flag; only valid in a matched spot/perp portfolio simulator.

## Required next-bar convention

Each bar-signal function returns a signal aligned to the input row. A backtester
must not fill at that same bar's close. The earliest allowed fill is the next
bar's open (or a more conservative executable quote). Signals are not orders.

## Provenance / licensing

The first three are clean-room reimplementations of the inspected signal
mathematics from Gotodataru/binance-futures-backtest. The repository had no
visible license at the time of audit, so its code is not copied. The carry
signal is an independent expression of the documented funding-carry rule.
Do not represent these as verbatim copies.

## Data gates

- Funding fade: OHLC close, point-in-time funding_rate, taker buy ratio.
- Taker pressure: OHLC and taker buy volume / total volume.
- OI divergence: OHLC, open interest, taker long/short volume ratio. This one
  remains conditional pending a valid economic interpretation and robust OI feed.
- Spot/perp carry: synchronized spot and perp prices, actual funding settlements,
  contract specifications and two-leg execution costs.

No backtest has been started by adding these files. Data contracts and execution
adapters must pass their own tests before any results are reported.


## Latest source audit

Batch 04 adds 15 distinct source-reviewed mechanisms. See [AUDIT_BATCH_04.md](AUDIT_BATCH_04.md) for exact source files, rule definitions, deduplication decisions, defects, licensing and import boundaries. The cumulative accepted/conditional source-review count is 23 of the requested 100. No historical backtest has started.


Batch 05 adds four source-reviewed mechanisms. The cumulative accepted/conditional source-review count is 27 of the requested 100; 73 remain. See [AUDIT_BATCH_05.md](AUDIT_BATCH_05.md). No historical backtest has started.
