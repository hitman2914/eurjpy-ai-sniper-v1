# 90-day / 21-pair historical backtest (paper only)

## Status

This adds the backtest engine and reporting CLI. It does **not** claim historical results until valid historical files are supplied. The current Twelve Data quota error means the live dashboard cannot supply this 21-symbol dataset for free at one-minute cadence.

## Data format

Place one CSV per pair in `data/backtest/`, named by pair without slash:
`EURJPY.csv`, `GBPJPY.csv`, `EURUSD.csv`, etc.

Required columns: `datetime,open,high,low,close`. Optional: `volume`.
Timestamps are parsed as UTC. Data must be 1-minute OHLC, sorted and unique. Missing candles are skipped; no synthetic candles are generated.

## Run

From the repository root in a Python environment with `requirements.txt` installed:

```bash
python scripts/backtest_21_pairs.py --data-dir data/backtest --output-dir backtest_output --days 90 --threshold 80 --cost-pips 2.0
```

Outputs:
- `backtest_output/summary.json`: pair-level metrics, train/test split, coverage and missing data
- `backtest_output/pair_summary.csv`: compact per-pair comparison
- `backtest_output/trades.csv`: every simulated trade

## Execution assumptions and safeguards

- Existing strategy and seven-agent decision logic are reused with threshold 80.
- Indicators are calculated causally; each signal sees only candles available at that signal close.
- Signal at candle close *i*, entry at candle *i+1* open, exit at candle *i+2* open.
- Chronological 70% in-sample / 30% out-of-sample split; no random shuffle.
- Default total round-trip cost is an explicit **assumption** of 2.0 pips, not a broker spread quote. Run alternate cost scenarios before drawing conclusions.
- Win rate excludes breakeven trades. Profit factor and max drawdown are reported in pips.
- The aggregate combines pips across pairs and is only a rough overview; compare per-pair results.
- No broker connection, live orders, or paper-journal writes occur.

## Important limitations

A 90-day 1-minute history is about 129,600 candles per pair (roughly 2.7 million candles for 21 pairs). This engine needs actual source files. Do not substitute current prices, repeat candles, or fabricate missing history. Public/free data availability, redistribution rights, timestamp conventions and historical coverage must be verified for the chosen provider. A free real-time quota does not imply free access to 90-day intraday history.
