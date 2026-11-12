import tempfile
import unittest
from pathlib import Path
import pandas as pd
from eurjpy_sniper import paper

class PaperTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.old=paper.DB
  paper.DB=Path(self.tmp.name)/'test.db'
  paper.init_db()
 def tearDown(self):
  paper.DB=self.old
  self.tmp.cleanup()
 def test_one_minute_settlement_and_tie(self):
  t=pd.Timestamp('2026-11-12T03:00:00Z')
  paper.add_trade('CALL',160.,10.,t)
  paper.settle_open(t,160.2)
  self.assertEqual(paper.history()[0]['status'],'OPEN')
  paper.settle_open(t+pd.Timedelta(minutes=1),160.2)
  self.assertEqual(paper.history()[0]['outcome'],'WIN')
  paper.add_trade('PUT',160.,10.,t+pd.Timedelta(minutes=2))
  paper.settle_open(t+pd.Timedelta(minutes=3),160.)
  self.assertEqual(paper.history()[0]['outcome'],'TIE')
 def test_auto_trade_is_idempotent_and_does_not_stack(self):
  t=pd.Timestamp('2026-11-12T04:00:00Z')
  self.assertTrue(paper.add_auto_trade('CALL',160.,10.,t))
  self.assertFalse(paper.add_auto_trade('CALL',160.,10.,t))
  self.assertFalse(paper.add_auto_trade('PUT',159.9,10.,t+pd.Timedelta(minutes=1)))
  self.assertEqual(len(paper.history()),1)
  paper.settle_open(t+pd.Timedelta(minutes=1),160.2)
  self.assertEqual(paper.history()[0]['outcome'],'WIN')
  self.assertTrue(paper.add_auto_trade('PUT',160.2,10.,t+pd.Timedelta(minutes=2)))
  self.assertEqual(len(paper.history()),2)

if __name__=='__main__':
 unittest.main()
