import sqlite3
from pathlib import Path
from datetime import datetime,timezone,timedelta
DB=Path(__file__).resolve().parent.parent/'paper_trades.db'
def con():
 c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def init_db():
 with con() as c:c.execute("CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,opened TEXT,side TEXT,entry REAL,expires TEXT,stake REAL,status TEXT,exit REAL,pnl REAL,outcome TEXT)")
def add_trade(side,entry,stake,candle_time):
 t=candle_time.to_pydatetime()+timedelta(minutes=2)
 with con() as c:c.execute('INSERT INTO trades(opened,side,entry,expires,stake,status) VALUES(?,?,?,?,?,?)',(datetime.now(timezone.utc).isoformat(),side,float(entry),t.isoformat(),float(stake),'OPEN'))
def settle_open(candle_time,price):
 t=candle_time.to_pydatetime()+timedelta(minutes=1)
 with con() as c:
  for r in c.execute("SELECT * FROM trades WHERE status='OPEN'").fetchall():
   e=datetime.fromisoformat(r['expires']); e=e.replace(tzinfo=timezone.utc) if e.tzinfo is None else e
   if t<e:continue
   outcome='TIE' if price==r['entry'] else 'WIN' if ((price>r['entry'])==(r['side']=='CALL')) else 'LOSS'; pnl=0 if outcome=='TIE' else r['stake'] if outcome=='WIN' else -r['stake']; c.execute('UPDATE trades SET status=?,exit=?,pnl=?,outcome=? WHERE id=?',('SETTLED',price,pnl,outcome,r['id']))
def history():
 with con() as c:return [dict(r) for r in c.execute('SELECT * FROM trades ORDER BY id DESC LIMIT 30')]
def stats():
 h=[r for r in history() if r['status']=='SETTLED']; w=sum(r['outcome']=='WIN' for r in h); l=sum(r['outcome']=='LOSS' for r in h); n=w+l; return {'trades':len(h),'wins':w,'losses':l,'win_rate':round(w/n*100,1) if n else None,'net_pnl':round(sum(r['pnl'] or 0 for r in h),2)}
