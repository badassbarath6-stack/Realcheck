import importlib.util, math, sys, unittest
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
        rows=[(0,10,12,9,11),(60000,11,13,10,12),(120000,12,14,11,13)]
        self.assertEqual(M.resample_m1(rows,3)[0],(0,10,14,9,13,3))
    def test_metrics(self):
        m=M.score_metrics([{"net_bps":10},{"net_bps":-5},{"net_bps":5}])
        self.assertEqual(m["trades"],3); self.assertAlmostEqual(m["pf"],3.0)
        self.assertAlmostEqual(m["win_rate"],2/3)
    def test_trade_checks_entry_bar_and_stop_first(self):
        m1=[(0,100,101,99,100),(60000,100,111,94,100),(120000,100,101,99,100)]
        trade=M._trade_for_setup(m1,1,1,100,95,110,2)
        self.assertEqual(trade["reason"],"stop")
        self.assertAlmostEqual(trade["net_bps"],-514.0)
    def test_target_exit(self):
        m1=[(0,100,101,99,100),(60000,100,105,99,103),(120000,103,111,102,110)]
        trade=M._trade_for_setup(m1,1,1,100,90,110,2)
        self.assertEqual(trade["reason"],"target")
    def test_month_archive_coverage(self):
        months=M.month_files()
        self.assertEqual(months[0],(2024,10)); self.assertEqual(months[-1],(2026,10))

if __name__=="__main__": unittest.main()
