import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"backtest"))
import top100_five_year_h1_m1 as bt

class BacktestSemanticsTests(unittest.TestCase):
    def setUp(self):
        self.m1=(
            np.array([0,60_000,120_000],dtype=np.int64),
            np.array([100.,100.,100.]),
            np.array([101.,121.,110.]),
            np.array([99.,99.,99.]),
            np.array([100.,120.,108.])
        )
    def test_first_touch_alerts_on_completed_minute_and_fills_next_open(self):
        setup={"symbol":"BTCUSDT","configId":"IR-T001","rank":1,"side":1,
            "impulseOpenTime":0,"detectedAt":0,"stop":90.,"level":95.}
        ts,o,h,l,c=self.m1
        l[0]=94.
        hit=bt.first_entry(setup,self.m1,180_000)
        self.assertEqual(hit["triggerIdx"],0)
        self.assertEqual(hit["fillIdx"],1)
        self.assertEqual(hit["entryTime"],60_000)
    def test_stop_touch_in_same_minute_rejects_entry(self):
        setup={"symbol":"BTCUSDT","configId":"IR-T001","rank":1,"side":1,
            "impulseOpenTime":0,"detectedAt":0,"stop":90.,"level":95.}
        self.m1[3][0]=89.
        self.assertIsNone(bt.first_entry(setup,self.m1,180_000))
    def test_fill_uses_next_minute_open_and_two_r_target(self):
        candidate={"symbol":"BTCUSDT","configId":"IR-T001","rank":1,"side":1,
            "fillIdx":1,"triggerIdx":0,"triggerMinute":0,"alertTime":60_000,
            "entryTime":60_000,"impulseOpenTime":0,"detectedAt":0,"stop":90.}
        empty_funding=(np.array([],dtype=np.int64),np.array([0.]))
        row=bt.simulate(candidate,self.m1,empty_funding,2.0,180_000)
        self.assertEqual(row["reason"],"TARGET")
        self.assertAlmostEqual(row["entry"],100.02,places=5)
        self.assertAlmostEqual(row["target"],120.06,places=2)
    def test_stop_wins_if_stop_and_target_touch_same_minute(self):
        candidate={"symbol":"BTCUSDT","configId":"IR-T001","rank":1,"side":1,
            "fillIdx":1,"triggerIdx":0,"triggerMinute":0,"alertTime":60_000,
            "entryTime":60_000,"impulseOpenTime":0,"detectedAt":0,"stop":90.}
        self.m1[3][1]=89.
        empty_funding=(np.array([],dtype=np.int64),np.array([0.]))
        row=bt.simulate(candidate,self.m1,empty_funding,2.0,180_000)
        self.assertEqual(row["reason"],"STOP")
    def test_pf_compares_only_configs_triggering_on_earliest_same_minute(self):
        def c(cid,rank,minute):
            return {"symbol":"BTCUSDT","configId":cid,"rank":rank,"impulseOpenTime":0,"triggerMinute":minute}
        candidates=[c("IR-T001",1,60_000),c("IR-T002",2,60_000),c("IR-T003",3,120_000)]
        selected,skipped=bt.select_alerts(candidates,{
            "IR-T001":{"profitFactor":1.3,"trades":100},
            "IR-T002":{"profitFactor":1.8,"trades":80},
            "IR-T003":{"profitFactor":3.0,"trades":200}
        })
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]["configId"],"IR-T002")
        self.assertEqual(skipped,[])
    def test_exactly_one_config_does_not_require_pf(self):
        candidate={"symbol":"ETHUSDT","configId":"IR-T050","rank":50,"impulseOpenTime":0,"triggerMinute":60_000}
        selected,skipped=bt.select_alerts([candidate],{})
        self.assertEqual(selected,[candidate])
        self.assertEqual(skipped,[])
    def test_source_contains_exact_100_approved_rows(self):
        cfg=bt.load_configs()
        self.assertEqual(len(cfg),100)
        self.assertEqual([x["rank"] for x in cfg],list(range(1,101)))

if __name__=="__main__":
    unittest.main()
