# Data sources

All URLs below were checked on 2026-10-18. NSE serves them as static files. Requests need a browser-like `User-Agent`. The ingest client throttles itself and caches every file under `data/raw/` so nothing is downloaded twice.

| Dataset | URL pattern | Coverage | Used for |
|---|---|---|---|
| Bhavcopy (UDiFF) | `nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{YYYYMMDD}_F_0000.csv.zip` | 2024-01-01 onward | Daily OHLCV, previous close, trades |
| Bhavcopy (legacy) | `nsearchives.nseindia.com/content/historical/EQUITIES/{YYYY}/{MON}/cm{DD}{MON}{YYYY}bhav.csv.zip` | Before 2024 | Same, for backfill |
| Full bhavdata | `nsearchives.nseindia.com/products/content/sec_bhavdata_full_{DDMMYYYY}.csv` | Recent years | Delivery quantity and delivery % |
| Index closes | `nsearchives.nseindia.com/content/indices/ind_close_all_{DDMMYYYY}.csv` | Recent years | Index OHLC, P/E, P/B, dividend yield |
| Index constituents | `nsearchives.nseindia.com/content/indices/ind_{name}list.csv` | Current list only | Universe and industry labels |

## Limits to know

- A weekday with no file is normally an exchange holiday. On the current day it can also mean the file is not published yet (usually by 18:00 IST), so today's run retries rather than recording a holiday.
- Constituent lists are current only. History of index membership starts from the first snapshot this project takes.
- NSE's terms restrict commercial redistribution. These files are fine for personal research (decision D2). A public product needs a licensed feed.
- There is no fundamentals data here. That needs a vendor or exchange XBRL filings in Phase 1.

## Candidates still to evaluate

- **Broker APIs** for intraday and cleaner history: Zerodha Kite Connect, Upstox, Angel One SmartAPI, Dhan. Each needs a trading account and API keys from the owner.
- **INDstocks API (INDmoney), the owner's broker (2026-10-23).** Per its own docs (not yet tested): the data API is free (₹10 per order applies only to orders placed through the API, which this app never does). It offers real-time quotes and depth, a WebSocket feed for up to 3,000 instruments per connection, historical candles at 1 min, 5 min, 15 min, 1 hour and daily ("10+ years" claimed), and an instrument master CSV. It needs an INDstocks account with KYC. The access token expires every 24 hours, so a daily re-login step is required. A static IP is needed only for orders. The docs say nothing about redistribution, so this is for personal use only. Docs: https://api-docs.indstocks.com/
- **Fundamentals:** a commercial vendor, or parsing XBRL results filed with NSE/BSE.
