-- Corporate actions come from NSE's feed instead of being inferred from previous close,
-- because NSE's previous close turned out not to be adjusted for splits (see docs/decisions.md D6).

CREATE TABLE corporate_actions (
    symbol      text NOT NULL,
    isin        text,
    series      text,
    ex_date     date NOT NULL,
    subject     text NOT NULL,
    kind        text NOT NULL,
    factor      numeric(20,12),
    fetched_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, ex_date, subject)
);
CREATE INDEX corporate_actions_kind_idx ON corporate_actions (kind, ex_date);

DROP TABLE price_adjustments;
CREATE TABLE price_adjustments (
    instrument_id  integer NOT NULL REFERENCES instruments(id),
    ex_date        date NOT NULL,
    factor         numeric(20,12) NOT NULL,
    kinds          text NOT NULL,
    source         text NOT NULL CHECK (source IN ('corporate_action', 'market_implied')),
    PRIMARY KEY (instrument_id, ex_date)
);
