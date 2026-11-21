import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "audited_strategies", Path("research/engine-audit/strategies.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class AuditedStrategyTests(unittest.TestCase):
    def test_funding_fade_requires_lagged_extreme(self):
        rows = []
        for i in range(65):
            rows.append({"timestamp": i, "close": 120.0-i*0.4,
                         "funding_rate": -0.001, "buy_ratio": 0.7})
        out = M.funding_rate_fade(rows)
        self.assertEqual(out[-1]["signal"], 1)
        self.assertEqual(out[-1]["execution_rule"], "next_bar_open")

    def test_funding_fade_does_not_use_current_funding(self):
        rows = [{"timestamp": i, "close": 120.0-i*0.4,
                 "funding_rate": 0.0, "buy_ratio": 0.7} for i in range(65)]
        rows[-1]["funding_rate"] = -0.01
        out = M.funding_rate_fade(rows)
        self.assertEqual(out[-1]["signal"], 0)

    def test_taker_pressure_lagged_flow_and_warmup(self):
        rows = []
        for i in range(100):
            rows.append({"timestamp": i, "open": 100, "high": 102,
                         "low": 98, "close": 101+i*0.1, "buy_ratio": 0.8})
        out = M.taker_buy_pressure_momentum(rows)
        self.assertEqual(out[0]["signal"], 0)
        self.assertEqual(out[-1]["signal"], 1)

    def test_oi_quadrant_continuation(self):
        rows = []
        for i in range(30):
            rows.append({"timestamp": i, "close": 100+i*1.0,
                         "open_interest": 1000+i*20,
                         "taker_ls_vol_ratio": 1.2})
        out = M.oi_price_quadrants(rows, {"lookback_bars": 3,
                                         "price_thresh": 0.005,
                                         "oi_thresh": 0.01})
        self.assertEqual(out[-1]["quadrant"], "price_up_oi_up")
        self.assertEqual(out[-1]["signal"], 1)
        self.assertIn("does not identify", out[-1]["interpretation_warning"])

    def test_missing_inputs_do_not_create_signals(self):
        rows = [{"timestamp": i, "close": 100+i, "high": 101+i,
                 "low": 99+i, "buy_ratio": None, "funding_rate": None}
                for i in range(70)]
        self.assertTrue(all(x["signal"] == 0 for x in M.funding_rate_fade(rows)))
        self.assertTrue(all(x["signal"] == 0 for x in M.taker_buy_pressure_momentum(rows)))


if __name__ == "__main__":
    unittest.main()
