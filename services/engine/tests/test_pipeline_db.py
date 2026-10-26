"""End-to-end pipeline test against a real Postgres + TimescaleDB.

Runs only when STOCKAI_TEST_DATABASE_URL points at a throwaway database. Its tables are dropped first.
"""

import io
import json
import os
import zipfile
from datetime import date

import psycopg
import pytest

from stockai import db
from stockai.ingest import pipeline
from stockai.prices import series

TEST_URL = os.environ.get("STOCKAI_TEST_DATABASE_URL")
pytestmark = [pytest.mark.db, pytest.mark.skipif(not TEST_URL, reason="STOCKAI_TEST_DATABASE_URL not set")]

HEADER = ("TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,"
          "OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,"
          "ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4")


def _row(day, symbol, o, h, low, c, prev, vol):
    return (f"{day},{day},CM,NSE,STK,1,INE{symbol[:6]:0<6}01011,{symbol},EQ,,,,,{symbol} LTD,"
            f"{o},{h},{low},{c},{c},{prev},,{c},,,{vol},{vol * c},10,F1,1,,,,,")


def _zip(lines):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("bhav.csv", "\n".join([HEADER, *lines]) + "\n")
    return buf.getvalue()


DAY1, DAY2 = date(2026, 10, 7), date(2026, 10, 8)
FILES = {
    "20261007_F_0000": _zip([_row("2026-10-07", "SPLITCO", 1290, 1310, 1280, 1300, 1290, 1000),
                             _row("2026-10-07", "STEADY", 100, 101, 99, 100, 99.5, 5000)]),
    "20261008_F_0000": _zip([_row("2026-10-08", "SPLITCO", 262, 265, 255, 258, 1300, 5200),
                             _row("2026-10-08", "STEADY", 100, 102, 99, 101, 100, 5100)]),
}
ACTIONS = json.dumps([{"symbol": "SPLITCO", "series": "EQ", "isin": "INE1", "exDate": "08-Oct-2026",
                       "subject": "Face Value Split (Sub-Division) - From Rs 10/- Per Share To Rs 2/- Per Share"}]).encode()


class FakeClient:
    def fetch(self, url, cache_key, use_cache=True, headers=None):
        if "corporates-corporateActions" in url:
            return ACTIONS
        for key, body in FILES.items():
            if key in url:
                return body
        return None


@pytest.fixture()
def conn(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_URL)
    with psycopg.connect(TEST_URL) as reset:
        reset.execute("DROP SCHEMA public CASCADE")
        reset.execute("CREATE SCHEMA public")
    # TimescaleDB must be created as the first command of a fresh session.
    with psycopg.connect(TEST_URL) as c:
        db.migrate(c)
        yield c


def test_split_is_applied_and_not_flagged(conn):
    client = FakeClient()
    results = pipeline.backfill(conn, client, DAY1, DAY2)
    assert [r.status for r in results] == ["ok", "ok"]
    assert results[1].adjustments == 1

    issues = conn.execute("SELECT check_name FROM data_quality_issues WHERE trade_date = %s", (DAY2,)).fetchall()
    assert ("extreme_move",) not in issues
    assert ("adjustment_applied",) in issues

    adjusted = series.load(conn, "SPLITCO")
    assert adjusted["close"].round(2).tolist() == [260.0, 258.0]
    assert adjusted["volume"].tolist() == [5000, 5200]
    raw = series.load(conn, "SPLITCO", adjusted=False)
    assert raw["close"].tolist() == [1300.0, 258.0]


def test_holiday_is_recorded_as_no_data(conn):
    [result] = pipeline.backfill(conn, FakeClient(), date(2026, 10, 2), date(2026, 10, 2))
    assert result.status == "no_data"
    status = conn.execute("SELECT status FROM ingest_runs WHERE trade_date = '2026-10-02'").fetchone()[0]
    assert status == "no_data"
