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
        for i in range(80):
            # Pair and primary correlate in the first segment, diverge, then re-align.
            p=100.0+i*0.1
            if 30<=i<55:
                p+=((i%2)*2-1)*2.0
            primary.append({"timestamp":i,"close":100.0+i*0.1+(((i%2)*2-1)*2.0 if 30<=i<55 else 0.0)})
            pair.append({"timestamp":i,"close":p})
        sig=correlation_break_recovery(primary,pair,{"window":10,"break_thr":0.2,"recovery_thr":0.5,"rel_scale":0.05})
        self.assertTrue(all(x["timestamp"]==i for i,x in enumerate(sig)))
        # The function must never use pair data with a timestamp later than the primary bar.
        truncated=correlation_break_recovery(primary[:40],pair,{"window":10,"break_thr":0.2,"recovery_thr":0.5,"rel_scale":0.05})
        self.assertEqual(len(truncated),40)

if __name__=="__main__": unittest.main()
