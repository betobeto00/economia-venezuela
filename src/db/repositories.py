"""
Repositorios de persistencia
============================

Capa de acceso a datos:
- ``SurveyRepository``: encuestas (surveys / survey_responses).
- ``MarketRepository``: datos de mercado (exchange_rates / inflation_points).

Ambos reciben una sesión (inyección de dependencias) para usarse con
FastAPI, scripts o tests (SQLite), y garantizan ingesta idempotente.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.db.models import (
    ExchangeRateORM,
    InflationPointORM,
    SurveyORM,
    SurveyResponseORM,
)
from src.models.market import ExchangeRate, InflationPoint
from src.models.survey import Survey, SurveyResponse

logger = logging.getLogger(__name__)


def _survey_to_orm(survey: Survey) -> SurveyORM:
    return SurveyORM(
        id=survey.id,
        survey_type=survey.survey_type,
        form_id=survey.form_id,
        sheet_id=survey.sheet_id,
        form_version=survey.form_version,
        name=survey.name,
        active=survey.active,
    )


def _survey_orm_to_model(orm: SurveyORM) -> Survey:
    return Survey(
        id=orm.id,
        survey_type=orm.survey_type,
        form_id=orm.form_id,
        sheet_id=orm.sheet_id,
        form_version=orm.form_version,
        name=orm.name,
        active=orm.active,
    )


def _response_to_orm(response: SurveyResponse) -> SurveyResponseORM:
    return SurveyResponseORM(
        survey_id=response.survey_id,
        submitted_at=response.submitted_at,
        respondent_segment=response.respondent_segment,
        timezone=response.timezone,
        raw_answers=response.raw_answers,
        kpis=response.kpis,
        quality_score=response.quality_score,
        source=response.source,
    )


def _response_orm_to_model(orm: SurveyResponseORM) -> SurveyResponse:
    return SurveyResponse(
        id=orm.id,
        survey_id=orm.survey_id,
        submitted_at=orm.submitted_at,
        respondent_segment=orm.respondent_segment or "",
        timezone=orm.timezone,
        raw_answers=orm.raw_answers or {},
        kpis=orm.kpis or {},
        quality_score=float(orm.quality_score) if orm.quality_score is not None else None,
        source=orm.source,
    )


class SurveyRepository:
    """Persistencia de formularios y respuestas de encuestas."""

    def __init__(self, session: Session):
        self.session = session

    # --- Surveys ---

    def save_survey(self, survey: Survey) -> Survey:
        """Inserta o actualiza un formulario y devuelve el persistido.

        Args:
            survey: Formulario (si ``id`` existe, actualiza; si no, inserta).

        Returns:
            Survey con los valores persistidos (incluido el id asignado).
        """
        orm = self.session.get(SurveyORM, survey.id)
        if orm is None:
            orm = _survey_to_orm(survey)
            self.session.add(orm)
        else:
            orm.survey_type = survey.survey_type
            orm.form_id = survey.form_id
            orm.sheet_id = survey.sheet_id
            orm.form_version = survey.form_version
            orm.name = survey.name
            orm.active = survey.active
        self.session.commit()
        self.session.refresh(orm)
        return _survey_orm_to_model(orm)

    def get_survey(self, survey_id: int) -> Optional[Survey]:
        orm = self.session.get(SurveyORM, survey_id)
        return _survey_orm_to_model(orm) if orm is not None else None

    def list_surveys(self, active_only: bool = True) -> List[Survey]:
        """Lista formularios (opcionalmente solo los activos), por id."""
        stmt = select(SurveyORM).order_by(SurveyORM.id)
        if active_only:
            stmt = stmt.where(SurveyORM.active.is_(True))
        return [_survey_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def upsert_surveys(self, surveys: List[Survey]) -> List[Survey]:
        """Guarda un lote de formularios (insert/update) en una transacción."""
        saved = []
        for survey in surveys:
            saved.append(self.save_survey(survey))
        return saved

    # --- Responses ---

    def save_responses(self, responses: List[SurveyResponse]) -> int:
        """Ingesta respuestas de forma idempotente.

        Se confirma por fila para que una respuesta duplicada (constraint
        única) no revierta el resto del lote; las duplicadas se omiten.

        Args:
            responses: Respuestas normalizadas a persistir.

        Returns:
            Número de respuestas nuevas insertadas.
        """
        saved = 0
        for response in responses:
            orm = _response_to_orm(response)
            self.session.add(orm)
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info(
                    "Respuesta duplicada omitida (survey_id=%s, submitted_at=%s)",
                    response.survey_id,
                    response.submitted_at,
                )
        return saved

    def list_responses(
        self,
        survey_id: Optional[int] = None,
        segment: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[SurveyResponse]:
        """Lista respuestas con filtros opcionales (por id ascendente)."""
        stmt = select(SurveyResponseORM).order_by(SurveyResponseORM.submitted_at)
        if survey_id is not None:
            stmt = stmt.where(SurveyResponseORM.survey_id == survey_id)
        if segment is not None:
            stmt = stmt.where(SurveyResponseORM.respondent_segment == segment)
        if since is not None:
            stmt = stmt.where(SurveyResponseORM.submitted_at >= since)
        if until is not None:
            stmt = stmt.where(SurveyResponseORM.submitted_at <= until)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_response_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def count_responses(self, survey_id: Optional[int] = None) -> int:
        """Cuenta respuestas (opcionalmente de un formulario)."""
        stmt = select(func.count(SurveyResponseORM.id))
        if survey_id is not None:
            stmt = stmt.where(SurveyResponseORM.survey_id == survey_id)
        return int(self.session.scalar(stmt) or 0)

    def delete_all_responses(self) -> int:
        """Elimina todas las respuestas (utilidad para tests/limpieza)."""
        result = self.session.query(SurveyResponseORM).delete()
        self.session.commit()
        return int(result)


def _rate_to_orm(rate: ExchangeRate) -> ExchangeRateORM:
    return ExchangeRateORM(
        source=rate.source,
        currency=rate.currency,
        rate=rate.rate,
        date=rate.date,
        variation_pct=rate.variation_pct,
    )


def _rate_orm_to_model(orm: ExchangeRateORM) -> ExchangeRate:
    return ExchangeRate(
        source=orm.source,
        currency=orm.currency,
        rate=float(orm.rate),
        date=orm.date,
        variation_pct=float(orm.variation_pct) if orm.variation_pct is not None else None,
    )


def _inflation_to_orm(point: InflationPoint) -> InflationPointORM:
    return InflationPointORM(
        source=point.source,
        period=point.period,
        monthly_rate=point.monthly_rate,
        annual_rate=point.annual_rate,
        index=point.index,
    )


def _inflation_orm_to_model(orm: InflationPointORM) -> InflationPoint:
    return InflationPoint(
        source=orm.source,
        period=orm.period,
        monthly_rate=float(orm.monthly_rate) if orm.monthly_rate is not None else None,
        annual_rate=float(orm.annual_rate) if orm.annual_rate is not None else None,
        index=float(orm.index) if orm.index is not None else None,
    )


class MarketRepository:
    """Persistencia de tasas de cambio y puntos de inflación (Fase A)."""

    def __init__(self, session: Session):
        self.session = session

    # --- Exchange rates ---

    def save_rates(self, rates: List[ExchangeRate]) -> int:
        """Inserta tasas de forma idempotente (única por source/currency/date).

        Returns:
            Número de tasas nuevas insertadas.
        """
        saved = 0
        for rate in rates:
            self.session.add(_rate_to_orm(rate))
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info(
                    "Tasa duplicada omitida (%s/%s/%s)",
                    rate.source, rate.currency, rate.date,
                )
        return saved

    def list_rates(
        self,
        source: Optional[str] = None,
        currency: Optional[str] = None,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ExchangeRate]:
        stmt = select(ExchangeRateORM).order_by(ExchangeRateORM.date)
        if source is not None:
            stmt = stmt.where(ExchangeRateORM.source == source)
        if currency is not None:
            stmt = stmt.where(ExchangeRateORM.currency == currency)
        if since is not None:
            stmt = stmt.where(ExchangeRateORM.date >= since)
        if until is not None:
            stmt = stmt.where(ExchangeRateORM.date <= until)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_rate_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def latest_rate(self, source: str, currency: str = "usd") -> Optional[ExchangeRate]:
        stmt = (
            select(ExchangeRateORM)
            .where(ExchangeRateORM.source == source, ExchangeRateORM.currency == currency)
            .order_by(ExchangeRateORM.date.desc())
            .limit(1)
        )
        orm = self.session.scalar(stmt)
        return _rate_orm_to_model(orm) if orm is not None else None

    # --- Inflation ---

    def save_inflation(self, points: List[InflationPoint]) -> int:
        """Inserta puntos de inflación de forma idempotente (única por source/period)."""
        saved = 0
        for point in points:
            self.session.add(_inflation_to_orm(point))
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info(
                    "Punto de inflación duplicado omitido (%s/%s)",
                    point.source, point.period,
                )
        return saved

    def list_inflation(
        self,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[InflationPoint]:
        stmt = select(InflationPointORM).order_by(InflationPointORM.period)
        if source is not None:
            stmt = stmt.where(InflationPointORM.source == source)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_inflation_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def latest_inflation(self, source: str) -> Optional[InflationPoint]:
        stmt = (
            select(InflationPointORM)
            .where(InflationPointORM.source == source)
            .order_by(InflationPointORM.period.desc())
            .limit(1)
        )
        orm = self.session.scalar(stmt)
        return _inflation_orm_to_model(orm) if orm is not None else None