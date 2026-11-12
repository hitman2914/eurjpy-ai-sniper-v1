# Automated free Dukascopy 90-day backtest

The GitHub Actions workflow `.github/workflows/backtest-90d.yml` downloads 1-minute bid candles from Dukascopy's publicly available feed for the 21 configured FX pairs, runs the paper-only backtester, and uploads JSON/CSV results as a workflow artifact.

## Run it

1. Open the repository's **Actions** tab.
2. Select **Free 90-day 21-pair FX backtest**.
3. Tap **Run workflow** on the main branch.
4. Wait for the job to finish.
5. Download the artifact named `fx-21-pair-90-day-backtest`.

The workflow is manual to avoid repeatedly downloading a large dataset or placing unnecessary load on the data source.

## Important

- Dukascopy data is historical research data, not the Twelve Data live feed and not a promise of executable broker prices.
- The downloaded candles are BID-side by default. The backtester deducts an assumed 2.0 pip round-trip cost; this is only a rough placeholder and not a verified spread for the user's broker or trading hours.
- Pairs not available from the source are listed as missing; the workflow does not invent data.
- Results are paper simulations only. They do not place orders.
- The 70/30 split is chronological. Out-of-sample results should be considered more informative than in-sample results, but one 90-day window is not enough to establish future profitability.
