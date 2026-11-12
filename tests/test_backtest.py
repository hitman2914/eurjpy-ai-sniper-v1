import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

from eurjpy_sniper.backtest import load_ohlc_csv, backtest_pair, _metrics, pip_size

class BacktestTests(unittest.TestCase):
    def test_pip_sizes(self):
        self.assertEqual(pip_size("EUR/JPY"), 0.01)
        self.assertEqual(pip_size("EUR/USD"), 0.0001)

    def test_metrics_exclude_breakeven_from_win_rate(self):
        trades = pd.DataFrame({"net_pips": [2.0, -1.0, 0.0]})
        m = _metrics(trades)
        self.assertEqual(m["trades"], 3)
        self.assertEqual(m["win_rate_pct"], 50.0)
        self.assertEqual(m["breakeven"], 1)
        self.assertEqual(m["net_pips"], 1.0)

    def test_csv_loader_normalizes_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "EURUSD.csv"
            pd.DataFrame({
                "datetime": ["2026-01-01T00:00:00Z", "2026-01-01T00:01:00Z"],
                "open": [1.1, 1.1], "high": [1.101, 1.102],
                "low": [1.099, 1.099], "close": [1.1, 1.101],
            }).to_csv(path, index=False)
            df = load_ohlc_csv(path)
            self.assertEqual(len(df), 2)
            self.assertEqual(str(df.index.tz), "UTC")

    def test_backtest_rejects_too_little_history(self):
        idx = pd.date_range("2026-01-01", periods=100, freq="min", tz="UTC")
        close = pd.Series(np.linspace(1.1, 1.11, len(idx)), index=idx)
        df = pd.DataFrame({"open": close, "high": close + .001,
                           "low": close - .001, "close": close, "volume": 0}, index=idx)
        with self.assertRaisesRegex(ValueError, "Insufficient history"):
            backtest_pair("EUR/USD", df)

if __name__ == "__main__":
    unittest.main()
