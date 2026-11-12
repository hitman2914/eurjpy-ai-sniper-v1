import tempfile,unittest
from pathlib import Path
import pandas as pd
from eurjpy_sniper import multi_paper
class MultiPaperTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.old=multi_paper.DB; multi_paper.DB=Path(self.tmp.name)/"multi.db"; multi_paper.init_db()
 def tearDown(self):
  multi_paper.DB=self.old; self.tmp.cleanup()
 def test_pair_journals_are_isolated(self):
  t=pd.Timestamp("2026-11-12T03:00:00Z"); e=t+pd.Timedelta(minutes=1)
  self.assertTrue(multi_paper.open_trade("EUR/JPY","CALL",160,10,t,e)); self.assertTrue(multi_paper.open_trade("GBP/JPY","PUT",200,10,t,e))
  self.assertEqual(multi_paper.summary("EUR/JPY")["open_trades"],1); self.assertEqual(multi_paper.summary("GBP/JPY")["open_trades"],1)
 def test_duplicate_signal_is_ignored(self):
  t=pd.Timestamp("2026-11-12T03:00:00Z"); e=t+pd.Timedelta(minutes=1)
  self.assertTrue(multi_paper.open_trade("EUR/JPY","CALL",160,10,t,e)); self.assertFalse(multi_paper.open_trade("EUR/JPY","CALL",160,10,t,e))
if __name__=="__main__": unittest.main()
