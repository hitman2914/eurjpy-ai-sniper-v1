#!/usr/bin/env python3
"""Run the 90-day 21-pair paper backtest from local 1-minute OHLC CSV files.

Expected filenames: EURJPY.csv, GBPJPY.csv, etc.
Required columns: datetime, open, high, low, close; volume is optional.
"""
import argparse
import json
from pathlib import Path
from eurjpy_sniper.backtest import run_universe, write_report

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/backtest")
    parser.add_argument("--output-dir", default="backtest_output")
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--threshold", type=int, default=80)
    parser.add_argument("--cost-pips", type=float, default=2.0,
                        help="Assumed total round-trip cost per trade in pips; adjust to broker evidence.")
    args = parser.parse_args()
    report = run_universe(args.data_dir, args.days, args.threshold, args.cost_pips)
    write_report(report, args.output_dir)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    print(f"Full report: {Path(args.output_dir) / 'summary.json'}")

if __name__ == "__main__":
    main()
