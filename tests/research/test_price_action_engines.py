import unittest
from research.engine_audit.price_action_engines import rsi_pivot_divergence, volume_range_exhaustion

class PriceActionEngineTests(unittest.TestCase):
    def test_exhaustion_needs_both_volume_and_range_cooling(self):
        rows=[]
        prices=[100,100,100,100,100,100,100,100,100,90,85,80,78,77,76,75,74,73]
        for i,c in enumerate(prices):
            rows.append({"timestamp":i,"open":c,"high":c+0.5,"low":c-0.5,"close":c,
                         "volume":100 if i<13 else 10})
        # Small final ranges and lower volume complete the cooling condition.
        for r in rows[11:]:
            r["high"]=r["close"]+0.05; r["low"]=r["close"]-0.05
        sig=volume_range_exhaustion(rows,{"lookback":5,"roc_threshold":0.05,"vol_fast":2,"vol_slow":5})
        self.assertTrue(any(x["direction"]==1 for x in sig))

    def test_exhaustion_rejects_missing_volume(self):
        rows=[{"timestamp":i,"high":2.,"low":1.,"close":1.5} for i in range(20)]
        with self.assertRaises(ValueError):
            volume_range_exhaustion(rows)

    def test_divergence_signals_only_after_pivot_confirmation(self):
        # Two troughs: second lower price low but RSI is higher due weaker momentum.
        closes=[100,98,96,94,92,90,92,94,96,95,93,91,89,91,93,95,97,99]
        rows=[{"timestamp":i,"high":c+0.5,"low":c-0.5,"close":c} for i,c in enumerate(closes)]
        sig=rsi_pivot_divergence(rows,{"rsi_period":3,"pivot_order":2,"max_pivot_gap":12})
        self.assertTrue(all(x["direction"]==0 for x in sig[:8]))
        self.assertTrue(any(x["direction"]==1 for x in sig[8:]))

if __name__=="__main__": unittest.main()
