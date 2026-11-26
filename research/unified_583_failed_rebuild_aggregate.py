#!/usr/bin/env python3
"""Merge targeted failed-engine retries and produce a distinct-engine top-100 ranking."""
import argparse, json
from pathlib import Path
import pandas as pd

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",default="baseline")
    ap.add_argument("--collected",default="collected")
    ap.add_argument("--engine-list",default="research/unified_583_failed_engine_ids.txt")
    ap.add_argument("--output",default="rebuilt-results")
    args=ap.parse_args()
    baseline=Path(args.baseline); collected=Path(args.collected); out=Path(args.output)
    out.mkdir(parents=True,exist_ok=True)
    ids={x.strip() for x in Path(args.engine_list).read_text().splitlines() if x.strip() and not x.startswith("#")}
    base=pd.read_csv(baseline/"all_engine_results.csv",low_memory=False)
    base_samples=pd.read_csv(baseline/"trade_samples.csv",low_memory=False)
    parts=sorted(collected.glob("batch_rebuild_part*.csv"))
    sample_parts=sorted(collected.glob("trade_samples_rebuild_part*.csv"))
    if len(parts)!=9 or len(sample_parts)!=9:
        raise SystemExit(f"Expected 9 worker result/sample files; got {len(parts)} and {len(sample_parts)}")
    retry=pd.concat([pd.read_csv(p,low_memory=False) for p in parts],ignore_index=True)
    retry_samples=pd.concat([pd.read_csv(p,low_memory=False) for p in sample_parts],ignore_index=True)
    if set(retry.engine_id.dropna().unique())!=ids:
        raise SystemExit(f"Retry engine coverage mismatch: expected {len(ids)}, got {retry.engine_id.nunique()}")
    # Every selected engine is rerun on all five timeframes; Pine runs both symbols.
    expected=0
    for eid in ids:
        lang=str(base.loc[base.engine_id==eid,"language"].iloc[0])
        expected += 10 if lang=="pine" else 5
    counts=retry.groupby("engine_id").size()
    missing={eid:expected for eid in []}
    bad={eid:int(counts.get(eid,0)) for eid in ids if int(counts.get(eid,0)) != (10 if str(base.loc[base.engine_id==eid,"language"].iloc[0])=="pine" else 5)}
    if bad:
        raise SystemExit(f"Incomplete retry rows by engine: {bad}")
    # Freeze every engine whose original eligible median PF is already > 1.30.
    # Retry results for those engines are ignored; their baseline rows and trades remain untouched.
    base_for_pf=base.copy()
    for c in ["trades","profit_factor"]:
        base_for_pf[c]=pd.to_numeric(base_for_pf[c],errors="coerce")
    base_for_pf["metric_warning"]=base_for_pf["metric_warning"].fillna("")
    base_for_pf["lookahead_on"]=base_for_pf["lookahead_on"].fillna("NO").astype(str).str.upper()
    eligible_base=base_for_pf[
        (base_for_pf.status=="BACKTESTED") &
        (base_for_pf.profit_factor_status=="FINITE") &
        (base_for_pf.trades>=30) &
        base_for_pf.profit_factor.notna() &
        (base_for_pf.metric_warning=="") &
        (base_for_pf.lookahead_on!="YES")
    ]
    protected_ids=set(eligible_base.groupby("engine_id").profit_factor.median().loc[lambda z:z>1.30].index)
    active_ids=ids-protected_ids
    retry_active=retry[retry.engine_id.isin(active_ids)].copy()
    if set(retry_active.engine_id.dropna().unique())!=active_ids:
        raise SystemExit(f"Active retry coverage mismatch after PF>1.30 protection: expected {len(active_ids)}, got {retry_active.engine_id.nunique()}")
    # Replace only underperforming/failed engines. High-PF engines are frozen as a whole.
    combined=pd.concat([base[~base.engine_id.isin(active_ids)],retry_active],ignore_index=True,sort=False)
    combined.to_csv(out/"all_engine_results_combined.csv",index=False)
    failed=combined[combined.engine_id.isin(active_ids)].copy()
    failed.to_csv(out/"failed_engine_rebuild_results.csv",index=False)
    retry_samples_active=retry_samples[retry_samples.engine_id.isin(active_ids)].copy()
    samples=pd.concat([base_samples[~base_samples.engine_id.isin(active_ids)],retry_samples_active],ignore_index=True,sort=False)
    samples.to_csv(out/"trade_samples_combined.csv",index=False)

    for c in ["trades","profit_factor","win_rate_pct","net_profit"]:
        combined[c]=pd.to_numeric(combined[c],errors="coerce")
    combined["metric_warning"]=combined["metric_warning"].fillna("")
    combined["lookahead_on"]=combined["lookahead_on"].fillna("NO").astype(str).str.upper()
    valid=combined[
        (combined.status=="BACKTESTED") &
        (combined.profit_factor_status=="FINITE") &
        (combined.trades>=30) &
        combined.profit_factor.notna() &
        (combined.metric_warning=="") &
        (combined.lookahead_on!="YES")
    ].copy()
    agg=valid.groupby(["engine_id","engine_name"]).agg(
        tested_cells=("engine_id","size"),
        total_closed_trades=("trades","sum"),
        median_profit_factor=("profit_factor","median"),
        mean_profit_factor=("profit_factor","mean"),
        min_profit_factor=("profit_factor","min"),
        max_profit_factor=("profit_factor","max"),
        median_win_rate_pct=("win_rate_pct","median"),
        mean_win_rate_pct=("win_rate_pct","mean"),
        profitable_cells=("net_profit",lambda x:int((x>0).sum())),
        total_net_profit=("net_profit","sum"),
        median_net_profit=("net_profit","median"),
    ).reset_index()
    agg=agg[agg.tested_cells>=2].copy()
    agg["profitable_cell_pct"]=(100*agg.profitable_cells/agg.tested_cells).round(1)
    agg=agg.sort_values(
        ["median_profit_factor","total_closed_trades","profitable_cell_pct"],
        ascending=False
    ).reset_index(drop=True)
    agg.insert(0,"engine_rank",range(1,len(agg)+1))
    top=agg.head(100).copy()
    top.to_csv(out/"top_100_distinct_engines.csv",index=False)
    details=valid[valid.engine_id.isin(top.engine_id)].merge(
        top[["engine_id","engine_rank"]],on="engine_id",how="inner"
    )
    details=details[[
        "engine_rank","engine_id","engine_name","symbol","timeframe","trades",
        "profit_factor","win_rate_pct","net_profit","execution_engine",
        "metric_warning","lookahead_on"
    ]].sort_values(["engine_rank","symbol","timeframe"])
    details.to_csv(out/"top_100_engine_market_timeframe_details.csv",index=False)
    samples[samples.engine_id.isin(top.engine_id)].to_csv(out/"top_100_trade_samples.csv",index=False)
    summary={
        "retry_engine_count":len(ids),
        "protected_high_pf_engine_count":len(protected_ids),
        "active_retry_engine_count":len(active_ids),
        "retry_result_rows":len(retry_active),
        "retry_status_counts":retry_active.status.value_counts(dropna=False).to_dict(),
        "retry_backtested_rows":int((retry_active.status=="BACKTESTED").sum()),
        "retry_error_rows":int((retry_active.status=="ERROR").sum()),
        "retry_not_run_rows":int(retry_active.status.astype(str).str.startswith("NOT_RUN").sum()),
        "combined_engine_count":int(combined.engine_id.nunique()),
        "eligible_distinct_engines_for_ranking":int(len(agg)),
        "top_100_distinct_engines":int(len(top)),
        "top_100_detail_rows":int(len(details)),
        "ranking_method":"Median finite PF across per-symbol/timeframe result cells with >=30 closed trades; excludes lookahead and metric-warning rows; requires >=2 eligible cells per engine; ties broken by total closed trades then profitable-cell percentage.",
        "note":"Net profit is reported for context but is not used as the primary ranking metric because sizing conventions vary across source engines. Any engine with original eligible median PF > 1.30 is frozen: baseline rows and trades are retained and retry outputs are ignored."
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2,default=str)+"\n")
    print(json.dumps(summary,indent=2,default=str))
if __name__=="__main__": main()
