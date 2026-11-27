#!/usr/bin/env python3
"""Binance USD-M volume explosion research; independent of live execution code."""
from __future__ import annotations
import argparse, csv, hashlib, io, json, math, urllib.error, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://data.binance.vision/data/futures/um"
START = date(2023, 11, 25)
END_EXCLUSIVE = date(2026, 11, 25)  # last included UTC day: 2026-11-24
TFS = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
THRESHOLDS = (1.5, 2.0, 2.5, 3.0, 4.0)
RR_VALUES = (1.2, 2.0, 3.0)
SL_ATR = (1.0, 1.5)
FEE_BPS_SIDE = 5.0
SLIPPAGE_BPS_SIDE = 2.0
MIN_TRADES_FOR_RANK = 30
MS = 60_000


def months_between(start, end):
    y, m = start.year, start.month
    while (y, m) < (end.year, end.month):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def download(url, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        return path
    req = urllib.request.Request(url, headers={"User-Agent": "Realcheck-VolumeResearch/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=180) as response, path.open("wb") as out:
            while True:
                chunk = response.read(1 << 20)
                if not chunk:
                    break
                out.write(chunk)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return path


def archive_paths(symbol, data_dir):
    paths = []
    for year, month in months_between(START, END_EXCLUSIVE):
        name = f"{symbol}-1m-{year}-{month:02d}.zip"
        url = f"{BASE}/monthly/klines/{symbol}/1m/{name}"
        paths.append(download(url, Path(data_dir) / name))
    day = START if START.day == 1 else START.replace(day=1)
    while day < END_EXCLUSIVE:
        if day.year == END_EXCLUSIVE.year and day.month == END_EXCLUSIVE.month:
            break
        day = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
    d = END_EXCLUSIVE.replace(day=1)
    while d < END_EXCLUSIVE:
        name = f"{symbol}-1m-{d.year}-{d.month:02d}-{d.day:02d}.zip"
        url = f"{BASE}/daily/klines/{symbol}/1m/{name}"
        paths.append(download(url, Path(data_dir) / name))
        d += timedelta(days=1)
    return paths


def read_m1(paths):
    rows = {}
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            csv_names = [n for n in archive.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError(f"No CSV found in Binance archive {path}")
            with archive.open(csv_names[0]) as raw:
                for line in io.TextIOWrapper(raw, encoding="utf-8"):
                    parts = line.strip().split(",")
                    if len(parts) < 11 or not parts[0].isdigit():
                        continue  # header
                    t = int(parts[0])
                    o, h, l, c, vol = map(float, parts[1:6])
                    taker_buy_base = float(parts[9])
                    if not all(math.isfinite(x) for x in (o, h, l, c, vol, taker_buy_base)):
                        raise ValueError(f"Non-finite kline value in {path}")
                    if min(o, h, l, c) <= 0 or vol < 0 or l > min(o, c) or h < max(o, c) or h < l:
                        raise ValueError(f"Invalid kline row in {path}: {parts[:11]}")
                    row = (o, h, l, c, vol, taker_buy_base)
                    if t in rows and rows[t] != row:
                        raise ValueError(f"Conflicting duplicate M1 timestamp {t}")
                    rows[t] = row
    lo = int(datetime.combine(START, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    hi = int(datetime.combine(END_EXCLUSIVE, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000)
    result = [(t, *v) for t, v in sorted(rows.items()) if lo <= t < hi]
    if not result:
        raise RuntimeError("No Binance M1 rows found in requested date range")
    gaps = [(a[0], b[0]) for a, b in zip(result, result[1:]) if b[0] - a[0] != MS]
    expected = (hi - lo) // MS
    coverage = len(result) / expected
    if coverage < 0.995:
        raise RuntimeError(f"M1 data coverage only {coverage:.3%}; refusing to backtest")
    return result, gaps


def resample(rows, minutes):
    step = minutes * MS
    buckets = {}
    for t, o, h, l, c, vol, taker_buy in rows:
        key = t // step * step
        if key not in buckets:
            buckets[key] = [o, h, l, c, vol, taker_buy, 1]
        else:
            x = buckets[key]
            x[1] = max(x[1], h)
            x[2] = min(x[2], l)
            x[3] = c
            x[4] += vol
            x[5] += taker_buy
            x[6] += 1
    return [(t, *x[:6]) for t, x in sorted(buckets.items()) if x[6] == minutes]


def enrich(bars):
    n = len(bars)
    out = []
    tr = []
    for i, b in enumerate(bars):
        t, o, h, l, c, vol, taker_buy = b
        prev_close = bars[i - 1][4] if i else c
        tr.append(max(h - l, abs(h - prev_close), abs(l - prev_close)))
    for i, b in enumerate(bars):
        t, o, h, l, c, vol, taker_buy = b
        if i >= 14:
            atr = sum(tr[i - 13:i + 1]) / 14
        else:
            atr = float("nan")
        prior_vol = [bars[j][5] for j in range(max(0, i - 20), i)]
        avg_vol = sum(prior_vol) / 20 if len(prior_vol) == 20 else float("nan")
        prior_high = max((bars[j][2] for j in range(max(0, i - 20), i)), default=float("nan"))
        prior_low = min((bars[j][3] for j in range(max(0, i - 20), i)), default=float("nan"))
        body = abs(c - o)
        rng = h - l
        out.append({"t": t, "o": o, "h": h, "l": l, "c": c, "v": vol,
                    "tb": taker_buy, "atr": atr, "avg_vol": avg_vol,
                    "vol_ratio": vol / avg_vol if avg_vol > 0 else float("nan"),
                    "body_ratio": body / rng if rng > 0 else 0.0,
                    "range_atr": rng / atr if atr > 0 else float("nan"),
                    "direction": 1 if c > o else (-1 if c < o else 0),
                    "prior_high": prior_high, "prior_low": prior_low,
                    "taker_buy_ratio": taker_buy / vol if vol > 0 else 0.0})
    return out


def make_signals(bars):
    specs = []
    # Ten genuinely distinct, explicitly named entry mechanisms.
    for x in THRESHOLDS:
        specs.append((f"V{len(specs)+1:02d}_VOL_{x:g}X", lambda b, x=x: b["vol_ratio"] >= x))
    specs += [
        ("V06_2X_STRONG_BODY", lambda b: b["vol_ratio"] >= 2 and b["body_ratio"] >= .60),
        ("V07_2X_RANGE_ATR", lambda b: b["vol_ratio"] >= 2 and b["range_atr"] >= 1.20),
        ("V08_2X_20BAR_BREAKOUT", lambda b: b["vol_ratio"] >= 2 and
         ((b["direction"] == 1 and b["c"] > b["prior_high"]) or
          (b["direction"] == -1 and b["c"] < b["prior_low"]))),
        ("V09_2X_TAKER_PRESSURE", lambda b: b["vol_ratio"] >= 2 and
         ((b["direction"] == 1 and b["taker_buy_ratio"] >= .60) or
          (b["direction"] == -1 and b["taker_buy_ratio"] <= .40))),
        ("V10_2X_BODY_AND_RANGE", lambda b: b["vol_ratio"] >= 2 and
         b["body_ratio"] >= .55 and b["range_atr"] >= 1.0),
    ]
    signals = defaultdict(list)
    for i, b in enumerate(bars):
        if i < 20 or not math.isfinite(b["atr"]) or b["direction"] == 0:
            continue
        for name, condition in specs:
            if condition(b):
                signals[name].append((i, b["direction"]))
    return signals


def latest_completed_direction(htf_bars, entry_time, htf_minutes):
    # Only candles whose close time is <= entry time may confirm a lower-TF signal.
    lo, hi = 0, len(htf_bars)
    while lo < hi:
        mid = (lo + hi) // 2
        if htf_bars[mid]["t"] + htf_minutes * MS <= entry_time:
            lo = mid + 1
        else:
            hi = mid
    return htf_bars[lo - 1]["direction"] if lo else 0


def evaluate_trade(bars, signal_i, direction, sl_mult, rr):
    if signal_i + 1 >= len(bars):
        return None
    sig = bars[signal_i]
    entry_bar = bars[signal_i + 1]
    entry = entry_bar["o"]
    risk = sig["atr"] * sl_mult
    if not math.isfinite(risk) or risk <= 0:
        return None
    stop = entry - direction * risk
    target = entry + direction * risk * rr
    exit_price, reason, exit_i = bars[-1]["c"], "end_of_data", len(bars) - 1
    for j in range(signal_i + 1, len(bars)):
        b = bars[j]
        if direction == 1:
            if b["o"] <= stop: exit_price, reason, exit_i = b["o"], "stop_gap", j; break
            if b["l"] <= stop: exit_price, reason, exit_i = stop, "stop", j; break
            if b["o"] >= target: exit_price, reason, exit_i = b["o"], "target_gap", j; break
            if b["h"] >= target: exit_price, reason, exit_i = target, "target", j; break
        else:
            if b["o"] >= stop: exit_price, reason, exit_i = b["o"], "stop_gap", j; break
            if b["h"] >= stop: exit_price, reason, exit_i = stop, "stop", j; break
            if b["o"] <= target: exit_price, reason, exit_i = b["o"], "target_gap", j; break
            if b["l"] <= target: exit_price, reason, exit_i = target, "target", j; break
    gross = direction * (exit_price - entry) / entry * 10_000
    costs = 2 * (FEE_BPS_SIDE + SLIPPAGE_BPS_SIDE)
    return {"signal_time": sig["t"], "entry_time": entry_bar["t"], "exit_time": bars[exit_i]["t"],
            "direction": "LONG" if direction == 1 else "SHORT", "entry": entry,
            "exit": exit_price, "stop": stop, "target": target, "exit_reason": reason,
            "signal_open": sig["o"], "signal_high": sig["h"], "signal_low": sig["l"], "signal_close": sig["c"],
            "signal_volume": sig["v"], "preceding_20_avg_volume": sig["avg_vol"],
            "volume_ratio": sig["vol_ratio"], "signal_atr": sig["atr"],
            "gross_bps": gross,
            "cost_bps": costs, "net_bps": gross - costs,
            "holding_bars": exit_i - signal_i - 1}


def metrics(trades):
    net = [x["net_bps"] for x in trades]
    gross = [x["gross_bps"] for x in trades]
    gp_net = sum(x for x in net if x > 0)
    gl_net = -sum(x for x in net if x < 0)
    gp_gross = sum(x for x in gross if x > 0)
    gl_gross = -sum(x for x in gross if x < 0)
    equity = peak = drawdown = 0.0
    for x in net:
        equity += x
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    return {"trades": len(net), "wins": sum(x > 0 for x in net), "losses": sum(x <= 0 for x in net),
            "win_rate_pct": 100 * sum(x > 0 for x in net) / len(net) if net else 0.0,
            "gross_profit_bps": gp_gross, "gross_loss_bps": gl_gross,
            "net_profit_bps": sum(net), "net_bps": sum(net),
            "profit_factor": gp_net / gl_net if gl_net else (999.0 if gp_net else 0.0),
            "expectancy_bps": sum(net) / len(net) if net else 0.0,
            "max_drawdown_bps": drawdown}

def split_name(timestamp):
    dt = datetime.fromtimestamp(timestamp / 1000, timezone.utc).date()
    if dt < date(2025, 11, 25): return "train"
    if dt < date(2026, 5, 25): return "validation"
    return "oos"


def simulate_model(bars, signals, model, htf=None, confirm_tf=None):
    eligible = []
    for sig_i, direction in signals:
        entry_i = sig_i + 1
        if entry_i >= len(bars):
            continue
        if htf is not None:
            confirm = latest_completed_direction(htf, bars[entry_i]["t"], TFS[confirm_tf])
            if confirm != direction:
                continue
        eligible.append((sig_i, direction))
    # Each SL/RR configuration is a separate portfolio with its own position lock.
    output = []
    time_to_idx = {b["t"]: i for i, b in enumerate(bars)}
    for sl in SL_ATR:
        for rr in RR_VALUES:
            next_allowed = 0
            for sig_i, direction in eligible:
                if sig_i < next_allowed:
                    continue
                trade = evaluate_trade(bars, sig_i, direction, sl, rr)
                if not trade:
                    continue
                trade.update({"model": model, "sl_atr": sl, "rr": rr,
                              "period": split_name(trade["entry_time"])})
                output.append(trade)
                exit_i = time_to_idx.get(trade["exit_time"], sig_i)
                next_allowed = exit_i + 1
    return output

def write_csv(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""): h.update(chunk)
    return h.hexdigest()


def run_symbol(symbol, data_dir, output_dir):
    paths = archive_paths(symbol, data_dir)
    m1, gaps = read_m1(paths)
    enriched = {}
    for tf, mins in TFS.items():
        enriched[tf] = enrich(resample(m1, mins))
    summary, all_trades = [], []
    # Independent same-timeframe engines.
    for tf, bars in enriched.items():
        sigs = make_signals(bars)
        for model, events in sigs.items():
            trades = simulate_model(bars, events, f"{model}_{tf}")
            all_trades.extend([dict(x, symbol=symbol, execution_tf=tf, confirmation_tf="none") for x in trades])
    # MTF: each execution timeframe is confirmed by every strictly higher available timeframe.
    tf_order = list(TFS)
    for exec_tf in tf_order:
        exec_bars = enriched[exec_tf]
        base_signals = make_signals(exec_bars)["V02_VOL_2X"]
        for confirm_tf in tf_order:
            if TFS[confirm_tf] <= TFS[exec_tf]: continue
            htf = enriched[confirm_tf]
            model = f"MTF_VOL2X_{exec_tf}_CONFIRM_{confirm_tf}"
            trades = simulate_model(exec_bars, base_signals, model, htf=htf, confirm_tf=confirm_tf)
            all_trades.extend([dict(x, symbol=symbol, execution_tf=exec_tf, confirmation_tf=confirm_tf) for x in trades])
    for model in sorted({x["model"] for x in all_trades}):
        for sl in SL_ATR:
            for rr in RR_VALUES:
                for period in ("train", "validation", "oos", "year_2023", "year_2024", "year_2025", "year_2026"):
                    if period.startswith("year_"):
                        year = int(period[-4:])
                        selected = [x for x in all_trades if x["model"] == model and x["sl_atr"] == sl and x["rr"] == rr and datetime.fromtimestamp(x["entry_time"] / 1000, timezone.utc).year == year]
                    else:
                        selected = [x for x in all_trades if x["model"] == model and x["sl_atr"] == sl and x["rr"] == rr and x["period"] == period]
                    summary.append({"symbol": symbol, "model": model, "sl_atr": sl, "rr": rr,
                                    "period": period, **metrics(selected)})
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / f"{symbol}_volume_mtf_trades.csv", all_trades)
    write_csv(out / f"{symbol}_volume_mtf_metrics.csv", summary)
    manifest = {"symbol": symbol, "venue": "Binance USD-M perpetual futures",
                "start_utc": START.isoformat(), "end_utc_inclusive": (END_EXCLUSIVE - timedelta(days=1)).isoformat(),
                "timeframes": list(TFS), "m1_rows": len(m1), "m1_coverage_pct": round(100 * len(m1) / ((END_EXCLUSIVE - START).days * 1440), 5),
                "m1_gap_count": len(gaps), "first_100_gaps": gaps[:100],
                "volume_field": "base asset volume (Binance kline column 5); taker-buy base volume (column 10)",
                "volume_baseline": "mean of preceding 20 completed candles, current candle excluded",
                "entry": "next execution-timeframe candle open after completed signal candle",
                "stop": "1.0x or 1.5x ATR(14) measured at signal candle; target RR 1.2, 2.0, 3.0",
                "intrabar_rule": "if stop and target both touched in one candle, stop is assumed first",
                "fees_slippage": {"fee_bps_per_side": FEE_BPS_SIDE, "slippage_bps_per_side": SLIPPAGE_BPS_SIDE},
                "periods": {"train": "2023-11-25 through 2025-11-24", "validation": "2025-11-25 through 2026-05-24", "oos": "2026-05-25 through 2026-11-24"},
                "funding": "Not yet included; results are fee/slippage-adjusted but not funding-adjusted",
                "source_archives": [{"file": p.name, "sha256": sha256(p)} for p in paths],
                "status": "RESEARCH_OUTPUT_NOT_PROMOTION_APPROVAL"}
    (out / f"{symbol}_volume_mtf_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps(manifest, indent=2))
    print(f"Wrote {len(summary)} metric rows and {len(all_trades)} trade rows for {symbol}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT", "BOTH"), default="BOTH")
    p.add_argument("--data-dir", default="/tmp/binance-volume")
    p.add_argument("--output-dir", default="volume-mtf-results")
    a = p.parse_args()
    for symbol in (("BTCUSDT", "ETHUSDT") if a.symbol == "BOTH" else (a.symbol,)):
        run_symbol(symbol, a.data_dir, a.output_dir)


if __name__ == "__main__":
    main()
