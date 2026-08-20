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
            lambda days: [{"source": "gaceta", "title": "Gaceta 1", "year": 2026,
                           "url": "http://g", "description": "Trámite"}],
        )
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro",
            lambda days: [{"source": "cepal", "indicator": "pib", "period": "2025",
                           "value": 94368.6, "unit": "USD", "impact": "Contexto"}],
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
        assert "proyeccion" in snap
        assert snap["proyeccion_rows"]

    def test_snapshot_sin_datos(self, session, monkeypatch):
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_fiscal_docs", lambda days: [])
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro", lambda days: [])
        snap = collect_snapshot("diario", session=session, with_ai=False)
        assert snap["market"] == []
        assert snap["fiscal_docs"] == []
        assert snap["macro"] == []
        assert snap["proyeccion_rows"] == []


class TestMarkdown:
    def test_fiscal_docs_block_vacio(self):
        text = "\n".join(fiscal_docs_block([]))
        assert "Sin trámites fiscales" in text

    def test_fiscal_docs_block_con_datos(self):
        text = "\n".join(fiscal_docs_block([
            {"source": "gaceta", "title": "Gaceta N° 43429", "year": 2026,
             "url": "http://g/43429", "date": "2026-08-04",
             "description": "Decreto N° 5.405 (nombramiento)"},
        ]))
        assert "| gaceta | 2026 | 2026-08-04 |" in text
        assert "Decreto N° 5.405" in text
        assert "impacto económico" in text

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
            "src.analyzers.reports.periodic._collect_fiscal_docs", lambda days: [])
        monkeypatch.setattr(
            "src.analyzers.reports.periodic._collect_macro", lambda days: [])
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


class TestEnsureComplete:
    """_ensure_complete recorta al último punto si el LLM cortó a media frase."""

    def test_texto_completo(self):
        from src.analyzers.reports.periodic import _ensure_complete

        assert _ensure_complete("Hola mundo.") == "Hola mundo."

    def test_texto_con_signos(self):
        from src.analyzers.reports.periodic import _ensure_complete

        assert _ensure_complete("¿Qué pasa?") == "¿Qué pasa?"
        assert _ensure_complete("¡Cuidado!") == "¡Cuidado!"

    def test_corta_a_media_frase(self):
        from src.analyzers.reports.periodic import _ensure_complete

        result = _ensure_complete("El dólar subió. Pero la inflación sigue")
        assert result == "El dólar subió."

    def test_texto_vacio(self):
        from src.analyzers.reports.periodic import _ensure_complete

        assert _ensure_complete("") == ""
        assert _ensure_complete("   ") == ""

    def test_muy_corto_sin_punto(self):
        from src.analyzers.reports.periodic import _ensure_complete

        # Si no hay punto significativo, devuelve tal cual
        result = _ensure_complete("abc")
        assert result == "abc"


class TestCleanProyeccion:
    """_clean_proyeccion quita prefacios meta del LLM."""

    def test_limpia_meta_inicial(self):
        from src.analyzers.reports.periodic import _clean_proyeccion

        text = (
            "We need to produce a projection for the next week.\n"
            "Based on the current data, the dollar will remain stable."
        )
        result = _clean_proyeccion(text)
        assert "We need" not in result
        assert "Based on" in result  # contenido válido, no meta

    def test_limpia_lineas_vacias(self):
        from src.analyzers.reports.periodic import _clean_proyeccion

        text = ("\n\nEl dólar subirá a 950.\n")
        result = _clean_proyeccion(text)
        assert result == "El dólar subirá a 950."

    def test_proyeccion_limpia(self):
        from src.analyzers.reports.periodic import _clean_proyeccion

        text = "El tipo de cambio se mantendrá estable en el rango de 900-920."
        result = _clean_proyeccion(text)
        assert result == text

    def test_i_will_prefix(self):
        from src.analyzers.reports.periodic import _clean_proyeccion

        text = "I will now produce a projection.\nEl dólar sube."
        result = _clean_proyeccion(text)
        assert "I will now produce" not in result
        assert "dólar sube" in result


class TestProjectionRows:
    """_projection_rows genera proyección heurística de tasas."""

    def test_con_variacion(self):
        from src.analyzers.reports.periodic import _projection_rows

        rows = _projection_rows([
            {"source": "bcv", "rate": 900.0, "variation_pct": 2.0},
        ])
        assert len(rows) == 1
        assert rows[0]["source"] == "bcv"
        assert rows[0]["rate"] == pytest.approx(918.0)

    def test_sin_variacion(self):
        from src.analyzers.reports.periodic import _projection_rows

        rows = _projection_rows([
            {"source": "bcv", "rate": 900.0, "variation_pct": None},
        ])
        assert rows == []

    def test_vacio(self):
        from src.analyzers.reports.periodic import _projection_rows

        assert _projection_rows([]) == []


class TestPdfStripHtml:
    """El PDF de noticias limpia HTML de los resúmenes RSS."""

    def test_noticias_html_stripped(self, tmp_path):
        from src.analyzers.reports.pdf_report import render_pdf

        snapshot = {
            "cadence": "diario",
            "period": "Día test",
            "generated_at": _now(),
            "market_series": [],
            "market": [],
            "inflation": [],
            "surveys": {},
            "sentiment": {},
            "articles": [{
                "title": "Dólar estable",
                "published": _now(),
                "source": "Primicia",
                "summary": "<p>El tipo de cambio <b>sigue</b> estable en 915.</p>",
            }],
            "fiscal_docs": [],
            "macro": [],
            "resumen": "",
        }
        path = str(tmp_path / "test_html.pdf")
        render_pdf(snapshot, path)
        data = __import__("pathlib").Path(path).read_text(encoding="latin-1")
        # El PDF no debe contener etiquetas HTML literales en el contenido
        assert "<p>" not in data
        assert "<b>" not in data