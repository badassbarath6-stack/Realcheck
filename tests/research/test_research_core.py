import importlib.util, math, unittest, sys
from pathlib import Path
SPEC=importlib.util.spec_from_file_location("impulse_research",Path("research/impulse_retracer_backtest.py"))
M=importlib.util.module_from_spec(SPEC); sys.modules[SPEC.name]=M; SPEC.loader.exec_module(M)

class ResearchCoreTests(unittest.TestCase):
    def test_exact_grid(self):
        self.assertEqual(len(M.configurations()),5184)
        self.assertEqual(len(set(M.configurations())),5184)
    def test_wilder_atr_seed_and_recurrence(self):
        bars=[(i,10.,12.,9.,11.) for i in range(6)]
        a=M.atr_wilder(bars,3)
        self.assertTrue(math.isnan(a[1]))
        self.assertAlmostEqual(a[2],3.0)
        self.assertAlmostEqual(a[3],3.0)
    def test_resample_ohlc(self):
        rows=[(0,10,12,9,11),(60_000,11,13,10,12),(120_000,12,14,11,13)]
        got=M.resample_m1(rows,3)[0]
        self.assertEqual(got,(0,10,14,9,13,3))
    def test_metrics(self):
        m=M.metrics([{"net_bps":10},{"net_bps":-5},{"net_bps":5}])
        self.assertEqual(m["trades"],3); self.assertAlmostEqual(m["pf"],3.0)
        self.assertAlmostEqual(m["win_rate"],2/3)

if __name__=="__main__": unittest.main()
