import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

RUNNER_PATH=Path("research/engine_audit/run_csv_backtest.py")
spec=importlib.util.spec_from_file_location("audit_csv_runner",RUNNER_PATH)
runner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)

class AuditRunnerTests(unittest.TestCase):
    def test_all_promoted_directional_engines_are_available(self):
        self.assertEqual(set(runner.ENGINES), {
            "funding_rate_mean_reversion",
            "taker_buy_pressure_momentum",
            "rsi_pivot_divergence",
            "volume_range_exhaustion",
        })

    def test_csv_loader_preserves_taker_volume_and_features(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bars.csv"
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=[
                    "timestamp","open","high","low","close","volume",
                    "taker_buy_base_volume","funding_rate","buy_ratio"])
                w.writeheader()
                w.writerow({"timestamp":1,"open":100,"high":101,"low":99,"close":100,
                    "volume":50,"taker_buy_base_volume":30,"funding_rate":0.0002,"buy_ratio":0.6})
                w.writerow({"timestamp":2,"open":100,"high":102,"low":99,"close":101,
                    "volume":60,"taker_buy_base_volume":36,"funding_rate":0.0002,"buy_ratio":0.6})
            rows=runner.load_rows(p)
            self.assertEqual(rows[0]["volume"],50.0)
            self.assertEqual(rows[0]["buy_ratio"],0.6)
            self.assertEqual(rows[0]["funding_rate"],0.0002)

    def test_non_monotonic_timestamp_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"bars.csv"
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["timestamp","open","high","low","close"])
                w.writeheader()
                for ts in (2,1):
                    w.writerow({"timestamp":ts,"open":100,"high":101,"low":99,"close":100})
            with self.assertRaises(ValueError):
                runner.load_rows(p)

if __name__=="__main__": unittest.main()
