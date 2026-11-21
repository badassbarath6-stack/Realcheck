import importlib.util
import unittest
from pathlib import Path
ROOT=Path("research/engine_audit")
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
E=load("audit_engines","engines.py"); A=load("audit_adapter","adapter.py")
def bars(n=130):
    out=[]
    for i in range(n):
        c=100+0.01*i
        out.append({"timestamp":i*300000,"open":c-0.01,"high":c+0.3,"low":c-0.3,"close":c,
            "buy_ratio":0.5,"funding_rate":0.0,"open_interest":1000.0,"taker_ls_vol_ratio":1.0,
            "realized_vol_30d":0.5})
    return out
class AuditedEngineTests(unittest.TestCase):
    def test_funding_fade_lag_and_warmup(self):
        d=bars(80)
        for i,r in enumerate(d):
            if i>=20:
                r["close"]=100-i*0.1; r["open"]=r["close"]-0.01
                r["high"]=r["close"]+0.3; r["low"]=r["close"]-0.3
                r["funding_rate"]=-0.001; r["buy_ratio"]=0.60
        s=E.funding_rate_mean_reversion(d,ema_period=10)
        self.assertTrue(all(x["direction"]==0 for x in s[:11])); self.assertEqual(s[-1]["direction"],1)
        clean=bars(80); clean[-1]["funding_rate"]=-0.01
        self.assertEqual(E.funding_rate_mean_reversion(clean,ema_period=10)[-1]["direction"],0)
    def test_taker_pressure_long_short(self):
        d=bars()
        for r in d: r["buy_ratio"]=0.70
        self.assertEqual(E.taker_buy_pressure_momentum(d,ma_period=10,confirm_bars=3,atr_period=10)[-1]["direction"],1)
        for r in d: r["buy_ratio"]=0.30
        self.assertEqual(E.taker_buy_pressure_momentum(d,ma_period=10,confirm_bars=3,atr_period=10)[-1]["direction"],-1)
    def test_oi_reversal_is_labelled_hypothesis(self):
        d=bars(20); d[-14]["close"]=100.; d[-14]["open_interest"]=1000.; d[-2]["close"]=99.; d[-2]["open_interest"]=900.
        s=E.oi_price_quadrants(d,lookback_bars=12,price_threshold=.005,oi_threshold=.01)[-1]
        self.assertEqual(s["direction"],1); self.assertIn("hypothesis",s["interpretation"])
        # Mutating the signal bar itself must not change its lagged OI/price quadrant.
        d[-1]["close"]=1000.; d[-1]["open_interest"]=5000.
        s2=E.oi_price_quadrants(d,lookback_bars=12,price_threshold=.005,oi_threshold=.01)[-1]
        self.assertEqual((s2["direction"],s2["regime"]),(s["direction"],s["regime"]))
    def test_carry_is_matched_hedge(self):
        s=E.spot_perp_funding_carry([{"timestamp":1,"funding_rate":.0002}])[0]
        self.assertTrue(s["active"]); self.assertEqual((s["spot_weight"],s["perp_weight"]),(1.,-1.))
    def test_as_inventory_and_funding_skew(self):
        n=E.avellaneda_stoikov_quotes(mid=100,inventory=0,funding_rate=0,variance_over_horizon=1,book_imbalance=0)
        t=E.avellaneda_stoikov_quotes(mid=100,inventory=.5,funding_rate=.001,variance_over_horizon=1,book_imbalance=0)
        self.assertLess(t["reservation_price"],n["reservation_price"]); self.assertTrue(t["allow_bid"])
        c=E.avellaneda_stoikov_quotes(mid=100,inventory=1.2,funding_rate=0,variance_over_horizon=1,book_imbalance=0)
        self.assertFalse(c["allow_bid"])
    def test_delivery_basis_costs(self):
        x=E.delivery_basis_economics(spot_mid=30000,futures_mark=33000,days_to_expiry=90,borrow_apr=.06)
        self.assertTrue(x["eligible"]); self.assertLess(x["net_annualized"],x["annualized_basis"])
        y=E.delivery_basis_economics(spot_mid=30000,futures_mark=30000,days_to_expiry=90,borrow_apr=.06)
        self.assertFalse(y["eligible"])
    def test_adapter_next_bar_and_stop_first(self):
        d=bars(4); d[1].update({"open":100,"high":110,"low":90,"close":100})
        def signal(rows): return [{"direction":1} for _ in rows]
        t=A.run_directional_signals(d,signal,stop_fraction=.05,target_r=2)
        self.assertEqual(t[0]["entry_timestamp"],d[1]["timestamp"]); self.assertEqual(t[0]["exit_reason"],"stop")
        self.assertAlmostEqual(t[0]["net_bps"],-514.)
    def test_adapter_one_position_at_a_time(self):
        d=bars(8)
        def signal(rows): return [{"direction":1} for _ in rows]
        self.assertEqual(len(A.run_directional_signals(d,signal)),1)
    def test_only_passed_directional_engines_are_registered(self):
        import sys
        sys.path.insert(0, str(ROOT))
        import registry
        self.assertEqual(set(registry.DIRECTIONAL_ENGINES), {
            "funding_rate_mean_reversion", "taker_buy_pressure_momentum"})
        self.assertIn("oi_price_quadrants", registry.CONDITIONAL_NOT_PROMOTED)

if __name__=="__main__": unittest.main()
