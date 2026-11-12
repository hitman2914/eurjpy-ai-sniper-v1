import pandas as pd
import numpy as np

def enrich(df):
 x=df.copy(); c,h,l=x.close,x.high,x.low
 for n in (20,50,200): x[f'ema{n}']=c.ewm(span=n,adjust=False).mean()
 d=c.diff(); g=d.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); z=(-d.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean(); rs=g/z.replace(0,np.nan)
 x['rsi']=(100-100/(1+rs)).mask((z==0)&(g>0),100).mask((g==0)&(z>0),0).mask((g==0)&(z==0),50)
 tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1); x['atr']=tr.ewm(alpha=1/14,adjust=False).mean()
 m=c.rolling(20).mean(); s=c.rolling(20).std(ddof=0); x['bb_upper']=m+2*s; x['bb_lower']=m-2*s
 e12=c.ewm(span=12,adjust=False).mean(); e26=c.ewm(span=26,adjust=False).mean(); x['macd']=e12-e26; x['macd_signal']=x.macd.ewm(span=9,adjust=False).mean()
 up,down=h.diff(),-l.diff(); p=up.where((up>down)&(up>0),0); q=down.where((down>up)&(down>0),0); a=tr.ewm(alpha=1/14,adjust=False).mean().replace(0,np.nan)
 pdi=100*p.ewm(alpha=1/14,adjust=False).mean()/a; mdi=100*q.ewm(alpha=1/14,adjust=False).mean()/a; dx=100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan); x['adx']=dx.ewm(alpha=1/14,adjust=False).mean()
 return x
