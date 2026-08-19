"""
Modelos ORM (SQLAlchemy) para Encuestas
=======================================

Tablas ``surveys`` y ``survey_responses`` según el esquema documentado en
Arquitectura.md. Los tipos JSON se declaran con variante JSONB para
PostgreSQL/TimescaleDB y JSON para SQLite (tests).

- ``raw_answers`` / ``kpis`` como JSONB: las preguntas cambian entre versiones
  de formulario sin romper el esquema.
- ``UNIQUE (survey_id, submitted_at, raw_answers)``: garantiza idempotencia
  a nivel de base de datos.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.session import Base

JSON_COLUMN = JSON().with_variant(JSONB(), "postgresql")

# BIGSERIAL en PostgreSQL; INTEGER (autoincrement) en SQLite para los tests
BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SurveyORM(Base):
    """Formulario de encuesta (Google Forms vinculado a una hoja)."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    survey_type: Mapped[str] = mapped_column(String(50), nullable=False)  # persona_comun | comerciante
    form_id: Mapped[str] = mapped_column(String(100), nullable=False)
    sheet_id: Mapped[str] = mapped_column(String(100), nullable=False)
    form_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str] = mapped_column(String(200), default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    responses: Mapped[list["SurveyResponseORM"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan"
    )


class SurveyResponseORM(Base):
    """Respuesta individual de una encuesta normalizada."""

    __tablename__ = "survey_responses"
    __table_args__ = (
        UniqueConstraint(
            "survey_id", "submitted_at", "raw_answers",
            name="uq_survey_response_idempotencia",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id"), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    respondent_segment: Mapped[Optional[str]] = mapped_column(String(50))
    timezone: Mapped[Optional[str]] = mapped_column(String(50))
    raw_answers: Mapped[dict] = mapped_column(JSON_COLUMN, default=dict)
    kpis: Mapped[dict] = mapped_column(JSON_COLUMN, default=dict)
    quality_score: Mapped[Optional[float]] = mapped_column(Numeric(3, 2))
    source: Mapped[str] = mapped_column(String(20), default="google_forms")

    survey: Mapped["SurveyORM"] = relationship(back_populates="responses")


class ExchangeRateORM(Base):
    """Tasa de cambio de un mercado/emisor en una fecha (Fase A)."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("source", "currency", "date", name="uq_exchange_rate"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # bcv, ovf, binance...
    currency: Mapped[str] = mapped_column(String(10), nullable=False)  # usd, usdt...
    rate: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    variation_pct: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))


class InflationPointORM(Base):
    """Punto de inflación mensual por emisor y período (Fase A)."""

    __tablename__ = "inflation_points"
    __table_args__ = (
        UniqueConstraint("source", "period", name="uq_inflation_point"),
    )

    id: Mapped[int] = mapped_column(BIGINT_ID, primary_key=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # bcv, ovf, world_bank
    period: Mapped[str] = mapped_column(String(7), nullable=False)  # YYYY-MM
    monthly_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    annual_rate: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    index: Mapped[Optional[float]] = mapped_column(Numeric(18, 6))