import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT=Path("research/engine_audit/prepare_metrics_features.py")
spec=importlib.util.spec_from_file_location("prepare_metrics",SCRIPT)
metrics=importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)

class MetricsPreparationTests(unittest.TestCase):
    def test_metrics_are_backward_asof_joined_without_future_fill(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            inp=root/"candles.csv"; met=root/"metrics.csv"; out=root/"merged.csv"
            with inp.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["timestamp","open","high","low","close"])
                w.writeheader()
                for ts in (50,150,250):
                    w.writerow({"timestamp":ts,"open":100,"high":101,"low":99,"close":100})
            with met.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["create_time","sum_open_interest","sum_taker_long_short_vol_ratio"])
                w.writeheader()
                w.writerow({"create_time":100,"sum_open_interest":1000,"sum_taker_long_short_vol_ratio":1.2})
                w.writerow({"create_time":200,"sum_open_interest":900,"sum_taker_long_short_vol_ratio":0.8})
            source=metrics.load_metrics([met])
            result=metrics.merge_metrics(inp,source,out)
            with out.open(newline="") as f: rows=list(csv.DictReader(f))
            self.assertEqual(rows[0]["open_interest"],"")
            self.assertEqual(rows[1]["open_interest"],"1000.0")
            self.assertEqual(rows[2]["open_interest"],"900.0")
            self.assertAlmostEqual(result["oi_coverage"],2/3)

if __name__=="__main__": unittest.main()
