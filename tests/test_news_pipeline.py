"""
Tests del pipeline de noticias y sentimiento (Fase A)
=====================================================

- Analizador de sentimiento (léxico en español): score y etiquetas.
- NewsRepository: save/list con idempotencia (artículos, posts, sentimiento).
- CLI collect_news (run_news_pipeline con collectors fake).
- Scheduler: register_news_job.
- Dashboard news_data (capa pura con sesión SQLite).
"""

from datetime import datetime

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src.analyzers.relevance import (
    filter_relevant,
    is_economically_relevant,
    relevance_score,
)
from src.analyzers.sentiment import (
    analyze_text,
    score_text,
    to_sentiment_score,
)
from src.db.models import Base
from src.db.repositories import NewsRepository
from src.models.news import NewsArticle, SentimentScore, SocialPost
from src.scheduler.jobs import register_news_job
from src.scripts.collect_news import run_news_pipeline


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


def _article(url="https://medio.com/1", source="El Medio", title="Inflación baja en julio"):
    return NewsArticle(source=source, title=title, url=url,
                       published=datetime(2026, 8, 19, 10, 0))


def _post(url="https://reddit.com/1", title="El dólar sube"):
    return SocialPost(source="reddit", channel="vzla", title=title, url=url,
                      text="Texto de ejemplo", score=100, num_comments=20,
                      published=datetime(2026, 8, 19, 12, 0))


class TestSentimentAnalyzer:
    def test_positivo(self):
        score, label = score_text("La economía venezolana muestra recuperación y crecimiento")
        assert label == "positive"
        assert score > 0

    def test_negativo(self):
        score, label = score_text("La crisis económica provoca pérdidas y desempleo")
        assert label == "negative"
        assert score < 0

    def test_neutral(self):
        score, label = score_text("El BCV publicó hoy su reporte mensual")
        assert label == "neutral"
        assert score == 0.0

    def test_vacio(self):
        assert score_text("") == (0.0, "neutral")
        assert score_text(None) == (0.0, "neutral")

    def test_negacion_invierte(self):
        # "no hay crecimiento" → el término positivo se invierte a negativo
        score, label = score_text("El gobierno dice que no hay crecimiento")
        assert label == "negative"

    def test_analyze_text_api(self):
        assert analyze_text("crisis")[1] == "negative"

    def test_to_sentiment_score(self):
        score = to_sentiment_score("news", 1, "La economía se recupera")
        assert score is not None
        assert score.item_type == "news"
        assert score.item_id == 1
        assert score.label == "positive"

    def test_to_sentiment_score_neutral_es_none(self):
        assert to_sentiment_score("news", 1, "El BCV publicó su reporte") is None


class TestNewsRepository:
    def test_save_articles_idempotente(self, session):
        repo = NewsRepository(session)
        assert repo.save_articles([_article()]) == 1
        assert repo.save_articles([_article()]) == 0  # duplicada
        assert repo.count_articles() == 1

    def test_list_articles(self, session):
        repo = NewsRepository(session)
        repo.save_articles([_article(url="u1", title="A"),
                            _article(url="u2", title="B", source="Otro")])
        articles = repo.list_articles(limit=10)
        assert len(articles) == 2
        assert repo.list_articles(source="Otro")[0].title == "B"

    def test_save_posts_idempotente(self, session):
        repo = NewsRepository(session)
        assert repo.save_posts([_post()]) == 1
        assert repo.save_posts([_post()]) == 0
        assert repo.count_posts() == 1

    def test_save_sentiment_idempotente(self, session):
        repo = NewsRepository(session)
        s1 = SentimentScore(item_type="news", item_id=1, text="crisis", score=-0.5, label="negative")
        assert repo.save_sentiment([s1]) == 1
        assert repo.save_sentiment([s1]) == 0
        assert len(repo.list_sentiment()) == 1

    def test_sentiment_summary(self, session):
        repo = NewsRepository(session)
        repo.save_sentiment([
            SentimentScore(item_type="news", item_id=1, text="crisis", score=-1.0, label="negative"),
            SentimentScore(item_type="social", item_id=2, text="crecimiento", score=0.5, label="positive"),
            SentimentScore(item_type="news", item_id=3, text="reporte", score=0.0, label="neutral"),
        ])
        summary = repo.sentiment_summary()
        assert summary["total"] == 3
        assert summary["positive"] == 1
        assert summary["neutral"] == 1
        assert summary["negative"] == 1
        assert summary["mean_score"] == pytest.approx(-0.1667, abs=0.001)

    def test_sentiment_summary_vacio(self, session):
        summary = NewsRepository(session).sentiment_summary()
        assert summary == {"total": 0, "positive": 0, "neutral": 0,
                           "negative": 0, "mean_score": 0.0}


class TestEconomicRelevance:
    def test_relevante_fuerte(self):
        # Un término fuerte (dolar, inflacion) basta
        assert is_economically_relevant("El dólar sube frente al bolívar")
        assert is_economically_relevant("Inflación de julio cae al 2%")

    def test_relevante_debil_requiere_dos(self):
        # Términos débiles solos no alcanzan
        assert not is_economically_relevant("El mercado de fichajes del fútbol")
        # Pero dos débiles sí
        assert is_economically_relevant("Empresas reportan ingresos y ganancias")

    def test_irrelevante(self):
        assert not is_economically_relevant("Huracán deja sin electricidad a Hawái")
        assert not is_economically_relevant("Terremoto causa 50 fallecidos")
        assert not is_economically_relevant("Ucrania lanza ataque con drones")
        assert not is_economically_relevant("Pieza teatral explora travesía de Odiseo")

    def test_vacio(self):
        assert not is_economically_relevant("")
        assert not is_economically_relevant(None)

    def test_relevance_score_pondera(self):
        assert relevance_score("El dólar sube") >= 3  # fuerte
        assert relevance_score("Empresas y mercados") >= 2  # dos débiles
        assert relevance_score("Nota cultural") == 0

    def test_filter_relevant(self):
        texts = ["El dólar sube", "Pieza teatral de Odiseo"]
        results = filter_relevant(texts)
        assert results[0][1] is True
        assert results[1][1] is False


class FakeRSS:
    def __init__(self, articles=None):
        self._articles = articles or []

    def fetch_articles(self, per_feed_limit=25):
        return self._articles


class FakeReddit:
    def __init__(self, posts=None, exc=None):
        self._posts = posts or []
        self._exc = exc

    def fetch_posts(self, limit=25):
        if self._exc:
            raise self._exc
        return self._posts


class TestRunNewsPipeline:
    def test_pipeline_completo(self, session):
        summary = run_news_pipeline(
            session,
            rss=FakeRSS([_article(), _article(url="u2", title="El dólar sigue subiendo")]),
            reddit=FakeReddit([_post()]),
        )
        assert summary["news"]["fetched"] == 2
        assert summary["news"]["relevant"] == 2
        assert summary["news"]["saved"] == 2
        assert summary["social"]["fetched"] == 1
        assert summary["social"]["relevant"] == 1
        assert summary["social"]["saved"] == 1
        # Los textos con tono generan sentimiento
        assert summary["sentiment"]["saved"] >= 2

    def test_pipeline_filtra_irrelevantes(self, session):
        summary = run_news_pipeline(
            session,
            rss=FakeRSS([
                _article(),  # "Inflación baja en julio" → relevante
                _article(url="u2", title="Huracán deja sin electricidad a Hawái"),
                _article(url="u3", title="Pieza teatral explora travesía de Odiseo"),
            ]),
            reddit=FakeReddit([_post(), _post(url="https://reddit.com/x", title="Cultura y arte")]),
        )
        assert summary["news"]["fetched"] == 3
        assert summary["news"]["relevant"] == 1
        assert summary["news"]["saved"] == 1
        assert summary["social"]["fetched"] == 2
        assert summary["social"]["relevant"] == 1
        assert summary["social"]["saved"] == 1

    def test_pipeline_reddit_caido_degrada(self, session):
        summary = run_news_pipeline(
            session,
            rss=FakeRSS([_article()]),
            reddit=FakeReddit(exc=RuntimeError("sin credenciales")),
        )
        assert summary["news"]["saved"] == 1
        assert summary["social"]["saved"] == 0

    def test_pipeline_vacio(self, session):
        summary = run_news_pipeline(session, rss=FakeRSS(), reddit=FakeReddit())
        assert summary["news"]["fetched"] == 0
        assert summary["news"]["saved"] == 0
        assert summary["social"]["saved"] == 0


class TestRegisterNewsJob:
    def test_registra_job(self):
        scheduler = BackgroundScheduler()
        register_news_job(scheduler)
        job = scheduler.get_job("collect_news")
        assert job is not None
        assert job.name == "Recolección periódica de noticias y sentimiento (Fase A)"

    def test_resregistra_sin_duplicar(self):
        scheduler = BackgroundScheduler()
        register_news_job(scheduler)
        register_news_job(scheduler)
        jobs = [j.id for j in scheduler.get_jobs()]
        assert jobs.count("collect_news") == 1


class TestDashboardNewsData:
    def test_sentiment_summary_db(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import news_data

        repo = NewsRepository(session)
        repo.save_sentiment([
            SentimentScore(item_type="news", item_id=1, text="crisis", score=-0.5, label="negative"),
        ])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        assert news_data.sentiment_summary()["negative"] == 1

    def test_sentiment_summary_db_caida_devuelve_vacio(self, monkeypatch):
        from src.dashboard import news_data

        def boom():
            raise ConnectionError("db caída")

        monkeypatch.setattr("src.db.session.session_scope", boom)
        assert news_data.sentiment_summary()["total"] == 0
        assert news_data.recent_articles() == []

    def test_recent_articles_db(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import news_data

        NewsRepository(session).save_articles([_article()])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        articles = news_data.recent_articles(limit=5)
        assert len(articles) == 1
        assert articles[0].title == "Inflación baja en julio"

    def test_sentiment_label(self):
        from src.dashboard.news_data import sentiment_label

        assert sentiment_label(0.5) == "Positivo"
        assert sentiment_label(-0.5) == "Negativo"
        assert sentiment_label(0.0) == "Neutral"