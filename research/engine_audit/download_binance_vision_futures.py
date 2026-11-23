#!/usr/bin/env python3
"""Download checksum-verified Binance Vision USD-M 1m archives and build local Freqtrade futures candles.
Uses the same public archive + SHA-256 method as the repository's successful Impulse Retracer backtest.
No exchange API / CCXT market-discovery calls are made here.
"""
import csv, hashlib, io, json, sys, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd

BASE = "https://data.binance.vision/data/futures/um"
START = datetime(2021, 11, 22, tzinfo=timezone.utc)
END_EXCLUSIVE = datetime(2026, 11, 22, tzinfo=timezone.utc)
START_MS = int(START.timestamp() * 1000)
END_MS = int(END_EXCLUSIVE.timestamp() * 1000)
SYMBOLS = ("BTCUSDT", "ETHUSDT")
TIMEFRAMES = {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}
DATA_ROOT = Path("user_data/data/binance/futures")
ARCHIVE_ROOT = Path("/tmp/binance-vision-archives")

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

def verified_download(url):
    target = ARCHIVE_ROOT / url.rsplit("/", 1)[-1]
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and target.stat().st_size:
        pass
    else:
        req = urllib.request.Request(url, headers={"User-Agent": "RealcheckHistoricalResearch/1.0"})
        with urllib.request.urlopen(req, timeout=180) as response, target.open("wb") as out:
            while True:
                block = response.read(1 << 20)
                if not block:
                    break
                out.write(block)
    req = urllib.request.Request(url + ".CHECKSUM", headers={"User-Agent": "RealcheckHistoricalResearch/1.0"})
    with urllib.request.urlopen(req, timeout=60) as response:
        checksum = response.read().decode("utf-8", "replace")
    import re
    match = re.search(r"\b([0-9a-fA-F]{64})\b", checksum)
    if not match:
        target.unlink(missing_ok=True)
        raise RuntimeError(f"Missing SHA-256 checksum: {url}")
    actual = sha256(target)
    if actual.lower() != match.group(1).lower():
        target.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch: {url}")
    return target

def archive_urls(symbol):
    urls = []
    y, m = 2021, 11
    while (y, m) <= (2026, 10):
        name = f"{symbol}-1m-{y}-{m:02d}.zip"
        urls.append(f"{BASE}/monthly/klines/{symbol}/1m/{name}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    for day in range(1, 22):
        name = f"{symbol}-1m-2026-11-{day:02d}.zip"
        urls.append(f"{BASE}/daily/klines/{symbol}/1m/{name}")
    return urls

def build_symbol(symbol):
    # Accumulate OHLCV directly into each requested timeframe, avoiding a multi-year M1 dataframe.
    bars = {tf: [] for tf in TIMEFRAMES}
    current = {}
    archives = archive_urls(symbol)
    for n, url in enumerate(archives, 1):
        path = verified_download(url)
        with zipfile.ZipFile(path) as zf:
            csv_names = [x for x in zf.namelist() if x.lower().endswith(".csv")]
            if not csv_names:
                raise RuntimeError(f"No CSV in archive {path}")
            with zf.open(csv_names[0]) as raw:
                reader = csv.reader(io.TextIOWrapper(raw, encoding="utf-8"))
                for row in reader:
                    if not row or not row[0].isdigit():
                        continue
                    ts = int(row[0])
                    if ts < START_MS or ts >= END_MS:
                        continue
                    o, h, l, c, v = map(float, row[1:6])
                    if min(o, h, l, c) <= 0 or l > min(o, c) or h < max(o, c) or h < l or v < 0:
                        raise RuntimeError(f"Invalid OHLCV row {symbol} {row[:6]}")
                    for tf, minutes in TIMEFRAMES.items():
                        step = minutes * 60_000
                        bucket = ts // step * step
                        key = (tf, bucket)
                        old = current.get(key)
                        if old is None:
                            current[key] = [o, h, l, c, v, 1]
                        else:
                            old[1] = max(old[1], h)
                            old[2] = min(old[2], l)
                            old[3] = c
                            old[4] += v
                            old[5] += 1
        print(f"{symbol}: verified archive {n}/{len(archives)}", flush=True)
    # Finalize only complete bars; partial bars at the requested window edge are excluded.
    for (tf, bucket), x in current.items():
        minutes = TIMEFRAMES[tf]
        if x[5] != minutes:
            continue
        bars[tf].append((bucket, *x[:5]))
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    for tf, rows in bars.items():
        rows.sort(key=lambda x: x[0])
        if not rows:
            raise RuntimeError(f"No {tf} bars generated for {symbol}")
        frame = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
        frame["date"] = pd.to_datetime(frame["date"], unit="ms", utc=True)
        frame.to_feather(DATA_ROOT / f"{symbol[:-4]}_USDT-{tf}-futures.feather")
        expected = (END_MS - START_MS) // (TIMEFRAMES[tf] * 60_000)
        if len(frame) != expected:
            raise RuntimeError(f"{symbol} {tf}: incomplete source history: expected {expected} complete bars, got {len(frame)}")
        print(f"{symbol} {tf}: {len(frame):,} complete bars verified", flush=True)
    return {tf: len(rows) for tf, rows in bars.items()}

if __name__ == "__main__":
    import io, re
    summary = {symbol: build_symbol(symbol) for symbol in SYMBOLS}
    Path("five-year-results").mkdir(exist_ok=True)
    Path("five-year-results/data_manifest.json").write_text(json.dumps({
        "source": "Binance Vision USD-M monthly/daily kline archives",
        "checksum_verified": True,
        "period_utc": {"start_inclusive": START.isoformat(), "end_exclusive": END_EXCLUSIVE.isoformat()},
        "symbols": list(SYMBOLS), "timeframes": summary,
        "note": "Exact five-year window matching the proven Realcheck archive workflow; all expected complete bars required; no CCXT/exchange API calls."
    }, indent=2))
