"""
Tests del collector de reservas internacionales del BCV
=======================================================

Construyen libros ``2_1_1.xlsx`` en memoria con la misma forma que publica el
Banco Central (``FECHA | BCV | FEM | TOTAL`` en millones de USD) para no
depender de la red.
"""

import io
from datetime import datetime

import openpyxl
import pytest

from src.collectors.errors import CollectorSourceError
from src.collectors.official.bcv_reserves_collector import (
    BCVReservesCollector,
    parse_history,
    parse_reserves,
)

HEADER = ["RESERVAS INTERNACIONALES", None, None, None]
TITLES = ["FECHA", "BCV", "FEM (1)", "TOTAL "]
UNITS = [None, "Millones de USD", None, None]


def _book(sheets: dict) -> bytes:
    """``{nombre_hoja: filas}`` → xlsx en bytes con el encabezado del BCV."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        for row in [HEADER, [], TITLES, UNITS] + rows:
            ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


class TestParseReserves:
    def test_toma_la_fila_mas_reciente(self):
        data = _book({"2026": [
            ["04/11/2026(*)", 13188, 3, 13191],
            ["03/11/2026(*)", 12964, 3, 12967],
        ]})

        point = parse_reserves(data)

        assert point.indicator == "reservas_internacionales"
        assert point.period == "2026-11-04"
        assert point.value == pytest.approx(13191e6)
        assert point.unit == "USD"
        assert point.source == "bcv"

    def test_usa_la_primera_hoja_con_datos(self):
        """La hoja del año en curso manda; las viejas no se mezclan."""
        data = _book({
            "2026": [["02/11/2026", 13084, 3, 13087]],
            "2025": [["31/12/2025", 10, 1, 11]],
        })

        point = parse_reserves(data)

        assert point.period == "2026-11-02"
        assert point.value == pytest.approx(13087e6)

    def test_salta_hoja_vacia(self):
        data = _book({
            "2026": [],
            "2025": [["31/12/2025", 100, 2, 102]],
        })

        point = parse_reserves(data)

        assert point.period == "2025-12-31"
        assert point.value == pytest.approx(102e6)

    def test_acepta_celdas_fecha_nativas(self):
        data = _book({"2026": [[datetime(2026, 11, 4), 13188, 3, 13191]]})

        point = parse_reserves(data)

        assert point.period == "2026-11-04"

    def test_ignora_filas_sin_total(self):
        data = _book({"2026": [
            ["04/11/2026(*)", 13188, 3, None],
            ["03/11/2026(*)", 12964, 3, 12967],
        ]})

        point = parse_reserves(data)

        assert point.period == "2026-11-03"

    def test_sin_filas_con_dato_falla(self):
        with pytest.raises(CollectorSourceError):
            parse_reserves(_book({"2026": []}))

    def test_archivo_ilegible_falla(self):
        with pytest.raises(CollectorSourceError):
            parse_reserves(b"no soy un xlsx")


class TestParseHistory:
    def test_serie_ordenada_con_componentes(self):
        data = _book({
            "2026": [
                ["04/11/2026(*)", 13188, 3, 13191],
                ["03/11/2026(*)", 12964, 3, 12967],
            ],
            "2025": [["31/12/2025", 100, 2, 102]],
        })

        days = parse_history(data, start_year=2020)

        assert [d.date for d in days] == ["2025-12-31", "2026-11-03", "2026-11-04"]
        assert days[-1].total_usd == pytest.approx(13191e6)
        assert days[-1].bcv_usd == pytest.approx(13188e6)
        assert days[-1].fem_usd == pytest.approx(3e6)

    def test_filtra_por_start_year(self):
        data = _book({
            "2026": [["04/11/2026(*)", 13188, 3, 13191]],
            "2025": [["31/12/2025", 100, 2, 102]],
        })

        days = parse_history(data, start_year=2026)

        assert [d.date for d in days] == ["2026-11-04"]

    def test_sin_datos_desde_el_ano_pedido_falla(self):
        data = _book({"2025": [["31/12/2025", 100, 2, 102]]})

        with pytest.raises(CollectorSourceError):
            parse_history(data, start_year=2026)


class TestBCVReservesCollector:
    def test_fetch_reserves(self, monkeypatch):
        data = _book({"2026": [["04/11/2026(*)", 13188, 3, 13191]]})
        monkeypatch.setattr(
            "src.collectors.official.bcv_reserves_collector.http_get_bytes",
            lambda url, params=None: data,
        )

        point = BCVReservesCollector().fetch_reserves()

        assert point.value == pytest.approx(13191e6)

    def test_fetch_history(self, monkeypatch):
        data = _book({
            "2026": [["04/11/2026(*)", 13188, 3, 13191]],
            "2025": [["31/12/2025", 100, 2, 102]],
        })
        monkeypatch.setattr(
            "src.collectors.official.bcv_reserves_collector.http_get_bytes",
            lambda url, params=None: data,
        )

        days = BCVReservesCollector().fetch_history(start_year=2020)

        assert len(days) == 2
