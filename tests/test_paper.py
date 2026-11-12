import tempfile
import unittest
from pathlib import Path
import pandas as pd
from eurjpy_sniper import paper


class PaperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = paper.DB
        paper.DB = Path(self.tmp.name) / 'test.db'
        paper.init_db()

    def tearDown(self):
        paper.DB = self.old
        self.tmp.cleanup()

    def test_trade_waits_for_next_candle_open_to_settle(self):
        signal = pd.Timestamp('2026-11-12T03:00:00Z')
        entry_time = signal + pd.Timedelta(minutes=1)
        exit_time = signal + pd.Timedelta(minutes=2)
        self.assertTrue(paper.add_auto_trade('CALL', 160.0, 10.0, signal, entry_time))
        paper.settle_open(entry_time, 160.1)
        self.assertEqual(paper.history()[0]['status'], 'OPEN')
        paper.settle_open(exit_time, 160.2)
        self.assertEqual(paper.history()[0]['outcome'], 'WIN')
        self.assertEqual(paper.history()[0]['exit'], 160.2)

    def test_auto_trade_is_idempotent_and_does_not_stack(self):
        t = pd.Timestamp('2026-11-12T04:00:00Z')
        entry = t + pd.Timedelta(minutes=1)
        self.assertTrue(paper.add_auto_trade('CALL', 160.0, 10.0, t, entry))
        self.assertFalse(paper.add_auto_trade('CALL', 160.0, 10.0, t, entry))
        self.assertFalse(paper.add_auto_trade('PUT', 159.9, 10.0, entry, entry + pd.Timedelta(minutes=1)))
        self.assertEqual(len(paper.history()), 1)
        paper.settle_open(entry + pd.Timedelta(minutes=1), 160.2)
        self.assertEqual(paper.history()[0]['outcome'], 'WIN')
        self.assertTrue(paper.add_auto_trade('PUT', 160.2, 10.0,
                                             entry + pd.Timedelta(minutes=1),
                                             entry + pd.Timedelta(minutes=2)))
        self.assertEqual(len(paper.history()), 2)


if __name__ == '__main__':
    unittest.main()
