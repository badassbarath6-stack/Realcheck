#!/usr/bin/env python3
"""Single dispatcher for the first ten Realcheck engines.

The source strategies remain unchanged in the pinned UEF source package.
This file coordinates them, applies a fail-closed minimum-target-distance
eligibility gate, and exposes a common interface for backtesting/live signals.

IMPORTANT: current UEF adapters return closed-trade events for some source
runtimes. A valid pre-entry 8-pip backtest requires adapters to expose each
candidate's native planned target BEFORE entry. This module deliberately refuses
to substitute a realised exit price for a planned target (that would be lookahead).
"""
from __future__ import annotations
import argparse, json, os, sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Mapping

SYSTEM_VERSION = "1.0.0"
MIN_TARGET_PIPS = 8.0
DEFAULT_PIP_SIZES = {"BTCUSDT": 1.0, "ETHUSDT": 0.1}  # project convention, not exchange-defined
DEFAULT_COST_BPS_PER_SIDE = 10.0  # 7.5 bps fee + 2.5 bps adverse slippage

# Original source IDs and names retained. No source strategy logic is rewritten.
ENGINES = (
 {"source_id":"SRC0540","engine_id":"PY_0106","name":"IchiV1","runtime":"freqtrade_python","source_file":"sources/python/PY_0106.py","preliminary_stress_pf":7.573245,"status":"research_only_until_source_equivalent_replay"},
 {"source_id":"SRC0367","engine_id":"PINE_0362","name":"VoVix DEVMA","runtime":"pynecore_pine","source_file":"sources/pine/PINE_0362.pine","preliminary_stress_pf":0.335624,"status":"research_only_fee_audit_below_1_30"},
 {"source_id":"SRC0151","engine_id":"PINE_0148","name":"Hybrid RSI Breakout","runtime":"pynecore_pine","source_file":"sources/pine/PINE_0148.pine","preliminary_stress_pf":0.483936,"status":"research_only_fee_audit_below_1_30"},
 {"source_id":"SRC0383","engine_id":"PINE_0378","name":"Zendog V3 DCA","runtime":"pynecore_pine","source_file":"sources/pine/PINE_0378.pine","preliminary_stress_pf":4.626931,"status":"research_only_dca_tail_risk_review"},
 {"source_id":"SRC0399","engine_id":"PY_0067","name":"BBRSITV","runtime":"freqtrade_python","source_file":"sources/python/PY_0067.py","preliminary_stress_pf":2.833163,"status":"research_only_small_sample_review"},
 {"source_id":"SRC0748","engine_id":"PY_0061","name":"Zeus","runtime":"freqtrade_python","source_file":"sources/python/PY_0061.py","preliminary_stress_pf":2.477103,"status":"research_only_until_source_equivalent_replay"},
 {"source_id":"SRC0581","engine_id":"PY_0119","name":"NASOSv4","runtime":"freqtrade_python","source_file":"sources/python/PY_0119.py","preliminary_stress_pf":1.691902,"status":"research_only_small_sample_review"},
 {"source_id":"SRC0632","engine_id":"PY_0145","name":"NotAnotherSMAOffset","runtime":"freqtrade_python","source_file":"sources/python/PY_0145.py","preliminary_stress_pf":1.157235,"status":"research_only_fee_audit_below_1_30"},
 {"source_id":"SRC0008","engine_id":"PINE_0008","name":"3Commas DCA","runtime":"pynecore_pine","source_file":"sources/pine/PINE_0008.pine","preliminary_stress_pf":1.539568,"status":"research_only_dca_tail_risk_review"},
 {"source_id":"SRC0156","engine_id":"PINE_0152","name":"ICT Entry V2","runtime":"pynecore_pine","source_file":"sources/pine/PINE_0152.pine","preliminary_stress_pf":0.581886,"status":"research_only_fee_audit_below_1_30"},
)

@dataclass(frozen=True)
class GateResult:
 eligible: bool
 gross_target_pips: float
 estimated_round_trip_cost_pips: float
 net_target_pips: float
 minimum_target_pips: float
 reason: str

class MissingNativeTargetError(ValueError): pass

def pip_size(symbol: str, overrides: Mapping[str,float] | None = None) -> float:
 key=symbol.upper(); raw=(overrides or {}).get(key,DEFAULT_PIP_SIZES.get(key))
 if raw is None or float(raw)<=0: raise ValueError(f"No pip-size convention configured for {key}; refusing to guess")
 return float(raw)

def minimum_target_gate(*,symbol:str,side:str,entry_price:float,native_target_price:float,
 minimum_pips:float=MIN_TARGET_PIPS,pip_sizes:Mapping[str,float]|None=None,
 cost_bps_per_side:float=DEFAULT_COST_BPS_PER_SIDE)->GateResult:
 if side not in {"LONG","SHORT"}: raise ValueError("side must be LONG or SHORT")
 if entry_price<=0 or native_target_price<=0: raise ValueError("entry and target prices must be positive")
 psize=pip_size(symbol,pip_sizes)
 move=native_target_price-entry_price if side=="LONG" else entry_price-native_target_price
 if move<=0: return GateResult(False,0.0,0.0,0.0,minimum_pips,"TARGET_NOT_IN_TRADE_DIRECTION")
 gross=move/psize; cost_price=entry_price*2.0*cost_bps_per_side/10000.0
 cost_pips=cost_price/psize; net=gross-cost_pips
 return GateResult(net>=minimum_pips,gross,cost_pips,net,minimum_pips,"PASS" if net>=minimum_pips else "NET_TARGET_BELOW_MINIMUM")

def load_uef_factory(uef_root:str|Path):
 root=Path(uef_root).expanduser().resolve()
 if not (root/"engine_factory.py").is_file(): raise FileNotFoundError(f"UEF_ROOT must contain engine_factory.py: {root}")
 sys.path.insert(0,str(root))
 from engine_factory import create_engine
 return create_engine,root

def run_all_engines(ohlcv,*,uef_root:str|Path,syminfo:Mapping[str,Any]|None=None,
 engine_inputs:Mapping[str,Mapping[str,Any]]|None=None,context:Mapping[str,Any]|None=None):
 """Run all ten unchanged source strategies on the same OHLCV sample."""
 create_engine,root=load_uef_factory(uef_root); outputs={}; failures={}
 for spec in ENGINES:
  try:
   engine=create_engine(spec["engine_id"],syminfo=syminfo,inputs=(engine_inputs or {}).get(spec["engine_id"]))
   outputs[spec["name"]]=engine.evaluate(ohlcv,context=context)
  except Exception as exc: failures[spec["name"]]=f"{type(exc).__name__}: {exc}"
 return {"version":SYSTEM_VERSION,"outputs":outputs,"failures":failures,"engine_count":len(ENGINES),"uef_root":str(root)}

def filter_native_candidates(candidates,*,symbol:str,pip_sizes:Mapping[str,float]|None=None,
 minimum_pips:float=MIN_TARGET_PIPS,cost_bps_per_side:float=DEFAULT_COST_BPS_PER_SIDE):
 """Filter candidate rows using native target BEFORE entry; never use realised exits."""
 required={"side","entry_price","native_target_price"}; missing=required.difference(candidates.columns)
 if missing: raise MissingNativeTargetError("Valid pre-entry minimum-pip replay requires native_target_price, entry_price and side; missing "+str(sorted(missing)))
 rows=[]
 for row in candidates.to_dict("records"):
  result=minimum_target_gate(symbol=symbol,side=str(row["side"]).upper(),entry_price=float(row["entry_price"]),
   native_target_price=float(row["native_target_price"]),minimum_pips=minimum_pips,pip_sizes=pip_sizes,cost_bps_per_side=cost_bps_per_side)
  rows.append({**row,**asdict(result)})
 import pandas as pd
 return pd.DataFrame(rows)

def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("--list",action="store_true")
 p.add_argument("--uef-root",default=os.environ.get("UEF_ROOT")); a=p.parse_args()
 if a.list:
  print(json.dumps({"version":SYSTEM_VERSION,"minimum_target_pips":MIN_TARGET_PIPS,"pip_sizes":DEFAULT_PIP_SIZES,"engines":ENGINES},indent=2)); return
 if not a.uef_root: p.error("Set --uef-root or UEF_ROOT to the pinned unified_engine_conversion package")
 p.error("Supply OHLCV through the Python API; CLI market-data backtesting is not enabled")

if __name__=="__main__": main()
