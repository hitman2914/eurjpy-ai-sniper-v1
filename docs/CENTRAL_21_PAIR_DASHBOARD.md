# Central 21-pair dashboard

The existing EUR/JPY dashboard remains available at `/`. The new combined paper-only dashboard is available at `/dashboard`, with JSON status at `/api/central/status`.

## Architecture
- One Twelve Data `/time_series` batch request for all configured pairs, using comma-separated symbols and the 1-minute interval.
- 50-second in-process cache to avoid duplicate API calls from page refreshes.
- 21 independent analysis evaluations and pair-isolated SQLite paper journals.
- One-minute browser refresh while the dashboard is open.
- No broker integration, live orders, or real-money execution.

## Required environment
- `TWELVE_DATA_API_KEY`: private Twelve Data API key.
- `PAPER_STAKE`: simulated stake per paper trade (default 10).
- `MIN_SIGNAL_SCORE`: minimum heuristic score (default 80).
- `CENTRAL_PAPER_DB_PATH`: optional path for the central SQLite journal.

## Important limitations before full launch
- A 21-symbol batch still consumes 21 API credits per refresh; batching reduces HTTP round trips, not symbol credit usage.
- Confirm that the selected Twelve Data plan permits all 21 forex symbols, 1-minute history, and internal dashboard display.
- A batch can partially fail. The dashboard reports live-feed coverage per pair and must not treat missing/stale feeds as valid signals.
- The free Render web service sleeps when idle. This dashboard refreshes only while it is open; reliable unattended operation needs an always-on permitted worker/hosting arrangement and durable database storage.
- Render local filesystem storage may be ephemeral. Configure persistent storage or a managed database before relying on long-term journals.
- Candle-open paper fills are simplified simulations, not guaranteed executable fills. Scores are heuristics, not probabilities or profit guarantees.

## Deploy
The existing Render service can deploy this branch after it is merged. Keep its current environment variables. After deployment, open `/dashboard` on the phone. The existing EUR/JPY page at `/` remains intact.
