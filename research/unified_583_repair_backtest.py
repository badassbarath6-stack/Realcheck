#!/usr/bin/env python3
"""Corrected full-registry runner reusing the checksum-verified input artifact."""
import argparse
import ast
import csv
import hashlib
import json
import math
import os
import re
import shutil
import signal
import subprocess
from zipfile import BadZipFile, ZipFile
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from unified_583_three_year_backtest import (
    SELECTED, TFS, START, END, DATA, PC, OUT, find_classes, find_trades
)

def metric_summary(values):
    wins = math.fsum(v for v in values if v > 0)
    losses = -math.fsum(v for v in values if v < 0)
    net = math.fsum(values) if values else 0.0
    count = len(values)
    if losses > 0:
        pf = round(wins / losses, 4)
        pf_status = "FINITE"
    elif wins > 0:
        pf = None
        pf_status = "UNBOUNDED_NO_LOSSES"
    else:
        pf = None
        pf_status = "NO_GAINS_OR_LOSSES"
    warning = ""
    if not math.isfinite(net):
        warning = "NON_FINITE_NET_PROFIT"
    elif abs(net) > 1e12:
        warning = "EXTREME_COMPOUNDED_NET_PROFIT_REVIEW"
    if pf is not None and pf > 100:
        warning = (warning + ";" if warning else "") + "EXTREME_PROFIT_FACTOR_REVIEW"
    win_rate = round(100.0 * sum(v > 0 for v in values) / count, 2) if count else 0.0
    return {
        "trades": count,
        "profit_factor": pf,
        "profit_factor_status": pf_status,
        "win_rate_pct": win_rate,
        "net_profit": round(net, 8) if math.isfinite(net) else net,
        "metric_warning": warning,
    }

def sample_pyne_trade(engine_id, engine_name, symbol, timeframe, trade):
    return {
        "engine_id": engine_id,
        "engine_name": engine_name,
        "language": "pine",
        "symbol": symbol,
        "timeframe": timeframe,
        "execution_engine": "PyneCore",
        "entry_time_ms": getattr(trade, "entry_time", None),
        "exit_time_ms": getattr(trade, "exit_time", None),
        "side": "LONG" if getattr(trade, "size", 0) > 0 else "SHORT",
        "size": abs(float(getattr(trade, "size", 0) or 0)),
        "entry_price": getattr(trade, "entry_price", None),
        "exit_price": getattr(trade, "exit_price", None),
        "profit": getattr(trade, "profit", None),
        "commission": getattr(trade, "commission", None),
        "profit_percent": getattr(trade, "profit_percent", None),
        "exit_comment": getattr(trade, "exit_comment", None) or getattr(trade, "exit_id", None),
    }

def pine_requires_context(row, source_text):
    checks = [
        ("mtf_request", "YES"),
        ("lower_tf_request", "YES"),
        ("nonstandard_chart_source", "YES"),
        ("external_fundamental_data", "YES"),
    ]
    for key, value in checks:
        if str(row.get(key, "")).upper() == value:
            return True, f"Manifest flag {key}=YES"
    patterns = [
        (r"\brequest\.security\s*\(", "request.security requires mapped secondary-symbol/timeframe data"),
        (r"\brequest\.security_lower_tf\s*\(", "request.security_lower_tf requires lower-timeframe arrays"),
        (r"\brequest\.(financial|economic|dividends|earnings|splits)\s*\(", "External fundamental/event data is unavailable"),
        (r"\bticker\.(heikinashi|renko|linebreak|kagi|pointfigure|range)\s*\(", "Non-standard chart construction is not mapped"),
    ]
    for pattern, reason in patterns:
        if re.search(pattern, source_text):
            return True, reason
    return False, ""

def iter_with_timeout(runner, timeout_seconds=600):
    """Bound one PyneCore engine/symbol/timeframe execution on hosted runners."""
    def _timeout_handler(signum, frame):
        raise TimeoutError(
            f"PyneCore execution exceeded {timeout_seconds}-second row timeout"
        )

    previous_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        yield from runner.run_iter()
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


def pine_run(row, timeframe, symbol):
    source_path = Path(row["artifact_path"])
    source_text = source_path.read_text(encoding="utf-8", errors="replace")
    needs_context, reason = pine_requires_context(row, source_text)
    lookahead_on = "YES" if re.search(r"barmerge\.lookahead_on|lookahead\s*=\s*barmerge\.lookahead_on", source_text) else "NO"
    tick = 0.1 if symbol == "BTC" else 0.01
    min_contract = 0.001 if symbol == "BTC" else 0.01
    base = {
        "engine_id": row["harvest_id"],
        "engine_name": Path(urlparse(row.get("source_url", "")).path).stem,
        "language": "pine",
        "timeframe": timeframe,
        "symbol": symbol,
        "execution_engine": "PyneCore",
        "lookahead_on": lookahead_on,
        "tick_size": tick,
        "min_contract": min_contract,
    }
    if needs_context:
        return {
            **base,
            "status": "NOT_RUN_REQUIRES_CONTEXT",
            "detail": reason + "; not approximated",
            "trades": 0,
            "profit_factor": None,
            "profit_factor_status": "NOT_CALCULATED",
            "win_rate_pct": 0,
            "net_profit": 0,
        }, []
    stem = Path(urlparse(row.get("source_url", "")).path).stem
    script = PC / "scripts" / f"strategy_{stem}.py"
    if not script.is_file():
        raise FileNotFoundError(f"Compiled PyneCore script not found: {script}")
    data_file = DATA / f"{symbol}_USDT-{timeframe}-futures.feather"
    frame = pd.read_feather(data_file)
    frame["date"] = pd.to_datetime(frame["date"], utc=True)
    from pynecore.core.script_runner import ScriptRunner
    from pynecore.core.syminfo import SymInfo
    from pynecore.types.ohlcv import OHLCV
    period = {"5m": "5", "15m": "15", "30m": "30", "1h": "60", "4h": "240"}[timeframe]
    candles = [
        OHLCV(
            timestamp=int(x.date.timestamp() * 1000),
            open=float(x.open), high=float(x.high), low=float(x.low),
            close=float(x.close), volume=float(x.volume)
        )
        for x in frame.itertuples(index=False)
    ]
    scale = int(round(1.0 / tick))
    syminfo = SymInfo(
        prefix="BINANCE", ticker=symbol, currency="USDT",
        basecurrency=symbol.replace("USDT", ""),
        description="Binance USD-M perpetual", period=period, type="crypto",
        mintick=tick, pricescale=scale, minmove=1, pointvalue=1.0,
        mincontract=min_contract, timezone="UTC", volumetype="base",
        opening_hours=[], session_starts=[], session_ends=[]
    )
    runner = ScriptRunner(
        script_path=script, ohlcv_iter=candles, syminfo=syminfo,
        inputs={}, security_data=None
    )
    values = []
    first_samples = []
    last_samples = deque(maxlen=3)
    for item in iter_with_timeout(runner, 1200):
        if len(item) != 3:
            continue
        for trade in item[2]:
            value = float(getattr(trade, "profit", 0.0) or 0.0)
            if not math.isfinite(value):
                raise ValueError("Non-finite PyneCore closed-trade profit")
            values.append(value)
            sample = sample_pyne_trade(
                row["harvest_id"], base["engine_name"], symbol, timeframe, trade
            )
            if len(first_samples) < 3:
                first_samples.append(sample)
            last_samples.append(sample)
    samples = first_samples + [
        item for item in last_samples if item not in first_samples
    ]
    metrics = metric_summary(values)
    return {
        **base, **metrics, "status": "BACKTESTED",
        "detail": "",
    }, samples

def patch_legacy_dicts(source_text):
    for attr in ("order_types", "order_time_in_force", "unfilledtimeout"):
        pattern = re.compile(r"(" + attr + r"\s*=\s*\{)(.*?)(\})", re.S)
        def replace_block(match):
            body = match.group(2)
            body = re.sub(r"(['\"])buy\1(\s*:)", r"\1entry\1\2", body)
            body = re.sub(r"(['\"])sell\1(\s*:)", r"\1exit\1\2", body)
            return match.group(1) + body + match.group(3)
        source_text = pattern.sub(replace_block, source_text)
    return source_text

def transform_freqtrade_source(source_text):
    notes = []
    original = source_text
    source_text = patch_legacy_dicts(source_text)
    # Legacy Freqtrade v2 exit callback was removed; preserve callback logic under v3 name.
    source_text = re.sub(r"\bcustom_sell\b", "custom_exit", source_text)
    # NumPy 2 removed these aliases; use the unchanged NaN sentinel.
    source_text = re.sub(r"\b(?:np|numpy)\.(?:NaN|NAN)\b", "np.nan", source_text)
    # Pandas removed fillna(method=...) in recent releases.
    source_text = re.sub(r"\.fillna\(\s*method\s*=\s*(['\"])ffill\1\s*\)", ".ffill()", source_text)
    source_text = re.sub(r"\.fillna\(\s*method\s*=\s*(['\"])bfill\1\s*\)", ".bfill()", source_text)
    # Preserve hyperopt parameter spaces while converting old v2 signal strings.
    source_text = re.sub(
        r"(space\s*=\s*)(['\"])(buy|sell)\2",
        lambda m: m.group(1) + m.group(2) + "__" + m.group(3).upper() + "_SPACE__" + m.group(2),
        source_text
    )
    replacements = [
        (r"\bpopulate_buy_trend\b", "populate_entry_trend"),
        (r"\bpopulate_sell_trend\b", "populate_exit_trend"),
        (r"\buse_sell_signal\b", "use_exit_signal"),
        (r"\bsell_profit_only\b", "exit_profit_only"),
        (r"\bsell_profit_offset\b", "exit_profit_offset"),
        (r"\bignore_roi_if_buy_signal\b", "ignore_roi_if_entry_signal"),
        (r"\bbuy_tag\b", "enter_tag"),
        (r"\bsell_tag\b", "exit_tag"),
    ]
    for pattern, replacement in replacements:
        source_text = re.sub(pattern, replacement, source_text)
    source_text = re.sub(r"(['\"])buy\1", r"\1enter_long\1", source_text)
    source_text = re.sub(r"(['\"])sell\1", r"\1exit_long\1", source_text)
    source_text = source_text.replace("__BUY_SPACE__", "buy").replace("__SELL_SPACE__", "sell")
    source_text = re.sub(
        r"from\s+freqtrade\.strategy\.hyper\s+import",
        "from freqtrade.strategy import",
        source_text
    )
    source_text = re.sub(
        r"from\s+numpy\.lib\s+import\s+math\b",
        "import math",
        source_text
    )
    source_text = re.sub(
        r"CategoricalParameter\(\s*([A-Za-z_]\w*)\.keys\(\)",
        r"CategoricalParameter(list(\1.keys())",
        source_text
    )
    source_text = re.sub(
        r"(INTERFACE_VERSION\s*=\s*)2\b",
        r"\g<1>3",
        source_text
    )
    if source_text != original:
        notes.append("legacy Freqtrade v2 API compatibility shim")
    if "CategoricalParameter(list(" in source_text:
        notes.append("dict_keys converted to list for parameter cloning")
    if "from numpy.lib import math" not in source_text and "import math" in source_text and "numpy.lib" in original:
        notes.append("NumPy math import compatibility shim")
    return source_text, "; ".join(dict.fromkeys(notes))

def offline_freqtrade_bootstrap():
    offline = Path("/tmp/realcheck-ft-offline")
    offline.mkdir(parents=True, exist_ok=True)
    bootstrap = offline / "sitecustomize.py"
    bootstrap.write_text(r'''
from freqtrade.exchange.exchange import Exchange

def _market(base, amount_step, price_step, quantity_precision, price_precision):
    symbol = f"{base}/USDT:USDT"
    return {
        "id": f"{base}USDT", "symbol": symbol, "base": base, "quote": "USDT",
        "settle": "USDT", "baseId": base, "quoteId": "USDT", "settleId": "USDT",
        "type": "swap", "spot": False, "margin": False, "swap": True,
        "future": False, "option": False, "active": True, "contract": True,
        "linear": True, "inverse": False, "contractSize": 1.0,
        "maker": 0.0002, "taker": 0.0005,
        "precision": {"amount": amount_step, "price": price_step},
        "limits": {
            "amount": {"min": amount_step, "max": 1000000.0},
            "price": {"min": price_step, "max": 1000000000.0},
            "cost": {"min": 5.0, "max": 1000000000.0},
            "leverage": {"min": 1.0, "max": 125.0},
        },
        "info": {
            "symbol": f"{base}USDT", "contractType": "PERPETUAL", "status": "TRADING",
            "baseAsset": base, "quoteAsset": "USDT", "marginAsset": "USDT",
            "quantityPrecision": quantity_precision, "pricePrecision": price_precision,
        },
    }

async def _offline_api_reload_markets(self, reload=False):
    markets = [
        _market("BTC", 0.001, 0.1, 3, 1),
        _market("ETH", 0.01, 0.01, 2, 2),
    ]
    self._api_async.set_markets(markets)
    timeframes = {"1m":"1m", "3m":"3m", "5m":"5m", "15m":"15m",
                  "30m":"30m", "1h":"1h", "2h":"2h", "4h":"4h", "1d":"1d"}
    self._api_async.timeframes = timeframes
    options = dict(getattr(self._api_async, "options", {}) or {})
    options["defaultType"] = "future"
    options["timeframes"] = {"swap": timeframes}
    self._api_async.options = options

def _offline_fill_leverage_tiers(self):
    self._leverage_tiers = {
        pair: [{
            "minNotional": 0.0, "maxNotional": 1000000000.0,
            "maintenanceMarginRate": 0.004, "maxLeverage": 125.0, "maintAmt": 0.0,
        }]
        for pair in ("BTC/USDT:USDT", "ETH/USDT:USDT")
    }

import numpy as np
np.NaN = np.nan
np.NAN = np.nan

Exchange._api_reload_markets = _offline_api_reload_markets
Exchange.check_time_offset = lambda self: None
Exchange.fill_leverage_tiers = _offline_fill_leverage_tiers
''')
    return offline

def classify_freqtrade_failure(detail):
    if any(token in detail for token in (
        "No data found", "No data available", "Tried to merge a faster timeframe",
        "Upsampling is not possible", "DataProvider is required for multiple timeframes"
    )):
        return "NOT_RUN_REQUIRES_CONTEXT"
    if "populate_entry_trend" in detail and "must be implemented" in detail:
        return "NOT_RUN_UNSUPPORTED_INTERFACE"
    if "No module named 'user_data." in detail:
        return "NOT_RUN_MISSING_EXTERNAL_HELPER"
    return "ERROR"

def freqtrade_trade_sample(engine_id, engine_name, timeframe, trade):
    return {
        "engine_id": engine_id,
        "engine_name": engine_name,
        "language": "python",
        "symbol": trade.get("pair", "BTC+ETH"),
        "timeframe": timeframe,
        "execution_engine": "Freqtrade",
        "open_date": trade.get("open_date"),
        "close_date": trade.get("close_date"),
        "entry_time": trade.get("open_date"),
        "exit_time": trade.get("close_date"),
        "side": "SHORT" if trade.get("is_short") else "LONG",
        "entry_price": trade.get("open_rate"),
        "exit_price": trade.get("close_rate"),
        "profit_abs": trade.get("profit_abs"),
        "profit": trade.get("profit_abs"),
        "profit_percent": trade.get("profit_ratio"),
        "exit_comment": trade.get("exit_reason"),
    }

def ft_run(row, strategy_class, timeframe):
    source = Path(row["artifact_path"])
    if not source.is_file():
        raise FileNotFoundError(source)
    tmp = Path("/tmp/realcheck-one-strategy")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    original = source.read_text(encoding="utf-8", errors="replace")
    transformed, compatibility = transform_freqtrade_source(original)
    Path("user_data/csvs").mkdir(parents=True, exist_ok=True)
    target = tmp / source.name
    target.write_text(transformed, encoding="utf-8")
    # Freqtrade's USD-M pair notation maps to BTC_USDT_USDT / ETH_USDT_USDT.
    for base in ("BTC", "ETH"):
        source_data = DATA / f"{base}_USDT-{timeframe}-futures.feather"
        alias = DATA / f"{base}_USDT_USDT-{timeframe}-futures.feather"
        if not source_data.is_file():
            raise FileNotFoundError(source_data)
        if not alias.exists():
            try:
                alias.symlink_to(source_data.resolve())
            except OSError:
                shutil.copy2(source_data, alias)
    offline = offline_freqtrade_bootstrap()
    config = Path("/tmp/realcheck-config.json")
    config.write_text(json.dumps({
        "dry_run": True,
        "strategy": strategy_class,
        "timeframe": timeframe,
        "trading_mode": "futures",
        "margin_mode": "isolated",
        "stake_currency": "USDT",
        "stake_amount": 1000,
        "dry_run_wallet": 10000,
        "tradable_balance_ratio": 0.99,
        "max_open_trades": 2,
        "datadir": "user_data/data/binance",
        "exchange": {
            "name": "binance", "key": "", "secret": "",
            "pair_whitelist": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
            "pair_blacklist": [],
        },
        "pairlists": [{"method": "StaticPairList"}],
        "dataformat_ohlcv": "feather",
        "dataformat_trades": "feather",
        "fee": 0.0005,
        "unfilledtimeout": {
            "entry": 10, "exit": 10, "exit_timeout_count": 0, "unit": "minutes"
        },
        "order_types": {
            "entry": "market", "exit": "market", "stoploss": "market",
            "stoploss_on_exchange": False,
        },
        "entry_pricing": {"price_side": "other", "use_order_book": True, "order_book_top": 1},
        "exit_pricing": {"price_side": "other", "use_order_book": True, "order_book_top": 1},
    }))
    result_dir = Path("/tmp/realcheck-ft-results") / f"{row['harvest_id']}_{strategy_class}_{timeframe}"
    shutil.rmtree(result_dir, ignore_errors=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = (
        str(offline.resolve()) + os.pathsep +
        str(Path("source-harvest/sources").resolve()) + os.pathsep +
        env.get("PYTHONPATH", "")
    )
    command = [
        "freqtrade", "backtesting",
        "--config", str(config),
        "--strategy-path", str(tmp),
        "--strategy", strategy_class,
        "--timeframe", timeframe,
        "--timerange", f"{START}-{END}",
        "--export", "trades",
        "--backtest-directory", str(result_dir),
    ]
    process = subprocess.run(
        command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        timeout=900, env=env
    )
    if process.returncode:
        detail = process.stdout[-3500:]
        return {
            "status": classify_freqtrade_failure(detail),
            "detail": detail,
            "compatibility_notes": compatibility,
            "execution_engine": "Freqtrade",
            "symbol": "BTC+ETH",
        }, []
    # Freqtrade 2026.10 stores the real timestamped JSON result INSIDE
    # backtest-result-<timestamp>.zip. The adjacent .meta.json and hidden
    # .last_result.json are metadata/pointers and must never be parsed as trades.
    result_archives = sorted(
        result_dir.glob("backtest-result-*.zip"),
        key=lambda p: p.stat().st_mtime
    )
    if not result_archives:
        pointer = result_dir / ".last_result.json"
        pointer_text = pointer.read_text(encoding="utf-8")[:1500] if pointer.is_file() else "missing"
        return {
            "status": "ERROR",
            "detail": (
                "Freqtrade exited 0 but produced no timestamped backtest-result ZIP in "
                + str(result_dir) + "; files=" + repr(sorted(p.name for p in result_dir.iterdir()))
                + "; hidden pointer=" + pointer_text + "\\n"
                + process.stdout[-2500:]
            ),
            "compatibility_notes": compatibility,
            "execution_engine": "Freqtrade",
            "symbol": "BTC+ETH",
        }, []
    archive_path = result_archives[-1]
    export_file = archive_path.stem + ".json"
    try:
        with ZipFile(archive_path, "r") as archive:
            members = set(archive.namelist())
            if export_file not in members:
                raise ValueError(
                    f"Timestamped Freqtrade JSON member {export_file!r} missing from "
                    f"{archive_path.name}; members={sorted(members)[:30]}"
                )
            export_bytes = archive.read(export_file)
    except BadZipFile as exc:
        raise ValueError(f"Freqtrade backtest export is not a valid ZIP: {archive_path}") from exc
    result_object = json.loads(export_bytes.decode("utf-8"))
    strategy_payload = (
        result_object.get("strategy", {}).get(strategy_class)
        if isinstance(result_object, dict) else None
    )
    if not isinstance(strategy_payload, dict):
        raise ValueError(
            f"Timestamped Freqtrade JSON lacks strategy payload for {strategy_class}"
        )
    trades = strategy_payload.get("trades")
    if not isinstance(trades, list):
        raise ValueError("Timestamped Freqtrade JSON strategy payload lacks a trades list")
    values = []
    for trade in trades:
        if not isinstance(trade, dict):
            raise ValueError("Freqtrade closed-trade record is not an object")
        if trade.get("is_open") is True:
            raise ValueError("Freqtrade export contains a still-open trade in its closed-trade list")
        if not trade.get("open_date") or not trade.get("close_date"):
            raise ValueError("Freqtrade closed-trade record lacks open_date or close_date")
        if trade.get("profit_abs") in ("", None):
            raise ValueError("Freqtrade closed-trade record has empty profit_abs")
        value = float(trade["profit_abs"])
        if not math.isfinite(value):
            raise ValueError("Non-finite Freqtrade closed-trade profit")
        values.append(value)
    export_dir = OUT / "freqtrade_exports" / row["harvest_id"] / timeframe
    export_dir.mkdir(parents=True, exist_ok=True)
    stored_export = export_dir / export_file
    stored_export.write_bytes(export_bytes)
    export_artifact_path = stored_export.relative_to(OUT).as_posix()
    stored_archive = export_dir / archive_path.name
    shutil.copy2(archive_path, stored_archive)
    export_archive_artifact_path = stored_archive.relative_to(OUT).as_posix()
    samples = []
    if trades:
        selected = list(enumerate(trades[:3]))
        start_index = max(3, len(trades) - 3)
        selected.extend((start_index + i, trades[start_index + i]) for i in range(len(trades) - start_index))
        seen = set()
        for index, trade in selected:
            if index in seen:
                continue
            seen.add(index)
            samples.append(freqtrade_trade_sample(
                row["harvest_id"], row.get("engine_name", strategy_class), timeframe, trade
            ))
    metrics = metric_summary(values)
    return {
        **metrics,
        "status": "BACKTESTED",
        "detail": "",
        "compatibility_notes": compatibility,
        "execution_engine": "Freqtrade",
        "symbol": "BTC+ETH",
        "export_file": export_file,
        "export_format": "timestamped_freqtrade_json",
        "export_container_file": archive_path.name,
        "export_container_sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "export_artifact_path": export_artifact_path,
        "export_archive_artifact_path": export_archive_artifact_path,
        "export_trade_records_validated": len(trades),
        "export_sha256": hashlib.sha256(export_bytes).hexdigest(),
    }, samples

def write_rows(path, rows):
    if not rows:
        path.write_text("")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int)
    parser.add_argument("--batches", type=int, default=12)
    parser.add_argument("--part-index", type=int, default=0)
    parser.add_argument("--part-count", type=int, default=1)
    parser.add_argument("--engine")
    parser.add_argument("--engine-list-file")
    parser.add_argument("--timeframe", choices=TFS)
    parser.add_argument("--output-tag", default="")
    args = parser.parse_args()
    if args.batches < 1:
        raise SystemExit("--batches must be >= 1")
    if args.part_count < 1 or not 0 <= args.part_index < args.part_count:
        raise SystemExit("--part-index must be within [0, part-count)")
    with Path("source-harvest/manifest.csv").open(newline="", encoding="utf-8") as handle:
        manifest = list(csv.DictReader(handle))
    selected = [row for row in manifest if row["harvest_id"] in SELECTED]
    selected.sort(key=lambda row: int(row["harvest_id"][3:]))
    if args.engine:
        selected = [row for row in selected if row["harvest_id"] == args.engine]
        if not selected:
            raise SystemExit(f"Unknown selected engine id: {args.engine}")
    if args.engine_list_file:
        raw_ids = Path(args.engine_list_file).read_text(encoding="utf-8").replace(",", "\n").splitlines()
        requested_ids = {item.strip() for item in raw_ids if item.strip() and not item.strip().startswith("#")}
        known_ids = {row["harvest_id"] for row in selected}
        unknown_ids = sorted(requested_ids - known_ids)
        if unknown_ids:
            raise SystemExit(f"Unknown engine IDs in list: {unknown_ids}")
        selected = [row for row in selected if row["harvest_id"] in requested_ids]
        if not selected:
            raise SystemExit("Engine list selected no engines")
    if args.batch is not None:
        if not 0 <= args.batch < args.batches:
            raise SystemExit("--batch must be within [0, batches)")
        selected = [row for i, row in enumerate(selected) if i % args.batches == args.batch]
    if args.part_count > 1:
        selected = [row for i, row in enumerate(selected) if i % args.part_count == args.part_index]
    timeframes = [args.timeframe] if args.timeframe else TFS
    if args.output_tag:
        tag = args.output_tag
    elif args.batch is not None and args.part_count > 1:
        tag = f"{args.batch:02d}_part{args.part_index}"
    elif args.part_count > 1:
        tag = f"rebuild_part{args.part_index}"
    else:
        tag = f"{args.batch:02d}" if args.batch is not None else "manual"
    results = []
    trade_samples = []
    batch_path = OUT / (f"batch_{tag}.csv" if tag.startswith("smoke") or tag == "manual" else f"batch_{tag}.csv")
    sample_path = OUT / f"trade_samples_{tag}.csv"

    def save():
        write_rows(batch_path, results)
        write_rows(sample_path, trade_samples)

    print(
        f"Selected {len(selected)} engines for batch={args.batch}, part={args.part_index}/{args.part_count}, tag={tag}",
        flush=True
    )
    for row in selected:
        engine_id = row["harvest_id"]
        language = row["implementation_language"]
        if language == "python":
            source = Path(row["artifact_path"])
            discovered_classes = find_classes(source)
            preferred_class = row.get("class_name", "").strip()
            classes = [preferred_class] if preferred_class in discovered_classes else discovered_classes
            if not classes:
                for timeframe in timeframes:
                    results.append({
                        "engine_id": engine_id, "engine_name": row.get("engine_name", ""),
                        "language": language, "timeframe": timeframe, "symbol": "BTC+ETH",
                        "status": "NOT_RUN_NO_STRATEGY_CLASS", "trades": 0,
                        "detail": "No IStrategy class found in source",
                    })
                save()
                continue
            for strategy_class in classes:
                for timeframe in timeframes:
                    base = {
                        "engine_id": engine_id,
                        "engine_name": row.get("engine_name", strategy_class),
                        "language": language,
                        "class": strategy_class,
                        "timeframe": timeframe,
                        "symbol": "BTC+ETH",
                        "execution_engine": "Freqtrade",
                    }
                    try:
                        print(f"Running Python {engine_id} {strategy_class} {timeframe}", flush=True)
                        metrics, samples = ft_run(row, strategy_class, timeframe)
                        results.append({**base, **metrics})
                        trade_samples.extend(samples)
                    except subprocess.TimeoutExpired:
                        results.append({**base, "status": "ERROR", "detail": "Freqtrade backtest exceeded 900-second timeout"})
                    except Exception as error:
                        results.append({**base, "status": "ERROR", "detail": repr(error)[:2500]})
                    save()
        elif language == "pine":
            source_path = Path(row["artifact_path"])
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
            for timeframe in timeframes:
                for symbol in ("BTC", "ETH"):
                    base = {
                        "engine_id": engine_id,
                        "engine_name": Path(urlparse(row.get("source_url", "")).path).stem,
                        "language": language,
                        "timeframe": timeframe,
                        "symbol": symbol,
                        "execution_engine": "PyneCore",
                        "tick_size": 0.1 if symbol == "BTC" else 0.01,
                        "min_contract": 0.001 if symbol == "BTC" else 0.01,
                        "lookahead_on": "YES" if re.search(
                            r"barmerge\.lookahead_on|lookahead\s*=\s*barmerge\.lookahead_on",
                            source_text
                        ) else "NO",
                    }
                    try:
                        print(f"Running Pine {engine_id} {symbol} {timeframe}", flush=True)
                        metrics, samples = pine_run(row, timeframe, symbol)
                        results.append({**base, **metrics})
                        trade_samples.extend(samples)
                    except Exception as error:
                        detail = repr(error)
                        if any(token in detail for token in (
                            "SecurityDataMissingError", "SecurityTimeframeHigherError",
                            "InputNotMainDefaultError", "ProviderUnavailableError",
                            "LiveSecuritySymbolError"
                        )):
                            status = "NOT_RUN_REQUIRES_CONTEXT"
                        else:
                            status = "ERROR"
                        results.append({**base, "status": status, "detail": detail[:2500], "trades": 0})
                    save()
        else:
            for timeframe in timeframes:
                results.append({
                    "engine_id": engine_id, "language": language, "timeframe": timeframe,
                    "status": "NOT_IN_ACTIVE_PORTABLE_REGISTRY",
                })
            save()
    save()
    print(json.dumps({
        "batch": args.batch, "tag": tag, "result_rows": len(results),
        "distinct_engines": len({row.get("engine_id") for row in results}),
        "backtested_rows": sum(row.get("status") == "BACKTESTED" for row in results),
        "closed_trade_samples": len(trade_samples),
    }, indent=2), flush=True)

if __name__ == "__main__":
    main()
