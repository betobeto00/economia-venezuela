"""
Tests del backfill de tasas históricas (usdt.com.ve)
====================================================

- ``aggregate_daily``: agrega snapshots a promedio diario por (source, currency).
- ``backfill_rates``: descarga (con monkeypatch), agrega y persiste idempotente.
- ``SOURCE_MAP``: binance→usdt, bybit→usdt, bcv→usd.
"""

from datetime import datetime, timedelta, timezone

from src.db.models import Base
from src.db.repositories import MarketRepository
from src.scripts.backfill_rates import (
    SOURCE_MAP,
    aggregate_daily,
    backfill_rates,
    download_csv,
)


def _csv_row(ts, source, buy, sell=""):
    return f"{ts},{source},{buy},{sell}"


CSV = "\n".join([
    "captured_at,source,buy_rate,sell_rate",
    _csv_row("2026-01-17T10:00:00+00:00", "binance", "460.5", "461"),
    _csv_row("2026-01-17T10:05:00+00:00", "binance", "461.5", "462"),
    _csv_row("2026-01-17T10:00:00+00:00", "bcv", "450.0", ""),
    _csv_row("2026-01-17T10:05:00+00:00", "bcv", "451.0", ""),
    _csv_row("2026-01-17T10:00:00+00:00", "bybit", "459.0", "453.01"),
    _csv_row("2026-01-18T10:00:00+00:00", "binance", "470.0", "471"),
    _csv_row("2026-01-18T10:00:00+00:00", "bcv", "455.0", ""),
    # fuente desconocida se ignora
    _csv_row("2026-01-18T10:00:00+00:00", "otro", "999", "999"),
    # sin buy_rate se ignora
    _csv_row("2026-01-18T10:00:00+00:00", "binance", "", ""),
])


class TestSourceMap:
    def test_mapeo(self):
        assert SOURCE_MAP == {
            "binance": ("binance", "usdt"),
            "bybit": ("bybit", "usdt"),
            "bcv": ("bcv", "usd"),
        }


class TestAggregateDaily:
    def test_promedio_por_dia_y_fuente(self):
        rates = aggregate_daily(CSV)
        # binance: día 17 -> (460.5+461.5)/2 = 461; día 18 -> 470
        binance = sorted([r for r in rates if r.source == "binance"], key=lambda r: r.date)
        assert len(binance) == 2
        assert binance[0].rate == 461.0
        assert binance[0].currency == "usdt"
        assert binance[1].rate == 470.0

        bcv = sorted([r for r in rates if r.source == "bcv"], key=lambda r: r.date)
        assert len(bcv) == 2
        assert bcv[0].rate == 450.5
        assert bcv[0].currency == "usd"

        bybit = [r for r in rates if r.source == "bybit"]
        assert len(bybit) == 1
        assert bybit[0].rate == 459.0

    def test_filtro_por_fecha(self):
        since = datetime(2026, 1, 18)
        rates = aggregate_daily(CSV, since=since)
        dates = {r.date.date().isoformat() for r in rates}
        assert dates == {"2026-01-18"}

    def test_desconocidos_ignorados(self):
        rates = aggregate_daily(CSV)
        assert all(r.source in ("binance", "bybit", "bcv") for r in rates)
        assert all(r.rate != 999 for r in rates)

    def test_fecha_se_normaliza_a_utc(self):
        rates = aggregate_daily(CSV)
        assert all(r.date.tzinfo is None for r in rates)


class TestDownloadCsv:
    def test_filtra_comentarios(self, monkeypatch):
        raw = "# header\ncaptured_at,source,buy_rate,sell_rate\na,b,c,d\n"

        class Resp:
            text = raw

            def raise_for_status(self):
                return None

        def fake_get(url, **kwargs):
            return Resp()

        monkeypatch.setattr("httpx.get", fake_get)
        out = download_csv()
        assert out == "captured_at,source,buy_rate,sell_rate\na,b,c,d"


class TestBackfillRates:
    def _session(self):
        import pytest
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        return sessionmaker(bind=engine)()

    def test_backfill_persiste(self, monkeypatch):
        monkeypatch.setattr("httpx.get", lambda url, **k: type("R", (), {
            "text": CSV,
            "raise_for_status": lambda self: None,
        })())
        session = self._session()
        result = backfill_rates(session, days=400, persist=True)
        assert result["saved"] == 5  # 2 binance + 2 bcv + 1 bybit
        assert MarketRepository(session).list_rates().__len__() == 5

    def test_backfill_idempotente(self, monkeypatch):
        monkeypatch.setattr("httpx.get", lambda url, **k: type("R", (), {
            "text": CSV,
            "raise_for_status": lambda self: None,
        })())
        session = self._session()
        backfill_rates(session, days=400, persist=True)
        result = backfill_rates(session, days=400, persist=True)
        assert result["saved"] == 0  # todos duplicados
        assert MarketRepository(session).list_rates().__len__() == 5

    def test_backfill_no_save_solo_conteos(self, monkeypatch):
        monkeypatch.setattr("httpx.get", lambda url, **k: type("R", (), {
            "text": CSV,
            "raise_for_status": lambda self: None,
        })())
        session = self._session()
        counts = backfill_rates(session, days=400, persist=False)
        assert counts == {"binance": 2, "bybit": 1, "bcv": 2}
        assert MarketRepository(session).list_rates().__len__() == 0