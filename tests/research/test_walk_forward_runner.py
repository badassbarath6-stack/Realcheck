import importlib.util
import unittest
from pathlib import Path
from research.engine_audit.source_backtest import validate_prefix_invariance

PATH=Path("research/engine_audit/run_walk_forward.py")
spec=importlib.util.spec_from_file_location("audit_wf_runner",PATH)
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

def bars(n=140):
    out=[]
    for i in range(n):
        c=100+i*.02
        out.append({"timestamp":i*900000,"open":c,"high":c+.5,"low":c-.5,"close":c,
            "volume":100.0,"buy_ratio":.65,"funding_rate":.0007,
            "open_interest":1000+i,"taker_ls_vol_ratio":1.1})
    return out

class WalkForwardRunnerTests(unittest.TestCase):
    def test_source_parameter_grids_and_native_timeframes(self):
        tf,g,fn,req=runner.strategy_spec("funding_mr")
        self.assertEqual(tf,"15m"); self.assertEqual(len(g),81)
        self.assertEqual(set(req),{"funding_rate","buy_ratio"})
        tf,g,fn,req=runner.strategy_spec("taker_momentum")
        self.assertEqual(tf,"5m"); self.assertEqual(len(g),108)
        self.assertTrue(all(p["tp_pct"]>p["sl_pct"] for p in g))
        tf,g,fn,req=runner.strategy_spec("oi_divergence")
        self.assertEqual(tf,"15m"); self.assertEqual(len(g),216)

    def test_imported_source_signal_wrappers_are_prefix_causal(self):
        d=bars()
        for name in ("funding_mr","taker_momentum","oi_divergence"):
            _,grid,fn,_=runner.strategy_spec(name)
            validate_prefix_invariance(fn,d,grid[0])

if __name__=="__main__": unittest.main()
