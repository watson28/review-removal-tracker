# Review Removal Tracker (work in progress)

Detects when businesses on Google Maps are actively suppressing negative reviews. Tracks daily `userRatingCount` and `rating` per business, computes manipulation metrics, and surfaces patterns of review removal.

The core signal: if a business consistently loses reviews while its rating climbs, it is likely getting negative reviews removed. The system quantifies this pattern with a set of metrics and a composite Manipulation Confidence Score (MCS).

---

## Implementation status

### Done

- **Storage layer** — PostgreSQL schema with Alembic migrations: `businesses`, `daily_snapshots`, `computed_metrics` tables
- **Data models** — `Business`, `DailySnapshot`, `ComputedMetrics` dataclasses
- **Google Places API client** — Place Details (daily snapshots) and Text Search (discovery)
- **Snapshot job** — daily collection of `userRatingCount` and `rating` per tracked business
- **Discovery job** — weekly Text Search to find new businesses by category and district

### Pending

- **Computation layer** — job that reads `daily_snapshots` and writes `computed_metrics`
- **Category median computation** — cross-business pass to derive CRI denominators
- **Discovery strategy** — switch from per-district queries to geographic grid (`locationRestriction: rectangle`) for broader and more uniform coverage
- **Adaptive polling** — daily snapshots for high-MCS or recently active businesses, reduced frequency for stable ones

---

## Commands

```bash
uv sync                                          # install dependencies
uv run pytest tests/                             # run all tests
uv run pytest tests/db/ -v                       # storage layer tests (requires Podman)
uv run pytest tests/data_collection/ -v          # collection layer tests (mocks, no DB)
uv run alembic upgrade head                      # apply migrations (requires DATABASE_URL)
uv run alembic revision --autogenerate -m "desc" # generate new migration
uv run pyrefly check src/ tests/                 # static type checking
uv run run-snapshot                              # run daily snapshot job
uv run run-discovery                             # run weekly discovery job
```

DB tests require Podman. The session fixture in `tests/db/conftest.py` starts and stops a `postgres:16` container on port 15432 automatically.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GOOGLE_API_KEY` | Yes | Google Maps Platform API key |
| `DISCOVERY_QUERIES` | No | Semicolon-separated `category:district` pairs, e.g. `restaurant:Mitte;hotel:Kreuzberg` |
| `SKIP_INACTIVE_DAYS` | No | Days of flat review count before skipping a business (default: 14) |
| `DB_POOL_SIZE` | No | SQLAlchemy pool size (default: 3) |
| `DB_MAX_OVERFLOW` | No | SQLAlchemy max overflow (default: 2) |
