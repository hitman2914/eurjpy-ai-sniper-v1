def evaluate_strategies(x):
 c,p=x.iloc[-1],x.iloc[-2]; out=[]
 bull=c.ema20>c.ema50>c.ema200; bear=c.ema20<c.ema50<c.ema200
 s='CALL' if bull and p.close<=p.ema20<c.close else 'PUT' if bear and p.close>=p.ema20>c.close else 'WAIT'; out.append({'name':'EMA Trend Pullback','side':s,'reason':'EMA alignment and reclaim' if s!='WAIT' else 'No aligned reclaim'})
 s='WAIT'
 if c.adx<22:
  if p.close<p.bb_lower and c.close>c.bb_lower and c.rsi<40:s='CALL'
  elif p.close>p.bb_upper and c.close<c.bb_upper and c.rsi>60:s='PUT'
 out.append({'name':'RSI + Bollinger Reversal','side':s,'reason':'Band re-entry and RSI confirmation' if s!='WAIT' else 'No qualified reversal'})
 q=x.iloc[-21:-1]; s='CALL' if c.close>q.high.max()+.05*c.atr else 'PUT' if c.close<q.low.min()-.05*c.atr else 'WAIT'; out.append({'name':'20-candle Range Breakout','side':s,'reason':'Close beyond recent range' if s!='WAIT' else 'No breakout'})
 body=abs(c.close-c.open); lw=min(c.open,c.close)-c.low; uw=c.high-max(c.open,c.close); s='CALL' if c.low<q.low.min() and c.close>q.low.min() and lw>body else 'PUT' if c.high>q.high.max() and c.close<q.high.max() and uw>body else 'WAIT'; out.append({'name':'Support/Resistance Rejection','side':s,'reason':'Sweep and rejection wick' if s!='WAIT' else 'No clear rejection'})
 return out
