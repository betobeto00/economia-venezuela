-- 001_create_surveys.sql
-- Tablas de encuestas (Fase B) — ver Arquitectura.md § Modelo de Datos
-- Compatible con PostgreSQL / TimescaleDB.
--
-- Aplicar en la base de datos objetivo (p.ej. dentro del contenedor db):
--   docker compose exec -T db psql -U postgres -d economia_ve < src/db/migrations/001_create_surveys.sql

CREATE TABLE IF NOT EXISTS surveys (
    id SERIAL PRIMARY KEY,
    survey_type VARCHAR(50) NOT NULL,   -- persona_comun | comerciante | ...
    form_id VARCHAR(100) NOT NULL,      -- ID del Google Form
    sheet_id VARCHAR(100) NOT NULL,     -- ID de la Google Sheet vinculada
    form_version INT NOT NULL DEFAULT 1,
    name VARCHAR(200),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS survey_responses (
    id BIGSERIAL PRIMARY KEY,
    survey_id INT REFERENCES surveys(id),
    submitted_at TIMESTAMPTZ NOT NULL,
    respondent_segment VARCHAR(50),
    timezone VARCHAR(50),
    raw_answers JSONB,                  -- Respuestas crudas (pregunta → valor)
    kpis JSONB,                         -- KPIs derivados normalizados
    quality_score DECIMAL(3,2),
    source VARCHAR(20) DEFAULT 'google_forms',
    UNIQUE (survey_id, submitted_at, raw_answers)  -- idempotencia
);

CREATE INDEX IF NOT EXISTS idx_survey_responses_survey_ts
    ON survey_responses (survey_id, submitted_at);
CREATE INDEX IF NOT EXISTS idx_survey_responses_segment
    ON survey_responses (respondent_segment);