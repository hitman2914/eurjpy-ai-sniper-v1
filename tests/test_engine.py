import unittest
import numpy as np
import pandas as pd
from eurjpy_sniper.indicators import enrich
from eurjpy_sniper.agents import decide
class EngineTests(unittest.TestCase):
 def test_pipeline(self):
  rng=np.random.default_rng(7); n=400; idx=pd.date_range('2026-11-10T00:00:00Z',periods=n,freq='min'); c=160+np.cumsum(rng.normal(0,.025,n)); o=np.r_[c[0],c[:-1]]; w=rng.uniform(.001,.02,n); d=pd.DataFrame({'open':o,'high':np.maximum(o,c)+w,'low':np.minimum(o,c)-w,'close':c,'volume':1},index=idx); x=enrich(d).dropna(); z=decide(x,80); self.assertIn(z['signal'],('CALL','PUT','WAIT')); self.assertEqual(len(z['strategies']),4); self.assertEqual(len(z['reasons']),7); self.assertTrue(0<=z['score']<=100)
if __name__=='__main__': unittest.main()
