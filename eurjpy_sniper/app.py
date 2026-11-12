from flask import Flask,render_template_string,jsonify,request
from .data import fetch_candles
from .indicators import enrich
from .agents import decide
from .paper import init_db,add_trade,settle_open,history,stats
from .config import MIN_SIGNAL_SCORE,PAPER_STAKE
HTML='''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURJPY AI SNIPER</title><style>body{background:#0b1220;color:#eef;font:16px system-ui;max-width:700px;margin:20px auto;padding:12px}.card{background:#17253a;padding:16px;border-radius:14px;margin:12px 0}button{padding:14px;background:#16896f;color:white;border:0;border-radius:9px;width:100%}.big{font-size:30px;font-weight:bold}</style><h2>EURJPY AI SNIPER V1</h2><p>PAPER ONLY · EURJPY · 1 MINUTE</p><div class="card"><small>DATA</small><p id="source">Loading</p><small>SIGNAL</small><div class="big" id="signal">WAIT</div><p id="score">--</p><p id="price">--</p><p id="rsi">--</p><p id="adx">--</p></div><div class="card"><h3>Four strategy engines</h3><div id="strats"></div></div><div class="card"><h3>Seven analysis roles</h3><ul id="agents"></ul></div><div class="card"><h3>Paper journal</h3><p id="stats"></p><button id="record" disabled>Record 1-minute paper evaluation</button><div id="history"></div></div><p>Score is a heuristic, not a probability. Synthetic data cannot generate signals or paper trades. No real orders or broker integration.</p><script>let d;async function refresh(){try{let r=await fetch('/api/status');d=await r.json();source.textContent=d.source;signal.textContent=d.signal;score.textContent=d.score+'/100';price.textContent='Price: '+(d.price??'--');rsi.textContent='RSI: '+(d.rsi??'--');adx.textContent='ADX: '+(d.adx??'--');strats.innerHTML=(d.strategies||[]).map(s=>s.name+': '+s.side+' — '+s.reason).join('<hr>');agents.innerHTML=(d.reasons||[]).map(s=>'<li>'+s+'</li>').join('');stats.textContent=JSON.stringify(d.stats);record.disabled=!(d.is_live&&['CALL','PUT'].includes(d.signal));history.innerHTML=(d.history||[]).map(t=>t.side+' '+t.status+' '+(t.outcome||'')).join('<br>')}catch(e){source.textContent=e}}record.onclick=async()=>{await fetch('/api/paper',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({side:d.signal})});refresh()};refresh();setInterval(refresh,15000)</script>'''
def create_app():
 app=Flask(__name__); init_db()
 @app.get('/')
 def home():return render_template_string(HTML)
 @app.get('/api/status')
 def status():
  try:
   raw,source=fetch_candles(); x=enrich(raw).dropna(); d=decide(x,MIN_SIGNAL_SCORE); live=source.startswith('LIVE DATA')
   if live:settle_open(x.index[-1],d['price'])
   else:d['signal']='WAIT';d['score']=0;d['reasons'].append('Synthetic candles: signals disabled.')
   d.update(source=source,is_live=live,stats=stats(),history=history());return jsonify(d)
  except Exception as e:return jsonify(signal='WAIT',score=0,source=str(e),is_live=False,strategies=[],reasons=['No fresh live feed; signals disabled'],stats=stats(),history=history())
 @app.post('/api/paper')
 def paper():
  b=request.get_json(silent=True) or {}; side=b.get('side')
  if side not in ('CALL','PUT'):return jsonify(error='Invalid side'),400
  try:
   raw,src=fetch_candles()
   if not src.startswith('LIVE DATA'):return jsonify(error='Live data required'),400
   x=enrich(raw).dropna(); d=decide(x,MIN_SIGNAL_SCORE)
   if d['signal']!=side:return jsonify(error='Signal changed; refresh'),409
   add_trade(side,d['price'],PAPER_STAKE,x.index[-1]);return jsonify(ok=True)
  except Exception as e:return jsonify(error=str(e)),400
 return app
