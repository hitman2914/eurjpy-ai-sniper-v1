"""Leakage-aware historical backtest for the existing paper signal rules.

Input candles must be timestamped 1-minute OHLC data. Signals are evaluated only
on completed candles; entry is next candle open; exit is the following candle
open. A fixed round-trip cost in pips is deducted from each trade.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import pandas as pd

from .agents import decide
from .config import SUPPORTED_PAIRS, MIN_SIGNAL_SCORE
from .indicators import enrich

WARMUP_BARS = 220
DEFAULT_DAYS = 90
DEFAULT_COST_PIPS = 2.0


def pip_size(pair: str) -> float:
    return 0.01 if pair.endswith("/JPY") else 0.0001


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    cols = {str(c).strip().lower(): c for c in df.columns}
    time_col = next((cols[k] for k in ("datetime", "timestamp", "time", "date") if k in cols), None)
    if time_col is None:
        raise ValueError("CSV needs a datetime, timestamp, time, or date column")
    required = ("open", "high", "low", "close")
    if any(k not in cols for k in required):
        raise ValueError("CSV needs open, high, low, close columns")
    out = pd.DataFrame(index=pd.to_datetime(df[time_col], utc=True, errors="coerce"))
    for key in required:
        out[key] = pd.to_numeric(df[cols[key]], errors="coerce").to_numpy()
    out["volume"] = pd.to_numeric(df[cols["volume"]], errors="coerce").fillna(0).to_numpy() if "volume" in cols else 0.0
    out.index.name = "datetime"
    out = out[~out.index.isna()].dropna(subset=list(required))
    out = out[~out.index.duplicated(keep="last")].sort_index()
    if (out[["open", "high", "low", "close"]] <= 0).any().any():
        raise ValueError("OHLC prices must be positive")
    if not (out["high"] >= out[["open", "close", "low"]].max(axis=1)).all():
        raise ValueError("Invalid OHLC: high is below another candle price")
    if not (out["low"] <= out[["open", "close", "high"]].min(axis=1)).all():
        raise ValueError("Invalid OHLC: low is above another candle price")
    return out[["open", "high", "low", "close", "volume"]]


def _metrics(trades: pd.DataFrame) -> dict:
    if trades.empty:
        return {"trades": 0, "wins": 0, "losses": 0, "breakeven": 0,
                "win_rate_pct": None, "net_pips": 0.0, "gross_profit_pips": 0.0,
                "gross_loss_pips": 0.0, "profit_factor": None, "max_drawdown_pips": 0.0}
    pnl = trades["net_pips"].astype(float)
    wins = int((pnl > 0).sum())
    losses = int((pnl < 0).sum())
    breakeven = int((pnl == 0).sum())
    gross_profit = float(pnl[pnl > 0].sum())
    gross_loss = float(-pnl[pnl < 0].sum())
    curve = pnl.cumsum()
    drawdown = curve - curve.cummax().clip(lower=0)
    return {
        "trades": int(len(trades)), "wins": wins, "losses": losses, "breakeven": breakeven,
        "win_rate_pct": round(wins / (wins + losses) * 100, 2) if wins + losses else None,
        "net_pips": round(float(pnl.sum()), 2),
        "gross_profit_pips": round(gross_profit, 2),
        "gross_loss_pips": round(gross_loss, 2),
        "profit_factor": round(gross_profit / gross_loss, 3) if gross_loss else (None if gross_profit == 0 else "inf"),
        "max_drawdown_pips": round(float(-drawdown.min()), 2),
    }


def backtest_pair(pair: str, candles: pd.DataFrame, days: int = DEFAULT_DAYS,
                  threshold: int = MIN_SIGNAL_SCORE, cost_pips: float = DEFAULT_COST_PIPS) -> dict:
    pair = pair.upper().replace("-", "/")
    if pair not in SUPPORTED_PAIRS:
        raise ValueError(f"Unsupported pair: {pair}")
    if days < 1 or cost_pips < 0:
        raise ValueError("days must be positive and cost_pips cannot be negative")
    if not isinstance(candles.index, pd.DatetimeIndex):
        raise ValueError("Candles must use a DatetimeIndex")
    x = candles.sort_index().copy()
    now = pd.Timestamp.now(tz="UTC")
    end = now
    start = now - pd.Timedelta(days=days)
    x = x.loc[(x.index >= start) & (x.index <= end)]
    if len(x) < WARMUP_BARS + 3:
        raise ValueError(f"Insufficient history: need at least {WARMUP_BARS + 3} one-minute candles")
    if x.index.has_duplicates:
        raise ValueError("Duplicate candle timestamps")
    enriched = enrich(x)
    rows = []
    pip = pip_size(pair)
    # i is the last fully closed signal candle; next open is entry, next-next open is exit.
    for i in range(WARMUP_BARS, len(enriched) - 2):
        signal_time, entry_time, exit_time = enriched.index[i:i + 3]
        if (entry_time - signal_time).total_seconds() > 90 or (exit_time - entry_time).total_seconds() > 90:
            continue
        history = enriched.iloc[:i + 1]
        decision = decide(history, threshold, pair=pair)
        side = decision["signal"]
        if side not in ("CALL", "PUT"):
            continue
        entry = float(x.loc[entry_time, "open"])
        exit_price = float(x.loc[exit_time, "open"])
        raw_pips = (exit_price - entry) / pip
        if side == "PUT":
            raw_pips = -raw_pips
        net_pips = raw_pips - cost_pips
        rows.append({
            "pair": pair, "signal_time": signal_time.isoformat(),
            "entry_time": entry_time.isoformat(), "exit_time": exit_time.isoformat(),
            "side": side, "score": int(decision["score"]), "entry": entry,
            "exit": exit_price, "gross_pips": round(raw_pips, 3),
            "cost_pips": float(cost_pips), "net_pips": round(net_pips, 3),
            "outcome": "WIN" if net_pips > 0 else "LOSS" if net_pips < 0 else "BREAKEVEN",
        })
    trades = pd.DataFrame(rows)
    if trades.empty:
        train, test = trades, trades
        split_time = None
    else:
        split = max(1, min(len(trades) - 1, int(len(trades) * 0.70))) if len(trades) > 1 else len(trades)
        train, test = trades.iloc[:split], trades.iloc[split:]
        split_time = trades.iloc[split]["signal_time"] if split < len(trades) else None
    return {
        "pair": pair, "timeframe": "1min", "requested_days": days,
        "window_start": start.isoformat(), "window_end": end.isoformat(),
        "data_start": x.index.min().isoformat(), "data_end": x.index.max().isoformat(),
        "start_coverage_lag_hours": round((x.index.min() - start).total_seconds() / 3600, 2),
        "end_data_age_hours": round((end - x.index.max()).total_seconds() / 3600, 2),
        "candles": int(len(x)), "warmup_bars": WARMUP_BARS,
        "coverage_warning": ("Data does not span the full requested window; interpret results cautiously." if (x.index.min() - start) > pd.Timedelta(days=1) or (end - x.index.max()) > pd.Timedelta(days=3) else None),
        "threshold": int(threshold), "round_trip_cost_pips_assumption": float(cost_pips),
        "trade_count": int(len(trades)), "all": _metrics(trades),
        "in_sample_70pct": _metrics(train), "out_of_sample_30pct": _metrics(test),
        "out_of_sample_start": split_time, "trades": rows,
        "limitations": [
            "Win rate is historical strategy performance, not a probability or guarantee.",
            "Entry and exit use next-candle opens; real fills may differ.",
            "A fixed round-trip pip cost is an assumption, not a broker quote.",
            "Only supplied CSV history is tested; gaps are skipped, not fabricated.",
            "The 70/30 split is chronological; no parameter tuning is performed.",
        ],
    }


def run_universe(data_dir: str | Path, days: int = DEFAULT_DAYS,
                 threshold: int = MIN_SIGNAL_SCORE, cost_pips: float = DEFAULT_COST_PIPS) -> dict:
    root = Path(data_dir)
    results, missing, errors = {}, [], {}
    for pair in sorted(SUPPORTED_PAIRS):
        slug = pair.replace("/", "")
        path = root / f"{slug}.csv"
        if not path.exists():
            missing.append(pair)
            continue
        try:
            results[pair] = backtest_pair(pair, load_ohlc_csv(path), days, threshold, cost_pips)
        except Exception as exc:
            errors[pair] = str(exc)
    return {
        "paper_only": True, "universe_size": len(SUPPORTED_PAIRS),
        "tested_pairs": len(results), "missing_pairs": missing, "errors": errors,
        "results": results,
        "aggregate": _metrics(pd.DataFrame(
            [trade for result in results.values() for trade in result["trades"]]
        )),
        "warning": "Aggregate combines pip results across different FX pairs; use per-pair metrics for meaningful comparison.",
    }


def write_report(report: dict, output_dir: str | Path) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = [trade for result in report["results"].values() for trade in result["trades"]]
    pd.DataFrame(rows).to_csv(out / "trades.csv", index=False)
    summary_rows = []
    for pair, result in report["results"].items():
        summary_rows.append({"pair": pair, **{k: result["all"][k] for k in
            ("trades", "wins", "losses", "breakeven", "win_rate_pct", "net_pips", "profit_factor", "max_drawdown_pips")},
            "out_of_sample": result["out_of_sample_30pct"]})
    pd.DataFrame(summary_rows).to_csv(out / "pair_summary.csv", index=False)
