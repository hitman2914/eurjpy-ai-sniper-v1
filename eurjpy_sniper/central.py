from flask import Blueprint, jsonify, render_template_string
from .config import SUPPORTED_PAIRS, PAPER_STAKE, MIN_SIGNAL_SCORE
from .multi_data import fetch_all
from .multi_paper import init_db, settle, open_trade, summary
from .indicators import enrich
from .agents import decide
bp=Blueprint("central_dashboard",__name__)
PAGE="""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='theme-color' content='#0b1220'><title>AI SNIPER 21 PAIR CONTROL</title><style>
*{box-sizing:border-box}body{margin:0;background:#0b1220;color:#eef;font:15px system-ui;padding:14px;max-width:1000px;margin:auto}h1{font-size:23px;margin:8px 0}.muted{color:#9aabc2;font-size:12px}.top{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}.pill{background:#123c35;color:#8ce2c6;border-radius:20px;padding:6px 10px;font-size:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:9px;margin-top:14px}.card{background:#142238;border:1px solid #263953;border-radius:13px;padding:12px;min-width:0}.pair{font-weight:700;font-size:17px}.signal{font-size:20px;font-weight:800;margin:7px 0}.CALL{color:#62d6a7}.PUT{color:#ff8585}.WAIT{color:#f0c66d}.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:14px 0}.stat{background:#142238;padding:12px;border-radius:12px}.stat b{font-size:20px;display:block}button{background:#24496c;color:white;border:0;padding:9px 12px;border-radius:8px}#detail{margin-top:14px}.hidden{display:none}.small{font-size:12px;color:#aabbd0}</style></head><body>
<div class='top'><div><div class='muted'>PAPER-ONLY MULTI-PAIR SYSTEM</div><h1>AI SNIPER — 21 PAIR CONTROL</h1></div><span class='pill' id='state'>Connecting…</span></div>
<div class='stats'><div class='stat'><b id='count'>--</b><span class='muted'>Live pair feeds</span></div><div class='stat'><b id='trades'>--</b><span class='muted'>Settled paper trades</span></div><div class='stat'><b id='pnl'>$--</b><span class='muted'>Combined paper P/L</span></div></div>
<div class='top'><span class='muted'>Refreshes once per minute while this page is open</span><button id='refresh'>Refresh now</button></div><div class='grid' id='pairs'></div><div id='detail' class='card hidden'></div>
<p class='muted'>Scores are heuristic, not probabilities. Candle-open fills are simulated references, not guaranteed executable prices. No broker connection or real orders.</p>
<script>
const pairs=document.getElementById('pairs'),state=document.getElementById('state'),detail=document.getElementById('detail');let busy=false,last={};
function esc(s){return String(s??'').replace(/[&<>""']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function card(p){let sig=p.signal||'WAIT';return '<div class="card"><div class="pair">'+esc(p.pair)+'</div><div class="signal '+sig+'">'+esc(sig)+'</div><div>Score: <b>'+(p.score??'--')+'/100</b></div><div class="small">'+esc(p.feed||'No feed')+'</div><div class="small">Paper P/L: $'+(p.stats?.net_pnl??'0.00')+' · Win rate: '+(p.stats?.win_rate??'--')+'%</div><div class="small">Open: '+(p.stats?.open_trades??0)+'</div><p><button onclick="showPair(\''+esc(p.pair)+'\')">Details</button></p></div>'}
window.showPair=function(pair){let p=last[pair];if(!p)return;detail.classList.remove('hidden');detail.innerHTML='<div class="top"><h2>'+esc(pair)+' details</h2><button onclick="detail.classList.add(\'hidden\')">Close</button></div><p>Signal: <b>'+esc(p.signal)+'</b> · Score: '+p.score+'/100 · Price: '+(p.price??'--')+'</p><p class="small">'+esc(p.error||p.feed||'')+'</p><p>Settled: '+(p.stats?.trades??0)+' · Wins: '+(p.stats?.wins??0)+' · Losses: '+(p.stats?.losses??0)+' · P/L: $'+(p.stats?.net_pnl??0)+'</p><h3>Recent paper trades</h3>'+((p.stats?.history||[]).map(function(t){return '<div class="small">'+esc(t.side)+' · '+esc(t.outcome||t.status)+' · entry '+t.entry+' · exit '+(t.exit??'pending')+' · P/L $'+(t.pnl??'--')+'</div>'}).join('')||'No trades yet')}
async function refresh(){if(busy)return;busy=true;state.textContent='Updating…';try{let r=await fetch('/api/central/status',{cache:'no-store'});let d=await r.json();last=Object.fromEntries((d.pairs||[]).map(function(p){return [p.pair,p]}));pairs.innerHTML=(d.pairs||[]).map(card).join('');document.getElementById('count').textContent=d.live_count+' / 21';document.getElementById('trades').textContent=d.total_trades;document.getElementById('pnl').textContent='$'+d.total_pnl;state.textContent=d.live_count+' live · '+new Date().toLocaleTimeString()}catch(e){state.textContent='Refresh error'}finally{busy=false}}
document.getElementById('refresh').onclick=refresh;refresh();setInterval(refresh,60000);
</script></body></html>"""
@bp.get("/dashboard")
def dashboard(): return render_template_string(PAGE)
@bp.get("/api/central/status")
def central_status():
    init_db(); frames,errors=fetch_all(); result=[]; live=0; total_trades=0; total_pnl=0.0
    for pair in sorted(SUPPORTED_PAIRS):
        item={"pair":pair,"signal":"WAIT","score":0,"feed":"No fresh live data","error":errors.get(pair)}
        if pair in frames:
            try:
                raw=frames[pair]; full=enrich(raw).dropna()
                if len(full)<3: raise RuntimeError("Not enough indicator-ready candles")
                entry_time=full.index[-1]; entry=float(raw.loc[entry_time,"open"]); settle(pair,entry_time,entry)
                decision=decide(full.iloc[:-1],MIN_SIGNAL_SCORE); signal=decision["signal"]; opened=False
                if signal in ("CALL","PUT") and decision["score"]>=MIN_SIGNAL_SCORE:
                    opened=open_trade(pair,signal,entry,PAPER_STAKE,full.index[-2],entry_time)
                item.update(signal=signal,score=decision["score"],price=entry,feed="LIVE · Twelve Data",
                    updated=str(entry_time),auto_opened=opened,reasons=decision["reasons"],strategies=decision["strategies"])
                live+=1
            except Exception as exc: item["error"]=str(exc)
        item["stats"]=summary(pair); total_trades+=item["stats"]["trades"]; total_pnl+=item["stats"]["net_pnl"]; result.append(item)
    return jsonify(pairs=result,live_count=live,total_trades=total_trades,total_pnl=round(total_pnl,2),paper_only=True)
