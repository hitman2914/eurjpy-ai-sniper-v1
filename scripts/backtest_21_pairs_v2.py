#!/usr/bin/env python3
import argparse, json
from eurjpy_sniper.backtest_v2 import run_v2_universe, write_v2_report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir",default="data/backtest")
    p.add_argument("--output-dir",default="backtest_v2_output")
    p.add_argument("--days",type=int,default=90)
    p.add_argument("--cost-pips",type=float,default=2.0)
    a=p.parse_args()
    report=run_v2_universe(a.data_dir,a.days,a.cost_pips)
    write_v2_report(report,a.output_dir)
    print(json.dumps({k:v for k,v in report.items() if k!="results"},indent=2))
    print("Full v2 report:",a.output_dir+"/summary_v2.json")
if __name__=="__main__": main()
