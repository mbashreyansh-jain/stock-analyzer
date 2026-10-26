# Stock AI

AI-assisted stock research for NSE (India). Product blueprint: https://claude.ai/artifact/AN8uJpPLf5BVU3hQCpHnb8

**New here and not a developer? Read [START-HERE.md](START-HERE.md) instead. To run the website on a Windows PC, follow [LOCAL-SERVER-SETUP.md](LOCAL-SERVER-SETUP.md).**

## Layout

| Path | What it is |
|---|---|
| `services/engine` | Python engine: NSE data ingest, adjustments, quality checks, and the website (`stockai.web`: sign-in, roles, blog, Gemini, pages) |
| `apps/web` | Website frontend: the approved pages (`pages/`, unchanged copies of `design/`), the shim and app scripts, sign-in/invite/admin pages (`static/`) |
| `db/migrations` | Numbered SQL migrations, applied by `stockai migrate` |
| `design/` | The approved prototypes (source of `apps/web/pages`) |
| `packages/ui` | Design tokens (`tokens.css`) |
| `docs/decisions.md` | Why things are the way they are |
| `docs/data-sources.md` | Every external URL the engine calls |
| `data/` | Local only, git-ignored: raw NSE file cache and logs |

## Website quick start (Windows, PostgreSQL 17 installed)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .\services\engine
.\.venv\Scripts\stockai.exe migrate
.\.venv\Scripts\stockai.exe create-admin --email you@example.com --name "Your Name"
.\.venv\Scripts\stockai.exe seed-blog
.\.venv\Scripts\stockai.exe serve
```

Then open http://localhost:8000. Settings come from `.env` (see `.env.example`).

## Developer quick start

Needs Docker, [uv](https://docs.astral.sh/uv/) and Python 3.12+.

```bash
cp .env.example .env
docker compose up -d --wait
cd services/engine
uv sync
uv run stockai migrate
uv run stockai universe
uv run stockai backfill --start 2023-10-02
uv run stockai status
```

Other commands: `uv run stockai --help`. API: `uv run uvicorn stockai.api.main:app --reload`, then open http://localhost:8000/docs.

## Tests

```bash
cd services/engine
uv run pytest -q
```

The end-to-end test in `tests/test_pipeline_db.py` runs only when `STOCKAI_TEST_DATABASE_URL` points at a throwaway database, because it drops every table there first. Locally:

```bash
STOCKAI_TEST_DATABASE_URL=postgresql://stockai:stockai@localhost:5433/stockai_test uv run pytest -q
```

## Data model (Phase 0)

- `instruments`: one row per NSE symbol, with ISIN, name and NIFTY industry
- `index_members`: dated snapshots of NIFTY 50, NIFTY NEXT 50 and NIFTY 500 membership
- `prices_daily`: raw OHLCV, previous close and delivery % per trading day (Timescale hypertable)
- `corporate_actions`: NSE's feed, with each subject parsed into a kind and factor
- `price_adjustments`: one combined split/bonus/demerger factor per stock and ex-date
- `index_daily`: NIFTY and sector index OHLC with P/E, P/B, dividend yield
- `ingest_runs`, `data_quality_issues`: what was loaded each day and what looked wrong
