#!/usr/bin/env python3
import csv,json,glob
from pathlib import Path
files=sorted(glob.glob("research-output/*_sl_rr_all.csv"))
if len(files)!=12:raise SystemExit(f"Expected 12 result files, found {len(files)}")
rows=[]
for fn in files:
 with open(fn,newline="") as f: part=list(csv.DictReader(f))
 manifest=json.load(open(fn.replace("_sl_rr_all.csv","_sl_rr_manifest.json")))
 if len(part)!=manifest["configurations"] or len(part)!=46*23:raise SystemExit(f"Incomplete grid in {fn}: {len(part)}")
 if manifest["m1_gap_count"]!=0:raise SystemExit(f"M1 gaps found in {fn}")
 rows.extend(part)
if len(rows)!=12*46*23:raise SystemExit(f"Expected 12696 pair configs, got {len(rows)}")
def val(r,new,old):
 return float(r[new] if new in r else r[old])
def aggregate(rs):
 gp=sum(val(r,"validation_net_profit_bps","validation_gross_profit_bps") for r in rs)
 gl=sum(val(r,"validation_net_loss_bps","validation_gross_loss_bps") for r in rs)
 ogp=sum(val(r,"oos_net_profit_bps","oos_gross_profit_bps") for r in rs)
 ogl=sum(val(r,"oos_net_loss_bps","oos_gross_loss_bps") for r in rs)
 vsgp=sum(float(r.get("validation_stress7_net_profit_bps",0)) for r in rs)
 vsgl=sum(float(r.get("validation_stress7_net_loss_bps",0)) for r in rs)
 osgP=sum(float(r.get("oos_stress7_net_profit_bps",0)) for r in rs)
 osgL=sum(float(r.get("oos_stress7_net_loss_bps",0)) for r in rs)
 return {
  "validation_trades":sum(int(float(r["validation_trades"])) for r in rs),
  "validation_pf":gp/gl if gl else (999.0 if gp else 0.0),
  "validation_net_bps":sum(float(r["validation_net_bps"]) for r in rs),
  "validation_stress7_pf":vsgp/vsgl if vsgl else 0.0,
  "oos_trades":sum(int(float(r["oos_trades"])) for r in rs),
  "oos_pf":ogp/ogl if ogl else (999.0 if ogp else 0.0),
  "oos_net_bps":sum(float(r["oos_net_bps"]) for r in rs),
  "oos_stress7_pf":osgP/osgL if osgL else 0.0,
  "oos_stress7_net_bps":sum(float(r["oos_stress7_net_bps"]) for r in rs),
  "pair_tf_positive_validation":sum(float(r["validation_pf"])>1 for r in rs),
  "pair_tf_positive_oos":sum(float(r["oos_pf"])>1 for r in rs),
  "pair_tf_positive_stress_oos":sum(float(r["oos_stress7_pf"])>1 for r in rs)}
groups={}
for r in rows:groups.setdefault((float(r["sl_atr"]),float(r["rr"])),[]).append(r)
summary=[]
for (sl,rr),rs in sorted(groups.items()):
 x={"sl_atr":sl,"rr":rr};x.update(aggregate(rs));summary.append(x)
Path("research-output").mkdir(exist_ok=True)
with open("research-output/global_sl_rr_aggregate.csv","w",newline="") as f:
 w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
eligible=[r for r in summary if r["validation_trades"]>=100]
eligible.sort(key=lambda x:(x["validation_pf"],x["validation_net_bps"]),reverse=True)
print(f"VERIFIED: {len(rows):,} pair-timeframe configurations; 1,058 shared SL/RR pairs.")
print("Global candidates ranked on validation only (>=100 validation trades across 12 pair/timeframes):")
for r in eligible[:20]:
 print(f"SL {r['sl_atr']:.1f} ATR | RR {r['rr']:.2f} | val PF {r['validation_pf']:.3f} n={r['validation_trades']} net={r['validation_net_bps']:.0f}bps | OOS PF {r['oos_pf']:.3f} n={r['oos_trades']} net={r['oos_net_bps']:.0f}bps | OOS stress PF {r['oos_stress7_pf']:.3f} net={r['oos_stress7_net_bps']:.0f}bps | positive pair/TF val/OOS/stress {r['pair_tf_positive_validation']}/{r['pair_tf_positive_oos']}/{r['pair_tf_positive_stress_oos']}")
print("\nBest validation candidate per asset/timeframe (>=30 validation trades):")
for sym in ("BTCUSDT","ETHUSDT"):
 for tf in ("5m","15m","30m","1h","2h","4h"):
  rs=[r for r in rows if r["symbol"]==sym and r["timeframe"]==tf and int(float(r["validation_trades"]))>=30]
  rs.sort(key=lambda x:(float(x["validation_pf"]),float(x["validation_net_bps"])),reverse=True)
  if rs:
   r=rs[0];print(f"{sym} {tf}: SL {float(r['sl_atr']):.1f} ATR RR {float(r['rr']):.2f} | val PF {float(r['validation_pf']):.3f} n={int(float(r['validation_trades']))} | OOS PF {float(r['oos_pf']):.3f} n={int(float(r['oos_trades']))} | OOS stress PF {float(r['oos_stress7_pf']):.3f}")
  else:print(f"{sym} {tf}: no configuration reached 30 validation trades")
