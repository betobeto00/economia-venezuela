"""
Tests de los collectors de Fase A (Semana 5)
============================================

Simulan respuestas HTTP parcheando ``src.collectors.http`` para no depender
de red. Cubren: BCV (tasa + IPC), OVF (IPC), Banco Mundial y ONAPRE.
"""

import json
from datetime import datetime

import pytest

from src.collectors.errors import CollectorSourceError
from src.collectors.market.bcv_collector import (
    BCVCollector,
    parse_dolarapi,
    parse_ipc,
)
from src.collectors.market.ovf_collector import (
    OVFCollector,
    find_inflation_post,
    parse_bulletin,
)


@pytest.fixture
def mock_http(monkeypatch):
    """Simula respuestas parcheando los helpers en los módulos que los usan."""
    responses = {}
    calls = []

    def fake_json(url, params=None):
        calls.append((url, params))
        return responses[url]

    def fake_text(url, params=None):
        calls.append((url, params))
        return responses[url]

    # BCV (solo http_get_json importado)
    monkeypatch.setattr("src.collectors.market.bcv_collector.http_get_json", fake_json)
    # OVF (solo http_get_text importado)
    monkeypatch.setattr("src.collectors.market.ovf_collector.http_get_text", fake_text)
    return responses, calls


DOLARAPI_OK = {
    "moneda": "Bolívares",
    "iso_currency": "VES",
    "precio": 9.63,
    "fecha": "2026-08-19T00:00:00.000Z",
    "variacion": 0.35,
}


class TestBCV:
    def test_parse_dolarapi(self):
        rate = parse_dolarapi(DOLARAPI_OK)
        assert rate.rate == 9.63
        assert rate.source == "bcv"
        assert rate.currency == "usd"
        assert rate.variation_pct == 0.35
        assert rate.iso_date == "2026-08-19"

    def test_parse_dolarapi_lista(self):
        rate = parse_dolarapi([DOLARAPI_OK])
        assert rate.rate == 9.63

    def test_parse_dolarapi_fallback_transferencia(self):
        rate = parse_dolarapi({"transferencia": 10.0, "actualizado": "2026-08-19"})
        assert rate.rate == 10.0

    def test_parse_dolarapi_sin_tasa(self):
        with pytest.raises(CollectorSourceError):
            parse_dolarapi({"moneda": "VES"})

    def test_parse_ipc(self):
        point = parse_ipc(
            {"period": "2026-07", "monthly_rate": 2.1, "annual_rate": 15.0},
            source="bcv",
        )
        assert point.monthly_rate == 2.1
        assert point.annual_rate == 15.0

    def test_parse_ipc_alias_espanol(self):
        point = parse_ipc(
            {"periodo": "2026-06", "inflacion_mensual": "1,5", "interanual": "12.3"},
            source="bcv",
        )
        assert point.monthly_rate == 1.5
        assert point.annual_rate == 12.3

    def test_parse_ipc_sin_periodo(self):
        with pytest.raises(CollectorSourceError):
            parse_ipc({"monthly_rate": 1.0}, source="bcv")

    def test_fetch_official_rate(self, mock_http):
        responses, _ = mock_http
        url = "https://ve.dolarapi.com/v1/dolares/oficial"
        responses[url] = DOLARAPI_OK
        collector = BCVCollector()
        rate = collector.fetch_official_rate()
        assert rate.rate == 9.63
        assert rate.date.year == 2026

    def test_fetch_ipc(self, mock_http):
        responses, _ = mock_http
        url = "https://api.bcv.org.ve/ipc"
        responses[url] = {"period": "2026-07", "monthly_rate": 2.1}
        collector = BCVCollector()
        point = collector.fetch_ipc("2026-07")
        assert point.period == "2026-07"
        assert point.monthly_rate == 2.1


BLOG_HTML = """
<html><body>
<a href="https://observatoriodefinanzas.com">Inicio</a>
<a href="https://observatoriodefinanzas.com/2026/08/la-inflacion-de-julio/">La inflación de julio fue de 1,2%</a>
</body></html>
"""

BULLETIN_HTML = """
<html><body>
<h1>Reporte de inflación de julio 2026</h1>
<p>La inflación mensual de julio fue de 1,2% y la interanual acumulada de 25,4%.</p>
</body></html>
"""


class TestOVF:
    def test_find_inflation_post(self):
        url = find_inflation_post(BLOG_HTML, "https://observatoriodefinanzas.com")
        assert url is not None
        assert "inflacion-de-julio" in url

    def test_find_inflation_post_relativo(self):
        html = BLOG_HTML.replace("https://observatoriodefinanzas.com/2026/08/la-inflacion-de-julio/",
                                 "/2026/08/la-inflacion-de-julio/")
        url = find_inflation_post(html, "https://observatoriodefinanzas.com")
        assert url == "https://observatoriodefinanzas.com/2026/08/la-inflacion-de-julio/"

    def test_parse_bulletin(self):
        point = parse_bulletin(BULLETIN_HTML, source="ovf")
        assert point.monthly_rate == 1.2
        assert point.annual_rate == 25.4

    def test_parse_bulletin_sin_tasas(self):
        with pytest.raises(CollectorSourceError):
            parse_bulletin("<html><p>sin datos</p></html>", source="ovf")

    def test_fetch_ipc(self, mock_http):
        responses, calls = mock_http
        base = "https://observatoriodefinanzas.com"
        post = base + "/2026/08/la-inflacion-de-julio/"
        responses[base + "/"] = BLOG_HTML
        responses[post] = BULLETIN_HTML
        point = OVFCollector().fetch_ipc("2026-07")
        assert point.source == "ovf"
        assert point.monthly_rate == 1.2
        assert calls[1][0] == post

    def test_fetch_ipc_sin_publicacion(self, mock_http):
        responses, _ = mock_http
        responses["https://observatoriodefinanzas.com/"] = "<html><a href='x'>Noticias</a></html>"
        with pytest.raises(CollectorSourceError):
            OVFCollector().fetch_ipc()