import unittest
import numpy as np
import pandas as pd
from eurjpy_sniper.backtest_v2 import backtest_v2_pair, CONFIGS

class V2ResearchTests(unittest.TestCase):
    def test_config_grid_has_three_distinct_horizons(self):
        self.assertEqual([c["hold"] for c in CONFIGS],[5,10,15])
    def test_v2_returns_all_configs_without_lookahead_error(self):
        n=1800
        idx=pd.date_range(end=pd.Timestamp.now(tz="UTC").floor("min"),periods=n,freq="min")
        close=pd.Series(1.1+np.arange(n)*0.000002+np.sin(np.arange(n)/15)*0.0001,index=idx)
        df=pd.DataFrame({"open":close.shift(1).fillna(close),"high":close+0.00005,
                         "low":close-0.00005,"close":close,"volume":0},index=idx)
        out=backtest_v2_pair("EUR/USD",df,days=3,cost_pips=2)
        self.assertEqual(len(out["configs"]),3)
        for c in out["configs"]:
            self.assertIn("out_of_sample_30pct",c)
            self.assertIn("profit_factor",c["all"])
