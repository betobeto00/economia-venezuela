"""
Tests del backfill de inflación (archivo del OVF por WP REST)
=============================================================

- ``period_from_title``: deduce ``YYYY-MM`` del mes nombrado en el título.
- ``validate_rates``: rechaza tasas implausibles (mensual > 100 % o
  interanual menor que la mensual).
- ``build_points``: descarta posts sin período o sin números válidos y dedupe.
"""

from datetime import datetime

import pytest

from src.scripts.backfill_inflation import (
    build_points,
    period_from_title,
    validate_rates,
)


def _post(date, title, body):
    return {
        "date": date,
        "title": {"rendered": title},
        "content": {"rendered": f"<p>{body}</p>"},
    }


class TestPeriodFromTitle:
    def test_mes_anterior_al_de_publicacion(self):
        # Publicado en junio sobre mayo → mayo del mismo año
        assert period_from_title("Inflación anualizada alcanza 229% en mayo",
                                 datetime(2025, 6, 9)) == "2025-05"

    def test_diciembre_publicado_en_enero(self):
        assert period_from_title("Diciembre en cifras", datetime(2026, 1, 8)) == "2025-12"

    def test_sin_mes(self):
        assert period_from_title("Reporte de coyuntura", datetime(2026, 1, 8)) is None

    def test_mes_siguiente_al_de_publicacion(self):
        # Título con el mes en curso (no el anterior)
        assert period_from_title("Inflación de marzo", datetime(2026, 3, 2)) == "2026-03"


class TestValidateRates:
    @pytest.mark.parametrize("monthly,annual", [(16.0, 63.1), (2.5, None), (100.0, 120.0)])
    def test_validas(self, monthly, annual):
        assert validate_rates(monthly, annual) is True

    @pytest.mark.parametrize("monthly,annual", [(None, 50.0), (0, 50.0), (-1, 50.0),
                                                (105.5, None), (16.0, 10.0)])
    def test_invalidas(self, monthly, annual):
        assert validate_rates(monthly, annual) is False


class TestBuildPoints:
    def test_acepta_y_dedupe(self):
        posts = [
            _post("2025-06-09T12:00:00", "Inflación en mayo",
                  "La inflación mensual de mayo fue de 16,0% y la interanual 63,1%."),
            # Mismo período, sin interanual: no debe reemplazar al bueno
            _post("2025-06-20T12:00:00", "Mayo en cifras",
                  "La inflación mensual de 12,0%."),
            # Sin mes en el título → descartado
            _post("2025-07-01T12:00:00", "Reporte de coyuntura",
                  "La inflación mensual de 9,0%."),
        ]
        result = build_points(posts)
        periods = [p.period for p in result["points"]]
        assert periods == ["2025-05"]
        assert result["sin_periodo"] == 1
        assert result["points"][0].annual_rate == pytest.approx(63.1)

    def test_rechaza_implausibles(self):
        posts = [
            _post("2025-05-05T12:00:00", "Abril en cifras",
                  "Inflación mensual de 150,0%."),
        ]
        result = build_points(posts)
        assert result["points"] == []
        assert result["rejected"] == 1
