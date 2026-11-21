#!/usr/bin/env python3
"""Aggregate all fixed-impulse retracement sweep outputs."""
import csv,json
from pathlib import Path
root=Path("research-output")
manifests=sorted(root.glob("*_manifest.json"))
if len(manifests)!=12:
    raise SystemExit(f"Expected 12 symbol/timeframe manifests, found {len(manifests)}")
all_rows=[]
for mp in manifests:
    m=json.loads(mp.read_text())
    p=root/f'{m["symbol"]}_{m["timeframe"]}_all_config_metrics.csv'
    with p.open(newline="") as f: rows=list(csv.DictReader(f))
    if len(rows)!=1000: raise SystemExit(f"{p}: expected 1000 rows, got {len(rows)}")
    tf=m["timeframe"]; expected=m["config1_impulse_minimum_atr_by_timeframe"][tf]
    if any(float(r["impulse_atr"])!=expected for r in rows): raise SystemExit(f"{p}: Config 1 impulse mismatch")
    eligible=[r for r in rows if int(float(r["validation_trades"]))>=50]
    eligible.sort(key=lambda r:(float(r["validation_pf"]),float(r["validation_net_bps"])),reverse=True)
    print(f'\n{m["symbol"]} {tf} | Config 1 >= {expected:.1f} ATR | tested all {len(rows)} retracements | >=50 validation trades: {len(eligible)}')
    print("  LOWEST 3 validation PF (all sample sizes):")
    for r in sorted(rows,key=lambda r:float(r["validation_pf"]))[:3]:
        print(f'    retr={float(r["retracement"])*100:.1f}% valPF={float(r["validation_pf"]):.3f} valN={int(float(r["validation_trades"]))} OOSPF={float(r["oos_pf"]):.3f} OOSN={int(float(r["oos_trades"]))}')
    print("  TOP 5 by validation PF (>=50 validation trades):")
    for r in eligible[:5]:
        print(f'    retr={float(r["retracement"])*100:.1f}% valPF={float(r["validation_pf"]):.3f} valN={int(float(r["validation_trades"]))} OOSPF={float(r["oos_pf"]):.3f} OOSN={int(float(r["oos_trades"]))} stressOOSPF={float(r["oos_slippage7_pf"]):.3f}')
    for r in rows: all_rows.append((m["symbol"],tf,r))
ranked=[x for x in all_rows if int(float(x[2]["validation_trades"]))>=50]
ranked.sort(key=lambda x:(float(x[2]["validation_pf"]),float(x[2]["validation_net_bps"])),reverse=True)
print("\n=== GLOBAL TOP 30 BY VALIDATION PF; OOS SHOWN ONLY AS HOLDOUT ===")
for sym,tf,r in ranked[:30]:
    print(f'{sym} {tf} retr={float(r["retracement"])*100:.1f}% valPF={float(r["validation_pf"]):.3f} n={int(float(r["validation_trades"]))} OOSPF={float(r["oos_pf"]):.3f} n={int(float(r["oos_trades"]))} stressOOSPF={float(r["oos_slippage7_pf"]):.3f}')
