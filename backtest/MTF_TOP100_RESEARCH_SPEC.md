# Impulse Retracer — Two-Year MTF Top-100 Research

Status: research specification; no results are claimed by this file.

## Objective
Re-discover a fresh ranked set of 100 configurations from a parameter search. The previously approved Top-100 CSV is not a candidate source and must not be reused as the answer. It may remain untouched as historical provenance.

## Fixed model architecture (must match live model)
- Instruments: BTCUSDT and ETHUSDT, Binance USD-M perpetuals.
- Primary impulse timeframe: H1, evaluated on every minute from the forming H1 candle using only information available at that minute.
- Entry timeframe: M1. Evaluate only completed M1 candles; a trigger is alerted at that candle close and simulated at the next M1 open.
- Retain all qualifying setup/configuration candidates through their pending window.
- One alert per symbol/H1 impulse across the whole 100-config model.
- If one configuration triggers in the first trigger minute, alert that configuration without PF gating.
- If multiple configurations trigger in that exact same M1 minute, select by validated training-period PF among those simultaneous contenders only. Never compare across different trigger minutes.
- Lock the symbol/H1 impulse after alert; no further alerts for that impulse.
- Pending expiry remains the existing `pending_bars=3` semantics: impulse hour plus next three complete H1 bars; expiry at the following H1 open.
- No intrabar look-ahead. If stop and target are touched in one M1 candle, stop-first. Adverse stop gaps fill at the candle open.
- Correct Wilder SMA seed and recurrence for ATR/ADX/RSI; align indicator history with live engine (1440 completed H1 bars plus current forming H1 snapshot).
- Research only. Do not deploy or alter live worker/production strategy registry.

## Two-year period and split
- UTC start: 2024-11-20 inclusive.
- UTC end: 2026-11-20 exclusive.
- Chronological split: first 60% training, next 20% validation, final 20% untouched out-of-sample.
- No parameter selection using the final 20%.
- Data integrity: verify archive checksums, continuous M1 timestamps, OHLC sanity, H1/M5/M15/H4 aggregation boundaries and no duplicates/gaps. Record source and checksums.

## Search factors
Core:
- Impulse threshold: 2.0, 2.2, 2.4, 2.6, 2.8, 3.0 × prior completed H1 ATR.
- ATR period: 10, 14, 20, 28.
- H1 retracement: 61.8%, 66.7%, 70.7%, 75.0%, 78.6%, 82.0%.
- ADX(14) min/max bands: 14–25, 18–30, 20–35, 25–40, 30–45.
- Stop/target: preserve structural opposite-impulse-extreme stop as the baseline; test structural buffer 0, 0.1, 0.2 ATR; target RR 1.5, 2.0, 2.5, 3.0, 4.0. Stop geometry and target RR are explicit configuration fields and must be used consistently in live-equivalent simulation.
- Pending bars fixed at 3 for this research.

Only additional factor:
- MTF confirmation timeframe: NONE (baseline), 5m, 15m, 1h, 4h.
- Confirmation rule: latest fully completed candle on the selected timeframe must agree directionally with the forming H1 impulse. For 1h use the current forming H1 direction, not a future close. For 4h use the latest fully completed H4 candle (do not use future H4 close). For M5/M15, use the latest fully completed candle available at the current M1 decision time.
- No candle-body threshold. No volume, EMA, RSI, session, or any other added confirmation factor. RSI is not a search dimension in this study; do not silently add it as a gate.

## Search procedure and selection
- Stage the search to avoid a combinatorial explosion: evaluate core-factor candidates first, then add the single MTF dimension. Use deterministic exhaustive/covering combinations and record the exact generated search-space size and every pruning rule.
- All MTF variants must share identical timestamped market data and execution/cost assumptions.
- Evaluate each configuration independently to estimate training/validation PF, then apply the model's earliest-trigger/one-alert selection rule using only same-minute contenders.
- Rank candidates on validation results, not training or final OOS. Require at least 30 completed training trades and 30 validation trades before eligibility; also report results for excluded low-sample candidates.
- Prefer robust net PF, expectancy, drawdown, sample size, and consistency across BTC/ETH and time segments. Do not force 100 if fewer than 100 pass minimum quality gates; if 100 are required for file compatibility, label lower-quality ranks as non-qualified rather than implying edge.
- After freezing Top 100 from validation, run the final 20% once as untouched OOS.

## Costs and reporting
- Fees: 5 bps per side.
- Slippage scenarios: 2 bps and 7 bps per side.
- Official Binance USD-M funding-rate archives; disclose missing/partial archive coverage.
- Report trades, wins/losses, win rate, gross/net bps, PF, expectancy, max drawdown, average win/loss, stop/target/time exits, holding time, BTC/ETH splits, long/short splits, monthly/quarterly stability, and stress results.
- Deliver: immutable search manifest, source/data checksums, full per-configuration metrics, candidate universe, validation-ranked Top-100 CSV, frozen final OOS trades and summary, and reproducibility metadata.

## Acceptance gates
1. Tests prove live-equivalent H1 forming-candle detection and M1 trigger/fill timing.
2. Tests prove MTF values are strictly as-of-time and use no incomplete future candle (except explicitly forming H1).
3. Tests prove one-alert-per-impulse, no cross-minute PF comparisons, single-candidate no-PF bypass, same-minute PF selection, pending expiry and stop-first handling.
4. Correct Wilder calculations and sufficient warmup are independently verified.
5. Run completes for both assets and every requested MTF variant; no partial output may be labelled complete.
6. Final OOS is untouched until Top-100 freeze; no PF registry is published to live configuration as a side effect.
