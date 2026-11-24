#!/usr/bin/env python3
"""Run source-faithful five-year Freqtrade tests for canonical direct-OHLCV candidates.
Only compatibility names are translated in an isolated temporary copy; source originals stay untouched.
"""
from __future__ import annotations
import ast, csv, json, re, shutil, subprocess, time, hashlib
from pathlib import Path

ROOT=Path.cwd(); HARVEST=ROOT/'source-harvest'; OUT=ROOT/'canonical-five-year-results'; TMP=Path('/tmp/realcheck-one-candidate')
START='20211122'; END='20261122'; PAIRS=['BTC/USDT:USDT','ETH/USDT:USDT']
TF_OK={'5m','15m','30m','1h','4h'}
OUT.mkdir(exist_ok=True)

def run(cmd,timeout=300):
    return subprocess.run(cmd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout)

def migrate_legacy_api(src: Path, dst: Path):
    text=src.read_text(encoding='utf-8',errors='replace')
    # Execution-copy-only Freqtrade API compatibility. No strategy rules or thresholds are changed.
    replacements={
      'populate_buy_trend':'populate_entry_trend',
      'populate_sell_trend':'populate_exit_trend',
      'use_sell_signal':'use_exit_signal',
      'sell_profit_only':'exit_profit_only',
      'sell_profit_offset':'exit_profit_offset',
      'ignore_roi_if_buy_signal':'ignore_roi_if_entry_signal',
    }
    for old,new in replacements.items(): text=text.replace(old,new)
    # Legacy signal dataframe column names in quoted literals only.
    text=re.sub(r'(["\'])buy\1', lambda m: m.group(1)+'enter_long'+m.group(1), text)
    text=re.sub(r'(["\'])sell\1', lambda m: m.group(1)+'exit_long'+m.group(1), text)
    dst.write_text(text,encoding='utf-8')

def strategy_classes(path):
    try: tree=ast.parse(path.read_text(encoding='utf-8',errors='replace'))
    except Exception as e: return [],f'AST_PARSE_ERROR: {e}'
    found=[]
    for node in tree.body:
      if not isinstance(node,ast.ClassDef): continue
      bases=[ast.unparse(b) for b in node.bases]
      if not any('IStrategy' in b for b in bases): continue
      methods={n.name for n in node.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
      entry='populate_entry_trend' if 'populate_entry_trend' in methods else ('populate_buy_trend' if 'populate_buy_trend' in methods else None)
      if entry: found.append((node.name,entry))
    return found,None

def write_csv(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='',encoding='utf-8') as f:
      w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def main():
    config={"dry_run":True,"strategy":"SampleStrategy","timeframe":"5m","trading_mode":"futures","margin_mode":"isolated",
      "stake_currency":"USDT","stake_amount":1000,"dry_run_wallet":10000,"tradable_balance_ratio":0.99,"max_open_trades":1,
      "exchange":{"name":"binance","key":"","secret":"","ccxt_config":{},"ccxt_async_config":{},"pair_whitelist":PAIRS,"pair_blacklist":[]},
      "pairlists":[{"method":"StaticPairList"}],"dataformat_ohlcv":"feather","dataformat_trades":"feather",
      "fee":0.0005,"unfilledtimeout":{"entry":10,"exit":10,"exit_timeout_count":0,"unit":"minutes"},
      "order_types":{"entry":"market","exit":"market","stoploss":"market","stoploss_on_exchange":False},
      "entry_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1},
      "exit_pricing":{"price_side":"other","use_order_book":False,"order_book_top":1}}
    Path('/tmp/config.json').write_text(json.dumps(config),encoding='utf-8')
    candidates=list(csv.DictReader((ROOT/'research/engine_audit/canonical_python_direct_candidates.csv').open(encoding='utf-8')))
    manifest={r['harvest_id']:r for r in csv.DictReader((HARVEST/'manifest.csv').open(encoding='utf-8'))}
    rows=[]
    for c in candidates:
      sid=c['source_id']; m=manifest.get(sid)
      if not m:
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':c['timeframe'],'status':'REJECTED_SOURCE_NOT_IN_HARVEST','detail':'No matching source manifest row'});continue
      original=ROOT/m['artifact_path']
      if not original.exists():
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':c['timeframe'],'status':'REJECTED_SOURCE_FILE_MISSING','detail':str(original)});continue
      actual=hashlib.sha256(original.read_bytes()).hexdigest()
      if actual != m['sha256']:
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':c['timeframe'],'status':'REJECTED_SOURCE_HASH_MISMATCH','detail':f'{actual} != {m["sha256"]}'});continue
      tf=c['timeframe']
      if tf not in TF_OK:
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':tf,'status':'NOT_TESTED_UNSUPPORTED_TIMEFRAME','detail':'No verified five-year candle dataset'});continue
      classes,err=strategy_classes(original)
      if err:
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':tf,'status':'REJECTED_SOURCE_PARSE_ERROR','detail':err});continue
      if not classes:
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'timeframe':tf,'status':'REJECTED_NO_ENTRY_IMPLEMENTATION','detail':'No concrete IStrategy class with entry method'});continue
      for cls,entry_method in classes:
        shutil.rmtree(TMP,ignore_errors=True);TMP.mkdir(parents=True)
        exec_src=TMP/original.name;migrate_legacy_api(original,exec_src)
        result_dir=OUT/'native_results'/f'{sid}_{cls}';result_dir.mkdir(parents=True,exist_ok=True)
        cmd=['python','research/engine_audit/offline_freqtrade_cli.py','backtesting','--config','/tmp/config.json','--strategy-path',str(TMP),'--strategy',cls,'--timeframe',tf,'--timerange',f'{START}-{END}','--export','trades','--backtest-directory',str(result_dir)]
        t0=time.time()
        try:
          p=run(cmd,timeout=300); result_files=sorted(result_dir.glob('*.json'),key=lambda q:q.stat().st_mtime,reverse=True); result_file=result_files[0] if result_files else None
          ok=p.returncode==0 and result_file is not None and result_file.stat().st_size>50
          status='BACKTESTED' if ok else 'FAILED'
          detail=p.stdout[-5000:].replace('\n',' | ')
          if ok:
            try:
              json.loads(result_file.read_text()); detail=f'Backtest JSON emitted: {result_file.name}'
            except Exception as e: status='FAILED_INVALID_RESULT';detail=f'Invalid result JSON: {e}; {detail}'
        except subprocess.TimeoutExpired:
          status='TIMEOUT';detail='Exceeded 300 seconds per strategy'
        rows.append({'engine_id':c['engine_id'],'source_id':sid,'class':cls,'timeframe':tf,'status':status,'seconds':round(time.time()-t0,1),'detail':detail,'source_sha256':actual,'execution_copy_compatibility_migration':True})
        write_csv(OUT/'progress.csv',rows)
    write_csv(OUT/'strategy_results.csv',rows)
    counts={}
    for r in rows:counts[r['status']]=counts.get(r['status'],0)+1
    summary={'date_range_utc':{'start':'2021-11-22','end':'2026-11-22'},'markets':PAIRS,'timeframes':sorted(TF_OK),'canonical_direct_ohlcv_candidates':len(candidates),'results':len(rows),'status_counts':counts,'compatibility_policy':'Only legacy Freqtrade API identifiers and legacy buy/sell signal column literals are renamed in isolated execution copies. Source originals and strategy thresholds are unchanged.','important':'BACKTESTED means native Freqtrade produced a parseable backtest result file. Profitability must be evaluated from trade/performance metrics; it is not implied by successful execution.'}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
