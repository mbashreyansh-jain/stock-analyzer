"""Daily equity bhavcopy: download URLs and parsers for the UDiFF and legacy formats.

Both parsers return the same columns (see PRICE_COLUMNS) so the rest of the engine
does not care which format a day came from.
"""

import io
import zipfile
from datetime import date

import pandas as pd

UDIFF_START = date(2024, 1, 1)
# EQ/BE/BZ are shares, RR are REITs and IV are InvITs (some sit in NIFTY 500).
EQUITY_SERIES = ("EQ", "BE", "BZ", "RR", "IV")

PRICE_COLUMNS = [
    "symbol", "isin", "name", "series", "open", "high", "low", "close",
    "last", "prev_close", "volume", "turnover", "trades",
]


def url_for(day: date) -> str:
    if day >= UDIFF_START:
        return f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day:%Y%m%d}_F_0000.csv.zip"
    mon = day.strftime("%b").upper()
    return f"https://nsearchives.nseindia.com/content/historical/EQUITIES/{day:%Y}/{mon}/cm{day:%d}{mon}{day:%Y}bhav.csv.zip"


def cache_key_for(day: date) -> str:
    return f"bhavcopy/{day:%Y}/{day:%Y%m%d}.csv.zip"


def _read_zipped_csv(raw: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        name = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        with zf.open(name) as fh:
            return pd.read_csv(fh, dtype=str, keep_default_na=False)


def parse(raw: bytes, day: date, series: tuple[str, ...] = EQUITY_SERIES) -> pd.DataFrame:
    """Parse a zipped bhavcopy into PRICE_COLUMNS, keeping only the given series."""
    df = _read_zipped_csv(raw)
    return parse_udiff(df, series) if day >= UDIFF_START else parse_legacy(df, series)


def parse_udiff(df: pd.DataFrame, series: tuple[str, ...] = EQUITY_SERIES) -> pd.DataFrame:
    df = df[(df["FinInstrmTp"] == "STK") & (df["SctySrs"].isin(series))]
    out = pd.DataFrame({
        "symbol": df["TckrSymb"].str.strip(),
        "isin": df["ISIN"].str.strip(),
        "name": df["FinInstrmNm"].str.strip(),
        "series": df["SctySrs"].str.strip(),
        "open": df["OpnPric"],
        "high": df["HghPric"],
        "low": df["LwPric"],
        "close": df["ClsPric"],
        "last": df["LastPric"],
        "prev_close": df["PrvsClsgPric"],
        "volume": df["TtlTradgVol"],
        "turnover": df["TtlTrfVal"],
        "trades": df["TtlNbOfTxsExctd"],
    })
    return _coerce(out)


def parse_legacy(df: pd.DataFrame, series: tuple[str, ...] = EQUITY_SERIES) -> pd.DataFrame:
    df = df.rename(columns=lambda c: c.strip())
    df = df[df["SERIES"].str.strip().isin(series)]
    out = pd.DataFrame({
        "symbol": df["SYMBOL"].str.strip(),
        "isin": df["ISIN"].str.strip(),
        "name": None,
        "series": df["SERIES"].str.strip(),
        "open": df["OPEN"],
        "high": df["HIGH"],
        "low": df["LOW"],
        "close": df["CLOSE"],
        "last": df["LAST"],
        "prev_close": df["PREVCLOSE"],
        "volume": df["TOTTRDQTY"],
        "turnover": df["TOTTRDVAL"],
        "trades": df["TOTALTRADES"],
    })
    return _coerce(out)


def _coerce(out: pd.DataFrame) -> pd.DataFrame:
    for col in ("open", "high", "low", "close", "last", "prev_close", "turnover"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ("volume", "trades"):
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype("int64")
    # Rights entitlements (e.g. NATCO-RE) trade for a few weeks only and are not shares.
    out = out[~out["symbol"].str.endswith("-RE")]
    # A symbol can briefly appear in two series on the same day. Keep the one with more volume.
    out = out.sort_values("volume", ascending=False).drop_duplicates("symbol", keep="first")
    return out.sort_values("symbol").reset_index(drop=True)[PRICE_COLUMNS]
