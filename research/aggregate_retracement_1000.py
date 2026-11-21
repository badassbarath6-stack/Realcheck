#!/usr/bin/env python3
"""Print concise retracement-only results; artifacts remain internal to the workflow."""
import csv, json
from pathlib import Path
root=Path("research-output")
all_rows=[]
for manifest_path in sorted(root.glob("*_manifest.json")):
    m=json.loads(manifest_path.read_text())
    p=root/f'{m["symbol"]}_{m["timeframe"]}_all_config_metrics.csv'
    with p.open(newline="") as f: rows=list(csv.DictReader(f))
    eligible=[r for r in rows if int(float(r["validation_trades"]))>=50]
    eligible.sort(key=lambda r:(float(r["validation_pf"]),float(r["validation_net_bps"])),reverse=True)
    print(f'\n{m["symbol"]} {m["timeframe"]}: {len(eligible)}/1000 configs meet 50 validation trades')
    for r in eligible[:5]:
        print("  retr={:.3f} ({:.1f}%) | val n={} WR={:.1f}% PF={:.3f} net={:.1f}bps | OOS n={} WR={:.1f}% PF={:.3f} net={:.1f}bps DD={:.1f}bps".format(
            float(r["retracement"]),float(r["retracement"])*100,int(float(r["validation_trades"])),
            float(r["validation_win_rate"])*100,float(r["validation_pf"]),float(r["validation_net_bps"]),
            int(float(r["oos_trades"])),float(r["oos_win_rate"])*100,float(r["oos_pf"]),
            float(r["oos_net_bps"]),float(r["oos_max_drawdown_bps"])))
    for r in eligible:
        all_rows.append((float(r["validation_pf"]),float(r["validation_net_bps"]),m["symbol"],m["timeframe"],r))
if len(list(root.glob("*_manifest.json")))!=12:
    raise SystemExit("Incomplete run: expected 12 symbol/timeframe manifests")
all_rows.sort(key=lambda x:(x[0],x[1]),reverse=True)
print("\n=== GLOBAL TOP 20 BY VALIDATION PF (OOS SHOWN, NOT USED FOR SELECTION) ===")
for _,__,sym,tf,r in all_rows[:20]:
    print("{} {} retr={:.3f} ({:.1f}%) | val PF={:.3f} n={} | OOS PF={:.3f} n={} net={:.1f}bps".format(
        sym,tf,float(r["retracement"]),float(r["retracement"])*100,float(r["validation_pf"]),
        int(float(r["validation_trades"])),float(r["oos_pf"]),int(float(r["oos_trades"])),float(r["oos_net_bps"])))
