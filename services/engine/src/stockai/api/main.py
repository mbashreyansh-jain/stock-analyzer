"""HTTP API the web app will call. Start with: uv run uvicorn stockai.api.main:app --reload"""

from datetime import date

from fastapi import FastAPI, HTTPException

from stockai import db
from stockai.prices import series

app = FastAPI(title="Stock AI engine", version="0.1.0")


@app.get("/health")
def health() -> dict:
    with db.connect() as conn:
        latest = conn.execute(
            "SELECT max(trade_date) FROM ingest_runs WHERE dataset = 'bhavcopy' AND status = 'ok'"
        ).fetchone()[0]
    return {"status": "ok", "latest_trading_day": latest}


@app.get("/instruments")
def instruments(index: str = "NIFTY 500") -> list[dict]:
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT i.symbol, i.name, i.industry, i.isin FROM instruments i
            JOIN index_members m ON m.instrument_id = i.id
            WHERE m.index_name = %s AND m.as_of = (SELECT max(as_of) FROM index_members WHERE index_name = %s)
            ORDER BY i.symbol
            """,
            (index.upper(), index.upper()),
        ).fetchall()
    return [{"symbol": s, "name": n, "industry": ind, "isin": isin} for s, n, ind, isin in rows]


@app.get("/prices/{symbol}")
def prices(symbol: str, start: date | None = None, end: date | None = None, adjusted: bool = True) -> list[dict]:
    with db.connect() as conn:
        try:
            df = series.load(conn, symbol, start, end, adjusted)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
    df["trade_date"] = df["trade_date"].astype(str)
    return df.astype(object).where(df.notna(), None).to_dict(orient="records")
