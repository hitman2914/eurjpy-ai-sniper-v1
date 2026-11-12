from flask import Flask,render_template_string,jsonify,request
from .data import fetch_candles
from .indicators import enrich
from .agents import decide
from .paper import init_db,add_auto_trade,settle_open,history,stats
from .config import MIN_SIGNAL_SCORE,PAPER_STAKE

HTML='''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURJPY AI SNIPER</title><style>body{background:#0b1220;color:#eef;font:16px system-ui;max-width:700px;margin:20px auto;padding:12px}.card{background:#17253a;padding:16px;border-radius:14px;margin:12px 0}button{padding:14px;background:#16896f;color:white;border:0;border-radius:9px;width:100%}.big{font-size:30px;font-weight:bold}.muted{color:#aab8cc;font-size:13px}.pill{display:inline-block;background:#075b4b;padding:5px 9px;border-radius:20px;font-size:13px}</style><h2>EURJPY AI SNIPER V1</h2><p>PAPER ONLY · EURJPY · 1 MINUTE</p><div class="card"><small>DATA</small><p id="source">Loading</p><small>SIGNAL</small><div class="big" id="signal">WAIT</div><p id="score">--</p><p id="price">--</p><p id="rsi">--</p><p id="adx">--</p></div><div class="card"><h3>Automatic paper trading</h3><p><span class="pill">AUTO PAPER MODE</span></p><p id="auto">Waiting for live data...</p><p class="muted">Automatically opens one simulated $10 position when a fresh completed 1-minute candle qualifies at the configured score threshold. Open positions are not stacked. No real orders are sent.</p></div><div class="card"><h3>Four strategy engines</h3><div id="strats"></div></div><div class="card"><h3>Seven analysis roles</h3><ul id="agents"></ul></div><div class="card"><h3>Paper journal</h3><p id="stats"></p><div id="history"></div></div><p>Score is a heuristic, not a probability. Synthetic data cannot generate signals or paper trades. No real orders or broker integration.</p><script>let d;async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'});d=await r.json();source.textContent=d.source;signal.textContent=d.signal;score.textContent=d.score+'/100';price.textContent='Price: '+(d.price??'--');rsi.textContent='RSI: '+(d.rsi??'--');adx.textContent='ADX: '+(d.adx??'--');auto.textContent=d.auto_opened?'New '+d.signal+' paper trade opened automatically.':(d.auto_status||'Scanning for a qualifying setup...');strats.innerHTML=(d.strategies||[]).map(s=>s.name+': '+s.side+' — '+s.reason).join('<hr>');agents.innerHTML=(d.reasons||[]).map(s=>'<li>'+s+'</li>').join('');let z=d.stats||{};stats.textContent='Settled: '+z.trades+' | Wins: '+z.wins+' | Losses: '+z.losses+' | Win rate: '+(z.win_rate===null?'--':z.win_rate+'%')+' | Net P/L: $'+z.net_pnl+' | Paper balance: $'+z.paper_balance;history.innerHTML=(d.history||[]).map(t=>t.side+' | '+t.status+' | Entry '+t.entry+(t.outcome?' | '+t.outcome+' | P/L $'+t.pnl:' | awaiting settlement')).join('<br>')||'No paper trades yet.'}catch(e){source.textContent='Dashboard refresh error: '+e}}refresh();setInterval(refresh,15000)</script>'''

def create_app():
 app=Flask(__name__)
 init_db()
 @app.get('/')
 def home():
  return render_template_string(HTML)
 @app.get('/api/status')
 def status():
  try:
   raw,source=fetch_candles()
   x=enrich(raw).dropna()
   d=decide(x,MIN_SIGNAL_SCORE)
   live=source.startswith('LIVE DATA')
   auto_opened=False
   if live:
    settle_open(x.index[-1],d['price'])
    if d['signal'] in ('CALL','PUT') and d['score']>=MIN_SIGNAL_SCORE:
     auto_opened=add_auto_trade(d['signal'],d['price'],PAPER_STAKE,x.index[-1])
    auto_status='New qualifying signal recorded automatically.' if auto_opened else ('Qualifying signal seen; an open paper trade or this candle was already recorded.' if d['signal'] in ('CALL','PUT') else 'Scanning automatically; no qualifying setup right now.')
   else:
    d['signal']='WAIT'
    d['score']=0
    d['reasons'].append('Synthetic candles: automatic paper trading disabled.')
    auto_status='Paused: live market data is required.'
   d.update(source=source,is_live=live,auto_mode=True,auto_opened=auto_opened,auto_status=auto_status,stats=stats(),history=history())
   return jsonify(d)
  except Exception as e:
   return jsonify(signal='WAIT',score=0,source=str(e),is_live=False,auto_mode=True,auto_opened=False,auto_status='Paused: live feed unavailable.',strategies=[],reasons=['No fresh live feed; automatic paper trading paused'],stats=stats(),history=history())
 return app
