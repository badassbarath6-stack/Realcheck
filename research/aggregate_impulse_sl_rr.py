#!/usr/bin/env python3
import csv,json,glob,sys
from pathlib import Path
files=sorted(glob.glob("research-output/*_sl_rr_all.csv"))
if len(files)!=12:raise SystemExit(f"Expected 12 result files, found {len(files)}")
rows=[]
for fn in files:
 with open(fn,newline="") as f: part=list(csv.DictReader(f))
 manifest=json.load(open(fn.replace("_sl_rr_all.csv","_sl_rr_manifest.json")))
 if len(part)!=manifest["configurations"] or len(part)!=46*23:
  raise SystemExit(f"Incomplete grid in {fn}: {len(part)}")
 if manifest["m1_gap_count"]!=0:raise SystemExit(f"M1 gaps found in {fn}")
 rows.extend(part)
if len(rows)!=12*46*23:raise SystemExit(f"Expected 12696 pair configs, got {len(rows)}")
def agg_key(rs):
 n=sum(int(float(r["validation_trades"])) for r in rs)
 gp=sum(float(r["validation_gross_profit_bps"]) for r in rs)
 gl=sum(float(r["validation_gross_loss_bps"]) for r in rs)
 sgp=sum(float(r["validation_stress7_net_bps"]) for r in rs if float(r["validation_stress7_net_bps"])>0)
 # Aggregate stress PF is recomputed from trade-level gross profit/loss unavailable in this compact CSV;
 # use stress net bps and normal PF as complementary diagnostics.
 net=sum(float(r["validation_net_bps"]) for r in rs)
 oosn=sum(int(float(r["oos_trades"])) for r in rs)
 oosgp=sum(float(r["oos_gross_profit_bps"]) for r in rs)
 oosgl=sum(float(r["oos_gross_loss_bps"]) for r in rs)
 oosnet=sum(float(r["oos_net_bps"]) for r in rs)
 stressnet=sum(float(r["oos_stress7_net_bps"]) for r in rs)
 return {"validation_trades":n,"validation_pf":gp/gl if gl else (999.0 if gp else 0.0),
         "validation_net_bps":net,"oos_trades":oosn,
         "oos_pf":oosgp/oosgl if oosgl else (999.0 if oosgp else 0.0),
         "oos_net_bps":oosnet,"oos_stress7_net_bps":stressnet,
         "pair_tf_positive_validation":sum(float(r["validation_pf"])>1 for r in rs),
         "pair_tf_positive_oos":sum(float(r["oos_pf"])>1 for r in rs),
         "pair_tf_positive_stress_oos":sum(float(r["oos_stress7_pf"])>1 for r in rs)}
groups={}
for r in rows:groups.setdefault((float(r["sl_atr"]),float(r["rr"])),[]).append(r)
summary=[]
for (sl,rr),rs in sorted(groups.items()):
 x={"sl_atr":sl,"rr":rr};x.update(agg_key(rs));summary.append(x)
Path("research-output").mkdir(exist_ok=True)
with open("research-output/global_sl_rr_aggregate.csv","w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
# Validation-only ranking; OOS is only displayed as a holdout.
eligible=[r for r in summary if r["validation_trades"]>=100]
eligible.sort(key=lambda x:(x["validation_pf"],x["validation_net_bps"]),reverse=True)
print(f"VERIFIED: {len(rows):,} pair-timeframe configurations; 1,058 shared SL/RR pairs.")
print("Global candidates ranked on validation only (>=100 validation trades across all 12 pair/timeframes):")
for r in eligible[:20]:
 print(f"SL {r['sl_atr']:.1f} ATR | RR {r['rr']:.2f} | val PF {r['validation_pf']:.3f} n={r['validation_trades']} net={r['validation_net_bps']:.0f}bps | OOS PF {r['oos_pf']:.3f} n={r['oos_trades']} net={r['oos_net_bps']:.0f}bps | OOS stress net={r['oos_stress7_net_bps']:.0f}bps | positive pair/TF val/OOS/stress {r['pair_tf_positive_validation']}/{r['pair_tf_positive_oos']}/{r['pair_tf_positive_stress_oos']}")
print("\nBest validation candidate per asset/timeframe (>=30 validation trades):")
for sym in ("BTCUSDT","ETHUSDT"):
 for tf in ("5m","15m","30m","1h","2h","4h"):
  rs=[r for r in rows if r["symbol"]==sym and r["timeframe"]==tf and int(float(r["validation_trades"]))>=30]
  rs.sort(key=lambda x:(float(x["validation_pf"]),float(x["validation_net_bps"])),reverse=True)
  if rs:
   r=rs[0];print(f"{sym} {tf}: SL {float(r['sl_atr']):.1f} ATR RR {float(r['rr']):.2f} | val PF {float(r['validation_pf']):.3f} n={int(float(r['validation_trades']))} | OOS PF {float(r['oos_pf']):.3f} n={int(float(r['oos_trades']))} | OOS stress PF {float(r['oos_stress7_pf']):.3f}")
  else:print(f"{sym} {tf}: no configuration reached 30 validation trades")
