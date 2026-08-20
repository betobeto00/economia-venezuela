-- TimescaleDB Setup para Economía Venezuela
-- Convierte tablas de series temporales en hypertables y agrega índices.
--
-- Ejecutar después de init_db():
--   psql -U postgres -d economia_ve -f src/db/migrations/timescale_setup.sql
--
-- O desde Python:
--   from src.db.session import get_engine
--   engine = get_engine()
--   with open("src/db/migrations/timescale_setup.sql") as f:
--       engine.execute(f.read())

-- 1. Habilitar extensión TimescaleDB (idempotente)
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- 2. Convertir exchange_rates a hypertable (por columna date)
--    Particionado por mes para queries rápidas de rango de fechas.
SELECT create_hypertable(
    'exchange_rates',
    'date',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 3. Convertir inflation_points a hypertable (por period como texto)
--    Usamos un integer time_dim: convertimos YYYY-MM a mes_num
ALTER TABLE inflation_points ADD COLUMN IF NOT EXISTS period_date DATE;
UPDATE inflation_points SET period_date = TO_DATE(period || '-01', 'YYYY-MM-DD')
    WHERE period_date IS NULL;
ALTER TABLE inflation_points ALTER COLUMN period_date SET NOT NULL;

SELECT create_hypertable(
    'inflation_points',
    'period_date',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 4. Convertir ibc_index a hypertable
SELECT create_hypertable(
    'ibc_index',
    'date',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 5. Convertir ibc_components a hypertable
SELECT create_hypertable(
    'ibc_components',
    'date',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 6. Convertir news_articles a hypertable (por published)
--    Solo si tiene published NOT NULL; los NULL se quedan en la tabla principal.
SELECT create_hypertable(
    'news_articles',
    'published',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 7. Convertir social_posts a hypertable (por published)
SELECT create_hypertable(
    'social_posts',
    'published',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 8. Convertir sentiment_scores a hypertable (por analyzed_at)
SELECT create_hypertable(
    'sentiment_scores',
    'analyzed_at',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 9. Convertir survey_responses a hypertable (por submitted_at)
SELECT create_hypertable(
    'survey_responses',
    'submitted_at',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

-- 10. Índices para queries frecuentes del dashboard

-- Tasas de cambio: buscar por fuente + moneda + rango de fechas
CREATE INDEX IF NOT EXISTS idx_exchange_rates_source_currency_date
    ON exchange_rates (source, currency, date DESC);

-- Inflación: buscar por fuente + período
CREATE INDEX IF NOT EXISTS idx_inflation_points_source_period
    ON inflation_points (source, period DESC);

-- IBC: buscar por fecha
CREATE INDEX IF NOT EXISTS idx_ibc_index_date
    ON ibc_index (date DESC);

-- Componentes IBC: buscar por fecha + ticker
CREATE INDEX IF NOT EXISTS idx_ibc_components_date_ticker
    ON ibc_components (date DESC, ticker);

-- Tickers venezolanos: buscar por fecha + ticker
CREATE INDEX IF NOT EXISTS idx_venezuelan_tickers_date_ticker
    ON venezuelan_tickers (date DESC, ticker);

-- Noticias: buscar por fecha de publicación
CREATE INDEX IF NOT EXISTS idx_news_articles_published
    ON news_articles (published DESC);

-- Social posts: buscar por fecha
CREATE INDEX IF NOT EXISTS idx_social_posts_published
    ON social_posts (published DESC);

-- Sentimiento: buscar por tipo + fecha
CREATE INDEX IF NOT EXISTS idx_sentiment_scores_type_date
    ON sentiment_scores (item_type, analyzed_at DESC);

-- Encuestas: buscar por segmento + fecha
CREATE INDEX IF NOT EXISTS idx_survey_responses_segment_date
    ON survey_responses (respondent_segment, submitted_at DESC);

-- 11. Políticas de retención (opcional, descomentar si se quiere)
--    Eliminar datos más antiguos de 2 años automáticamente:
-- SELECT add_retention_policy('exchange_rates', INTERVAL '2 years', if_not_exists => TRUE);
-- SELECT add_retention_policy('news_articles', INTERVAL '1 year', if_not_exists => TRUE);
-- SELECT add_retention_policy('social_posts', INTERVAL '1 year', if_not_exists => TRUE);
-- SELECT add_retention_policy('sentiment_scores', INTERVAL '1 year', if_not_exists => TRUE);

-- 12. Continuous Aggregates (opcional, para métricas pre-computadas)
--    Promedio diario de tasas de cambio (para gráficos):
-- CREATE MATERIALIZED VIEW IF NOT EXISTS daily_exchange_rates
--     WITH (timescaledb.continuous) AS
--     SELECT
--         time_bucket('1 day', date) AS day,
--         source,
--         currency,
--         AVG(rate) AS avg_rate,
--         MIN(rate) AS min_rate,
--         MAX(rate) AS max_rate,
--         COUNT(*) AS num_points
--     FROM exchange_rates
--     GROUP BY day, source, currency
--     WITH NO DATA;
