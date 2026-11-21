import unittest
from datetime import datetime, timezone
from research.engine_audit.source_backtest import (
    run_trades, walk_forward, validate_prefix_invariance
)

def make_bars(n, step_ms=3600000):
    rows=[]
    for i in range(n):
        price=100.0+i*0.01
        rows.append({"timestamp":i*step_ms,"close_timestamp":(i+1)*step_ms-1,
            "open":price,"high":price+0.2,"low":price-0.2,"close":price+0.05})
    return rows

class SourceBacktestTests(unittest.TestCase):
    def test_next_open_hold_exit_and_costs(self):
        bars=make_bars(6)
        sig=[{"direction":1}]+[{"direction":0} for _ in range(5)]
        trades=run_trades(bars,sig,hold_bars=2,fee_bps_per_side=5,
                          slippage_bps_per_side=2,fill_model="conservative")
        self.assertEqual(len(trades),1)
        self.assertEqual(trades[0]["entry_timestamp"],bars[1]["timestamp"])
        self.assertEqual(trades[0]["exit_timestamp"],bars[3]["timestamp"])
        self.assertEqual(trades[0]["exit_reason"],"hold")
        self.assertEqual(trades[0]["hold_actual"],2)
        self.assertEqual(trades[0]["commission_bps"],10.0)

    def test_stop_first_when_stop_and_target_hit_same_bar(self):
        bars=make_bars(5)
        bars[1].update({"open":100.0,"high":101.0,"low":99.0,"close":100.0})
        bars[2].update({"open":100.0,"high":105.0,"low":95.0,"close":100.0})
        sig=[{"direction":1}]+[{"direction":0} for _ in range(4)]
        trade=run_trades(bars,sig,hold_bars=3,sl_pct=.02,tp_pct=.04,
                         fee_bps_per_side=0,slippage_bps_per_side=0)[0]
        self.assertEqual(trade["exit_reason"],"stop")
        self.assertLess(trade["net_bps"],0)

    def test_conservative_gap_stop_is_worse_than_source_compatible_fill(self):
        bars=make_bars(5)
        bars[1].update({"open":100.0,"high":101.0,"low":99.0,"close":100.0})
        bars[2].update({"open":95.0,"high":96.0,"low":94.0,"close":95.0})
        sig=[{"direction":1}]+[{"direction":0} for _ in range(4)]
        source=run_trades(bars,sig,hold_bars=3,sl_pct=.02,tp_pct=.04,
            fee_bps_per_side=0,slippage_bps_per_side=0,fill_model="source_compatible")[0]
        conservative=run_trades(bars,sig,hold_bars=3,sl_pct=.02,tp_pct=.04,
            fee_bps_per_side=0,slippage_bps_per_side=2,fill_model="conservative")[0]
        self.assertEqual(source["exit_reason"],"stop")
        self.assertEqual(conservative["exit_reason"],"stop_gap")
        self.assertLess(conservative["net_bps"],source["net_bps"])

    def test_long_only_source_exit_closes_at_next_open(self):
        bars=make_bars(6)
        sig=[{"direction":1},{"direction":0},{"direction":0,"exit_long":True},
             {"direction":0},{"direction":0},{"direction":0}]
        trade=run_trades(bars,sig,hold_bars=5,sl_pct=.5,tp_pct=.5,
                         fee_bps_per_side=0,slippage_bps_per_side=0)[0]
        self.assertEqual(trade["exit_reason"],"signal_exit_long")
        self.assertEqual(trade["exit_timestamp"],bars[3]["timestamp"])
        self.assertEqual(trade["exit_time_precision"],"bar_open")

    def test_prefix_invariance_rejects_future_dependent_signal(self):
        bars=make_bars(20)
        def bad_signal(rows,params):
            return [{"direction":1 if i==len(rows)-1 else 0} for i,_ in enumerate(rows)]
        with self.assertRaisesRegex(ValueError,"look-ahead"):
            validate_prefix_invariance(bad_signal,bars,{})

    def test_walk_forward_uses_training_only_and_emits_oos_windows(self):
        start=int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp()*1000)
        bars=[]
        for i in range(18*31*24+48):
            ts=start+i*3600000
            p=100.0+i*0.01
            bars.append({"timestamp":ts,"open":p,"high":p+0.2,"low":p-0.2,
                         "close":p+0.05})
        def signals(rows,params):
            return [{"direction":1} for _ in rows]
        result=walk_forward(bars,signals,[{"hold_bars":1},{"hold_bars":2}],
            timeframe="1h",min_train_trades=1,fee_bps_per_side=1,
            slippage_bps_per_side=0,fill_model="source_compatible")
        self.assertGreaterEqual(result["summary"]["oos_windows"],5)
        self.assertGreater(result["summary"]["trades"],0)
        first_test=result["windows"][0]["test_start"]
        self.assertTrue(all(t["entry_timestamp"]>=first_test for t in result["trades"]))
        self.assertTrue(all("best_params" in w for w in result["windows"]))

if __name__=="__main__": unittest.main()
