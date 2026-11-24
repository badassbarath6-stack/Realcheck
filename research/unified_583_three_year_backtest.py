#!/usr/bin/env python3
"""Native-runtime screening of the 583-engine UEF registry across five crypto timeframes."""
import argparse, ast, csv, json, os, re, shutil, subprocess, sys, time
from pathlib import Path
from urllib.parse import urlparse
import pandas as pd

PY_RANGES="385,391-392,395,398-401,403-404,407-408,412,415-418,420-424,428,430,448,454-456,461,463-465,467-469,475,477-478,491-494,500-501,506-509,513-515,517-518,523-524,526,528,530,535,539-540,542-543,550,553,557,559-565,569,571,573,575,577-578,581-582,585,587,590,592,594-596,598-604,607,609,611,614-615,617-618,620-621,625-627,631-632,634,639-645,649-651,655-658,662-669,673-675,693-694,710-711,713,716-718,722,724,726-727,732-735,737-740,743-744,746,748,750-754,756,759-760,762,764,767-770,773-776,778-779,781-786,789-796,799-802,804-805,807-811"
PINE_RANGES="1-24,26,28-87,89-154,156-343,345-384"
TFS=["5m","15m","30m","1h","4h"]
START="20231124"; END="20261124"
DATA=Path("user_data/data/binance/futures")
SRC=Path("source-harvest/sources")
PC=Path("pynecore-strategies")
OUT=Path("three-year-results"); OUT.mkdir(exist_ok=True)

def expand(spec):
    out=set()
    for x in spec.split(","):
        if "-" in x:
            a,b=map(int,x.split("-")); out.update(range(a,b+1))
        else: out.add(int(x))
    return out
SELECTED={f"SRC{x:04d}" for x in expand(PY_RANGES+" ,"+PINE_RANGES)}

def pf(values):
    wins=sum(x for x in values if x>0); losses=abs(sum(x for x in values if x<0))
    return round(wins/losses,4) if losses else (None if wins==0 else 999.0)

def summarize(values):
    return {"trades":len(values),"profit_factor":pf(values),
            "win_rate_pct":round(100*sum(x>0 for x in values)/len(values),2) if values else 0,
            "net_profit":round(sum(values),8)}

def find_classes(path):
    try: tree=ast.parse(path.read_text(encoding="utf-8",errors="replace"))
    except Exception: return []
    names=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.ClassDef) and any("IStrategy" in ast.unparse(b) for b in n.bases):
            names.append(n.name)
    return names

def find_trades(obj):
    if isinstance(obj,dict):
        if isinstance(obj.get("trades"),list): return obj["trades"]
        for v in obj.values():
            x=find_trades(v)
            if x is not None:return x
    if isinstance(obj,list):
        for v in obj:
            x=find_trades(v)
            if x is not None:return x
    return []

def ft_run(row, cls, tf):
    src=Path(row["artifact_path"])
    if not src.exists(): raise FileNotFoundError(src)
    tmp=Path("/tmp/realcheck-one-strategy"); shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir(parents=True)
    shutil.copy2(src,tmp/src.name)
    cfg=Path("/tmp/realcheck-config.json")
    cfg.write_text(json.dumps({
      "dry_run":True,"strategy":cls,"timeframe":tf,"trading_mode":"futures","margin_mode":"isolated",
      "stake_currency":"USDT","stake_amount":1000,"dry_run_wallet":10000,"tradable_balance_ratio":0.99,
      "max_open_trades":2,"exchange":{"name":"binance","key":"","secret":"","pair_whitelist":["BTC/USDT:USDT","ETH/USDT:USDT"],"pair_blacklist":[]},
      "pairlists":[{"method":"StaticPairList"}],"dataformat_ohlcv":"feather","dataformat_trades":"feather","fee":0.0005,
      "unfilledtimeout":{"entry":10,"exit":10,"exit_timeout_count":0,"unit":"minutes"},
      "order_types":{"entry":"market","exit":"market","stoploss":"market","stoploss_on_exchange":False},
      "entry_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1},
      "exit_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1}
    }))
    dest=OUT/f"ft_{row['harvest_id']}_{cls}_{tf}.json"
    env=os.environ.copy(); env["PYTHONPATH"]=str(SRC.resolve())+os.pathsep+env.get("PYTHONPATH","")
    cmd=["freqtrade","backtesting","--config",str(cfg),"--strategy-path",str(tmp),"--strategy",cls,
         "--timeframe",tf,"--timerange",f"{START}-{END}","--export","trades","--export-filename",str(dest)]
    p=subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300,env=env)
    if p.returncode or not dest.exists(): return {"status":"FAILED","detail":p.stdout[-2500:]}
    obj=json.loads(dest.read_text()); trades=find_trades(obj)
    vals=[]
    for t in trades:
        v=t.get("profit_abs",t.get("profit_ratio",t.get("profit_pct",0)))
        try: vals.append(float(v))
        except Exception: pass
    return {"status":"BACKTESTED",**summarize(vals),"detail":p.stdout[-500:]}

def pine_run(row, tf, symbol):
    url=row.get("source_url","")
    stem=Path(urlparse(url).path).stem
    script=PC/"scripts"/f"strategy_{stem}.py"
    if not script.is_file(): raise FileNotFoundError(f"Compiled PyneCore script not found: {script}")
    f=DATA/f"{symbol}_USDT-{tf}-futures.feather"
    df=pd.read_feather(f); df["date"]=pd.to_datetime(df["date"],utc=True)
    from pynecore.core.script_runner import ScriptRunner
    from pynecore.core.syminfo import SymInfo
    from pynecore.types.ohlcv import OHLCV
    period={"5m":"5","15m":"15","30m":"30","1h":"60","4h":"240"}[tf]
    candles=[OHLCV(timestamp=int(x.date.timestamp()*1000),open=float(x.open),high=float(x.high),low=float(x.low),close=float(x.close),volume=float(x.volume)) for x in df.itertuples(index=False)]
    si=SymInfo(prefix="BINANCE",ticker=symbol,currency="USDT",basecurrency=symbol.replace("USDT",""),
      description="Binance USD-M perpetual",period=period,type="crypto",mintick=0.01,pricescale=100,minmove=1,
      pointvalue=1.0,timezone="UTC",volumetype="base",opening_hours=[],session_starts=[],session_ends=[])
    runner=ScriptRunner(script_path=script,ohlcv_iter=candles,syminfo=si,inputs={},security_data=None)
    closed=[]
    for item in runner.run_iter():
        if len(item)==3: closed.extend(item[2])
    vals=[]
    for t in closed:
        v=getattr(t,"profit",None)
        if v is None: v=getattr(t,"profit_percent",0)
        vals.append(float(v or 0))
    return {"status":"BACKTESTED","symbol":symbol,**summarize(vals),"detail":""}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--batch",type=int,required=True); ap.add_argument("--batches",type=int,default=12); a=ap.parse_args()
    rows=list(csv.DictReader((Path("source-harvest")/"manifest.csv").open()))
    selected=[r for r in rows if r["harvest_id"] in SELECTED]
    selected.sort(key=lambda r:int(r["harvest_id"][3:]))
    batch=[r for i,r in enumerate(selected) if i%a.batches==a.batch]
    results=[]; progress=OUT/f"batch_{a.batch:02d}.csv"
    def save():
        if results:
            keys=sorted({k for x in results for k in x})
            with progress.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(results)
    print(f"Selected {len(selected)} of 1000 harvest sources; batch {a.batch+1}/{a.batches}: {len(batch)} engines",flush=True)
    for row in batch:
        hid=row["harvest_id"]; lang=row["implementation_language"]
        if lang=="python":
            source=Path(row["artifact_path"]); classes=[row.get("class_name","").strip()] if row.get("class_name","").strip() else find_classes(source)
            if not classes: results.append({"engine_id":hid,"language":lang,"timeframe":"all","status":"REJECTED_NO_STRATEGY_CLASS"}); save(); continue
            for cls in classes:
                for tf in TFS:
                    base={"engine_id":hid,"engine_name":row.get("engine_name",""),"language":lang,"class":cls,"timeframe":tf}
                    try: results.append({**base,**ft_run(row,cls,tf)})
                    except Exception as e: results.append({**base,"status":"ERROR","detail":repr(e)[:2000]})
                    save()
        elif lang=="pine":
            for tf in TFS:
                for symbol in ("BTC","ETH"):
                    base={"engine_id":hid,"engine_name":Path(urlparse(row.get("source_url","")).path).stem,
                          "language":lang,"timeframe":tf,"symbol":symbol,"lookahead_on":row.get("lookahead_on","")}
                    if row.get("mtf_request")=="YES" or row.get("lower_tf_request")=="YES" or row.get("nonstandard_chart_source")=="YES" or row.get("external_fundamental_data")=="YES":
                        results.append({**base,"status":"NOT_RUN_REQUIRES_CONTEXT","detail":"Source requires mapped security/lower-timeframe/nonstandard/fundamental feed; not approximated"})
                    else:
                        try: results.append({**base,**pine_run(row,tf,symbol)})
                        except Exception as e: results.append({**base,"status":"ERROR","detail":repr(e)[:2000]})
                    save()
        else:
            results.append({"engine_id":hid,"language":lang,"status":"NOT_IN_ACTIVE_REGISTRY"})
            save()
    print(f"Batch {a.batch} finished: {len(results)} result rows",flush=True)

if __name__=="__main__": main()
