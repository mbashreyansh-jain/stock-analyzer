-- Core tables for instruments, daily prices, adjustments and ingest bookkeeping.
-- TimescaleDB is used where it is installed (the cloud server). A plain PostgreSQL install
-- (for example on Windows for local development) works too: the price tables stay ordinary tables.

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
        CREATE EXTENSION IF NOT EXISTS timescaledb;
    END IF;
END $$;

CREATE TABLE instruments (
    id          serial PRIMARY KEY,
    symbol      text NOT NULL UNIQUE,
    isin        text,
    name        text,
    series      text,
    industry    text,
    is_active   boolean NOT NULL DEFAULT true,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Snapshot of index membership on a given day, so backtests can use the list as it was then.
CREATE TABLE index_members (
    index_name     text NOT NULL,
    as_of          date NOT NULL,
    instrument_id  integer NOT NULL REFERENCES instruments(id),
    PRIMARY KEY (index_name, as_of, instrument_id)
);

-- Raw, unadjusted daily prices exactly as NSE reported them.
CREATE TABLE prices_daily (
    instrument_id  integer NOT NULL REFERENCES instruments(id),
    trade_date     date NOT NULL,
    series         text NOT NULL,
    open           numeric(14,4) NOT NULL,
    high           numeric(14,4) NOT NULL,
    low            numeric(14,4) NOT NULL,
    close          numeric(14,4) NOT NULL,
    last           numeric(14,4),
    prev_close     numeric(14,4),
    volume         bigint NOT NULL,
    turnover       numeric(20,2),
    trades         integer,
    delivery_qty   bigint,
    delivery_pct   numeric(6,2),
    source         text NOT NULL,
    PRIMARY KEY (instrument_id, trade_date)
);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('prices_daily', by_range('trade_date', INTERVAL '1 year'));
    END IF;
END $$;

-- Split, bonus and similar adjustments. Prices before ex_date are multiplied by factor.
CREATE TABLE price_adjustments (
    instrument_id        integer NOT NULL REFERENCES instruments(id),
    ex_date              date NOT NULL,
    factor               numeric(20,12) NOT NULL,
    reported_prev_close  numeric(14,4) NOT NULL,
    actual_prev_close    numeric(14,4) NOT NULL,
    source               text NOT NULL DEFAULT 'derived_prev_close',
    PRIMARY KEY (instrument_id, ex_date)
);

CREATE TABLE index_daily (
    index_name   text NOT NULL,
    trade_date   date NOT NULL,
    open         numeric(14,4),
    high         numeric(14,4),
    low          numeric(14,4),
    close        numeric(14,4) NOT NULL,
    pe           numeric(10,2),
    pb           numeric(10,2),
    div_yield    numeric(10,2),
    volume       bigint,
    turnover_cr  numeric(20,2),
    PRIMARY KEY (index_name, trade_date)
);
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('index_daily', by_range('trade_date', INTERVAL '1 year'));
    END IF;
END $$;

-- One row per dataset per day: did the download and load succeed?
CREATE TABLE ingest_runs (
    dataset      text NOT NULL,
    trade_date   date NOT NULL,
    status       text NOT NULL CHECK (status IN ('ok', 'no_data', 'error')),
    row_count    integer,
    message      text,
    finished_at  timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (dataset, trade_date)
);

CREATE TABLE data_quality_issues (
    id             bigserial PRIMARY KEY,
    trade_date     date NOT NULL,
    check_name     text NOT NULL,
    severity       text NOT NULL CHECK (severity IN ('info', 'warn', 'error')),
    instrument_id  integer REFERENCES instruments(id),
    detail         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at     timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX data_quality_issues_date_idx ON data_quality_issues (trade_date);
