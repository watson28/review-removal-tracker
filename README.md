# Review Removal Tracker (work in progress)

Detects when businesses on Google Maps are actively suppressing negative reviews. Tracks daily `userRatingCount` and `rating` per business, computes manipulation metrics, and surfaces patterns of review removal.

The core signal: if a business consistently loses reviews while its rating climbs, it is likely getting negative reviews removed. The system quantifies this pattern with a set of metrics and a composite Manipulation Confidence Score (MCS).

---

## Implementation status

### Done

- **Storage layer** — PostgreSQL schema with Alembic migrations: `businesses`, `daily_snapshots`, `computed_metrics`, `grid_cells`, `cell_activity` tables
- **Data models** — `Business`, `DailySnapshot`, `ComputedMetrics`, `GridCell`, `CellActivity` dataclasses
- **Google Places API client** — Nearby Search (grid pass), Place Details (fallback), Text Search (discovery)
- **Hex grid generator** — city-agnostic, driven by `config/cities/*.toml` (bounds, center, zone/cell radii); inner zone uses denser cells, outer zone coarser
- **Snapshot job** — every-2-days collection of `userRatingCount` and `rating` per tracked business
- **Discovery job** — Text Search seeding by category × district, city-aware via TOML config

### Pending

- **Cell-based collection pipeline** — use `grid_cells` + Nearby Search as the primary snapshot path, with Place Details only for businesses missed by the grid
- **Cell pruning** — deactivate cells that produce no hits after 2+ weeks of `cell_activity`
- **Computation layer** — job that reads `daily_snapshots` and writes `computed_metrics` over 14/30/90-day windows (snapshot-over-snapshot deltas)
- **Category median computation** — cross-business pass to derive CRI denominators
- **Dashboard** — Streamlit per-business timelines, MCS leaderboard, district/category filters, collection health view

---

## Commands

```bash
uv sync                                          # install dependencies
uv run pytest tests/                             # run all tests
uv run pytest tests/db/ -v                       # storage layer tests (requires Podman)
uv run pytest tests/data_collection/ -v          # collection layer tests (mocks, no DB)
uv run pytest tests/grid/ -v                     # hex-grid + city-config tests
uv run alembic upgrade head                      # apply migrations (requires DATABASE_URL)
uv run alembic revision --autogenerate -m "desc" # generate new migration
uv run pyrefly check src/ tests/ scripts/        # static type checking

# Operational scripts (each accepts --help)
uv run python scripts/generate_grid.py           # generate hex grid, load into grid_cells
uv run python scripts/generate_grid.py --dry-run # preview cell counts without DB writes
uv run python scripts/run_discovery.py           # seed businesses via Text Search
uv run python scripts/run_discovery.py --dry-run # preview queries without API/DB calls
uv run python scripts/run_collection.py          # fetch a snapshot for every active business
```

All scripts default to `config/cities/berlin.toml`; pass `--city PATH` to target a different city.

DB tests require Podman. The session fixture in `tests/db/conftest.py` starts and stops a `postgres:16` container on port 15432 automatically.

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GOOGLE_API_KEY` | Yes | Google Maps Platform API key |
| `SKIP_INACTIVE_DAYS` | No | Days of flat review count before skipping a business (default: 14) |
| `DB_POOL_SIZE` | No | SQLAlchemy pool size (default: 3) |
| `DB_MAX_OVERFLOW` | No | SQLAlchemy max overflow (default: 2) |
