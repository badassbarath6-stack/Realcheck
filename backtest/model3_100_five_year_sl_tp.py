#!/usr/bin/env python3
"""Five-year Model 3-100 SL/TP research run on official Binance USD-M Futures data.

This is a research-only runner. It does not modify the embedded 100 configurations,
does not submit orders, and does not change the live evaluator.
"""
import argparse
import bisect
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Model_3-100_Google_Apps_Script.gs"
CACHE = ROOT / ".backtest-cache"
OUT = ROOT / "backtest-results"
BASE_URL = "https://data.binance.vision/data/futures/um"
SYMBOL = "BTCUSDT"
MINUTE = 60_000
HOUR = 60 * MINUTE
MAX_HOLD = 24 * HOUR
FEE_BPS_PER_SIDE = 5.0
SLIPPAGE_SCENARIOS = (2.0, 7.0)  # GAS research baseline; current live fill estimate stress case
SL_MULTIPLIERS = (0.50, 0.75, 1.00, 1.25, 1.50, 2.00)
TP_RR_VALUES = (1.00, 1.25, 1.50, 2.00, 2.50, 3.00, 4.00, 5.00)
SPLIT_TIME = None


def utc_ms(date_text):
    return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp() * 1000)


def http_bytes(url, retries=4):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Model-3-100-research/1.0", "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read()
        except Exception as exc:
            last = exc
            if attempt + 1 < retries:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Download failed after {retries} attempts: {url}: {last}")


def archive_url(kind, interval, period):
    if kind == "monthly":
        filename = f"{SYMBOL}-{interval}-{period}.zip"
    else:
        filename = f"{SYMBOL}-{interval}-{period}.zip"
    return f"{BASE_URL}/{kind}/klines/{SYMBOL}/{interval}/{filename}"


def fetch_archive(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    local = CACHE / Path(urllib.parse.urlparse(url).path).name
    if not local.exists():
        payload = http_bytes(url)
        local.write_bytes(payload)
    checksum_url = url + ".CHECKSUM"
    checksum_text = http_bytes(checksum_url).decode("utf-8", "replace").strip()
    expected = checksum_text.split()[0].lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise RuntimeError(f"Unexpected Binance checksum format for {url}: {checksum_text[:100]}")
    actual = hashlib.sha256(local.read_bytes()).hexdigest()
    if actual != expected:
        local.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for Binance archive {url}: expected {expected}, got {actual}")
    return local, actual


def archive_periods(start_ms, end_ms):
    start = datetime.fromtimestamp(start_ms / 1000, timezone.utc)
    end = datetime.fromtimestamp((end_ms - 1) / 1000, timezone.utc)
    months = []
    cur = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    last = datetime(end.year, end.month, 1, tzinfo=timezone.utc)
    while cur <= last:
        months.append(cur.strftime("%Y-%m"))
        if cur.month == 12:
            cur = datetime(cur.year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            cur = datetime(cur.year, cur.month + 1, 1, tzinfo=timezone.utc)
    days = []
    cur_day = datetime(end.year, end.month, end.day, tzinfo=timezone.utc)
    first_day = datetime(start.year, start.month, start.day, tzinfo=timezone.utc)
    while cur_day >= first_day:
        days.append(cur_day.strftime("%Y-%m-%d"))
        cur_day -= timedelta(days=1)
    return months, list(reversed(days))


def read_kline_zip(path, start_ms, end_ms):
    rows = {}
    with zipfile.ZipFile(path) as archive:
        csv_names = [n for n in archive.namelist() if n.lower().endswith(".csv")]
        if not csv_names:
            raise RuntimeError(f"No CSV found inside {path.name}")
        for name in csv_names:
            with archive.open(name) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
                for row in reader:
                    if len(row) < 6:
                        continue
                    try:
                        ts = int(float(row[0]))
                        o, h, low, close, vol = map(float, row[1:6])
                    except (ValueError, TypeError):
                        continue
                    if ts < start_ms or ts >= end_ms:
                        continue
                    if not all(math.isfinite(x) for x in (o, h, low, close, vol)):
                        raise RuntimeError(f"Non-finite OHLCV in {path.name} at {ts}")
                    if h < low or h < max(o, close) or low > min(o, close) or vol < 0:
                        raise RuntimeError(f"Invalid OHLCV in {path.name} at {ts}")
                    rows[ts] = (ts, o, h, low, close, vol, ts + (MINUTE if "1m" in path.name else HOUR) - 1)
    return rows


def load_klines(interval, start_ms, end_ms):
    months, days = archive_periods(start_ms, end_ms)
    merged = {}
    checksums = []
    # Binance publishes monthly archives only after a month is complete.
    # Use daily files for the current/incomplete final month, not a guessed monthly URL.
    current_month = datetime.fromtimestamp((end_ms - 1) / 1000, timezone.utc).strftime("%Y-%m")
    archive_months = [m for m in months if m != current_month]
    for month in archive_months:
        url = archive_url("monthly", interval, month)
        path, digest = fetch_archive(url)
        checksums.append({"file": path.name, "sha256": digest})
        merged.update(read_kline_zip(path, start_ms, end_ms))
    for day in days:
        if day[:7] != current_month:
            continue
        url = archive_url("daily", interval, day)
        path, digest = fetch_archive(url)
        checksums.append({"file": path.name, "sha256": digest})
        merged.update(read_kline_zip(path, start_ms, end_ms))
    ordered = [merged[k] for k in sorted(merged)]
    step = MINUTE if interval == "1m" else HOUR
    if not ordered:
        raise RuntimeError(f"No {interval} Binance candles downloaded")
    for i in range(1, len(ordered)):
        if ordered[i][0] - ordered[i - 1][0] != step:
            raise RuntimeError(f"{interval} candle gap: {ordered[i-1][0]} -> {ordered[i][0]}")
    expected = (end_ms - start_ms) // step
    if len(ordered) != expected:
        raise RuntimeError(f"{interval} coverage mismatch: expected {expected:,} rows, got {len(ordered):,}")
    return ordered, checksums


def load_configs():
    source = SOURCE.read_text(encoding="utf-8")
    match = re.search(r"const M3_CONFIGS = (\[[\s\S]*?\]);", source)
    if not match:
        raise RuntimeError("Could not extract the existing M3_CONFIGS array.")
    configs = json.loads(match.group(1))
    if len(configs) != 100:
        raise RuntimeError(f"Expected exactly 100 configurations; found {len(configs)}")
    for cfg in configs:
        if cfg.get("symbol") != SYMBOL or cfg.get("timeframe") != "1h":
            raise RuntimeError(f"Unexpected config scope: {cfg}")
    return configs


def wilder(values, n):
    out = [None] * len(values)
    acc = None
    count = 0
    for i, value in enumerate(values):
        if value is None or not math.isfinite(value):
            continue
        if acc is None:
            acc = value
            count = 1
        else:
            acc = (1 - 1 / n) * acc + value / n
            count += 1
        if count >= n:
            out[i] = acc
    return out


def indicators(bars, atr_n):
    n = len(bars)
    tr = [None] * n
    pdm = [0.0] * n
    mdm = [0.0] * n
    delta = [None] * n
    for i in range(1, n):
        b, p = bars[i], bars[i - 1]
        tr[i] = max(b[2] - b[3], abs(b[2] - p[4]), abs(b[3] - p[4]))
        up, down = b[2] - p[2], p[3] - b[3]
        pdm[i] = up if up > down and up > 0 else 0.0
        mdm[i] = down if down > up and down > 0 else 0.0
        delta[i] = b[4] - p[4]
    atr_raw = wilder(tr, atr_n)
    atr_prior = [atr_raw[i - 1] if i else None for i in range(n)]
    ag = wilder([None if x is None else max(x, 0) for x in delta], 14)
    al = wilder([None if x is None else max(-x, 0) for x in delta], 14)
    rsi = []
    for a, b in zip(ag, al):
        if a is None or b is None:
            rsi.append(None)
        elif b == 0:
            rsi.append(100.0)
        else:
            rsi.append(100 - 100 / (1 + a / b))
    atr14 = wilder(tr, 14)
    p = wilder(pdm, 14)
    m = wilder(mdm, 14)
    dx = []
    for a, plus, minus in zip(atr14, p, m):
        if a is None or plus is None or minus is None or a == 0:
            dx.append(None)
        else:
            pdi, mdi = 100 * plus / a, 100 * minus / a
            den = pdi + mdi
            dx.append(None if den == 0 else 100 * abs(pdi - mdi) / den)
    return {"atr_prior": atr_prior, "rsi": rsi, "adx": wilder(dx, 14)}


def impulse_signal(bar, ind, i, cfg):
    atr, adx, rsi = ind["atr_prior"][i], ind["adx"][i], ind["rsi"][i]
    if atr is None or adx is None or not math.isfinite(atr) or atr <= 0:
        return 0
    if adx < cfg["adx_min"] or adx > cfg["adx_max"]:
        return 0
    direction = 1 if bar[4] > bar[1] else (-1 if bar[4] < bar[1] else 0)
    if not direction or bar[2] - bar[3] < cfg["impulse_atr"] * atr:
        return 0
    mode = cfg["rsi_mode"]
    if mode == "exact":
        if direction == 1 and not (rsi is not None and 50 <= rsi <= 70):
            return 0
        if direction == -1 and not (rsi is not None and 30 <= rsi <= 50):
            return 0
    elif mode == "loose":
        if direction == 1 and not (rsi is not None and 50 <= rsi <= 75):
            return 0
        if direction == -1 and not (rsi is not None and 25 <= rsi <= 50):
            return 0
    elif mode != "none":
        raise RuntimeError(f"Unknown RSI mode: {mode}")
    return direction


def find_entry(setup, minute_times, minute_rows, end_ms):
    eligible = setup["impulse_ts"] + HOUR
    expires = setup["impulse_ts"] + (setup["pending_bars"] + 1) * HOUR
    i = bisect.bisect_left(minute_times, eligible)
    while i < len(minute_rows) and minute_times[i] < min(expires, end_ms):
        b = minute_rows[i]
        side, level, structural_stop = setup["side"], setup["level"], setup["stop"]
        stop_touched = b[3] <= structural_stop if side == 1 else b[2] >= structural_stop
        entry_touched = b[3] <= level if side == 1 else b[2] >= level
        if stop_touched and entry_touched:
            return None
        if stop_touched:
            return None
        if entry_touched:
            raw_fill = min(b[1], level) if side == 1 else max(b[1], level)
            return {
                **setup,
                "entry_idx": i,
                "entry_time": b[0],
                "raw_fill": raw_fill,
                "entry_minute": b,
            }
        i += 1
    return None


def fetch_funding(start_ms, end_ms):
    # First try the official USD-M Futures funding history endpoint with full pagination.
    # A single 1,000-row response is NOT sufficient for a multi-year window.
    events = {}
    errors = []
    cursor = start_ms
    rest_ok = True
    while cursor < end_ms:
        query = urllib.parse.urlencode({"symbol": SYMBOL, "startTime": cursor, "endTime": end_ms - 1, "limit": 1000})
        url = "https://fapi.binance.com/fapi/v1/fundingRate?" + query
        try:
            payload = json.loads(http_bytes(url).decode("utf-8"))
            if not isinstance(payload, list):
                raise RuntimeError("Unexpected funding REST payload")
            if not payload:
                break
            for item in payload:
                t, rate = int(item["fundingTime"]), float(item["fundingRate"])
                if start_ms <= t < end_ms and math.isfinite(rate):
                    events[t] = rate
            last_ts = max(int(item["fundingTime"]) for item in payload)
            if len(payload) < 1000 or last_ts < cursor:
                break
            cursor = last_ts + 1
        except Exception as exc:
            errors.append("funding REST: " + str(exc)[:220])
            rest_ok = False
            break
    if rest_ok and events:
        return sorted(events.items()), "Binance USD-M Futures fundingRate REST (paginated)", errors

    # Official Binance public monthly archive fallback. Funding archives contain:
    # calc_time, funding_interval_hours, last_funding_rate.
    events = {}
    months, _ = archive_periods(start_ms, end_ms)
    for month in months:
        filename = f"{SYMBOL}-fundingRate-{month}.zip"
        archive = f"{BASE_URL}/monthly/fundingRate/{SYMBOL}/{filename}"
        try:
            path, _ = fetch_archive(archive)
            with zipfile.ZipFile(path) as zf:
                for name in zf.namelist():
                    if not name.lower().endswith(".csv"):
                        continue
                    with zf.open(name) as raw:
                        reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8", newline=""))
                        for row in reader:
                            if len(row) < 3:
                                continue
                            try:
                                # Schema: calc_time, funding_interval_hours, last_funding_rate.
                                if row[0].strip().upper() == SYMBOL and len(row) >= 4:
                                    t, rate = int(float(row[1])), float(row[3])
                                else:
                                    t, rate = int(float(row[0])), float(row[2])
                            except (ValueError, TypeError):
                                continue
                            if start_ms <= t < end_ms and math.isfinite(rate):
                                events[t] = rate
        except Exception as exc:
            errors.append(f"archive {filename}: {str(exc)[:120]}")
    if events:
        return sorted(events.items()), "Binance USD-M Futures official monthly fundingRate archives", errors
    return [], "unavailable", errors

def simulate_candidate(candidate, minute_rows, funding_times, funding_prefix, end_ms):
    side = candidate["side"]
    results = []
    for slip in SLIPPAGE_SCENARIOS:
        fill = candidate["raw_fill"] * (1 + side * slip / 10_000)
        structural_risk = abs(fill - candidate["stop"])
        if structural_risk <= 0 or (side == 1 and candidate["stop"] >= fill) or (side == -1 and candidate["stop"] <= fill):
            for sl in SL_MULTIPLIERS:
                for rr in TP_RR_VALUES:
                    results.append({"sl": sl, "rr": rr, "slippage": slip, "outcome": None})
            continue
        variants = []
        for sl in SL_MULTIPLIERS:
            risk = structural_risk * sl
            stop = fill - side * risk
            for rr in TP_RR_VALUES:
                variants.append({
                    "sl": sl, "rr": rr, "slippage": slip,
                    "risk": risk, "stop": stop, "target": fill + side * risk * rr,
                    "active": True, "outcome": None,
                })
        entry_time = candidate["entry_time"]
        time_exit_at = entry_time + MAX_HOLD
        max_i = min(len(minute_rows) - 1, candidate["entry_idx"] + 1440)
        for j in range(candidate["entry_idx"], max_i + 1):
            b = minute_rows[j]
            if not any(v["active"] for v in variants):
                break
            for v in variants:
                if not v["active"]:
                    continue
                stop_hit = b[3] <= v["stop"] if side == 1 else b[2] >= v["stop"]
                target_hit = b[2] >= v["target"] if side == 1 else b[3] <= v["target"]
                reason = None
                if stop_hit:
                    adverse_gap = (side == 1 and b[1] < v["stop"]) or (side == -1 and b[1] > v["stop"])
                    raw_exit = b[1] if adverse_gap else v["stop"]
                    reason = "STOP"
                elif target_hit:
                    raw_exit = v["target"]
                    reason = "TARGET"
                elif b[0] + MINUTE >= time_exit_at:
                    raw_exit = b[4]
                    reason = "TIME"
                else:
                    continue
                exit_price = raw_exit * (1 - side * v["slippage"] / 10_000)
                gross_bps = side * (exit_price - fill) / fill * 10_000
                fee_bps = 2 * FEE_BPS_PER_SIDE
                left = bisect.bisect_left(funding_times, entry_time)
                right = bisect.bisect_right(funding_times, b[0] + MINUTE - 1)
                funding_rate_sum = funding_prefix[right] - funding_prefix[left]
                funding_cost_bps = funding_rate_sum * side * 10_000
                net_bps = gross_bps - fee_bps - funding_cost_bps
                risk_bps = v["risk"] / fill * 10_000
                v["outcome"] = {
                    "entry_time": entry_time, "exit_time": b[0] + MINUTE - 1,
                    "side": "LONG" if side == 1 else "SHORT",
                    "entry": fill, "exit": exit_price, "stop": v["stop"], "target": v["target"],
                    "reason": reason, "gross_bps": gross_bps, "fees_bps": fee_bps,
                    "funding_cost_bps": funding_cost_bps, "net_bps": net_bps,
                    "net_R": net_bps / risk_bps if risk_bps else 0.0,
                    "hold_minutes": (b[0] - entry_time) // MINUTE + 1,
                    "config_rank": candidate["rank"], "config_id": candidate["config_id"],
                    "impulse_time": candidate["impulse_ts"],
                    "entry_level": candidate["level"],
                    "sl_multiplier": v["sl"], "tp_rr": v["rr"], "slippage_bps_side": v["slippage"],
                }
                v["active"] = False
        for v in variants:
            results.append({
                "sl": v["sl"], "rr": v["rr"], "slippage": v["slippage"],
                "outcome": v["outcome"],
            })
    return results


def metric(records, censored=0):
    if not records:
        return {
            "trades": 0, "censored": censored, "wins": 0, "losses": 0,
            "win_rate_pct": None, "profit_factor": None, "net_bps": 0.0,
            "avg_net_bps": None, "avg_net_R": None, "max_drawdown_bps": None,
            "stop_pct": None, "target_pct": None, "time_pct": None,
            "avg_hold_minutes": None,
        }
    ordered = sorted(records, key=lambda x: x["exit_time"])
    pnls = [x["net_bps"] for x in ordered]
    wins = sum(1 for x in pnls if x > 0)
    losses = len(pnls) - wins
    positive = sum(x for x in pnls if x > 0)
    negative = -sum(x for x in pnls if x < 0)
    equity = peak = drawdown = 0.0
    for pnl in pnls:
        equity += pnl
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    n = len(ordered)
    reasons = {k: sum(1 for x in ordered if x["reason"] == k) for k in ("STOP", "TARGET", "TIME")}
    return {
        "trades": n, "censored": censored, "wins": wins, "losses": losses,
        "win_rate_pct": 100 * wins / n,
        "profit_factor": positive / negative if negative > 0 else (None if positive == 0 else 999.0),
        "net_bps": sum(pnls), "avg_net_bps": sum(pnls) / n,
        "avg_net_R": sum(x["net_R"] for x in ordered) / n,
        "max_drawdown_bps": drawdown,
        "stop_pct": 100 * reasons["STOP"] / n,
        "target_pct": 100 * reasons["TARGET"] / n,
        "time_pct": 100 * reasons["TIME"] / n,
        "avg_hold_minutes": sum(x["hold_minutes"] for x in ordered) / n,
    }


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2021-11-19")
    parser.add_argument("--end", default="2026-11-19", help="exclusive UTC date boundary")
    args = parser.parse_args()
    start_ms, end_ms = utc_ms(args.start), utc_ms(args.end)
    pre_roll_ms = start_ms - 60 * 24 * HOUR
    if end_ms <= start_ms:
        raise RuntimeError("End date must be after start date.")
    days = (end_ms - start_ms) // (24 * HOUR)
    if days < 1750 or days > 1900:
        raise RuntimeError(f"Expected a five-year window; got {days} days.")

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"MODEL 3-100 | {SYMBOL} USD-M perpetual | {args.start} to {args.end} UTC (end exclusive)")
    print("Downloading official Binance USD-M Futures 1m and 1h public archives with SHA-256 verification...")
    global SPLIT_TIME
    SPLIT_TIME = start_ms + int((end_ms - start_ms) * 0.60)  # first 60% development, final 40% validation
    configs = load_configs()
    hourly_rows, hourly_checksums = load_klines("1h", pre_roll_ms, end_ms)
    minute_rows, minute_checksums = load_klines("1m", start_ms, end_ms)
    print(f"Verified candles: 1h={len(hourly_rows):,}; 1m={len(minute_rows):,}; configs={len(configs)}")
    hourly_times = [r[0] for r in hourly_rows]
    minute_times = [r[0] for r in minute_rows]
    funding, funding_source, funding_errors = fetch_funding(start_ms, end_ms)
    funding_times = [x[0] for x in funding]
    funding_prefix = [0.0]
    for _, rate in funding:
        funding_prefix.append(funding_prefix[-1] + rate)
    expected_funding = days * 3
    funding_coverage = min(100.0, 100 * len(funding) / expected_funding) if expected_funding else 0.0
    funding_complete = funding_coverage >= 95.0
    print(f"Funding records: {len(funding)} (rough expected {expected_funding}); coverage={funding_coverage:.1f}% source={funding_source}")

    candidates = []
    config_signal_counts = defaultdict(int)
    config_hit_counts = defaultdict(int)
    for cfg in configs:
        ind = indicators(hourly_rows, int(cfg["atr_period"]))
        for i in range(1, len(hourly_rows)):
            impulse = hourly_rows[i]
            if impulse[0] < start_ms or impulse[0] + HOUR >= end_ms:
                continue
            side = impulse_signal(impulse, ind, i, cfg)
            if not side:
                continue
            config_signal_counts[int(cfg["pf_rank"])] += 1
            span = impulse[2] - impulse[3]
            if span <= 0:
                continue
            level = impulse[2] - cfg["retracement"] * span if side == 1 else impulse[3] + cfg["retracement"] * span
            stop = impulse[3] if side == 1 else impulse[2]
            setup = {
                "rank": int(cfg["pf_rank"]),
                "config_id": f"M3_100_R{int(cfg['pf_rank']):03d}",
                "group_id": int(cfg["group_id"]),
                "pending_bars": int(cfg["pending_bars"]),
                "side": side, "impulse_ts": impulse[0],
                "level": level, "stop": stop,
                "original_rr": float(cfg["rr"]),
                "retracement": float(cfg["retracement"]),
            }
            hit = find_entry(setup, minute_times, minute_rows, end_ms)
            if hit:
                candidates.append(hit)
                config_hit_counts[int(cfg["pf_rank"])] += 1

    # The live model emits at most one entry alert for an originating 1h impulse:
    # when multiple configs touch, it chooses the best PF-ranked qualifying config.
    by_impulse = {}
    for c in candidates:
        key = c["impulse_ts"]
        if key not in by_impulse or c["rank"] < by_impulse[key]["rank"]:
            by_impulse[key] = c
    model_candidates = list(by_impulse.values())
    print(f"Qualified impulses={sum(config_signal_counts.values()):,}; 1m entry hits={len(candidates):,}; unique model alerts={len(model_candidates):,}")

    config_records = defaultdict(list)
    model_records = defaultdict(list)
    pooled_records = defaultdict(list)
    config_censored = defaultdict(int)
    model_censored = defaultdict(int)
    pooled_censored = defaultdict(int)
    detail_rows = []
    candidate_rows = []
    model_candidate_ids = {id(x) for x in model_candidates}

    for idx, candidate in enumerate(candidates, 1):
        if idx % 100 == 0:
            print(f"Simulating candidate {idx:,}/{len(candidates):,} ...")
        outcomes = simulate_candidate(candidate, minute_rows, funding_times, funding_prefix, end_ms)
        candidate_rows.append({
            "config_rank": candidate["rank"], "config_id": candidate["config_id"],
            "group_id": candidate["group_id"], "impulse_utc": datetime.fromtimestamp(candidate["impulse_ts"]/1000, timezone.utc).isoformat(),
            "entry_utc": datetime.fromtimestamp(candidate["entry_time"]/1000, timezone.utc).isoformat(),
            "side": "LONG" if candidate["side"] == 1 else "SHORT",
            "entry_level": candidate["level"], "raw_fill": candidate["raw_fill"],
            "structural_stop": candidate["stop"], "original_config_rr": candidate["original_rr"],
            "is_unique_model_alert": id(candidate) in model_candidate_ids,
        })
        for item in outcomes:
            key = (item["sl"], item["rr"], item["slippage"])
            outcome = item["outcome"]
            config_key = (candidate["rank"],) + key
            pooled_records[key]
            if outcome is None:
                config_censored[config_key] += 1
                pooled_censored[key] += 1
                if id(candidate) in model_candidate_ids:
                    model_censored[key] += 1
                continue
            config_records[config_key].append(outcome)
            pooled_records[key].append(outcome)
            if id(candidate) in model_candidate_ids:
                model_records[key].append(outcome)
                detail_rows.append(outcome)

    grid_rows = []
    for slip in SLIPPAGE_SCENARIOS:
        for sl in SL_MULTIPLIERS:
            for rr in TP_RR_VALUES:
                key = (sl, rr, slip)
                all_m = metric(model_records[key], model_censored[key])
                pooled_m = metric(pooled_records[key], pooled_censored[key])
                early = metric([x for x in model_records[key] if x["entry_time"] < SPLIT_TIME])
                late = metric([x for x in model_records[key] if x["entry_time"] >= SPLIT_TIME])
                grid_rows.append({
                    "sl_multiplier": sl, "tp_rr": rr, "slippage_bps_side": slip,
                    "model_unique_alert_trades": all_m["trades"], "model_censored": all_m["censored"],
                    "model_win_rate_pct": all_m["win_rate_pct"], "model_profit_factor": all_m["profit_factor"],
                    "model_net_bps": all_m["net_bps"], "model_avg_net_R": all_m["avg_net_R"],
                    "model_max_drawdown_bps": all_m["max_drawdown_bps"],
                    "model_stop_pct": all_m["stop_pct"], "model_target_pct": all_m["target_pct"], "model_time_pct": all_m["time_pct"],
                    "early_trades": early["trades"], "early_pf": early["profit_factor"], "early_net_bps": early["net_bps"],
                    "late_trades": late["trades"], "late_pf": late["profit_factor"], "late_net_bps": late["net_bps"],
                    "all_config_trades_correlated": pooled_m["trades"], "all_config_pf_diagnostic": pooled_m["profit_factor"],
                    "all_config_net_bps_diagnostic": pooled_m["net_bps"],
                    "funding_records": len(funding), "funding_coverage_pct": round(funding_coverage, 2),
                    "funding_complete": funding_complete,
                })

    config_rows = []
    for cfg in configs:
        rank = int(cfg["pf_rank"])
        for slip in SLIPPAGE_SCENARIOS:
            for sl in SL_MULTIPLIERS:
                for rr in TP_RR_VALUES:
                    key = (rank, sl, rr, slip)
                    m = metric(config_records[key], config_censored[key])
                    early = metric([x for x in config_records[key] if x["entry_time"] < SPLIT_TIME])
                    late = metric([x for x in config_records[key] if x["entry_time"] >= SPLIT_TIME])
                    config_rows.append({
                        "config_rank": rank, "config_id": f"M3_100_R{rank:03d}",
                        "group_id": int(cfg["group_id"]), "original_config_rr": float(cfg["rr"]),
                        "sl_multiplier": sl, "tp_rr": rr, "slippage_bps_side": slip,
                        "is_original_exit_baseline": bool(sl == 1.0 and rr == float(cfg["rr"]) and slip == 2.0),
                        "signal_count": config_signal_counts[rank], "entry_hits": config_hit_counts[rank],
                        "trades": m["trades"], "censored": m["censored"], "win_rate_pct": m["win_rate_pct"],
                        "profit_factor": m["profit_factor"], "net_bps": m["net_bps"], "avg_net_R": m["avg_net_R"],
                        "max_drawdown_bps": m["max_drawdown_bps"], "stop_pct": m["stop_pct"],
                        "target_pct": m["target_pct"], "time_pct": m["time_pct"],
                        "early_trades": early["trades"], "early_pf": early["profit_factor"],
                        "late_trades": late["trades"], "late_pf": late["profit_factor"],
                    })

    # Add ranks for each config; low-sample variants remain visible but are not promoted.
    by_config = defaultdict(list)
    for row in config_rows:
        by_config[(row["config_rank"], row["slippage_bps_side"])].append(row)
    for group in by_config.values():
        eligible = [r for r in group if r["trades"] >= 5 and r["net_bps"] > 0 and r["profit_factor"] is not None]
        eligible.sort(key=lambda r: (r["profit_factor"], r["net_bps"], r["trades"]), reverse=True)
        for position, row in enumerate(eligible, 1):
            row["config_variant_rank"] = position
        for row in group:
            row.setdefault("config_variant_rank", "")

    # Primary ranking is the one-alert-per-impulse model stream. Do not promote
    # a parameter set on PF alone: require 30 closed trades and positive net.
    eligible_grid = [r for r in grid_rows if r["slippage_bps_side"] == 2.0 and
                     r["model_unique_alert_trades"] >= 30 and r["model_net_bps"] > 0 and
                     r["model_profit_factor"] is not None]
    eligible_grid.sort(key=lambda r: (
        r["model_profit_factor"],
        r["late_pf"] if r["late_pf"] is not None else -1,
        r["model_net_bps"],
        -abs(r["model_max_drawdown_bps"] or 0)
    ), reverse=True)
    for position, row in enumerate(eligible_grid, 1):
        row["model_rank"] = position
    for row in grid_rows:
        row.setdefault("model_rank", "")

    checksums = hourly_checksums + minute_checksums
    summary = {
        "status": "COMPLETED" if len(minute_rows) == (end_ms-start_ms)//MINUTE and len(hourly_rows) == (end_ms-pre_roll_ms)//HOUR else "INVALID",
        "symbol": SYMBOL, "market": "Binance USD-M perpetual futures",
        "data_source": "Official Binance Public Data archive (futures/um klines), sourced from USD-M Futures klines",
        "start_utc": datetime.fromtimestamp(start_ms/1000, timezone.utc).isoformat(),
        "end_utc_exclusive": datetime.fromtimestamp(end_ms/1000, timezone.utc).isoformat(),
        "warmup_start_utc": datetime.fromtimestamp(pre_roll_ms/1000, timezone.utc).isoformat(),
        "test_days": days, "hourly_candles_including_warmup": len(hourly_rows),
        "minute_candles_in_test_window": len(minute_rows),
        "expected_hourly_candles": (end_ms-pre_roll_ms)//HOUR,
        "expected_minute_candles": (end_ms-start_ms)//MINUTE,
        "configurations_unchanged": len(configs), "configuration_source": SOURCE.name,
        "sl_multipliers": list(SL_MULTIPLIERS), "tp_rr_values": list(TP_RR_VALUES),
        "sl_tp_combinations_per_cost_scenario": len(SL_MULTIPLIERS)*len(TP_RR_VALUES),
        "execution_costs": {
            "fee_bps_per_side": FEE_BPS_PER_SIDE,
            "slippage_scenarios_bps_per_side": list(SLIPPAGE_SCENARIOS),
            "2_bps_scenario": "Matches existing Google Apps Script M3.SLIPPAGE_BPS_PER_SIDE",
            "7_bps_scenario": "Stress case matching current realtime evaluator's entry-fill estimate",
        },
        "funding": {
            "source": funding_source, "records": len(funding), "rough_expected_records": expected_funding,
            "coverage_pct": round(funding_coverage, 2), "complete_95pct_threshold": funding_complete,
            "errors": funding_errors[:12],
            "note": "Funding is applied when records are available; if coverage is below 95%, SL/TP rankings are provisional and must not be promoted to live configuration.",
        },
        "signal_logic": "Existing 100 BTCUSDT 1h configurations; same Wilder ATR/RSI/ADX and impulse rules; 1h close confirms; 1m candles find first retracement touch; entry is cancelled if structural stop is touched before or in the same minute as entry.",
        "exit_logic": "Six structural-stop distance multipliers; eight independent TP R multiples; 1m exit simulation; stop-first when stop and target are both inside one minute candle; adverse stop gaps fill at minute open; max hold 24 hours.",
        "alert_logic": "One model-level trade per originating strong 1h candle; if multiple configurations get a valid 1m entry, the lowest PF rank number is selected, matching the one-alert-per-impulse rule.",
        "trade_overlap": "Each originating strong-candle signal is evaluated independently, consistent with the current realtime alert scanner; overlapping alert trades can occur across different impulse candles.",
        "candidates_with_entry_touch_all_configs": len(candidates),
        "unique_model_alert_impulses": len(model_candidates),
        "signals_by_config_rank": {str(k): v for k, v in sorted(config_signal_counts.items())},
        "entry_hits_by_config_rank": {str(k): v for k, v in sorted(config_hit_counts.items())},
        "eligible_parameter_sets_at_2bps_slippage_min30_trades": len(eligible_grid),
        "top_five_eligible_model_variants": [
            {k: r.get(k) for k in ("model_rank","sl_multiplier","tp_rr","model_unique_alert_trades","model_win_rate_pct","model_profit_factor","model_net_bps","model_max_drawdown_bps","early_pf","late_pf","late_net_bps")}
            for r in eligible_grid[:5]
        ],
        "archive_checksums": checksums,
        "outputs": ["sl_tp_grid_results.csv","config_sl_tp_rankings.csv","candidate_entries.csv","model_alert_stream_trade_outcomes.csv"],
        "important": "No live configuration, SL, TP, signal rule, or deployment file is changed by this backtest. Results are research output only.",
    }
    (OUT / "backtest_summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    write_csv(OUT / "sl_tp_grid_results.csv", grid_rows, list(grid_rows[0].keys()))
    write_csv(OUT / "config_sl_tp_rankings.csv", config_rows, list(config_rows[0].keys()))
    write_csv(OUT / "candidate_entries.csv", candidate_rows, list(candidate_rows[0].keys()) if candidate_rows else ["config_rank"])
    detail_fields = list(detail_rows[0].keys()) if detail_rows else ["config_rank"]
    write_csv(OUT / "model_alert_stream_trade_outcomes.csv", detail_rows, detail_fields)

    print("BACKTEST RESULT")
    print(json.dumps({
        "status": summary["status"], "1m_candles": len(minute_rows), "1h_candles": len(hourly_rows),
        "configs": len(configs), "entry_hits": len(candidates), "unique_alert_impulses": len(model_candidates),
        "funding_records": len(funding), "funding_coverage_pct": round(funding_coverage, 2),
        "eligible_parameter_sets": len(eligible_grid), "top_five": summary["top_five_eligible_model_variants"],
    }, indent=2))
    print(f"Artifacts prepared in {OUT}")
    if not funding_complete:
        print("WARNING: funding coverage below 95%; SL/TP rankings are provisional and must not be promoted to live configuration.")
    if not eligible_grid:
        print("WARNING: No parameter set met the 30-trade + positive-net eligibility rule.")
    if summary["status"] != "COMPLETED":
        raise RuntimeError("Backtest data coverage validation failed.")


if __name__ == "__main__":
    main()
