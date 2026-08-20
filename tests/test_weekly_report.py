"""
Tests del informe semanal automatizado (punto 25)
=================================================

- Bloques Markdown (mercado, inflación, encuestas, sentimiento, noticias).
- ``build_weekly_report`` con y sin resumen IA (monkeypatch de la cadena).
- ``collect_weekly_snapshot`` lee de la base (SQLite) y agrega tasas.
- Scheduler: register_weekly_report_job.
"""

from datetime import datetime, timedelta, timezone

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src.analyzers.reports.weekly import (
    build_weekly_report,
    collect_weekly_snapshot,
    market_block,
    sentiment_block,
)
from src.db.models import Base
from src.db.repositories import MarketRepository, NewsRepository, SurveyRepository
from src.models.market import ExchangeRate, InflationPoint
from src.models.news import NewsArticle
from src.models.survey import Survey, SurveyResponse
from src.scheduler.jobs import register_weekly_report_job


@pytest.fixture
def session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TestLimpiarTasas:
    def test_filtra_picos_anomalos(self):
        from src.analyzers.reports.weekly import _clean_rates
        from src.models.market import ExchangeRate

        rates = [
            ExchangeRate(source="binance", currency="usdt", rate=900,
                         date=_now() - timedelta(hours=3)),
            ExchangeRate(source="binance", currency="usdt", rate=915,
                         date=_now() - timedelta(hours=2)),
            ExchangeRate(source="binance", currency="usdt", rate=1500,
                         date=_now() - timedelta(hours=1)),
        ]
        clean = _clean_rates(rates)
        assert [r.rate for r in clean] == [900, 915]

    def test_sin_datos_limpiables_devuelve_original(self):
        from src.analyzers.reports.weekly import _clean_rates
        from src.models.market import ExchangeRate

        rates = [ExchangeRate(source="bcv", currency="usd", rate=36.5,
                              date=_now())]
        assert _clean_rates(rates) == rates


class TestBloquesMarkdown:
    def test_market_block_vacio(self):
        lines = market_block([])
        assert "Sin datos de mercado" in "\n".join(lines)

    def test_market_block_con_datos(self):
        lines = market_block([
            {"source": "bcv", "rate": 36.5, "variation_pct": -1.2, "date": _now()},
            {"source": "binance", "rate": 40.0, "variation_pct": 2.5, "date": _now()},
        ])
        text = "\n".join(lines)
        assert "| bcv |" in text
        assert "36.50" in text
        assert "-1.20" in text

    def test_sentiment_block(self):
        lines = sentiment_block({
            "total": 10, "positive": 6, "neutral": 2, "negative": 2, "mean_score": 0.2,
        })
        text = "\n".join(lines)
        assert "Tono general:** Positivo" in text
        assert "Positivas: 6" in text

    def test_sentiment_block_vacio(self):
        text = "\n".join(sentiment_block({}))
        assert "Sin análisis de sentimiento" in text

    def test_inflation_fuente_entre_parentesis(self):
        from src.analyzers.reports.weekly import inflation_block

        text = "\n".join(inflation_block([
            {"source": "ovf", "period": "2026-07", "monthly_rate": 1.8,
             "annual_rate": 45.2},
        ]))
        assert "(OVF)" in text

    def test_articles_fuente_y_resumen(self):
        from src.analyzers.reports.weekly import articles_block

        text = "\n".join(articles_block([
            {"title": "Dólar sube", "source": "Primicia",
             "published": _now(), "summary": "El paralelo escaló a 930."},
        ]))
        assert "Primicia" in text
        assert "El paralelo escaló a 930." in text

    def test_projection_block(self):
        from src.analyzers.reports.weekly import projection_block

        text = "\n".join(projection_block(
            "Se espera un dólar estable.",
            [{"source": "bcv", "rate": 780.5}],
        ))
        assert "Proyección para la próxima semana" in text
        assert "Se espera un dólar estable." in text
        assert "| bcv | 780.50 |" in text

    def test_clean_summary_quita_wordpress(self):
        from src.analyzers.reports.weekly import _clean_summary

        raw = (
            "La compañía que había adquirido el control. "
            "La entrada Crossover Energy cerca de concretar "
            "acuerdos petroleros con Pdvsa se publicó primero "
            "en Diario Primicia"
        )
        result = _clean_summary(raw)
        assert "La entrada" not in result
        assert "se publicó primero" not in result
        assert "La compañía" in result


class TestBuildWeeklyReport:
    def test_plantilla_sin_ia(self):
        out = build_weekly_report(ai_enabled=False)
        assert out.startswith("# Informe Semanal")
        assert "## Mercado" in out
        assert "## Inflación" in out
        assert "## Encuestas" in out
        assert "## Sentimiento de Noticias" in out

    def test_con_resumen_ia(self, monkeypatch):
        monkeypatch.setattr(
            "src.analyzers.llm.summarize",
            lambda *a, **k: "Resumen IA del informe",
        )
        out = build_weekly_report(ai_enabled=True)
        assert "## Resumen IA" in out
        assert "Resumen IA del informe" in out

    def test_ia_falla_solo_plantilla(self, monkeypatch):
        monkeypatch.setattr(
            "src.analyzers.llm.summarize",
            lambda *a, **k: None,
        )
        out = build_weekly_report(ai_enabled=True)
        assert "## Resumen IA" not in out


class TestCollectWeeklySnapshot:
    def _populate(self, session):
        repo = SurveyRepository(session)
        survey = repo.save_survey(Survey(
            id=1, survey_type="persona_comun", form_id="f1", sheet_id="s1", name="PC",
        ))
        repo.save_responses([
            SurveyResponse(
                survey_id=survey.id,
                submitted_at=_now() - timedelta(days=1),
                respondent_segment="persona_comun",
                raw_answers={"sent": {"inflacion_12m": 40}},
            )
        ])
        MarketRepository(session).save_rates([
            ExchangeRate(source="bcv", currency="usd", rate=36.0, date=_now() - timedelta(days=5)),
            ExchangeRate(source="bcv", currency="usd", rate=36.5, date=_now() - timedelta(days=1)),
        ])
        MarketRepository(session).save_inflation([
            InflationPoint(source="ovf", period="2026-07", monthly_rate=1.8, annual_rate=45.2),
        ])
        NewsRepository(session).save_articles([
            NewsArticle(source="Primicia", title="Dólar baja", url="https://x/1", published=_now()),
        ])

    def test_snapshot_agrega_tasas(self, session):
        self._populate(session)
        snap = collect_weekly_snapshot(days=7, session=session)
        assert len(snap["market"]) == 1
        row = snap["market"][0]
        assert row["source"] == "bcv"
        assert row["rate"] == 36.5
        # Variación vs la primera tasa del período: (36.5-36)/36
        assert row["variation_pct"] == pytest.approx(1.3889, abs=0.01)

    def test_snapshot_inflacion_y_noticias(self, session):
        self._populate(session)
        snap = collect_weekly_snapshot(days=7, session=session)
        assert snap["inflation"][0]["source"] == "ovf"
        assert snap["inflation"][0]["monthly_rate"] == 1.8
        assert snap["articles"][0]["title"] == "Dólar baja"
        assert snap["surveys"]["persona_comun"]["n_responses"] == 1

    def test_snapshot_vacio(self, session):
        snap = collect_weekly_snapshot(days=7, session=session)
        assert snap["market"] == []
        assert snap["inflation"] == []
        assert snap["articles"] == []
        assert snap["sentiment"]["total"] == 0


class TestRegisterWeeklyReportJob:
    def test_registra_job_cron(self):
        scheduler = BackgroundScheduler()
        register_weekly_report_job(scheduler)
        job = scheduler.get_job("weekly_report")
        assert job is not None
        assert job.trigger.__class__.__name__ == "CronTrigger"

    def test_resregistra_sin_duplicar(self):
        scheduler = BackgroundScheduler()
        register_weekly_report_job(scheduler)
        register_weekly_report_job(scheduler)
        jobs = [j.id for j in scheduler.get_jobs()]
        assert jobs.count("weekly_report") == 1