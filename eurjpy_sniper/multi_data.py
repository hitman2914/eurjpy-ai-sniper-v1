import time
import requests
import pandas as pd
from .config import API_KEY, INTERVAL, SUPPORTED_PAIRS

_cache = {"at": 0.0, "pairs": None, "errors": {}}
CACHE_SECONDS = 50

def _frame(payload):
    values = payload.get("values") if isinstance(payload, dict) else None
    if not values:
        raise RuntimeError(payload.get("message", "No candle values") if isinstance(payload, dict) else "Invalid response")
    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df: df["volume"] = 0.0
    else: df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("datetime").set_index("datetime")
    df = df[df.index < pd.Timestamp.now(tz="UTC").floor("min")]
    if len(df) < 210: raise RuntimeError("Fewer than 210 completed 1-minute candles")
    if (pd.Timestamp.now(tz="UTC") - df.index[-1]).total_seconds() > 180: raise RuntimeError("Stale completed-candle feed")
    return df[["open", "high", "low", "close", "volume"]].tail(300)

def fetch_all(force=False):
    if not API_KEY: return {}, {p:"TWELVE_DATA_API_KEY is not configured" for p in sorted(SUPPORTED_PAIRS)}
    if not force and _cache["pairs"] is not None and time.time()-_cache["at"] < CACHE_SECONDS:
        return {k:v.copy() for k,v in _cache["pairs"].items()}, dict(_cache["errors"])
    symbols=",".join(sorted(SUPPORTED_PAIRS))
    response=requests.get("https://api.twelvedata.com/time_series",
        params={"symbol":symbols,"interval":INTERVAL,"outputsize":300,"apikey":API_KEY,"format":"JSON","timezone":"UTC"},timeout=25)
    response.raise_for_status(); payload=response.json(); pairs={}; errors={}
    if isinstance(payload,dict):
        for pair in sorted(SUPPORTED_PAIRS):
            item=payload.get(pair)
            try:
                pairs[pair]=_frame(item)
            except Exception as exc:
                errors[pair]=str(exc)
        if not pairs and payload.get("status")=="error":
            errors={p:payload.get("message","Twelve Data request failed") for p in sorted(SUPPORTED_PAIRS)}
    else: errors={p:"Unexpected Twelve Data batch response" for p in sorted(SUPPORTED_PAIRS)}
    _cache.update(at=time.time(),pairs={k:v.copy() for k,v in pairs.items()},errors=dict(errors))
    return pairs,errors
