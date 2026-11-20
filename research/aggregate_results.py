#!/usr/bin/env python3
import csv, json
from pathlib import Path

root=Path("research-output")
summaries=[]; monthly={}
for manifest_path in sorted(root.glob("*_manifest.json")):
    m=json.loads(manifest_path.read_text())
    symbol,tf=m["symbol"],m["timeframe"]
    metrics_path=root/f"{symbol}_{tf}_all_config_metrics.csv"
    with metrics_path.open(newline="") as f: rows=list(csv.DictReader(f))
    qualified=[r for r in rows if int(float(r["validation_trades"]))>=30]
    qualified.sort(key=lambda r:(float(r["validation_pf"]),float(r["validation_net_bps"])),reverse=True)
    top=qualified[0] if qualified else {}
    summaries.append({
        "symbol":symbol,"timeframe":tf,"configurations":m["configurations"],
        "candidate_trades":m["candidate_trades"],"train_selected":m["selected_trades"]["train"],
        "validation_selected":m["selected_trades"]["validation"],"oos_selected":m["selected_trades"]["oos"],
        "qualified_configs":len(qualified),"top_validation_pf":top.get("validation_pf",""),
        "top_validation_trades":top.get("validation_trades",""),
        "top_oos_pf":top.get("oos_pf",""),"top_oos_trades":top.get("oos_trades",""),
        "top_oos_net_bps":top.get("oos_net_bps",""),"m1_gap_count":m["m1_gap_count"],
        "funding_rate_rows":m.get("funding_rate_rows",0)
    })
    trades_path=root/f"{symbol}_{tf}_selected_trades.csv"
    if trades_path.exists():
        with trades_path.open(newline="") as f:
            for row in csv.DictReader(f):
                if row.get("period") not in ("validation","oos"): continue
                month=row["entry_ms"][:6] if len(row["entry_ms"])>=6 else row["entry_ms"]
                key=(symbol,tf,row["period"],month,row["direction"])
                item=monthly.setdefault(key,{"trades":0,"wins":0,"net_bps":0.0})
                item["trades"]+=1
                item["wins"]+=float(row["net_bps"])>0
                item["net_bps"]+=float(row["net_bps"])
with (root/"cross_timeframe_comparison.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(summaries[0]) if summaries else ["symbol","timeframe"]); w.writeheader(); w.writerows(summaries)
with (root/"monthly_direction_stability.csv").open("w",newline="") as f:
    fields=["symbol","timeframe","period","month","direction","trades","wins","win_rate","net_bps"]
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    for (symbol,tf,period,month,direction),v in sorted(monthly.items()):
        w.writerow({"symbol":symbol,"timeframe":tf,"period":period,"month":month,"direction":direction,
                    "trades":v["trades"],"wins":v["wins"],"win_rate":v["wins"]/v["trades"],
                    "net_bps":v["net_bps"]})
if len(summaries)!=12: raise SystemExit(f"Expected 12 pair/timeframe manifests; found {len(summaries)}")
print(json.dumps({"pairs":len(summaries),"monthly_groups":len(monthly)},indent=2))
