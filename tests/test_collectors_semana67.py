"""
Tests de los collectors de Fase A (Semana 6-7)
==============================================

Cubren: BVC (yfinance), Binance P2P, CGR, INE y OPEC con mocks.
"""

import pandas as pd
import pytest

from src.collectors.errors import CollectorSourceError
from src.collectors.fiscal.cgr_collector import CGRCollector, find_documents
from src.collectors.international.opec_collector import (
    OPECCollector,
    parse_basket_price,
)
from src.collectors.market.binance_collector import BinanceCollector
from src.collectors.market.bvc_collector import BVCCollector, _to_index_point
from src.collectors.official.ine_collector import INECollector, find_indicators


class TestBVC:
    def test_to_index_point(self):
        idx = pd.DatetimeIndex(["2026-08-19"], name="Date")
        row = pd.DataFrame({"Close": [1234.5]}, index=idx).iloc[0]
        point = _to_index_point(row, "IBC")
        assert point.value == 1234.5
        assert point.symbol == "IBC"
        assert point.date.year == 2026

    def test_to_index_point_sin_cierre(self):
        row = pd.Series({"Close": None}, name="2026-08-19")
        with pytest.raises(CollectorSourceError):
            _to_index_point(row, "IBC")

    def test_fetch_index_con_fake_ticker(self, monkeypatch):
        class FakeTicker:
            def history(self, period=None):
                return pd.DataFrame(
                    {"Close": [100.0, 105.5]},
                    index=pd.to_datetime(["2026-08-18", "2026-08-19"]),
                )

        collector = BVCCollector()
        collector._history = lambda period=None: FakeTicker().history(period)
        point = collector.fetch_index()
        assert point.rate == 105.5
        assert point.source == "bvc"
        assert point.currency == "usd"

    def test_fetch_index_sin_datos(self):
        collector = BVCCollector()
        collector._history = lambda period=None: pd.DataFrame()
        with pytest.raises(CollectorSourceError):
            collector.fetch_index()


class TestBinance:
    def test_fetch_usdt_rate(self, monkeypatch):
        response = {
            "data": [
                {"adv": {"price": "96.50", "asset": "USDT", "fiat": "VES"}}
            ]
        }

        def fake_post(url, json=None, params=None):
            assert json["tradeType"] == "SELL"
            assert json["asset"] == "USDT"
            return response

        monkeypatch.setattr(
            "src.collectors.market.binance_collector.http_post_json", fake_post
        )
        rate = BinanceCollector().fetch_usdt_rate()
        assert rate.source == "binance"
        assert rate.currency == "usdt"
        assert rate.rate == 96.5

    def test_fetch_usdt_rate_sin_ofertas(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.market.binance_collector.http_post_json",
            lambda url, json=None, params=None: {"data": []},
        )
        with pytest.raises(CollectorSourceError):
            BinanceCollector().fetch_usdt_rate()

    def test_fetch_usdt_rate_no_parseable(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.market.binance_collector.http_post_json",
            lambda url, json=None, params=None: {"data": [{"adv": {}}]},
        )
        with pytest.raises(CollectorSourceError):
            BinanceCollector().fetch_usdt_rate()


CGR_HTML = """
<html>
<a href="https://www.cgr.gob.ve/informes/informe_gestion_2025.pdf">Informe de Gestión 2025</a>
<a href="/memoria_2024.pdf">Memoria y Cuenta 2024</a>
<a href="/noticias">Noticias</a>
</html>
"""


class TestCGR:
    def test_find_documents(self):
        docs = find_documents(CGR_HTML, "https://www.cgr.gob.ve")
        assert len(docs) == 2
        assert docs[0].title == "Informe de Gestión 2025"
        assert docs[0].year == 2025
        assert docs[1].url == "https://www.cgr.gob.ve/memoria_2024.pdf"
        assert docs[1].year == 2024

    def test_fetch_documents(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.fiscal.cgr_collector.http_get_text",
            lambda url, params=None: CGR_HTML,
        )
        docs = CGRCollector().fetch_documents()
        assert len(docs) == 2


INE_HTML = """
<html><body>
<p>La tasa de desempleo fue 5,4% en 2025.</p>
<p>La pobreza alcanzó 30.2% según el último informe.</p>
<p>Población total: 28.4 millones.</p>
</body></html>
"""


class TestINE:
    def test_find_indicators(self):
        points = find_indicators(INE_HTML)
        labels = {p.indicator for p in points}
        assert "desempleo" in labels
        assert "pobreza" in labels
        assert "poblacion" in labels

    def test_find_indicators_sin_datos(self):
        assert find_indicators("<html><p>sin indicadores</p></html>") == []

    def test_fetch_indicators(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.official.ine_collector.http_get_text",
            lambda url, params=None: INE_HTML,
        )
        points = INECollector().fetch_indicators()
        assert len(points) == 3


OPEC_HTML = """
<html><body>
<h1>OPEC Reference Basket</h1>
<p>The OPEC Reference Basket price was $78.45 per barrel.</p>
</body></html>
"""


class TestOPEC:
    def test_parse_basket_price(self):
        point = parse_basket_price(OPEC_HTML)
        assert point.value == 78.45
        assert point.indicator == "cesta_opep"
        assert point.unit == "USD/bbl"

    def test_parse_basket_price_sin_precio(self):
        with pytest.raises(CollectorSourceError):
            parse_basket_price("<html><p>sin precio</p></html>")

    def test_fetch_basket_price(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.international.opec_collector.http_get_text",
            lambda url, params=None: OPEC_HTML,
        )
        point = OPECCollector().fetch_basket_price()
        assert point.value == 78.45