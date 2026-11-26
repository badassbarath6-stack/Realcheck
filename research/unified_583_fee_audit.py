#!/usr/bin/env python3
"""Recalculate top-10 engine trade ledgers under common fee and slippage assumptions."""
import argparse, csv, json, math, re, zipfile
from pathlib import Path
import pandas as pd

ENGINE_META = {
    "SRC0540": ("IchiV1", 10.68960, 3229, "Freqtrade"),
    "SRC0367": ("VoVix DEVMA", 7.84610, 21469, "PyneCore"),
    "SRC0151": ("Hybrid RSI Breakout", 7.32010, 44539, "PyneCore"),
    "SRC0383": ("Zendog V3 DCA", 4.91380, 1844, "PyneCore"),
    "SRC0399": ("BBRSITV", 3.84805, 74, "Freqtrade"),
    "SRC0748": ("Zeus", 2.75840, 576, "Freqtrade"),
    "SRC0581": ("NASOSv4", 1.82550, 115, "Freqtrade"),
    "SRC0632": ("NotAnotherSMAOffset", 1.75610, 235, "Freqtrade"),
    "SRC0008": ("3Commas DCA", 1.73405, 13489, "PyneCore"),
    "SRC0156": ("ICT Entry V2", 1.38010, 589, "PyneCore"),
}
BASE_FEE, STRESS_FEE, STRESS_SLIPPAGE = 0.0005, 0.00075, 0.00025

def fnum(x, default=0.0):
    try:
        v=float(x)
        return v if math.isfinite(v) else default
    except (TypeError,ValueError):
        return default

def pf(values):
    wins=math.fsum(v for v in values if v>0)
    losses=-math.fsum(v for v in values if v<0)
    return wins/losses if losses>0 else (None if wins==0 else math.inf)

def load_freqtrade(root):
    rows=[]
    for path in Path(root).rglob("*.zip"):
        m=re.search(r"SRC\d{4}",str(path))
        if not m or m.group(0) not in ENGINE_META: continue
        eid=m.group(0); tf=path.parent.name
        with zipfile.ZipFile(path) as z:
            member=next(n for n in z.namelist() if n.endswith(".json"))
            payload=json.loads(z.read(member))
        strategy=next(iter(payload["strategy"].values()))
        for t in strategy.get("trades",[]):
            amount=fnum(t.get("amount")); entry=fnum(t.get("open_rate")); exit_=fnum(t.get("close_rate"))
            short=bool(t.get("is_short",False))
            gross=(entry-exit_ if short else exit_-entry)*amount
            no,nc=amount*entry,amount*exit_
            funding=fnum(t.get("funding_fees"))
            native_fee=no*fnum(t.get("fee_open"))+nc*fnum(t.get("fee_close"))
            rows.append({
                "engine_id":eid,"engine_name":ENGINE_META[eid][0],"execution_engine":"Freqtrade",
                "symbol":str(t.get("pair","")).split("/")[0],"timeframe":tf,
                "side":"SHORT" if short else "LONG","entry_time":t.get("open_date"),"exit_time":t.get("close_date"),
                "entry_price":entry,"exit_price":exit_,"size":amount,"gross_pnl":gross,
                "source_native_commission":native_fee,"funding_fee":funding,
                "source_native_net_pnl":fnum(t.get("profit_abs")),"notional_round_trip":no+nc,
                "source_reconciliation_error":fnum(t.get("profit_abs"))-(gross-native_fee-funding),
                "exit_reason":t.get("exit_reason","")
            })
    return rows

def load_pyne(root):
    rows=[]
    for path in Path(root).rglob("trade_samples_top10_pine_fee_part*.csv"):
        if not path.stat().st_size: continue
        for t in csv.DictReader(path.open(newline="",encoding="utf-8")):
            eid=t.get("engine_id")
            if eid not in ENGINE_META: continue
            size=fnum(t.get("size")); entry=fnum(t.get("entry_price")); exit_=fnum(t.get("exit_price"))
            commission=fnum(t.get("commission")); source_net=fnum(t.get("profit"))
            gross=source_net+commission # PyneCore closed-trade profit is after commission.
            side=str(t.get("side","LONG")).upper()
            price_gross=(entry-exit_ if side=="SHORT" else exit_-entry)*size
            rows.append({
                "engine_id":eid,"engine_name":ENGINE_META[eid][0],"execution_engine":"PyneCore",
                "symbol":str(t.get("symbol","")),"timeframe":str(t.get("timeframe","")),
                "side":side,"entry_time":t.get("entry_time_ms"),"exit_time":t.get("exit_time_ms"),
                "entry_price":entry,"exit_price":exit_,"size":size,"gross_pnl":gross,
                "source_native_commission":commission,"funding_fee":0.0,
                "source_native_net_pnl":source_net,"notional_round_trip":size*(entry+exit_),
                "source_reconciliation_error":gross-price_gross,"exit_reason":t.get("exit_comment","")
            })
    return rows

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--baseline",required=True)
    ap.add_argument("--collected",required=True)
    ap.add_argument("--output",default="top10-fee-audit")
    a=ap.parse_args()
    df=pd.DataFrame(load_freqtrade(a.baseline)+load_pyne(a.collected))
    if df.empty: raise SystemExit("No complete trade ledgers found")
    df["fee_005_each_side"]=df.notional_round_trip*BASE_FEE
    df["standard_net_005"]=df.gross_pnl-df.fee_005_each_side-df.funding_fee
    df["fee_0075_each_side"]=df.notional_round_trip*STRESS_FEE
    df["slippage_0025_each_side"]=df.notional_round_trip*STRESS_SLIPPAGE
    df["stress_net_0075_fee_0025_slippage"]=df.gross_pnl-df.fee_0075_each_side-df.slippage_0025_each_side-df.funding_fee
    out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    df.to_csv(out/"top10_full_trade_cost_ledger.csv",index=False)
    def metric(g,col):
        x=g[col].astype(float)
        return {"profit_factor":pf(x.tolist()),"pnl":float(x.sum()),
                "win_rate_pct":float((x>0).mean()*100),"avg_trade_pnl":float(x.mean())}
    cells=[]
    for (eid,tf,sym),g in df.groupby(["engine_id","timeframe","symbol"]):
        name,bpf,btr,lang=ENGINE_META[eid]
        r={"engine_id":eid,"engine_name":name,"source_language":lang,"baseline_median_pf":bpf,
           "baseline_eligible_trades":btr,"timeframe":tf,"symbol":sym,"closed_trades":len(g)}
        for label,col in [("gross","gross_pnl"),("source_native_net","source_native_net_pnl"),
                          ("standard_net_005","standard_net_005"),
                          ("stress_net","stress_net_0075_fee_0025_slippage")]:
            for k,v in metric(g,col).items(): r[label+"_"+k]=v
        for label,col in [("source_native_commission_total","source_native_commission"),
                          ("standard_fee_005_total","fee_005_each_side"),
                          ("stress_fee_0075_total","fee_0075_each_side"),
                          ("stress_slippage_total","slippage_0025_each_side"),
                          ("funding_total","funding_fee")]:
            r[label]=float(g[col].sum())
        r["median_gross_move_bps"]=float((10000*g.gross_pnl/(g["size"]*g.entry_price).replace(0,math.nan)).median())
        r["max_abs_source_reconciliation_error"]=float(g.source_reconciliation_error.abs().max())
        cells.append(r)
    pd.DataFrame(cells).to_csv(out/"top10_fee_audit_by_symbol_timeframe.csv",index=False)
    rolls=[]
    for eid,g in df.groupby("engine_id"):
        name,bpf,btr,lang=ENGINE_META[eid]
        r={"engine_id":eid,"engine_name":name,"source_language":lang,"baseline_median_pf":bpf,
           "baseline_eligible_trades":btr,"full_ledger_trades":len(g),
           "symbols":",".join(sorted(g.symbol.astype(str).unique())),
           "timeframes":",".join(sorted(g.timeframe.astype(str).unique()))}
        for label,col in [("gross","gross_pnl"),("source_native_net","source_native_net_pnl"),
                          ("standard_net_005","standard_net_005"),
                          ("stress_net","stress_net_0075_fee_0025_slippage")]:
            for k,v in metric(g,col).items(): r[label+"_"+k]=v
        for label,col in [("source_native_commission_total","source_native_commission"),
                          ("standard_fee_005_total","fee_005_each_side"),
                          ("stress_fee_0075_total","fee_0075_each_side"),
                          ("stress_slippage_total","slippage_0025_each_side"),
                          ("funding_total","funding_fee")]:
            r[label]=float(g[col].sum())
        r["median_gross_move_bps"]=float((10000*g.gross_pnl/(g["size"]*g.entry_price).replace(0,math.nan)).median())
        r["max_abs_source_reconciliation_error"]=float(g.source_reconciliation_error.abs().max())
        rolls.append(r)
    roll=pd.DataFrame(rolls).sort_values("baseline_median_pf",ascending=False)
    roll.to_csv(out/"top10_fee_audit_engine_rollup.csv",index=False)
    summary={
      "engines_with_full_ledgers":int(df.engine_id.nunique()),"closed_trade_records":int(len(df)),
      "freqtrade_trade_records":int((df.execution_engine=="Freqtrade").sum()),
      "pynecore_trade_records":int((df.execution_engine=="PyneCore").sum()),
      "max_abs_source_reconciliation_error":float(df.source_reconciliation_error.abs().max()),
      "source_native_net_total":float(df.source_native_net_pnl.sum()),
      "gross_total":float(df.gross_pnl.sum()),"standard_net_005_total":float(df.standard_net_005.sum()),
      "stress_net_total":float(df.stress_net_0075_fee_0025_slippage.sum()),
      "standard_fee_005_total":float(df.fee_005_each_side.sum()),
      "stress_fee_0075_total":float(df.fee_0075_each_side.sum()),
      "stress_slippage_total":float(df.slippage_0025_each_side.sum()),
      "funding_total":float(df.funding_fee.sum()),
      "coverage_note":"Complete ledger for every available engine/timeframe/symbol row. Compare PF within each symbol/timeframe; pooled engine totals combine sizing and are descriptive only.",
      "scenarios":{"gross":"Price P&L before commissions, funding and slippage.",
        "source_native_net":"Original runner net after source-configured commissions and recorded funding.",
        "standard_net_005":"Gross less 0.05% notional fee on entry and exit, plus recorded funding.",
        "stress_net":"Gross less 0.075% fee and 0.025% adverse slippage on each side, plus recorded funding."}
    }
    (out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
    print(roll[["engine_id","engine_name","full_ledger_trades","gross_profit_factor",
                "source_native_net_profit_factor","standard_net_005_profit_factor",
                "stress_net_profit_factor"]].to_string(index=False))

if __name__=="__main__": main()
