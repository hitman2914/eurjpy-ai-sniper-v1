import time
import requests
import pandas as pd
from .config import API_KEY, INTERVAL, SUPPORTED_PAIRS

# Cache both successful data and failures. This prevents the browser's 60-second
# polling from hammering Twelve Data while an account is rate-limited.
_cache = {"at": 0.0, "pairs": None, "errors": {}}
CACHE_SECONDS = 60


def _frame(payload):
    values = payload.get("values") if isinstance(payload, dict) else None
    if not values:
        message = payload.get("message", "No candle values") if isinstance(payload, dict) else "Invalid response"
        raise RuntimeError(str(message))
    df = pd.DataFrame(values)
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if "volume" not in df:
        df["volume"] = 0.0
    else:
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    df = df.dropna(subset=["open", "high", "low", "close"]).sort_values("datetime").set_index("datetime")
    df = df[df.index < pd.Timestamp.now(tz="UTC").floor("min")]
    if len(df) < 210:
        raise RuntimeError("Fewer than 210 completed 1-minute candles")
    if (pd.Timestamp.now(tz="UTC") - df.index[-1]).total_seconds() > 180:
        raise RuntimeError("Stale completed-candle feed")
    return df[["open", "high", "low", "close", "volume"]].tail(300)


def _all_errors(message):
    return {pair: message for pair in sorted(SUPPORTED_PAIRS)}


def fetch_all(force=False):
    if not API_KEY:
        return {}, _all_errors("TWELVE_DATA_API_KEY is not configured")

    if not force and _cache["pairs"] is not None and time.time() - _cache["at"] < CACHE_SECONDS:
        return {key: value.copy() for key, value in _cache["pairs"].items()}, dict(_cache["errors"])

    symbols = ",".join(sorted(SUPPORTED_PAIRS))
    try:
        response = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": symbols,
                "interval": INTERVAL,
                "outputsize": 300,
                "apikey": API_KEY,
                "format": "JSON",
                "timezone": "UTC",
            },
            timeout=25,
        )
        if response.status_code == 429:
            message = "Twelve Data rate limit reached (HTTP 429). Feeds paused; no paper signals will be opened until quota is available."
            _cache.update(at=time.time(), pairs={}, errors=_all_errors(message))
            return {}, dict(_cache["errors"])
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        # Never echo request URLs: Twelve Data API keys are sent as query params.
        status = getattr(getattr(exc, "response", None), "status_code", None)
        message = f"Twelve Data request failed (HTTP {status}). Feeds paused; check API quota and key in Render." if status else "Twelve Data connection failed. Feeds paused; check service/network logs."
        _cache.update(at=time.time(), pairs={}, errors=_all_errors(message))
        return {}, dict(_cache["errors"])
    except ValueError:
        message = "Twelve Data returned invalid JSON. Feeds paused."
        _cache.update(at=time.time(), pairs={}, errors=_all_errors(message))
        return {}, dict(_cache["errors"])

    pairs, errors = {}, {}
    if isinstance(payload, dict):
        for pair in sorted(SUPPORTED_PAIRS):
            try:
                pairs[pair] = _frame(payload.get(pair))
            except Exception as exc:
                # Provider error messages are safe to show; never include request URLs or credentials.
                errors[pair] = str(exc)[:180]
        if not pairs and payload.get("status") == "error":
            message = str(payload.get("message", "Twelve Data request failed"))[:180]
            errors = _all_errors(message)
    else:
        errors = _all_errors("Unexpected Twelve Data batch response")

    _cache.update(
        at=time.time(),
        pairs={key: value.copy() for key, value in pairs.items()},
        errors=dict(errors),
    )
    return pairs, errors
