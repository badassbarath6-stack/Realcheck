import unittest
from research.engine_audit.specialist_signal_engines import (
    round_number_bounce, wall_pull_detector, book_imbalance_zscore, correlation_break_recovery
)

class SpecialistSignalEngineTests(unittest.TestCase):
    def test_round_number_support_bounce(self):
        rows=[
            {"timestamp":1,"close":100.0,"low":99.0,"high":101.0},
            {"timestamp":2,"close":101.5,"low":99.5,"high":102.0},
        ]
        sig=round_number_bounce(rows,{"level_step_frac":0.1,"touch_threshold":0.01})
        self.assertEqual(sig[-1]["direction"],1)
        resistance=[{"timestamp":3,"close":108.0,"low":107.0,"high":111.0}]
        exit_sig=round_number_bounce(resistance,{"level_step_frac":0.1,"touch_threshold":0.003})[0]
        self.assertEqual(exit_sig["direction"],0)
        self.assertTrue(exit_sig["exit_long"])

    def test_wall_pull_only_emits_on_event_edge(self):
        rows=[]
        for i in range(12):
            rows.append({"timestamp":i,"close":100.0,"offer_wall_price":100.05,
                "offer_wall_qty":100.0 if i<8 else 10.0,
                "bid_wall_price":99.95,"bid_wall_qty":100.0})
        sig=wall_pull_detector(rows,{"lookback":5,"pull_frac":0.3,"prox_frac":0.001})
        self.assertEqual(sig[8]["direction"],1)
        self.assertEqual(sum(x["direction"]==1 for x in sig),1)

    def test_book_imbalance_requires_warmup_and_is_signed(self):
        rows=[]
        for i in range(70):
            rows.append({"timestamp":i,"close":100.0,"bid_total":200.0 if i<65 else 400.0,
                         "offer_total":200.0 if i<65 else 100.0})
        sig=book_imbalance_zscore(rows,{"window":60,"max_z":2})
        self.assertEqual(sig[10]["direction"],0)
        self.assertEqual(sig[-1]["direction"],1)

    def test_correlation_break_recovery_is_point_in_time(self):
        primary=[]; pair=[]
        px=py=100.0
        for i in range(80):
            if i:
                pair_return=0.01 if i%2 else -0.01
                primary_return=pair_return if i<15 or i>=25 else -pair_return
                py*=1.0+pair_return
                px*=1.0+primary_return
            primary.append({"timestamp":i,"close":px})
            pair.append({"timestamp":i,"close":py})
        params={"window":3,"break_thr":0.0,"recovery_thr":0.5,"rel_scale":0.05}
        sig=correlation_break_recovery(primary,pair,params)
        self.assertTrue(any(x["direction"]!=0 for x in sig[25:]))
        # Future pair observations must not alter outputs before their timestamps.
        truncated=correlation_break_recovery(primary[:40],pair,params)
        matched=correlation_break_recovery(primary[:40],pair[:40],params)
        self.assertEqual(truncated,matched)

if __name__=="__main__": unittest.main()
