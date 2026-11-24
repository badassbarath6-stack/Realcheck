#!/usr/bin/env python3
"""Strict coverage, trade-record and ranking validation for the repaired 583 run."""
import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from unified_583_three_year_backtest import SELECTED, TFS

def read_csv(path):
    if not path.is_file() or path.stat().st_size == 0:
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))

def write_csv(path, rows):
    if not rows:
        path.write_text("")
        return
    fields = sorted({key for row in rows for key in row})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

def number(value, default=0.0):
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default

def pf_sort_key(row):
    status = row.get("profit_factor_status", "")
    unbounded = 1 if status == "UNBOUNDED_NO_LOSSES" else 0
    pf = number(row.get("profit_factor"), 0.0)
    return (unbounded, pf, number(row.get("trades")), number(row.get("win_rate_pct")))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--collected", default="collected")
    parser.add_argument("--output", default="three-year-results")
    parser.add_argument("--input-manifest", default="source-harvest/manifest.csv")
    args = parser.parse_args()
    collected = Path(args.collected)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)

    batch_paths = [collected / f"batch_{i:02d}.csv" for i in range(12)]
    missing_batches = [str(path) for path in batch_paths if not path.is_file() or path.stat().st_size == 0]
    rows = []
    for path in batch_paths:
        rows.extend(read_csv(path))

    manifest = read_csv(Path(args.input_manifest))
    selected_manifest = [row for row in manifest if row.get("harvest_id") in SELECTED]
    language_by_id = {row["harvest_id"]: row.get("implementation_language", "") for row in selected_manifest}
    expected_ids = set(SELECTED)
    expected_pine = {eid for eid, lang in language_by_id.items() if lang == "pine"}
    expected_python = {eid for eid, lang in language_by_id.items() if lang == "python"}

    actual_ids = {row.get("engine_id", "") for row in rows if row.get("engine_id")}
    missing_ids = sorted(expected_ids - actual_ids)
    extra_ids = sorted(actual_ids - expected_ids)
    per_engine = defaultdict(list)
    for row in rows:
        per_engine[row.get("engine_id", "")].append(row)

    coverage_errors = []
    for engine_id in sorted(expected_ids):
        items = per_engine.get(engine_id, [])
        language = language_by_id.get(engine_id, "")
        expected_count = 10 if language == "pine" else 5 if language == "python" else 0
        if len(items) != expected_count:
            coverage_errors.append(
                f"{engine_id}: expected {expected_count} rows for {language}, got {len(items)}"
            )
        actual_tfs = {item.get("timeframe") for item in items}
        if actual_tfs != set(TFS):
            coverage_errors.append(f"{engine_id}: timeframe coverage {sorted(actual_tfs)}")
        if language == "pine":
            actual_symbols = {item.get("symbol") for item in items}
            if actual_symbols != {"BTC", "ETH"}:
                coverage_errors.append(f"{engine_id}: Pine symbol coverage {sorted(actual_symbols)}")
        elif language == "python":
            if any(item.get("symbol") != "BTC+ETH" for item in items):
                coverage_errors.append(f"{engine_id}: Python combined-pair label missing")

    duplicate_keys = []
    seen = set()
    for row in rows:
        if row.get("language") == "pine":
            key = (row.get("engine_id"), row.get("timeframe"), row.get("symbol"))
        else:
            key = (row.get("engine_id"), row.get("timeframe"))
        if key in seen:
            duplicate_keys.append(key)
        seen.add(key)

    status_counts = Counter(row.get("status", "UNKNOWN") for row in rows)
    backtested = [row for row in rows if row.get("status") == "BACKTESTED"]
    closed_trades = sum(int(number(row.get("trades"))) for row in backtested)
    zero_trade_rows = sum(int(number(row.get("trades"))) == 0 for row in backtested)
    positive_trade_rows = sum(int(number(row.get("trades"))) > 0 for row in backtested)

    samples = []
    for i in range(12):
        samples.extend(read_csv(collected / f"trade_samples_{i:02d}.csv"))
    sample_keys = set()
    for sample in samples:
        if sample.get("language") == "pine":
            sample_keys.add((sample.get("engine_id"), sample.get("timeframe"), sample.get("symbol")))
        else:
            sample_keys.add((sample.get("engine_id"), sample.get("timeframe")))
    missing_sample_rows = []
    for row in backtested:
        if int(number(row.get("trades"))) <= 0:
            continue
        if row.get("language") == "pine":
            key = (row.get("engine_id"), row.get("timeframe"), row.get("symbol"))
        else:
            key = (row.get("engine_id"), row.get("timeframe"))
        if key not in sample_keys:
            missing_sample_rows.append(key)

    pf_ranked = []
    for row in backtested:
        trades = int(number(row.get("trades")))
        pf_status = row.get("profit_factor_status", "")
        if trades >= 30 and pf_status in ("FINITE", "UNBOUNDED_NO_LOSSES"):
            pf_ranked.append(dict(row))
    pf_ranked.sort(key=pf_sort_key, reverse=True)
    for rank, row in enumerate(pf_ranked, 1):
        row["pf_rank"] = rank
        row["pf_ranking_note"] = (
            "Unbounded: no losing closed trades" if row.get("profit_factor_status") == "UNBOUNDED_NO_LOSSES"
            else "Finite gross-profit / gross-loss"
        )

    entry_ranked = [
        dict(row) for row in backtested if int(number(row.get("trades"))) > 0
    ]
    entry_ranked.sort(
        key=lambda row: (
            number(row.get("trades")),
            1 if row.get("profit_factor_status") == "UNBOUNDED_NO_LOSSES" else 0,
            number(row.get("profit_factor")),
        ),
        reverse=True,
    )
    for rank, row in enumerate(entry_ranked, 1):
        row["entry_rank"] = rank

    error_groups = Counter()
    not_run_groups = Counter()
    warning_rows = []
    for row in rows:
        status = row.get("status", "UNKNOWN")
        detail = row.get("detail", "")
        if status not in ("BACKTESTED", "NOT_RUN_REQUIRES_CONTEXT", "NOT_RUN_UNSUPPORTED_INTERFACE",
                          "NOT_RUN_NO_STRATEGY_CLASS", "NOT_RUN_MISSING_EXTERNAL_HELPER"):
            error_groups[(status, detail[:1000])] += 1
        if status.startswith("NOT_RUN"):
            not_run_groups[(status, detail[:1000])] += 1
        if row.get("metric_warning"):
            warning_rows.append(row)

    summary = {
        "result_rows": len(rows),
        "expected_result_rows": 4810,
        "distinct_engines_attempted": len(actual_ids),
        "expected_distinct_engines": 583,
        "pine_engine_ids": len(expected_pine),
        "python_engine_ids": len(expected_python),
        "pine_result_rows": sum(row.get("language") == "pine" for row in rows),
        "python_result_rows": sum(row.get("language") == "python" for row in rows),
        "backtested_rows": len(backtested),
        "closed_trades": closed_trades,
        "positive_trade_rows": positive_trade_rows,
        "zero_trade_backtest_rows": zero_trade_rows,
        "trade_sample_rows": len(samples),
        "backtested_rows_missing_trade_samples": len(missing_sample_rows),
        "pf_ranked_rows_min_30_trades": len(pf_ranked),
        "entry_ranked_rows": len(entry_ranked),
        "status_counts": dict(status_counts),
        "period_utc": ["2023-11-24", "2026-11-23"],
        "timeframes": list(TFS),
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "batch_files": 12,
        "ranking_rule": "PF descending (unbounded/no-loss rows first), then closed trades; PF ranking requires >=30 closed trades",
        "data_and_execution_notes": [
            "Reused the checksum-verified Binance USD-M 1m archive and prepared 5m/15m/30m/1h/4h candles from run 45358233591.",
            "Pine BTC tick size corrected to 0.1; ETH tick size 0.01; native script order/exit settings retained.",
            "Freqtrade USD-M runs use local candles, offline Binance contract metadata, 10,000 USDT starting wallet, 1,000 USDT stake, 2 concurrent pairs, and 0.05% fee per side.",
            "Legacy Freqtrade v2 names were translated to current v3 signal/config names in a temporary copy only; harvested originals were not changed.",
            "Python rows combine BTC and ETH in one Freqtrade backtest per timeframe; Pine rows are separate BTC and ETH runs.",
            "Pine requests needing secondary symbols/timeframes, lower-timeframe arrays, non-standard chart feeds, or external fundamentals are marked not run rather than approximated.",
            "PF with no losing trades is reported as unbounded rather than capped at an arbitrary value.",
            "Net profit outliers are flagged for manual review; this is an in-sample screening run, not a walk-forward validation."
        ],
    }
    diagnostics = {
        "summary": summary,
        "missing_batch_files": missing_batches,
        "missing_engine_ids": missing_ids,
        "extra_engine_ids": extra_ids,
        "coverage_errors": coverage_errors[:200],
        "duplicate_result_keys": [list(key) for key in duplicate_keys[:200]],
        "missing_trade_sample_keys": [list(key) for key in missing_sample_rows[:200]],
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (output / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    write_csv(output / "all_engine_results.csv", rows)
    write_csv(output / "trade_samples.csv", samples)
    write_csv(output / "ranked_profit_factor_min_30_trades.csv", pf_ranked)
    write_csv(output / "ranked_highest_entries.csv", entry_ranked)
    write_csv(output / "error_summary.csv", [
        {"status": key[0], "detail": key[1], "rows": count}
        for key, count in error_groups.most_common()
    ])
    write_csv(output / "not_run_summary.csv", [
        {"status": key[0], "detail": key[1], "rows": count}
        for key, count in not_run_groups.most_common()
    ])
    write_csv(output / "metric_warnings.csv", warning_rows)
    print(json.dumps(summary, indent=2))

    blockers = []
    if missing_batches:
        blockers.append("Missing batch files")
    if len(rows) != 4810:
        blockers.append(f"Expected 4810 rows, found {len(rows)}")
    if len(actual_ids) != 583 or missing_ids or extra_ids:
        blockers.append(f"Expected 583 engine IDs, found {len(actual_ids)}")
    if len(expected_ids) != 583:
        blockers.append(f"Selected registry itself contains {len(expected_ids)} IDs")
    if len(expected_pine) != 379 or len(expected_python) != 204:
        blockers.append(f"Unexpected language registry split: Pine={len(expected_pine)}, Python={len(expected_python)}")
    if coverage_errors:
        blockers.append(f"Engine/timeframe/symbol coverage errors: {len(coverage_errors)}")
    if duplicate_keys:
        blockers.append(f"Duplicate result keys: {len(duplicate_keys)}")
    if closed_trades <= 0:
        blockers.append("No real closed trades were exported")
    if missing_sample_rows:
        blockers.append(f"Backtested rows with trades but no trade samples: {len(missing_sample_rows)}")
    if blockers:
        raise SystemExit("INCOMPLETE OR INVALID BACKTEST: " + "; ".join(blockers))

if __name__ == "__main__":
    main()
