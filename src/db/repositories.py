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
    IBCComponentORM,
    IBCIndexORM,
    InflationPointORM,
    NewsArticleORM,
    SentimentScoreORM,
    SocialPostORM,
    SurveyORM,
    SurveyResponseORM,
    VenezuelanTickerORM,
)
from src.models.market import ExchangeRate, InflationPoint
from src.models.news import NewsArticle, SentimentScore, SocialPost
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


def _article_to_orm(article: NewsArticle) -> NewsArticleORM:
    return NewsArticleORM(
        source=article.source,
        title=article.title,
        url=article.url,
        published=article.published,
        summary=article.summary,
    )


def _article_orm_to_model(orm: NewsArticleORM) -> NewsArticle:
    return NewsArticle(
        source=orm.source,
        title=orm.title,
        url=orm.url,
        published=orm.published,
        summary=orm.summary,
    )


def _post_to_orm(post: SocialPost) -> SocialPostORM:
    return SocialPostORM(
        source=post.source,
        channel=post.channel,
        title=post.title,
        url=post.url,
        text=post.text,
        score=post.score,
        num_comments=post.num_comments,
        published=post.published,
    )


def _post_orm_to_model(orm: SocialPostORM) -> SocialPost:
    return SocialPost(
        source=orm.source,
        channel=orm.channel,
        title=orm.title,
        url=orm.url,
        text=orm.text,
        score=orm.score,
        num_comments=orm.num_comments,
        published=orm.published,
    )


def _sentiment_to_orm(score: SentimentScore) -> SentimentScoreORM:
    return SentimentScoreORM(
        item_type=score.item_type,
        item_id=score.item_id,
        text=score.text,
        score=score.score,
        label=score.label,
    )


def _sentiment_orm_to_model(orm: SentimentScoreORM) -> SentimentScore:
    return SentimentScore(
        item_type=orm.item_type,
        item_id=orm.item_id,
        text=orm.text,
        score=float(orm.score),
        label=orm.label,
        analyzed_at=orm.analyzed_at,
    )


class NewsRepository:
    """Persistencia de noticias, posts sociales y puntajes de sentimiento."""

    def __init__(self, session: Session):
        self.session = session

    # --- Articles ---

    def save_articles(self, articles: List[NewsArticle]) -> int:
        """Inserta artículos de forma idempotente (única por source/url).

        Returns:
            Número de artículos nuevos insertados.
        """
        saved = 0
        for article in articles:
            self.session.add(_article_to_orm(article))
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info(
                    "Artículo duplicado omitido (%s)", article.url,
                )
        return saved

    def list_articles(
        self,
        source: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[NewsArticle]:
        stmt = select(NewsArticleORM).order_by(NewsArticleORM.published.desc())
        if source is not None:
            stmt = stmt.where(NewsArticleORM.source == source)
        if since is not None:
            stmt = stmt.where(NewsArticleORM.published >= since)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_article_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def count_articles(self) -> int:
        return int(self.session.scalar(select(func.count(NewsArticleORM.id))) or 0)

    # --- Social posts ---

    def save_posts(self, posts: List[SocialPost]) -> int:
        """Inserta posts de forma idempotente (única por source/url)."""
        saved = 0
        for post in posts:
            self.session.add(_post_to_orm(post))
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info("Post duplicado omitido (%s)", post.url)
        return saved

    def list_posts(
        self,
        channel: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[SocialPost]:
        stmt = select(SocialPostORM).order_by(SocialPostORM.published.desc())
        if channel is not None:
            stmt = stmt.where(SocialPostORM.channel == channel)
        if since is not None:
            stmt = stmt.where(SocialPostORM.published >= since)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_post_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def count_posts(self) -> int:
        return int(self.session.scalar(select(func.count(SocialPostORM.id))) or 0)

    # --- Sentiment ---

    def save_sentiment(self, scores: List[SentimentScore]) -> int:
        """Inserta puntajes de sentimiento de forma idempotente.

        Única por (item_type, item_id); un re-análisis no duplica.
        """
        saved = 0
        for score in scores:
            self.session.add(_sentiment_to_orm(score))
            try:
                self.session.commit()
                saved += 1
            except IntegrityError:
                self.session.rollback()
                logger.info(
                    "Sentimiento duplicado omitido (%s/%s)",
                    score.item_type, score.item_id,
                )
        return saved

    def list_sentiment(
        self,
        item_type: Optional[str] = None,
        label: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[SentimentScore]:
        stmt = select(SentimentScoreORM).order_by(SentimentScoreORM.analyzed_at.desc())
        if item_type is not None:
            stmt = stmt.where(SentimentScoreORM.item_type == item_type)
        if label is not None:
            stmt = stmt.where(SentimentScoreORM.label == label)
        if limit is not None:
            stmt = stmt.limit(limit)
        return [_sentiment_orm_to_model(orm) for orm in self.session.scalars(stmt)]

    def sentiment_summary(self) -> dict:
        """Resumen agregado: conteos por etiqueta y promedio ponderado.

        Returns:
            Dict con total, positive, neutral, negative y mean_score (0 si vacío).
        """
        rows = self.session.execute(
            select(SentimentScoreORM.label, func.count(SentimentScoreORM.id))
            .group_by(SentimentScoreORM.label)
        ).all()
        counts = {label: int(n) for label, n in rows}
        total = sum(counts.values())
        mean = 0.0
        if total:
            mean_rows = self.session.execute(
                select(func.avg(SentimentScoreORM.score))
            ).scalar()
            mean = float(mean_rows or 0.0)
        return {
            "total": total,
            "positive": counts.get("positive", 0),
            "neutral": counts.get("neutral", 0),
            "negative": counts.get("negative", 0),
            "mean_score": round(mean, 4),
        }


# ---------------------------------------------------------------------------
# IBC Index Repository
# ---------------------------------------------------------------------------

class IBCIndexRepository:
    """Persistencia del índice IBC y sus componentes."""

    def __init__(self, session: Session):
        self.session = session

    def save_index(self, date: datetime, value: float, change: float = 0,
                   change_pct: float = 0) -> bool:
        """Guarda un punto del índice IBC (idempotente)."""
        existing = self.session.execute(
            select(IBCIndexORM).where(IBCIndexORM.date == date)
        ).scalar_one_or_none()
        if existing:
            existing.value = value
            existing.change = change
            existing.change_pct = change_pct
            return False
        self.session.add(IBCIndexORM(
            date=date, value=value, change=change, change_pct=change_pct,
        ))
        return True

    def save_components(self, date: datetime, components: list) -> int:
        """Guarda componentes del IBC para una fecha. Retorna cantidad insertados."""
        saved = 0
        for comp in components:
            existing = self.session.execute(
                select(IBCComponentORM).where(
                    IBCComponentORM.date == date,
                    IBCComponentORM.ticker == comp["ticker"],
                )
            ).scalar_one_or_none()
            if not existing:
                self.session.add(IBCComponentORM(
                    date=date,
                    ticker=comp["ticker"],
                    name=comp.get("name", comp["ticker"]),
                    price=comp.get("price", 0),
                    change_pct=comp.get("change_pct", 0),
                    volume=comp.get("volume", 0),
                ))
                saved += 1
        return saved

    def list_index(self, since: Optional[datetime] = None,
                   until: Optional[datetime] = None,
                   limit: int = 50) -> List[dict]:
        """Lista puntos del índice IBC en un rango."""
        stmt = select(IBCIndexORM).order_by(IBCIndexORM.date.desc())
        if since:
            stmt = stmt.where(IBCIndexORM.date >= since)
        if until:
            stmt = stmt.where(IBCIndexORM.date <= until)
        stmt = stmt.limit(limit)
        return [
            {"date": orm.date, "value": float(orm.value),
             "change": float(orm.change), "change_pct": float(orm.change_pct)}
            for orm in self.session.scalars(stmt)
        ]

    def list_components(self, date: Optional[datetime] = None,
                        since: Optional[datetime] = None,
                        until: Optional[datetime] = None,
                        limit: int = 50) -> List[dict]:
        """Lista componentes del IBC."""
        stmt = select(IBCComponentORM).order_by(IBCComponentORM.date.desc())
        if date:
            stmt = stmt.where(IBCComponentORM.date == date)
        if since:
            stmt = stmt.where(IBCComponentORM.date >= since)
        if until:
            stmt = stmt.where(IBCComponentORM.date <= until)
        stmt = stmt.limit(limit)
        return [
            {"date": orm.date, "ticker": orm.ticker, "name": orm.name,
             "price": float(orm.price), "change_pct": float(orm.change_pct),
             "volume": orm.volume}
            for orm in self.session.scalars(stmt)
        ]


# ---------------------------------------------------------------------------
# Venezuelan Tickers Repository
# ---------------------------------------------------------------------------

class VenezuelanTickerRepository:
    """Persistencia de tickers venezolanos relevantes."""

    def __init__(self, session: Session):
        self.session = session

    def save_tickers(self, date: datetime, tickers: list) -> int:
        """Guarda tickers para una fecha. Retorna cantidad insertados."""
        saved = 0
        for t in tickers:
            existing = self.session.execute(
                select(VenezuelanTickerORM).where(
                    VenezuelanTickerORM.date == date,
                    VenezuelanTickerORM.ticker == t["ticker"],
                )
            ).scalar_one_or_none()
            if not existing:
                self.session.add(VenezuelanTickerORM(
                    date=date,
                    ticker=t["ticker"],
                    name=t.get("name", t["ticker"]),
                    close=t.get("close", 0),
                    change_pct=t.get("change_pct", 0),
                    avg_volume=t.get("avg_volume", 0),
                ))
                saved += 1
        return saved

    def list_tickers(self, since: Optional[datetime] = None,
                     until: Optional[datetime] = None,
                     limit: int = 100) -> List[dict]:
        """Lista datos de tickers en un rango."""
        stmt = select(VenezuelanTickerORM).order_by(VenezuelanTickerORM.date.desc())
        if since:
            stmt = stmt.where(VenezuelanTickerORM.date >= since)
        if until:
            stmt = stmt.where(VenezuelanTickerORM.date <= until)
        stmt = stmt.limit(limit)
        return [
            {"date": orm.date, "ticker": orm.ticker, "name": orm.name,
             "close": float(orm.close), "change_pct": float(orm.change_pct),
             "avg_volume": orm.avg_volume}
            for orm in self.session.scalars(stmt)
        ]