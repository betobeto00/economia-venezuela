"""
Tests de los nuevos collectors (SENIAT, MPPEF, PDVSA, FMI, CEPAL)
=================================================================
"""

import pytest
from datetime import date, timedelta

from src.collectors.errors import CollectorSourceError
from src.collectors.fiscal.mppef_collector import MPPEFCollector
from src.collectors.fiscal.seniat_collector import SENIATCollector
from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector
from src.collectors.international.cepal_collector import (
    CEPALCollector,
    GDP_RUBRO_TOTAL,
    parse_data,
    parse_dimensions,
)
from src.collectors.international.imf_collector import IMFCollector, parse_imf_series
from src.collectors.international.pdvsa_collector import PDVSACollector, parse_basket_price
from src.collectors.international.unsceb_collector import (
    UNSCEBCollector,
    aggregate_by_year,
    parse_expenses,
)

# ---------------------------------------------------------------- SENIAT

SENIAT_HTML = """
<html>
<a href="https://www.seniat.gob.ve/wp-content/uploads/2026/01/Aviso_web_decreto_exoneracion_5196.pdf">Aviso Decreto Exoneración 2026</a>
<a href="/wp-content/uploads/2026/01/Gaceta_Oficial_6952.pdf">Gaceta Oficial N° 6952</a>
<a href="/wp-content/uploads/2024/01/Glosario-Aduanero.pdf">Glosario Aduanero</a>
<a href="/portal/tributario">Portal Tributario</a>
</html>
"""


class TestSENIAT:
    def test_find_documents(self):
        from src.collectors.fiscal.documents import find_documents
        from src.collectors.fiscal.seniat_collector import DOC_EXTENSIONS, DOC_KEYWORDS

        docs = find_documents(
            SENIAT_HTML, "https://www.seniat.gob.ve", source="seniat",
            extensions=DOC_EXTENSIONS, keywords=DOC_KEYWORDS,
        )
        assert len(docs) == 3
        assert {d.source for d in docs} == {"seniat"}
        assert docs[0].year == 2026
        assert docs[1].url == "https://www.seniat.gob.ve/wp-content/uploads/2026/01/Gaceta_Oficial_6952.pdf"

    def test_fetch_documents(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.fiscal.seniat_collector.http_get_text",
            lambda url, params=None: SENIAT_HTML,
        )
        docs = SENIATCollector().fetch_documents()
        assert len(docs) == 3


# ---------------------------------------------------------------- MPPEF

MPPEF_HTML = """
<html>
<a href="https://www.mppef.gob.ve/wp-content/uploads/2026/08/Informe_Ejecucion_Presupuestaria.pdf">Informe de Ejecución Presupuestaria 2026</a>
<a href="/wp-content/uploads/2026/01/Memoria_2025.pdf">Memoria y Cuenta 2025</a>
<a href="/noticias">Noticias</a>
</html>
"""


class TestMPPEF:
    def test_find_documents(self):
        from src.collectors.fiscal.documents import find_documents

        docs = find_documents(
            MPPEF_HTML, "https://www.mppef.gob.ve", source="mppef",
            extensions=(".pdf", ".xls", ".xlsx"),
            keywords=("presupuesto", "ejecuci", "finanza", "fiscal", "gaceta", "memoria"),
        )
        assert len(docs) == 2
        assert docs[0].year == 2026
        assert docs[0].title == "Informe de Ejecución Presupuestaria 2026"

    def test_fetch_documents(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.fiscal.mppef_collector.http_get_text",
            lambda url, params=None: MPPEF_HTML,
        )
        docs = MPPEFCollector().fetch_documents()
        assert len(docs) == 2


# ---------------------------------------------------------------- PDVSA

PDVSA_HTML = """
<html><body>
<h2>Cesta venezolana</h2>
<p>El precio de la cesta venezolana se ubicó en $62,45 por barril.</p>
</body></html>
"""

PDVSA_ALT_HTML = """
<html><body>
<p>The Venezuelan basket price was $64.10 per barrel.</p>
</body></html>
"""

PDVSA_DOCS_HTML = """
<html>
<a href="https://pdvsa-adhoc.com/wp-content/uploads/2026/03/Comunicado-Resultados-operacionales-2025.pdf">Comunicado Resultados operacionales 2025</a>
<a href="/wp-content/uploads/2025/05/CITGO-REPORTA_ES.pdf">CITGO reporta avances operativos</a>
<a href="/noticias">Noticias</a>
</html>
"""


class TestPDVSA:
    def test_parse_basket_price(self):
        point = parse_basket_price(PDVSA_HTML)
        assert point.value == 62.45
        assert point.indicator == "cesta_venezolana"
        assert point.unit == "USD/bbl"

    def test_parse_basket_price_ingles(self):
        point = parse_basket_price(PDVSA_ALT_HTML)
        assert point.value == 64.10

    def test_parse_basket_price_sin_precio(self):
        with pytest.raises(CollectorSourceError):
            parse_basket_price("<html><p>sin precio</p></html>")

    def test_fetch_basket_price(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.international.pdvsa_collector.http_get_text",
            lambda url, params=None: PDVSA_HTML,
        )
        point = PDVSACollector().fetch_basket_price()
        assert point.value == 62.45

    def test_fetch_documents(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.international.pdvsa_collector.http_get_text",
            lambda url, params=None: PDVSA_DOCS_HTML,
        )
        docs = PDVSACollector().fetch_documents()
        assert len(docs) == 2
        assert docs[0].source == "pdvsa"
        assert docs[0].year == 2025
        assert "Resultados operacionales" in docs[0].title


# ---------------------------------------------------------------- FMI

IMF_PAYLOAD = {
    "CompactData": {
        "DataSet": {
            "Series": [{
                "@INDICATOR": "NGDP_RPCH",
                "Obs": [
                    {"@TIME_PERIOD": "2020", "@OBS_VALUE": "-30.0"},
                    {"@TIME_PERIOD": "2021", "@OBS_VALUE": "1.2"},
                    {"@TIME_PERIOD": "2022", "@OBS_VALUE": "n/a"},
                ],
            }]
        }
    }
}


class TestIMF:
    def test_parse_imf_series(self):
        points = parse_imf_series(IMF_PAYLOAD, "NGDP_RPCH")
        assert [p.period for p in points] == ["2020", "2021"]
        assert points[0].value == -30.0
        assert points[1].value == 1.2
        assert points[0].source == "imf"
        assert points[0].unit == "%"

    def test_parse_imf_series_filtra_indicador(self):
        points = parse_imf_series(IMF_PAYLOAD, "PCPIPCH")
        assert points == []

    def test_parse_imf_series_sin_datos(self):
        with pytest.raises(CollectorSourceError):
            parse_imf_series({"CompactData": {"DataSet": None}}, "NGDP_RPCH")

    def test_fetch_gdp_growth(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.international.imf_collector.http_get_json",
            lambda url, params=None: IMF_PAYLOAD,
        )
        points = IMFCollector().fetch_gdp_growth()
        assert len(points) == 2
        assert points[0].indicator == "NGDP_RPCH"

    def test_fetch_indicator_url(self, monkeypatch):
        seen = {}

        def fake(url, params=None):
            seen["url"] = url
            return IMF_PAYLOAD

        monkeypatch.setattr(
            "src.collectors.international.imf_collector.http_get_json", fake
        )
        IMFCollector().fetch_gdp_growth()
        assert "IFS/A.VE.NGDP_RPCH" in seen["url"]


# ---------------------------------------------------------------- CEPAL

CEPAL_DIMS = {
    "body": {"dimensions": [
        {"id": 208, "members": [
            {"name": "Brasil", "id": 5},
            {"name": "Venezuela (República Bolivariana de)", "id": 259},
        ]},
        {"id": 21004, "members": [{"name": "Producto interno bruto (PIB)", "id": 21166}]},
        {"id": 29117, "members": [
            {"name": "1990", "id": 29160},
            {"name": "1991", "id": 29161},
            {"name": "1992", "id": 29162},
        ]},
    ]}
}

CEPAL_DATA = {
    "body": {
        "metadata": {"indicator_name": "PIB", "unit": "Millones de dólares"},
        "data": [
            {"value": "150446.247", "dim_208": 259, "dim_21004": 21166, "dim_29117": 29160},
            {"value": "165084.498", "dim_208": 259, "dim_21004": 21166, "dim_29117": 29161},
            {"value": "abc", "dim_208": 259, "dim_21004": 21166, "dim_29117": 29162},
        ],
    }
}


class TestCEPAL:
    def test_parse_dimensions(self):
        mapping = parse_dimensions(CEPAL_DIMS)
        assert mapping["country"] == 259
        assert mapping["years"][29160] == 1990
        assert mapping["years"][29162] == 1992

    def test_parse_dimensions_sin_anios(self):
        with pytest.raises(CollectorSourceError):
            parse_dimensions({"body": {"dimensions": []}})

    def test_parse_data(self):
        metadata, rows = parse_data(CEPAL_DATA)
        assert metadata["unit"] == "Millones de dólares"
        assert rows == [{"year": 29160, "value": 150446.247},
                        {"year": 29161, "value": 165084.498}]

    def test_parse_data_sin_observaciones(self):
        with pytest.raises(CollectorSourceError):
            parse_data({"body": {"data": []}})

    def test_fetch_gdp(self, monkeypatch):
        def fake(url, params=None):
            if url.endswith("/dimensions"):
                return CEPAL_DIMS
            return CEPAL_DATA

        monkeypatch.setattr(
            "src.collectors.international.cepal_collector.http_get_json", fake
        )
        points = CEPALCollector().fetch_gdp(start_year=1990, end_year=1991)
        assert [p.period for p in points] == ["1990", "1991"]
        assert points[0].value == 150446.247
        assert points[0].indicator == "pib_total"
        assert points[0].source == "cepal"
        assert points[0].unit == "Millones de dólares"

    def test_fetch_gdp_members_incluye_rubro(self, monkeypatch):
        seen = {}

        def fake(url, params=None):
            if url.endswith("/dimensions"):
                return CEPAL_DIMS
            seen["members"] = params.get("members")
            return CEPAL_DATA

        monkeypatch.setattr(
            "src.collectors.international.cepal_collector.http_get_json", fake
        )
        CEPALCollector().fetch_gdp()
        assert seen["members"] == f"259,{GDP_RUBRO_TOTAL}"


# ---------------------------------------------------------------- UNSCEB

UNSCEB_CSV = (
    "calendar_year,agency,sub_agency,amount,_currency_amount,country/territory,"
    "subregion,location_type,region,function\r\n"
    "2019,UNEP,UNEP,237900.52,USD,Venezuela (Bolivarian Republic of),South America,"
    "COU,Americas,Development Assistance\r\n"
    "2019,UNICEF,UNICEF,100000.00,USD,Venezuela (Bolivarian Republic of),South America,"
    "COU,Americas,Humanitarian\r\n"
    "2020,UNIDO,UNIDO,879647.24,EUR,Venezuela (Bolivarian Republic of),South America,"
    "COU,Americas,\r\n"
    "2019,UNEP,UNEP,-500.00,USD,Venezuela (Bolivarian Republic of),South America,"
    "COU,Americas,Development Assistance\r\n"
    "2020,FAO,FAO,999999.00,USD,Brasil,South America,COU,Americas,Development\r\n"
    "2020,UNICEF,UNICEF,abc,USD,Venezuela (Bolivarian Republic of),South America,"
    "COU,Americas,\r\n"
)


class TestUNSCEB:
    def test_parse_expenses_filtra_venezuela(self):
        rows = parse_expenses(UNSCEB_CSV.encode("utf-8"))
        assert len(rows) == 5  # excluye Brasil y la fila sin país
        assert all(r["country/territory"].startswith("Venezuela") for r in rows)

    def test_aggregate_by_year(self):
        rows = parse_expenses(UNSCEB_CSV.encode("utf-8"))
        points = aggregate_by_year(rows)
        # 2019 USD: 237900.52 + 100000 - 500 = 337400.52
        # 2020 EUR: 879647.24
        assert len(points) == 2
        usd19 = next(p for p in points if p.period == "2019" and p.unit == "USD")
        assert usd19.value == 337400.52
        eur20 = next(p for p in points if p.period == "2020" and p.unit == "EUR")
        assert eur20.value == 879647.24
        assert usd19.indicator == "gasto_onu_venezuela"

    def test_fetch_venezuela_expenses(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.international.unsceb_collector.http_get_bytes",
            lambda url, params=None: UNSCEB_CSV.encode("utf-8"),
        )
        points = UNSCEBCollector().fetch_venezuela_expenses()
        assert len(points) == 2
        assert points[0].source == "unsceb"


# ---------------------------------------------------------------- GACETA OFICIAL

BUSQUEDA_HTML = """
<table class="table" id="tablaGacetas"><tbody>
<tr><td>43.429</td><td>ORDINARIA</td><td>GACETA OFICIAL</td><td>04/08/2026</td>
<td>472605</td><td>472628</td>
<td><span class="badge bg-success">PUBLICADO</span></td>
<td><a href="http://www.gacetaoficial.gob.ve/gacetas/43429">Ver</a></td></tr>
<tr><td>43.420</td><td>EXTRAORDINARIA</td><td>GACETA OFICIAL</td><td>21/07/2026</td>
<td>472477</td><td>472492</td>
<td><span class="badge bg-success">PUBLICADO</span></td>
<td><a href="http://www.gacetaoficial.gob.ve/gacetas/43420">Ver</a></td></tr>
<tr><td>x</td><td>ORDINARIA</td><td>GACETA OFICIAL</td><td>fecha_invalida</td>
<td>1</td><td>2</td>
<td><span class="badge bg-success">PUBLICADO</span></td>
<td><a href="http://www.gacetaoficial.gob.ve/gacetas/99999">Ver</a></td></tr>
</tbody></table>
"""


class TestGacetaOficial:
    def test_parse_busqueda(self):
        collector = GacetaOficialCollector(base_url="http://www.gacetaoficial.gob.ve")
        rows = collector._parse_busqueda(BUSQUEDA_HTML)
        assert len(rows) == 2  # descarta fecha inválida
        assert rows[0]["numero"] == 43429
        assert rows[0]["tipo"] == "ORDINARIA"
        assert rows[0]["fecha"].isoformat() == "2026-08-04"
        assert rows[1]["numero"] == 43420
        assert rows[1]["tipo"] == "EXTRAORDINARIA"

    def test_pdf_url_pattern(self):
        collector = GacetaOficialCollector()
        url = collector._pdf_url(43429, date(2026, 8, 4), "ordinaria")
        assert url.endswith("/storage/2026/43429-2026-08-04-ORDINARIA.pdf")

    def test_fetch_documentos(self, monkeypatch):
        monkeypatch.setattr(
            "src.collectors.fiscal.gaceta_collector.http_get_text",
            lambda url, params=None: BUSQUEDA_HTML,
        )
        docs = GacetaOficialCollector().fetch_documentos(["presupuesto"])
        assert len(docs) == 2
        assert docs[0].source == "gaceta"
        assert docs[0].url.endswith("43429-2026-08-04-ORDINARIA.pdf")
        assert docs[0].year == 2026

    def test_fetch_documentos_deduplica(self, monkeypatch):
        seen = []

        def fake(url, params=None):
            seen.append(params.get("texto"))
            return BUSQUEDA_HTML

        monkeypatch.setattr(
            "src.collectors.fiscal.gaceta_collector.http_get_text", fake
        )
        docs = GacetaOficialCollector().fetch_documentos(["presupuesto", "endeudamiento"])
        assert seen == ["presupuesto", "endeudamiento"]
        assert len(docs) == 2  # misma gaceta en ambas búsquedas -> dedupe

    def test_fetch_gacetas_dia(self, monkeypatch):
        def fake(url, params=None):
            assert params == {"year": 2026, "month": 6, "day": 17}
            return [{"numero_gaceta": 43399, "categoria": "ORDINARIA",
                     "fecha_gaceta": "2026-06-17",
                     "ruta_archivo": "/storage/2026/43399-2026-06-17-ORDINARIA.pdf"}]

        monkeypatch.setattr(
            "src.collectors.fiscal.gaceta_collector.http_get_json", fake
        )
        gs = GacetaOficialCollector().fetch_gacetas_dia(2026, 6, 17)
        assert gs[0]["numero_gaceta"] == 43399

    def test_fetch_calendario(self, monkeypatch):
        html = ('<div class="calendar-day has-gaceta" data-year="2026" '
                'data-month="6" data-day="17">17<span class="badge">1</span></div>'
                '<div class="calendar-day" data-year="2026" data-month="6" '
                'data-day="18">18</div>')
        monkeypatch.setattr(
            "src.collectors.fiscal.gaceta_collector.http_get_text",
            lambda url, params=None: html,
        )
        days = GacetaOficialCollector().fetch_calendario()
        assert days == [{"year": 2026, "month": 6, "day": 17}]

    def test_fetch_recientes(self, monkeypatch):
        calls = []

        def fake(url, params=None):
            calls.append(params)
            return []

        monkeypatch.setattr(
            "src.collectors.fiscal.gaceta_collector.http_get_json", fake
        )
        GacetaOficialCollector().fetch_recientes(days=3)
        assert len(calls) == 3
        assert calls[0]["day"] == (date.today() - timedelta(days=2)).day