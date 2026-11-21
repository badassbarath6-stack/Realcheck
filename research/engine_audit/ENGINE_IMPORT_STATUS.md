# Audited Mechanism Import — Research Branch

This branch is isolated from the approved Impulse Retracer runner and production deployment.

## Imported source-derived mechanisms

| Engine | Core rule preserved | Required fields | Status |
|---|---|---|---|
| Funding-rate mean reversion | Lagged funding extreme + lagged EMA trend context + lagged taker buy-ratio confirmation | OHLCV-derived buy ratio, point-in-time funding | Imported and registered for directional adapter; awaits historical feature feed |
| Taker-buy-pressure momentum | Lagged rolling taker-buy share, consecutive bar confirmation, ATR activity filter | Taker-buy volume / total volume | Imported and registered for directional adapter; awaits feature feed |
| Spot/perpetual funding carry | Positive funding threshold creates matched spot-long/perp-short sleeve | Spot close, perp funding, realized volatility | Imported as a matched hedge sleeve; spot feed and settlement cashflows required |
| Avellaneda–Stoikov funding-aware market making | Inventory-skewed reservation price, funding tilt, book-imbalance tilt, A-S spread and inventory caps | L1/L2 book, timestamps, fills, inventory, funding | Quote model imported; requires event-driven queue/fill simulation |
| Dated-futures cash-and-carry | Annualized delivery basis net of financing and both-leg fees | Spot, dated futures mark, expiry, borrow APR, contract specs | Economics module imported; requires expiry-aware execution/rehedge adapter |

## Conditional / rejected / held out

- OI/price quadrants: conditional module only. It uses lagged price/OI changes and labels falling-OI reversal directions as hypotheses, not observed trader intent. A regression test guards against current-bar look-ahead.
- Naive fixed-spread market maker: baseline only, not an independent alpha mechanism.
- Fixed funding threshold and funding z-score fade: variants of the same funding-extreme fade; deduplicated.
- Cross-exchange funding-adjusted OU: held out because inspected source uses rolling median backward-fill (future leakage) and full-sample ADF diagnostics. No import until corrected.
- Compression-conditioned breakout: held out pending evidence that it differs from Donchian/Turtle breakout already in the candidate set.

## Execution contract

- Directional bar engines emit a signal at bar close.
- The generic adapter enters at the next bar open, uses pessimistic stop-first resolution, and charges both-side fees and slippage.
- Its fixed fractional stop/target is an adapter-level evaluation policy, not a claim that the upstream engine used those exits. Reports must label this distinction.
- Market-making and cross-venue engines must never use the candle adapter. They require event-driven book/trade/fill/venue clocks.
- Carry sleeves are portfolio hedges, not naked directional trades. They require matched quantities and funding settlement cashflows.

## Data gap versus current Realcheck runner

The existing runner's M1 parser currently keeps OHLC only. It does not persist total volume, taker-buy volume, OI, taker long/short ratio, spot OHLC, L1/L2 depth, queue position, or dated-futures marks/expiry. The new modules therefore have explicit data contracts and are not silently routed into the old impulse/retracement simulator.

## Validation

The dedicated GitHub Actions workflow compiles the imported modules and runs the existing research regression suite plus audit-specific tests. The previous source-audit commit completed that workflow successfully. The OI lag correction in the current commit is covered by a new no-look-ahead regression test; its workflow result is pending.

## Audit count

Five distinct mechanisms passed source-level mechanism review and have been imported as research modules. OI remains conditional and is not promoted. These are code-level imports only; no historical backtest or profitability claim is made. The 100-candidate source audit remains incomplete.
