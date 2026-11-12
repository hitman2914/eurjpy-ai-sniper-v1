import os, sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta
DB=Path(os.getenv("CENTRAL_PAPER_DB_PATH",os.getenv("PAPER_DB_PATH","central_paper.db")))
def _con():
    c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row; return c
def init_db():
    DB.parent.mkdir(parents=True,exist_ok=True)
    with _con() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS pair_trades(
        id INTEGER PRIMARY KEY,pair TEXT NOT NULL,opened TEXT NOT NULL,side TEXT NOT NULL,
        entry REAL NOT NULL,expires TEXT NOT NULL,stake REAL NOT NULL,status TEXT NOT NULL,
        exit REAL,pnl REAL,outcome TEXT,signal_candle TEXT,UNIQUE(pair,signal_candle))""")
def _iso(t):
    x=t.to_pydatetime() if hasattr(t,"to_pydatetime") else t
    if x.tzinfo is None: x=x.replace(tzinfo=timezone.utc)
    return x.astimezone(timezone.utc).isoformat()
def settle(pair,candle_time,price):
    now=_iso(candle_time)
    with _con() as c:
        rows=c.execute("SELECT * FROM pair_trades WHERE pair=? AND status='OPEN'",(pair,)).fetchall()
        for r in rows:
            if now<r["expires"]: continue
            win=float(price)>r["entry"] if r["side"]=="CALL" else float(price)<r["entry"]
            outcome="TIE" if float(price)==r["entry"] else ("WIN" if win else "LOSS")
            pnl=0.0 if outcome=="TIE" else (r["stake"] if outcome=="WIN" else -r["stake"])
            c.execute("UPDATE pair_trades SET status='SETTLED',exit=?,pnl=?,outcome=? WHERE id=?",(float(price),pnl,outcome,r["id"]))
def open_trade(pair,side,entry,stake,signal_time,entry_time):
    sig=_iso(signal_time); ent=entry_time.to_pydatetime() if hasattr(entry_time,"to_pydatetime") else entry_time
    if ent.tzinfo is None: ent=ent.replace(tzinfo=timezone.utc)
    expires=(ent+timedelta(minutes=1)).astimezone(timezone.utc).isoformat()
    with _con() as c:
        if c.execute("SELECT 1 FROM pair_trades WHERE pair=? AND status='OPEN'",(pair,)).fetchone(): return False
        cur=c.execute("""INSERT OR IGNORE INTO pair_trades(pair,opened,side,entry,expires,stake,status,signal_candle)
        VALUES(?,?,?,?,?,?,?,?)""",(pair,datetime.now(timezone.utc).isoformat(),side,float(entry),expires,float(stake),"OPEN",sig))
        return cur.rowcount==1
def summary(pair):
    with _con() as c:
        rows=[dict(r) for r in c.execute("SELECT * FROM pair_trades WHERE pair=? ORDER BY id DESC LIMIT 10",(pair,))]
        agg=c.execute("""SELECT COUNT(*) AS trades,
            SUM(CASE WHEN outcome='WIN' THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN outcome='LOSS' THEN 1 ELSE 0 END) AS losses,
            COALESCE(SUM(pnl),0) AS net_pnl
            FROM pair_trades WHERE pair=? AND status='SETTLED'""",(pair,)).fetchone()
        opened=c.execute("SELECT COUNT(*) FROM pair_trades WHERE pair=? AND status='OPEN'",(pair,)).fetchone()[0]
    wins=agg["wins"] or 0; losses=agg["losses"] or 0; n=wins+losses; pnl=round(agg["net_pnl"],2)
    return {"trades":agg["trades"],"wins":wins,"losses":losses,"win_rate":round(wins/n*100,1) if n else None,
    "net_pnl":pnl,"paper_balance":round(1000+pnl,2),"open_trades":opened,"history":rows}
