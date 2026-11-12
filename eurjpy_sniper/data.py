import time,requests,numpy as np,pandas as pd
from .config import API_KEY,SYMBOL,INTERVAL
_cache={'at':0,'df':None}
def _demo(n=300):
 end=pd.Timestamp.now(tz='UTC').floor('min')-pd.Timedelta(minutes=1); idx=pd.date_range(end=end,periods=n,freq='min'); rng=np.random.default_rng(int(time.time())//60); c=162+np.cumsum(rng.normal(0,.0002,n)); o=np.r_[c[0],c[:-1]]; w=rng.uniform(.00003,.0002,n)
 return pd.DataFrame({'open':o,'high':np.maximum(o,c)+w,'low':np.minimum(o,c)-w,'close':c,'volume':1},index=idx)
def fetch_candles(n=300):
 if not API_KEY: return _demo(n),'DEMO ONLY — synthetic candles; signals disabled'
 if _cache['df'] is not None and time.time()-_cache['at']<20: return _cache['df'].copy(),'LIVE DATA — Twelve Data'
 r=requests.get('https://api.twelvedata.com/time_series',params={'symbol':SYMBOL,'interval':INTERVAL,'outputsize':n,'apikey':API_KEY,'format':'JSON','timezone':'UTC'},timeout=15); r.raise_for_status(); j=r.json()
 if 'values' not in j: raise RuntimeError(j.get('message','No market data'))
 d=pd.DataFrame(j['values']); d['datetime']=pd.to_datetime(d.datetime,utc=True)
 for k in ['open','high','low','close']: d[k]=pd.to_numeric(d[k],errors='coerce')
 # Forex feeds may omit volume; use a neutral zero column when absent.
 if 'volume' in d.columns: d['volume']=pd.to_numeric(d['volume'],errors='coerce').fillna(0)
 else: d['volume']=0.0
 d=d.dropna(subset=['open','high','low','close']).sort_values('datetime').set_index('datetime')[['open','high','low','close','volume']]; d=d[d.index<pd.Timestamp.now(tz='UTC').floor('min')]
 if len(d)<210 or (pd.Timestamp.now(tz='UTC')-d.index[-1]).total_seconds()>180: raise RuntimeError('Insufficient or stale completed-candle data')
 _cache.update(at=time.time(),df=d.tail(n)); return d.tail(n),'LIVE DATA — Twelve Data'
