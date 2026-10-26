import io
import zipfile
from datetime import date

import pandas as pd

from stockai.data.nse import bhavcopy

UDIFF = """TradDt,BizDt,Sgmt,Src,FinInstrmTp,FinInstrmId,ISIN,TckrSymb,SctySrs,XpryDt,FininstrmActlXpryDt,StrkPric,OptnTp,FinInstrmNm,OpnPric,HghPric,LwPric,ClsPric,LastPric,PrvsClsgPric,UndrlygPric,SttlmPric,OpnIntrst,ChngInOpnIntrst,TtlTradgVol,TtlTrfVal,TtlNbOfTxsExctd,SsnId,NewBrdLotQty,Rmks,Rsvd1,Rsvd2,Rsvd3,Rsvd4
2026-10-16,2026-10-16,CM,NSE,STK,2885,INE002A01018,RELIANCE,EQ,,,,,RELIANCE INDUSTRIES LTD,1215.00,1215.40,1193.00,1211.20,1211.20,1215.00,,1211.19,,,17225283,20794678894.30,247276,F1,1,,,,,
2026-10-16,2026-10-16,CM,NSE,STK,19078,IN0020200104,SGBJUN28,GB,,,,,2.5%GOLDBONDS2028SR-III,14600.00,14649.85,14600.00,14649.85,14649.85,14594.81,,14649.85,,,4,58499.70,4,F1,1,,,,,
2026-10-16,2026-10-16,CM,NSE,STK,1,INE000000001,NATCO-RE,BE,,,,,NATCO RE,26.00,27.00,25.00,26.35,26.35,39.35,,26.35,,,100,2635.00,3,F1,1,,,,,
2026-10-16,2026-10-16,CM,NSE,STK,2,INE000000002,DUAL,EQ,,,,,DUAL LTD,10.00,11.00,9.00,10.50,10.50,10.00,,10.50,,,500,5250.00,10,F1,1,,,,,
2026-10-16,2026-10-16,CM,NSE,STK,3,INE000000002,DUAL,BE,,,,,DUAL LTD,10.00,10.00,10.00,10.00,10.00,10.00,,10.00,,,5,50.00,1,F1,1,,,,,
"""

LEGACY = """SYMBOL,SERIES,OPEN,HIGH,LOW,CLOSE,LAST,PREVCLOSE,TOTTRDQTY,TOTTRDVAL,TIMESTAMP,TOTALTRADES,ISIN,
TCS,EQ,3300,3350,3290,3340.5,3341,3310,1500000,5000000000,02-JAN-2023,90000,INE467B01029,
1018GS2026,GS,118,118,118,118,118,116,648,76464,02-JAN-2023,4,IN0020010081,
"""


def _zip(text: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("file.csv", text)
    return buf.getvalue()


def test_url_switches_format_on_udiff_start():
    assert bhavcopy.url_for(date(2024, 1, 2)).endswith("BhavCopy_NSE_CM_0_0_0_20240102_F_0000.csv.zip")
    assert bhavcopy.url_for(date(2023, 12, 29)).endswith("/2023/DEC/cm29DEC2023bhav.csv.zip")


def test_udiff_keeps_equities_only_and_normalises_columns():
    df = bhavcopy.parse(_zip(UDIFF), date(2026, 10, 16))
    assert list(df.columns) == bhavcopy.PRICE_COLUMNS
    assert set(df["symbol"]) == {"RELIANCE", "DUAL"}  # bond and rights entitlement dropped
    rel = df.set_index("symbol").loc["RELIANCE"]
    assert rel["close"] == 1211.20 and rel["prev_close"] == 1215.00
    assert rel["volume"] == 17225283 and rel["name"] == "RELIANCE INDUSTRIES LTD"


def test_duplicate_symbol_keeps_higher_volume_series():
    df = bhavcopy.parse(_zip(UDIFF), date(2026, 10, 16)).set_index("symbol")
    assert df.loc["DUAL", "series"] == "EQ"


def test_legacy_format():
    df = bhavcopy.parse(_zip(LEGACY), date(2023, 1, 2))
    assert list(df["symbol"]) == ["TCS"]
    row = df.iloc[0]
    assert row["close"] == 3340.5 and row["volume"] == 1500000 and row["trades"] == 90000
    assert pd.isna(row["name"])
