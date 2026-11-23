#!/usr/bin/env python3
"""Attempt source-faithful 5-year Freqtrade backtests; never silently translate other languages."""
import ast,csv,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path("source-harvest"); OUT=Path("five-year-results"); TMP=Path("/tmp/one-strategy")
START="20211122"; END="20261122"
PAIRS=["BTC/USDT:USDT","ETH/USDT:USDT"]
TF_OK={"5m","15m","30m","1h","4h"}
OUT.mkdir(exist_ok=True)
def run(cmd,timeout=240):
    return subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)
def get_classes(p):
    try: t=ast.parse(p.read_text(encoding="utf-8",errors="replace"))
    except Exception:return []
    found=[]
    for n in ast.walk(t):
        if isinstance(n,ast.ClassDef):
            bases=[ast.unparse(x) for x in n.bases]
            if any("IStrategy" in b for b in bases): found.append(n.name)
    return found
def timeframe(p):
    try:t=ast.parse(p.read_text(encoding="utf-8",errors="replace"))
    except Exception:return None
    for n in ast.walk(t):
        if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="timeframe" for x in n.targets):
            try:return ast.literal_eval(n.value)
            except Exception:pass
    return None
def main():
    manifest=list(csv.DictReader((ROOT/"manifest.csv").open()))
    py=[r for r in manifest if r["implementation_language"]=="python"]
    pine=[r for r in manifest if r["implementation_language"]=="pine"]
    mql=[r for r in manifest if r["implementation_language"]=="mql5"]
    config={"dry_run":True,"strategy":"SampleStrategy","timeframe":"5m","trading_mode":"futures","margin_mode":"isolated",
      "stake_currency":"USDT","stake_amount":1000,"tradable_balance_ratio":0.99,"max_open_trades":1,
      "exchange":{"name":"binance","key":"","secret":"","ccxt_config":{},"ccxt_async_config":{},"pair_whitelist":PAIRS,"pair_blacklist":[]},
      "pairlists":[{"method":"StaticPairList"}],"dataformat_ohlcv":"feather","dataformat_trades":"feather",
      "fee":0.0005,"unfilledtimeout":{"entry":10,"exit":10,"exit_timeout_count":0,"unit":"minutes"},
      "order_types":{"entry":"market","exit":"market","stoploss":"market","stoploss_on_exchange":False},
      "entry_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1},
      "exit_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1}}
    Path("user_data").mkdir(exist_ok=True)
    Path("/tmp/config.json").write_text(json.dumps(config))
    rows=[]
    for r in py:
      src=Path(r["artifact_path"]); classes=get_classes(src); tf=timeframe(src)
      if not classes:
        rows.append({"id":r["harvest_id"],"language":"python","class":"","timeframe":tf or "unknown","status":"REJECTED_NO_IStrategy_CLASS","detail":"Static parser found no IStrategy class"});continue
      for cls in classes:
        if tf not in TF_OK:
          rows.append({"id":r["harvest_id"],"language":"python","class":cls,"timeframe":tf or "unknown","status":"NOT_TESTED_UNSUPPORTED_TIMEFRAME","detail":"No matching five-year candle dataset"});continue
        shutil.rmtree(TMP,ignore_errors=True);TMP.mkdir(parents=True)
        shutil.copy2(src,TMP/src.name)
        dest=OUT/f'{r["harvest_id"]}_{cls}'
        cmd=["python","research/engine_audit/offline_freqtrade_cli.py","backtesting","--config","/tmp/config.json","--strategy-path",str(TMP),
             "--strategy",cls,"--timeframe",tf,"--timerange",f"{START}-{END}","--export","trades",
             "--export-filename",str(dest)+".json"]
        started=time.time()
        try:
          p=run(cmd,timeout=300)
          status="BACKTESTED" if p.returncode==0 and (dest.with_suffix(".json")).exists() else "FAILED"
          detail=p.stdout[-3500:].replace("\n"," | ")
        except subprocess.TimeoutExpired as e:
          status="TIMEOUT";detail="Exceeded 300 seconds per strategy"
        rows.append({"id":r["harvest_id"],"language":"python","class":cls,"timeframe":tf,"status":status,"seconds":round(time.time()-started,1),"detail":detail})
        with (OUT/"progress.csv").open("w",newline="") as f:
          w=csv.DictWriter(f,fieldnames=sorted({k for x in rows for k in x}));w.writeheader();w.writerows(rows)
    for r in pine:
      rows.append({"id":r["harvest_id"],"language":"pine","class":"","timeframe":"source-defined","status":"NOT_TESTED_NO_PINE_RUNTIME","detail":"Pine strategy requires Pine-compatible runtime/semantic port; no candle-only approximation performed"})
    for r in mql:
      rows.append({"id":r["harvest_id"],"language":"mql5","class":"","timeframe":"source-defined","status":"NOT_TESTED_NO_METATRADER_RUNTIME","detail":"MT5 EA requires MetaTrader tester/runtime and broker-symbol contract mapping"})
    fields=sorted({k for x in rows for k in x})
    with (OUT/"strategy_results.csv").open("w",newline="") as f:
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    counts={}
    for x in rows:counts[x["status"]]=counts.get(x["status"],0)+1
    report={"period_utc":{"start":"2021-11-22","end":"2026-11-22"},"markets":PAIRS,"timeframes_downloaded":sorted(TF_OK),
      "harvested_source_files":len(manifest),"freqtrade_source_files":len(py),"pine_source_files":len(pine),"mql5_source_files":len(mql),
      "result_rows":len(rows),"status_counts":counts,
      "limitations":["A successful native Freqtrade run is a source execution attempt, not proof of profitability or semantic uniqueness.",
      "Pine and MQL5 are explicitly not claimed backtested; they require their native runtimes or separately parity-audited ports.",
      "Strategies with unsupported dependencies, incompatible APIs, missing futures support, or unavailable feeds are recorded as failures/not tested.",
      "Only 5m/15m/30m/1h/4h candle histories are provisioned; source-required order-book, liquidation, on-chain, options, or other feeds are not fabricated."]}
    Path(OUT/"summary.json").write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=="__main__":main()
