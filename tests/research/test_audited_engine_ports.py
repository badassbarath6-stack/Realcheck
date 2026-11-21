import unittest
from research.engine_audit.bar_signal_engines import (
    funding_rate_mean_reversion,
    taker_buy_pressure_momentum,
    oi_price_divergence,
    spot_perp_funding_carry,
)

class AuditedEnginePortTests(unittest.TestCase):
    def rows(self, n=100, **extra):
        out=[]
        for i in range(n):
            row={"timestamp":i*60_000,"close":100.0+i*0.1,"high":101.0+i*0.1,"low":99.0+i*0.1}
            row.update({k:(v[i] if isinstance(v,list) else v) for k,v in extra.items()})
            out.append(row)
        return out

    def test_funding_fade_is_lagged_and_directional(self):
        n=80
        rows=self.rows(n, funding_rate=[-0.001]*n, buy_ratio=[0.6]*n)
        # Falling closes put price below prior EMA; all features are available.
        for i,r in enumerate(rows):
            r["close"]=200.0-i*0.2; r["high"]=r["close"]+0.5; r["low"]=r["close"]-0.5
        sig=funding_rate_mean_reversion(rows,{"ema_period":10})
        self.assertTrue(any(x==1 for x in sig))
        self.assertEqual(sig[:11],[0]*11)

    def test_taker_pressure_requires_warmup_and_flow_fields(self):
        n=120
        rows=self.rows(n,buy_ratio=[0.8]*n)
        sig=taker_buy_pressure_momentum(rows,{"ma_period":5,"confirm_bars":2,"atr_period":5})
        self.assertEqual(sig[:53],[0]*53)
        self.assertTrue(any(x==1 for x in sig))

    def test_oi_quadrants_are_explicitly_opt_in(self):
        n=40
        rows=self.rows(n,open_interest=[100.0+i*2 for i in range(n)],taker_ls_vol_ratio=[1.2]*n)
        sig=oi_price_divergence(rows,{"lookback_bars":3,"price_thresh":0.001,"oi_thresh":0.001,"use_mr":0})
        self.assertTrue(any(x==1 for x in sig))

    def test_carry_is_binary_and_not_a_directional_short(self):
        rows=[{"timestamp":1,"funding_rate":0.0002},{"timestamp":2,"funding_rate":-0.0001}]
        self.assertEqual(spot_perp_funding_carry(rows),[1,0])

    def test_invalid_timestamp_order_rejected(self):
        rows=self.rows(3)
        rows[2]["timestamp"]=rows[1]["timestamp"]
        with self.assertRaises(ValueError):
            funding_rate_mean_reversion(rows)

if __name__=="__main__":
    unittest.main()
