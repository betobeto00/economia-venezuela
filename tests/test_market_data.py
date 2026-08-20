"""
Tests de la capa de datos de mercado (Fase A)
=============================================

- MarketRepository (save/list/latest con idempotencia).
- CLI collect_market (run_market_pipeline con collectors fake).
- Scheduler: register_market_job.
- Dashboard market_data (capa pura con sesión SQLite).
"""

from datetime import datetime

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src.db.models import Base
from src.db.repositories import MarketRepository
from src.models.market import ExchangeRate, InflationPoint
from src.scheduler.jobs import register_market_job
from src.scripts.collect_market import run_market_pipeline


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


def _rate(source="bcv", currency="usd", date=None):
    return ExchangeRate(
        source=source, currency=currency, rate=9.63,
        date=date or datetime(2026, 8, 19),
        variation_pct=0.35,
    )


def _point(source="bcv", period="2026-07", monthly=2.1):
    return InflationPoint(source=source, period=period, monthly_rate=monthly)


class TestMarketRepository:
    def test_save_rates_idempotente(self, session):
        repo = MarketRepository(session)
        assert repo.save_rates([_rate()]) == 1
        assert repo.save_rates([_rate()]) == 0  # duplicada
        assert len(repo.list_rates()) == 1

    def test_latest_rate(self, session):
        repo = MarketRepository(session)
        repo.save_rates([
            _rate(date=datetime(2026, 8, 18)),
            _rate(date=datetime(2026, 8, 19)),
        ])
        latest = repo.latest_rate("bcv")
        assert latest.rate == 9.63
        assert latest.date.day == 19

    def test_save_inflation_idempotente(self, session):
        repo = MarketRepository(session)
        assert repo.save_inflation([_point()]) == 1
        assert repo.save_inflation([_point()]) == 0
        assert len(repo.list_inflation()) == 1

    def test_latest_inflation(self, session):
        repo = MarketRepository(session)
        repo.save_inflation([_point(period="2026-06"), _point(period="2026-07")])
        latest = repo.latest_inflation("bcv")
        assert latest.period == "2026-07"
        assert latest.monthly_rate == 2.1


class FakeBcv:
    def fetch_official_rate(self):
        return _rate()

    def fetch_ipc(self, period):
        return _point(period=period)


class FakeOvf:
    def fetch_ipc(self, period):
        return InflationPoint(source="ovf", period=period, monthly_rate=3.4)


class FakeBinance:
    def fetch_usdt_rate(self):
        return ExchangeRate(
            source="binance", currency="usdt", rate=96.5, date=datetime(2026, 8, 19)
        )


class TestRunMarketPipeline:
    def test_pipeline_completo(self, session):
        summary = run_market_pipeline(
            session, FakeBcv(), FakeOvf(), FakeBinance(), period="2026-07"
        )
        assert summary["bcv_rate"]["saved"] == 1
        assert summary["bcv_ipc"]["saved"] == 1
        assert summary["ovf_ipc"]["saved"] == 1
        assert summary["binance_usdt"]["saved"] == 1
        repo = MarketRepository(session)
        # bcv + binance + bvc_ibc = 3 tasas
        rates = repo.list_rates()
        assert len(rates) >= 2  # al menos bcv + binance
        assert len(repo.list_inflation()) == 2

    def test_pipeline_idempotente(self, session):
        run_market_pipeline(session, FakeBcv(), FakeOvf(), FakeBinance())
        summary = run_market_pipeline(session, FakeBcv(), FakeOvf(), FakeBinance())
        assert summary["bcv_rate"]["saved"] == 0
        assert summary["bcv_ipc"]["saved"] == 0

    def test_pipeline_fuente_rota_no_falla(self, session):
        class Broken:
            def fetch_official_rate(self):
                raise RuntimeError("sin red")

            def fetch_ipc(self, period):
                raise RuntimeError("sin red")

        summary = run_market_pipeline(session, Broken(), FakeOvf(), Broken())
        assert "ovf_ipc" in summary
        assert "bcv_rate" not in summary
        assert summary["ovf_ipc"]["saved"] == 1


class TestRegisterMarketJob:
    def test_registra_job(self):
        scheduler = BackgroundScheduler()
        register_market_job(scheduler)
        job = scheduler.get_job("collect_market")
        assert job is not None
        assert job.trigger.interval.total_seconds() == 30 * 60

    def test_no_duplica(self):
        scheduler = BackgroundScheduler()
        register_market_job(scheduler)
        register_market_job(scheduler)
        assert len(scheduler.get_jobs()) == 1

    def test_collect_market_job_no_falla(self):
        from src.scheduler.jobs import collect_market_job

        assert isinstance(collect_market_job(), dict)


class TestDashboardMarketData:
    def test_latest_rate_desde_db(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        MarketRepository(session).save_rates([_rate()])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        assert market_data.latest_rate("bcv").rate == 9.63
        assert market_data.latest_rate("ovf") is None

    def test_latest_inflation_desde_db(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        MarketRepository(session).save_inflation([_point()])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        assert market_data.latest_inflation("bcv").monthly_rate == 2.1

    def test_dashboard_metrics(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        repo = MarketRepository(session)
        repo.save_rates([_rate(), _rate(source="binance", currency="usdt", date=datetime(2026, 8, 20))])
        repo.save_inflation([_point()])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        metrics = market_data.dashboard_metrics()
        assert metrics["oficial"].source == "bcv"
        assert metrics["paralelo"].source == "binance"
        assert metrics["inflacion"].monthly_rate == 2.1

    def test_dashboard_metrics_fallback_inflacion_ovf(self, session, monkeypatch):
        # BCV IPC no disponible → el dashboard usa OVF como fallback.
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        MarketRepository(session).save_inflation(
            [_point(source="ovf", period="2026-06", monthly=3.4)]
        )
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        metrics = market_data.dashboard_metrics()
        assert metrics["inflacion"].source == "ovf"
        assert metrics["inflacion"].monthly_rate == 3.4

    def test_latest_rate_db_caida_devuelve_none(self, monkeypatch):
        from src.dashboard import market_data

        def boom():
            raise ConnectionError("db caída")

        monkeypatch.setattr("src.db.session.session_scope", boom)
        assert market_data.latest_rate("bcv") is None
        assert market_data.dashboard_metrics()["oficial"] is None

    def test_format_metric(self):
        from src.dashboard.market_data import format_metric

        assert format_metric(None) == "—"
        assert format_metric(9.5, " Bs") == "9.50 Bs"
        assert format_metric(2.1, " %") == "2.10 %"


class TestBrechaCambiaria:
    def test_brecha_porcentaje(self):
        from src.dashboard.market_data import brecha_porcentaje

        oficial = ExchangeRate(source="bcv", currency="usd", rate=100.0, date=datetime(2026, 8, 19))
        paralelo = ExchangeRate(source="binance", currency="usdt", rate=110.0, date=datetime(2026, 8, 19))
        assert brecha_porcentaje(oficial, paralelo) == pytest.approx(10.0)

    def test_brecha_falta_dato_devuelve_none(self):
        from src.dashboard.market_data import brecha_porcentaje

        oficial = ExchangeRate(source="bcv", currency="usd", rate=100.0, date=datetime(2026, 8, 19))
        assert brecha_porcentaje(oficial, None) is None
        assert brecha_porcentaje(None, None) is None

    def test_brecha_series_desde_db(self, session, monkeypatch):
        from contextlib import nullcontext
        from datetime import timedelta

        import src.db.session as db_session
        from src.dashboard import market_data

        repo = MarketRepository(session)
        base = datetime(2026, 8, 1)
        for i in range(5):
            repo.save_rates([
                ExchangeRate(source="bcv", currency="usd", rate=100.0,
                             date=base + timedelta(days=i)),
                ExchangeRate(source="binance", currency="usdt", rate=110.0,
                             date=base + timedelta(days=i)),
            ])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        df = market_data.brecha_series("binance", since_days=180)
        assert len(df) == 5
        assert list(df.columns) == ["oficial", "paralelo", "brecha_%"]
        assert df["brecha_%"].iloc[0] == pytest.approx(10.0)

    def test_brecha_series_sin_datos(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        df = market_data.brecha_series("binance")
        assert df.empty

    def test_dashboard_metrics_incluye_bybit(self, session, monkeypatch):
        from contextlib import nullcontext

        import src.db.session as db_session
        from src.dashboard import market_data

        repo = MarketRepository(session)
        repo.save_rates([
            _rate(date=datetime(2026, 8, 19)),
            _rate(source="binance", currency="usdt", date=datetime(2026, 8, 20)),
            ExchangeRate(source="bybit", currency="usdt", rate=90.0, date=datetime(2026, 8, 20)),
        ])
        monkeypatch.setattr(db_session, "session_scope", lambda: nullcontext(session))
        metrics = market_data.dashboard_metrics()
        assert metrics["bybit"].source == "bybit"
        assert metrics["bybit"].rate == 90.0