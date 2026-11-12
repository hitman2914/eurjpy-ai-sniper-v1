from flask import Flask, render_template_string, jsonify
from .data import fetch_candles
from .indicators import enrich
from .agents import decide
from .paper import init_db, add_auto_trade, settle_open, history, stats
from .config import MIN_SIGNAL_SCORE, PAPER_STAKE, PAIR, BOT_NAME
from .central import bp as central_dashboard_bp

HTML='''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>EURJPY AI SNIPER</title><style>body{background:#0b1220;color:#eef;font:16px system-ui;max-width:700px;margin:20px auto;padding:12px}.card{background:#17253a;padding:16px;border-radius:14px;margin:12px 0}button{padding:14px;background:#16896f;color:white;border:0;border-radius:9px;width:100%}.big{font-size:30px;font-weight:bold}.muted{color:#aab8cc;font-size:13px}.pill{display:inline-block;background:#075b4b;padding:5px 9px;border-radius:20px;font-size:13px}</style><h2>EURJPY AI SNIPER V1</h2><p>PAPER ONLY · EURJPY · 1 MINUTE</p><div class="card"><small>DATA</small><p id="source">Loading</p><small>SIGNAL</small><div class="big" id="signal">WAIT</div><p id="score">--</p><p id="price">--</p><p id="rsi">--</p><p id="adx">--</p></div><div class="card"><h3>Automatic paper trading</h3><p><span class="pill">AUTO PAPER MODE</span></p><p id="auto">Waiting for live data...</p><p class="muted">Simulated entry uses the next candle open after signal confirmation; simulated exit uses the following candle open. No real orders are sent.</p></div><div class="card"><h3>Four strategy engines</h3><div id="strats"></div></div><div class="card"><h3>Seven analysis roles</h3><ul id="agents"></ul></div><div class="card"><h3>Paper journal</h3><p id="stats"></p><div id="history"></div></div><p>Score is a heuristic, not a probability. Synthetic data cannot generate signals or paper trades. No real orders or broker integration.</p><script>let d;async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'});d=await r.json();source.textContent=d.source;signal.textContent=d.signal;score.textContent=d.score+'/100';price.textContent='Price: '+(d.price??'--');rsi.textContent='RSI: '+(d.rsi??'--');adx.textContent='ADX: '+(d.adx??'--');auto.textContent=d.auto_opened?'New '+d.signal+' paper trade opened automatically.':(d.auto_status||'Scanning for a qualifying setup...');strats.innerHTML=(d.strategies||[]).map(s=>s.name+': '+s.side+' — '+s.reason).join('<hr>');agents.innerHTML=(d.reasons||[]).map(s=>'<li>'+s+'</li>').join('');let z=d.stats||{};stats.textContent='Settled: '+z.trades+' | Wins: '+z.wins+' | Losses: '+z.losses+' | Win rate: '+(z.win_rate===null?'--':z.win_rate+'%')+' | Net P/L: $'+z.net_pnl+' | Paper balance: $'+z.paper_balance;history.innerHTML=(d.history||[]).map(t=>t.side+' | '+t.status+' | Entry '+t.entry+(t.outcome?' | '+t.outcome+' | P/L $'+t.pnl:' | awaiting settlement')).join('<br>')||'No paper trades yet.'}catch(e){source.textContent='Dashboard refresh error: '+e}}refresh();setInterval(refresh,15000)</script>'''

def create_app():
    app = Flask(__name__)
    app.register_blueprint(central_dashboard_bp)
    init_db()

    @app.get('/')
    def home():
        page = HTML.replace('EURJPY AI SNIPER V1', BOT_NAME + ' V1').replace('EURJPY', PAIR.replace('/', '')).replace('EUR/JPY', PAIR)
        return render_template_string(page)

    @app.get('/api/status')
    def status():
        try:
            raw, source = fetch_candles()
            full = enrich(raw).dropna()
            live = source.startswith('LIVE DATA')
            auto_opened = False
            if len(full) < 2:
                raise RuntimeError('Waiting for enough completed candles')
            # At each newly available completed bar, use its OPEN as the prior
            # signal candle's next-candle entry reference.
            entry_candle_time = full.index[-1]
            entry_price = float(raw.loc[entry_candle_time, 'open'])
            if live:
                settle_open(entry_candle_time, entry_price)
            signal_data = full.iloc[:-1]
            d = decide(signal_data, MIN_SIGNAL_SCORE)
            d['price'] = entry_price
            if live and d['signal'] in ('CALL', 'PUT') and d['score'] >= MIN_SIGNAL_SCORE:
                auto_opened = add_auto_trade(d['signal'], entry_price, PAPER_STAKE,
                                             signal_data.index[-1], entry_candle_time)
                auto_status = 'New qualifying signal recorded at the next candle open.' if auto_opened else 'No new position: this candle was already recorded or another paper position is open.'
            elif not live:
                d['signal'] = 'WAIT'
                d['score'] = 0
                d['reasons'].append('Synthetic candles: automatic paper trading disabled.')
                auto_status = 'Paused: live market data is required.'
            else:
                auto_status = 'Scanning automatically; no qualifying setup right now.'
            d.update(source=source, pair=PAIR, bot_name=BOT_NAME, is_live=live,
                     auto_mode=True, auto_opened=auto_opened, auto_status=auto_status,
                     stats=stats(), history=history())
            return jsonify(d)
        except Exception as e:
            return jsonify(signal='WAIT', score=0, pair=PAIR, bot_name=BOT_NAME,
                           source=str(e), is_live=False, auto_mode=True,
                           auto_opened=False, auto_status='Paused: live feed unavailable.',
                           strategies=[], reasons=['No fresh live feed; automatic paper trading paused'],
                           stats=stats(), history=history())

    return app
