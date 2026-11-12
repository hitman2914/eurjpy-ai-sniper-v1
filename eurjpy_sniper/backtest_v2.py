"""Experimental, paper-only v2 strategy research. Never places orders.

Uses completed 1m candles, a closed 5m trend filter, next-minute-open entry,
fixed holding horizons, one position at a time, and conservative cost deduction.
This is a research challenger, not the production signal engine.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd
from .backtest import load_ohlc_csv, _metrics, pip_size
from .config import SUPPORTED_PAIRS
from .indicators import enrich

WARMUP = 1300
CONFIGS = [
    {"name": "trend_adx18_hold5", "adx_min": 18.0, "hold": 5, "session": "all"},
    {"name": "trend_adx22_hold10", "adx_min": 22.0, "hold": 10, "session": "london_ny"},
    {"name": "trend_adx18_hold15", "adx_min": 18.0, "hold": 15, "session": "london_ny"},
]

def _higher_timeframe(candles: pd.DataFrame) -> pd.Series:
    bars = candles[["open","high","low","close"]].resample("5min", label="right", closed="left").agg(
        {"open":"first","high":"max","low":"min","close":"last"}).dropna()
    bars["ema50"] = bars.close.ewm(span=50, adjust=False).mean()
    bars["ema200"] = bars.close.ewm(span=200, adjust=False).mean()
    # A 5m bar timestamp denotes its close; only map already closed bars to 1m signal times.
    return pd.DataFrame({"htf_bull": bars.ema50 > bars.ema200, "htf_ready": bars.ema200.notna()}, index=bars.index)

def _signals(candles: pd.DataFrame, adx_min: float) -> pd.Series:
    x = enrich(candles)
    htf = _higher_timeframe(candles)
    aligned = pd.merge_asof(
        pd.DataFrame({"time": x.index}).sort_values("time"),
        htf.reset_index().rename(columns={htf.index.name or "index":"time"}).sort_values("time"),
        on="time", direction="backward", allow_exact_matches=True
    )
    bull_htf = aligned.htf_bull.fillna(False).to_numpy()\n    htf_ready = aligned.htf_ready.fillna(False).to_numpy()
    prev = x.close.shift(1)
    pullback_up = (prev <= x.ema20.shift(1)) & (x.close > x.ema20)
    pullback_dn = (prev >= x.ema20.shift(1)) & (x.close < x.ema20)
    bull = (x.ema20 > x.ema50) & (x.ema50 > x.ema200) & bull_htf
    bear = (x.ema20 < x.ema50) & (x.ema50 < x.ema200) & (~bull_htf)
    momentum_up = (x.rsi >= 52) & (x.macd > x.macd_signal)
    momentum_dn = (x.rsi <= 48) & (x.macd < x.macd_signal)
    qualified = x.adx >= adx_min
    side = pd.Series("", index=x.index, dtype="object")
    side.loc[bull & pullback_up & momentum_up & qualified] = "CALL"
    side.loc[bear & pullback_dn & momentum_dn & qualified] = "PUT"
    return side

def _session_ok(ts: pd.Timestamp, session: str) -> bool:
    if session == "all":
        return True
    # UTC overlap-focused window; deliberately simple and transparent.
    return 7 <= ts.hour < 17

def _run_config(pair: str, candles: pd.DataFrame, cost_pips: float, cfg: dict) -> dict:
    x = candles.sort_index().copy()
    side = _signals(x, cfg["adx_min"])
    pip = pip_size(pair)
    rows = []
    i = WARMUP
    # Do not open a new position until the prior fixed-horizon trade has exited.
    while i + cfg["hold"] < len(x):
        ts = x.index[i]
        if not _session_ok(ts, cfg["session"]) or side.iloc[i] not in ("CALL","PUT"):
            i += 1
            continue
        entry_i, exit_i = i + 1, i + 1 + cfg["hold"]
        if exit_i >= len(x):
            break
        # Reject gaps; do not synthesize prices or carry positions over missing candles.
        if any((x.index[k] - x.index[k-1]).total_seconds() > 90 for k in range(i, exit_i + 1)):
            i += 1
            continue
        entry, exit_price = float(x.open.iloc[entry_i]), float(x.open.iloc[exit_i])
        raw = (exit_price-entry)/pip
        direction = side.iloc[i]
        if direction == "PUT":
            raw = -raw
        net = raw - cost_pips
        rows.append({"pair":pair,"config":cfg["name"],"signal_time":ts.isoformat(),
                     "entry_time":x.index[entry_i].isoformat(),"exit_time":x.index[exit_i].isoformat(),
                     "side":direction,"hold_minutes":cfg["hold"],"entry":entry,"exit":exit_price,
                     "gross_pips":round(raw,3),"cost_pips":cost_pips,"net_pips":round(net,3),
                     "outcome":"WIN" if net>0 else "LOSS" if net<0 else "BREAKEVEN"})
        i = exit_i + 1
    trades = pd.DataFrame(rows)
    if len(trades) >= 2:
        split = max(1,min(len(trades)-1,int(len(trades)*.70)))
        train,test=trades.iloc[:split],trades.iloc[split:]
    else:
        train,test=trades,trades
    return {"config":cfg,"all":_metrics(trades),"in_sample_70pct":_metrics(train),
            "out_of_sample_30pct":_metrics(test),"trades":rows}

def backtest_v2_pair(pair: str, candles: pd.DataFrame, days: int=90, cost_pips: float=2.0) -> dict:
    pair=pair.upper().replace("-","/")
    if pair not in SUPPORTED_PAIRS: raise ValueError(f"Unsupported pair: {pair}")
    if days<1 or cost_pips<0: raise ValueError("days must be positive and cost_pips non-negative")
    if not isinstance(candles.index,pd.DatetimeIndex): raise ValueError("Candles need DatetimeIndex")
    x=candles.sort_index().copy()
    end=pd.Timestamp.now(tz="UTC"); start=end-pd.Timedelta(days=days)
    x=x.loc[(x.index>=start)&(x.index<=end)]
    if len(x)<WARMUP+20: raise ValueError(f"Insufficient history: need at least {WARMUP+20} candles")
    runs=[_run_config(pair,x,cost_pips,cfg) for cfg in CONFIGS]
    return {"pair":pair,"timeframe":"1min","requested_days":days,"candles":len(x),
            "data_start":x.index.min().isoformat(),"data_end":x.index.max().isoformat(),
            "cost_pips_assumption":cost_pips,"configs":runs,
            "note":"Experimental challenger only; fixed holding exits, no broker fills, no guaranteed profit."}

def run_v2_universe(data_dir: str|Path, days:int=90, cost_pips:float=2.0) -> dict:
    root=Path(data_dir); results={}; missing=[]; errors={}
    for pair in sorted(SUPPORTED_PAIRS):
        path=root/f"{pair.replace('/','')}.csv"
        if not path.exists(): missing.append(pair); continue
        try: results[pair]=backtest_v2_pair(pair,load_ohlc_csv(path),days,cost_pips)
        except Exception as exc: errors[pair]=str(exc)
    aggregate={}
    for cfg in CONFIGS:
        rows=[t for result in results.values() for run in result["configs"] if run["config"]["name"]==cfg["name"] for t in run["trades"]]
        aggregate[cfg["name"]]=_metrics(pd.DataFrame(rows))
    return {"paper_only":True,"universe_size":len(SUPPORTED_PAIRS),"tested_pairs":len(results),
            "missing_pairs":missing,"errors":errors,"aggregate_by_config":aggregate,"results":results}

def write_v2_report(report:dict, output_dir:str|Path)->None:
    out=Path(output_dir); out.mkdir(parents=True,exist_ok=True)
    (out/"summary_v2.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    rows=[t for r in report["results"].values() for c in r["configs"] for t in c["trades"]]
    pd.DataFrame(rows).to_csv(out/"trades_v2.csv",index=False)
    summary=[]
    for pair,r in report["results"].items():
        for c in r["configs"]:
            summary.append({"pair":pair,"config":c["config"]["name"],**c["all"],"out_of_sample":c["out_of_sample_30pct"]})
    pd.DataFrame(summary).to_csv(out/"pair_summary_v2.csv",index=False)
