"""Index closing values (with P/E, P/B, dividend yield) and index constituent lists."""

import io
from datetime import date

import pandas as pd

# Constituent list files published by NSE, keyed by the index name we store.
CONSTITUENT_FILES = {
    "NIFTY 50": "ind_nifty50list.csv",
    "NIFTY NEXT 50": "ind_niftynext50list.csv",
    "NIFTY 500": "ind_nifty500list.csv",
}


def close_url_for(day: date) -> str:
    return f"https://nsearchives.nseindia.com/content/indices/ind_close_all_{day:%d%m%Y}.csv"


def close_cache_key_for(day: date) -> str:
    return f"indices/{day:%Y}/{day:%Y%m%d}.csv"


def constituents_url(index_name: str) -> str:
    return f"https://nsearchives.nseindia.com/content/indices/{CONSTITUENT_FILES[index_name]}"


def parse_closes(raw: bytes) -> pd.DataFrame:
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    df = df.rename(columns=lambda c: c.strip())

    def num(col: str) -> pd.Series:
        return pd.to_numeric(df[col].str.strip().replace({"-": None, "": None}), errors="coerce")

    out = pd.DataFrame({
        "index_name": df["Index Name"].str.strip().str.upper(),
        "open": num("Open Index Value"),
        "high": num("High Index Value"),
        "low": num("Low Index Value"),
        "close": num("Closing Index Value"),
        "pe": num("P/E"),
        "pb": num("P/B"),
        "div_yield": num("Div Yield"),
        "volume": num("Volume"),
        "turnover_cr": num("Turnover (Rs. Cr.)"),
    })
    out = out.dropna(subset=["close"])
    out["volume"] = out["volume"].astype("Int64")
    return out.drop_duplicates("index_name").reset_index(drop=True)


def parse_constituents(raw: bytes) -> pd.DataFrame:
    """Return symbol, name, industry, isin for each member of the index."""
    df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    df = df.rename(columns=lambda c: c.strip())
    # NSE lists placeholder rows such as DUMMYHEG for pending index changes.
    df = df[~df["Symbol"].str.strip().str.startswith("DUMMY")]
    return pd.DataFrame({
        "symbol": df["Symbol"].str.strip(),
        "name": df["Company Name"].str.strip(),
        "industry": df["Industry"].str.strip(),
        "isin": df["ISIN Code"].str.strip(),
    })
