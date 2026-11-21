# Audited Mechanism Import — Research Branch

This branch is isolated from the approved Impulse Retracer runner and production deployment.

## Imported source-derived mechanisms

| Engine | Core rule preserved | Required fields | Status |
|---|---|---|---|
| Funding-rate mean reversion | Lagged funding extreme + lagged EMA trend context + lagged taker buy-ratio confirmation | OHLCV-derived buy ratio, point-in-time funding | Signal module imported; awaiting historical feature feed |
| Taker-buy-pressure momentum | Lagged rolling taker-buy share, consecutive bar confirmation, ATR activity filter | Taker-buy volume / total volume | Signal module imported; awaiting feature feed |
| Spot/perpetual funding carry | Positive funding threshold creates matched spot-long/perp-short sleeve | Spot close, perp funding, realized volatility | Signal module imported; spot feed required |
| Avellaneda–Stoikov funding-aware market making | Inventory-skewed reservation price, funding tilt, book-imbalance tilt, A-S spread and inventory caps | L1/L2 book, timestamps, fills, inventory, funding | Quote model imported; not backtestable with candle-only runner |
| Dated-futures cash-and-carry | Annualized delivery basis net of financing and both-leg fees | Spot, dated futures mark, expiry, borrow APR, contract specs | Economics module imported; execution/rehedge adapter still required |

## Conditional / rejected / held out

- OI/price quadrants: conditional module only. Falling OI cannot identify which side is closing; reversal directions are explicitly marked as hypotheses, not observed trader intent.
- Naive fixed-spread market maker: baseline only, not an independent alpha mechanism.
- Fixed funding threshold and funding z-score fade: variants of the same funding-extreme fade; deduplicated.
- Cross-exchange funding-adjusted OU: held out because inspected source uses rolling median backward-fill (future leakage) and full-sample ADF diagnostics. No import until corrected.
- Compression-conditioned breakout: held out pending evidence that it differs from Donchian/Turtle breakout already in the candidate set.

## Execution contract

- Directional bar engines emit a signal at bar close.
- The generic adapter enters at the next bar open, uses pessimistic stop-first resolution, and charges both-side fees and slippage.
- Its fixed fractional stop/target is an adapter evaluation policy, not a claim that the upstream engine used those exits. Reports must label this distinction.
- Market-making and cross-venue engines must never use the candle adapter. They require event-driven book/trade/fill/venue clocks.
- Carry sleeves are portfolio hedges, not naked directional trades. They require matched quantities and funding settlement cashflows.

## Data gap versus current Realcheck runner

The existing runner's M1 parser currently keeps OHLC only. It does not persist total volume, taker-buy volume, OI, taker long/short ratio, spot OHLC, L1/L2 depth, queue position, or dated-futures marks/expiry. The new modules therefore have explicit data contracts and are not silently routed into the old impulse/retracement simulator.

## Audit count

Five distinct mechanisms passed source-level mechanism review and have been imported as research modules. OI remains conditional and is not promoted. These are code-level imports only; no historical backtest or profitability claim is made. The 100-candidate source audit remains incomplete.
