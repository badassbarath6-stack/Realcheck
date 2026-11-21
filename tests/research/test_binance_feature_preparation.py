import csv
import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT=Path("research/engine_audit/prepare_binance_feature_csv.py")
spec=importlib.util.spec_from_file_location("prepare_binance_features",SCRIPT)
prep=importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)

class BinanceFeaturePreparationTests(unittest.TestCase):
    def test_funding_is_backward_asof_joined_at_resampled_bar_open(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); kd=root/"klines"; fd=root/"funding"; kd.mkdir(); fd.mkdir()
            zp=kd/"m1.zip"
            with zipfile.ZipFile(zp,"w") as z:
                lines=[]
                for i in range(4):
                    op=i*60000; cl=op+59999
                    lines.append(",".join(map(str,[op,100,101,99,100,50,cl,5000,10,30,3000,0])))
                z.writestr("m1.csv","\n".join(lines)+"\n")
            with (fd/"funding.csv").open("w",newline="") as f:
                w=csv.writer(f); w.writerow(["fundingTime","fundingRate"])
                w.writerow([50000,0.0002]); w.writerow([150000,-0.0001])
            klines=prep.load_klines([zp])
            funding=prep.load_funding([fd/"funding.csv"])
            out=root/"features.csv"
            stats=prep.build_feature_csv(klines,funding,out)
            with out.open(newline="") as f: rows=list(csv.DictReader(f))
            self.assertEqual(stats["bars"],4)
            self.assertAlmostEqual(float(rows[0]["buy_ratio"]),0.6)
            self.assertAlmostEqual(float(rows[0]["funding_rate"]),0.0)
            self.assertAlmostEqual(float(rows[1]["funding_rate"]),0.0002)
            self.assertAlmostEqual(float(rows[2]["funding_rate"]),0.0002)
            self.assertAlmostEqual(float(rows[3]["funding_rate"]),-0.0001)
            self.assertEqual(rows[0]["funding_age_ms"],"")
            self.assertEqual(int(rows[1]["funding_age_ms"]),10000)
            self.assertEqual(int(rows[0]["close_timestamp"]),59999)

    def test_5m_resample_sums_taker_volume_and_joins_funding_at_bucket_open(self):
        klines=[]
        for i in range(10):
            op=i*60000; close=op+59999; price=100.0+i
            klines.append((op,close,price,price+1,price-1,price+0.5,10.0,6.0))
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"five.csv"
            prep.build_feature_csv(klines,[(180000,0.0003)],out,timeframe_minutes=5)
            with out.open(newline="") as f: rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),2)
            self.assertEqual(float(rows[0]["volume"]),50.0)
            self.assertEqual(float(rows[0]["taker_buy_base_volume"]),30.0)
            self.assertAlmostEqual(float(rows[0]["buy_ratio"]),0.6)
            self.assertEqual(float(rows[0]["funding_rate"]),0.0)
            self.assertAlmostEqual(float(rows[1]["funding_rate"]),0.0003)

    def test_m1_gap_fails_closed(self):
        rows=[
            (0,59999,100.,101.,99.,100.,10.,5.),
            (120000,179999,100.,101.,99.,100.,10.,5.),
        ]
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"continuity"):
                prep.build_feature_csv(rows,[],Path(d)/"out.csv")

if __name__=="__main__": unittest.main()
