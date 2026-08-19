-- 002: Datos de mercado (Fase A)
-- Tasas de cambio y puntos de inflación por emisor.

CREATE TABLE IF NOT EXISTS exchange_rates (
    id            BIGSERIAL PRIMARY KEY,
    source        VARCHAR(20) NOT NULL,           -- bcv, ovf, binance, ...
    currency      VARCHAR(10) NOT NULL,           -- usd, usdt, ...
    rate          NUMERIC(18, 6) NOT NULL,
    date          TIMESTAMPTZ NOT NULL,
    variation_pct NUMERIC(10, 4),
    CONSTRAINT uq_exchange_rate UNIQUE (source, currency, date)
);

CREATE INDEX IF NOT EXISTS idx_exchange_rates_source_date
    ON exchange_rates (source, date DESC);

CREATE TABLE IF NOT EXISTS inflation_points (
    id           BIGSERIAL PRIMARY KEY,
    source       VARCHAR(20) NOT NULL,            -- bcv, ovf, world_bank
    period       VARCHAR(7) NOT NULL,             -- YYYY-MM
    monthly_rate NUMERIC(10, 4),
    annual_rate  NUMERIC(10, 4),
    index        NUMERIC(18, 6),
    CONSTRAINT uq_inflation_point UNIQUE (source, period)
);

CREATE INDEX IF NOT EXISTS idx_inflation_points_source_period
    ON inflation_points (source, period DESC);