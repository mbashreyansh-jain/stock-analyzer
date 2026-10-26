from stockai.data.nse import delivery, indices

DELIVERY = b"""SYMBOL, SERIES, DATE1, PREV_CLOSE, OPEN_PRICE, HIGH_PRICE, LOW_PRICE, LAST_PRICE, CLOSE_PRICE, AVG_PRICE, TTL_TRD_QNTY, TURNOVER_LACS, NO_OF_TRADES, DELIV_QTY, DELIV_PER
20MICRONS, EQ, 16-Oct-2026, 192.42, 192.90, 195.49, 191.25, 191.25, 193.32, 193.71, 52159, 101.04, 1939, 21843, 41.88
BHAGYANGR, BE, 08-Oct-2026, 454.55, 39.00, 41.40, 39.00, 41.40, 41.40, 40.86, 118087, 48.25, 269, -, -
"""

CLOSES = b"""Index Name,Index Date,Open Index Value,High Index Value,Low Index Value,Closing Index Value,Points Change,Change(%),Volume,Turnover (Rs. Cr.),P/E,P/B,Div Yield
Nifty 50,16-10-2026,23065.1,23149.85,22913.8,23146.15,148.8,.65,391557143,38621.86,19.77,2.84,1.49
India VIX,16-10-2026,13.1,13.4,12.5,12.84,-0.41,-3.1,-,-,-,-,-
"""

CONSTITUENTS = b"""Company Name,Industry,Symbol,Series,ISIN Code
360 ONE WAM Ltd.,Financial Services,360ONE,EQ,INE466L01038
Dummy Holding,Financial Services,DUMMYHEG,EQ,INE000000000
"""


def test_delivery_drops_rows_without_delivery_data():
    df = delivery.parse(DELIVERY)
    assert list(df["symbol"]) == ["20MICRONS"]
    assert df.iloc[0]["delivery_qty"] == 21843 and df.iloc[0]["delivery_pct"] == 41.88


def test_index_closes_handle_missing_values():
    df = indices.parse_closes(CLOSES).set_index("index_name")
    assert df.loc["NIFTY 50", "close"] == 23146.15 and df.loc["NIFTY 50", "pe"] == 19.77
    assert df.loc["INDIA VIX", "close"] == 12.84
    assert str(df.loc["INDIA VIX", "pe"]) == "nan"


def test_constituents_drop_placeholders():
    df = indices.parse_constituents(CONSTITUENTS)
    assert list(df["symbol"]) == ["360ONE"]
    assert df.iloc[0]["industry"] == "Financial Services"
