# Multi-pair AI SNIPER setup

This codebase is configurable for the following 20 pairs:

CAD/JPY, GBP/JPY, GBP/AUD, CHF/JPY, EUR/CHF, USD/JPY, GBP/USD, USD/CHF, USD/CAD, GBP/CAD, AUD/CHF, GBP/CHF, EUR/AUD, AUD/CAD, EUR/CAD, AUD/JPY, EUR/USD, CAD/CHF, EUR/GBP, AUD/USD.

EUR/JPY remains the default deployment.

## One isolated bot deployment per pair

Create a separate Render web service from this repository for each pair. Use:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn run:app`
- Environment variable `PAIR`: exact pair, e.g. `GBP/JPY`
- Environment variable `TWELVE_DATA_API_KEY`: add privately in Render; never commit or share it
- Environment variable `PAPER_STAKE`: `10`
- Environment variable `MIN_SIGNAL_SCORE`: `80`
- Environment variable `PAPER_DB_PATH`: optional per-service database path

Each service has its own local SQLite paper journal. On Render free instances, local files may be ephemeral and the service sleeps when idle; use persistent storage or a managed database before treating journals as durable. Free web services are not guaranteed always-on background workers. The dashboard must be loaded to trigger its polling loop.

## Safety and validation

- Paper simulation only. No broker integration or live order execution.
- A score is a heuristic, not a probability or a promise of profit.
- The strategy thresholds are shared starting settings, not pair-specific optimization.
- Confirm the data feed actually returns fresh completed 1-minute candles for each symbol.
- Check the Twelve Data plan's symbol, API-credit, and display restrictions before launching many services.
- Deploy in small batches and inspect each pair independently before expanding.
- Current paper entry/exit references use the next candle's open and the following candle's open, respectively, when those completed bars become available. This is a candle-based simulation, not guaranteed executable fill pricing.
