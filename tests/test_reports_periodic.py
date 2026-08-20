"""
Tests de los informes periódicos (diario/semanal/.../anual) en Markdown y PDF
=============================================================================
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.analyzers.reports.periodic import (
    CADENCES,
    build_markdown,
    collect_snapshot,
    fiscal_docs_block,
    generate_periodic_report,
    macro_block,
    save_report,
)
from src.db.models import Base
from src.db.repositories import MarketRepository, NewsRepository, SurveyRepository
from src.models.market import ExchangeRate, InflationPoint
from src.models.news import NewsArticle


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


def _populate(session):
    MarketRepository(session).save_rates([
        ExchangeRate(source="bcv", currency="usd", rate=36.0,
                     date=_now() - timedelta(days=5)),
        ExchangeRate(source="bcv", currency="usd", rate=36.5,
                     date=_now() - timedelta(days=1)),
    ])
    MarketRepository(session).save_inflation([
        InflationPoint(source="ovf", period="2026-07", monthly_rate=1.8,
                       annual_rate=45.2),
    ])
    NewsRepository(session).save_articles([
        NewsArticle(source="Primicia", title="Dólar baja", url="https://x/1",
                    published=_now()),
    ])


class TestCadences:
    def test_cadencias_definidas(self):
        assert set(CADENCES) == {
            "diario", "semanal", "mensual", "trimestral", "semestral", "anual",
        }
        assert CADENCES["semanal"]["days"] == 7
        assert CADENCES["anual"]["days"] == 365

    def test_cadencia_invalida(self, session):
        with pytest.raises(ValueError):
            collect_snapshot("bimensual", session=session)


class TestCollectSnapshot:
    def test_snapshot_estructura(self, session, monkeypatch):
        _populate(session)
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_fiscal_docs",
            lambda: [{"source": "gaceta", "title": "Gaceta 1", "year": 2026,
                      "url": "http://g"}],
        )
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro",
            lambda: [{"source": "cepal", "indicator": "pib", "period": "2025",
                      "value": 94368.6, "unit": "USD"}],
        )
        snap = collect_snapshot("semanal", session=session, with_ai=False)
        assert snap["cadence"] == "semanal"
        assert "Semana" in snap["period"]
        assert snap["market"][0]["source"] == "bcv"
        assert len(snap["market_series"]) == 2
        assert snap["inflation"][0]["source"] == "ovf"
        assert snap["fiscal_docs"][0]["source"] == "gaceta"
        assert snap["macro"][0]["source"] == "cepal"
        assert snap["resumen"] == ""

    def test_snapshot_sin_datos(self, session, monkeypatch):
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_fiscal_docs", lambda: [])
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro", lambda: [])
        snap = collect_snapshot("diario", session=session, with_ai=False)
        assert snap["market"] == []
        assert snap["fiscal_docs"] == []
        assert snap["macro"] == []


class TestMarkdown:
    def test_fiscal_docs_block_vacio(self):
        text = "\n".join(fiscal_docs_block([]))
        assert "Sin documentos fiscales" in text

    def test_fiscal_docs_block_con_datos(self):
        text = "\n".join(fiscal_docs_block([
            {"source": "gaceta", "title": "Gaceta N° 43429", "year": 2026,
             "url": "http://g/43429"},
        ]))
        assert "| gaceta | 2026 |" in text
        assert "http://g/43429" in text

    def test_macro_block(self):
        text = "\n".join(macro_block([
            {"source": "cepal", "indicator": "pib", "period": "2025",
             "value": 94368.6, "unit": "USD"},
        ]))
        assert "94,368.60" in text
        assert "cepal" in text

    def test_build_markdown_vacio(self):
        out = build_markdown({
            "cadence": "semanal",
            "period": "Semana del test",
            "generated_at": _now(),
            "market": [], "inflation": [], "surveys": {},
            "sentiment": {}, "articles": [], "fiscal_docs": [], "macro": [],
            "resumen": "",
        })
        assert out.startswith("# Informe Semanal")
        assert "Sin datos de mercado" in out
        assert "Marco Fiscal y Legislativo Reciente" in out
        assert "Indicadores Macroeconómicos" in out


class TestGeneracion:
    def test_save_report(self, tmp_path):
        path = save_report("# Hola", "diario", str(tmp_path), generated_at=_now())
        assert path.endswith(".md")
        assert __import__("pathlib").Path(path).exists()
        assert __import__("pathlib").Path(path).read_text(encoding="utf-8") == "# Hola"

    def test_generate_md_y_pdf(self, session, monkeypatch, tmp_path):
        _populate(session)
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_fiscal_docs", lambda: [])
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro", lambda: [])
        result = generate_periodic_report(
            "semanal", output_dir=str(tmp_path), formats=("md", "pdf"),
            session=session, with_ai=False,
        )
        assert "md" in result["paths"]
        assert "pdf" in result["paths"]
        md = __import__("pathlib").Path(result["paths"]["md"])
        pdf = __import__("pathlib").Path(result["paths"]["pdf"])
        assert md.exists()
        assert pdf.exists()
        assert md.read_text(encoding="utf-8").startswith("# Informe Semanal")
        assert pdf.read_bytes()[:5] == b"%PDF-"


class TestRenderPdf:
    def test_render_pdf(self, tmp_path):
        from src.analyzers.reports.pdf_report import render_pdf

        snapshot = {
            "cadence": "diario",
            "period": "Día test",
            "generated_at": _now(),
            "market_series": [{"source": "bcv", "currency": "usd", "rate": 36.5,
                               "date": _now().isoformat()}],
            "market": [{"source": "bcv", "currency": "usd", "rate": 36.5,
                        "variation_pct": 1.2, "date": _now()}],
            "inflation": [{"source": "ovf", "period": "2026-07",
                           "monthly_rate": 1.8, "annual_rate": 45.2}],
            "surveys": {},
            "sentiment": {"total": 3, "positive": 1, "neutral": 1,
                          "negative": 1, "mean_score": 0.0},
            "articles": [{"title": "Noticia", "published": _now()}],
            "fiscal_docs": [{"source": "an", "title": "Ley", "year": 2026,
                             "url": "http://an"}],
            "macro": [{"source": "cepal", "indicator": "pib", "period": "2025",
                       "value": 94368.6, "unit": "USD"}],
            "resumen": "Resumen ejecutivo.",
        }
        path = str(tmp_path / "test.pdf")
        render_pdf(snapshot, path)
        data = __import__("pathlib").Path(path).read_bytes()
        assert data[:5] == b"%PDF-"
        assert len(data) > 5000


class TestScheduler:
    def test_registra_informes_periodicos(self):
        from apscheduler.schedulers.background import BackgroundScheduler

        from src.scheduler.jobs import register_periodic_report_jobs

        scheduler = BackgroundScheduler()
        register_periodic_report_jobs(scheduler)
        jobs = {j.id: j for j in scheduler.get_jobs()}
        for cadence in ("diario", "semanal", "mensual", "trimestral",
                        "semestral", "anual"):
            assert f"report_{cadence}" in jobs
            assert jobs[f"report_{cadence}"].trigger.__class__.__name__ == \
                "CronTrigger"

    def test_resregistra_sin_duplicar(self):
        from apscheduler.schedulers.background import BackgroundScheduler

        from src.scheduler.jobs import register_periodic_report_jobs

        scheduler = BackgroundScheduler()
        register_periodic_report_jobs(scheduler)
        register_periodic_report_jobs(scheduler)
        jobs = [j.id for j in scheduler.get_jobs()]
        assert jobs.count("report_semanal") == 1