import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone, timedelta

DB = Path(os.getenv('PAPER_DB_PATH', str(Path(__file__).resolve().parent.parent / 'paper_trades.db')))


def con():
    c = sqlite3.connect(DB, timeout=10)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with con() as c:
        c.execute("CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY,opened TEXT,side TEXT,entry REAL,expires TEXT,stake REAL,status TEXT,exit REAL,pnl REAL,outcome TEXT)")
        cols = {r['name'] for r in c.execute("PRAGMA table_info(trades)").fetchall()}
        if 'signal_candle' not in cols:
            c.execute("ALTER TABLE trades ADD COLUMN signal_candle TEXT")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS one_auto_trade_per_candle ON trades(signal_candle) WHERE signal_candle IS NOT NULL")


def _utc(value):
    t = value.to_pydatetime() if hasattr(value, 'to_pydatetime') else value
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def _iso_candle(candle_time):
    return _utc(candle_time).isoformat()


def add_trade(side, entry, stake, candle_time):
    key = _iso_candle(candle_time)
    expires = (_utc(candle_time) + timedelta(minutes=2)).isoformat()
    with con() as c:
        c.execute('INSERT INTO trades(opened,side,entry,expires,stake,status) VALUES(?,?,?,?,?,?)',
                  (datetime.now(timezone.utc).isoformat(), side, float(entry), expires, float(stake), 'OPEN'))


def add_auto_trade(side, entry, stake, signal_candle, entry_candle=None):
    """Record a simulated entry at the next candle's open; settle at the following candle's open."""
    signal_key = _iso_candle(signal_candle)
    entry_time = _utc(entry_candle if entry_candle is not None else signal_candle)
    expires = (entry_time + timedelta(minutes=1)).isoformat()
    with con() as c:
        c.execute('BEGIN IMMEDIATE')
        if c.execute("SELECT 1 FROM trades WHERE status='OPEN' LIMIT 1").fetchone():
            return False
        cur = c.execute('INSERT OR IGNORE INTO trades(opened,side,entry,expires,stake,status,signal_candle) VALUES(?,?,?,?,?,?,?)',
                        (datetime.now(timezone.utc).isoformat(), side, float(entry), expires, float(stake), 'OPEN', signal_key))
        return cur.rowcount == 1


def settle_open(candle_time, price):
    """Settle only when a later candle opens at or beyond the recorded expiry."""
    now = _utc(candle_time)
    with con() as c:
        for r in c.execute("SELECT * FROM trades WHERE status='OPEN'").fetchall():
            expiry = datetime.fromisoformat(r['expires'])
            expiry = expiry.replace(tzinfo=timezone.utc) if expiry.tzinfo is None else expiry
            if now < expiry:
                continue
            outcome = 'TIE' if float(price) == float(r['entry']) else 'WIN' if ((float(price) > float(r['entry'])) == (r['side'] == 'CALL')) else 'LOSS'
            pnl = 0.0 if outcome == 'TIE' else float(r['stake']) if outcome == 'WIN' else -float(r['stake'])
            c.execute('UPDATE trades SET status=?,exit=?,pnl=?,outcome=? WHERE id=?',
                      ('SETTLED', float(price), pnl, outcome, r['id']))


def history():
    with con() as c:
        return [dict(r) for r in c.execute('SELECT * FROM trades ORDER BY id DESC LIMIT 30')]


def stats():
    h = [r for r in history() if r['status'] == 'SETTLED']
    w = sum(r['outcome'] == 'WIN' for r in h)
    l = sum(r['outcome'] == 'LOSS' for r in h)
    n = w + l
    net = round(sum(r['pnl'] or 0 for r in h), 2)
    return {'trades': len(h), 'wins': w, 'losses': l,
            'win_rate': round(w / n * 100, 1) if n else None,
            'net_pnl': net, 'starting_balance': 1000.0,
            'paper_balance': round(1000.0 + net, 2)}
