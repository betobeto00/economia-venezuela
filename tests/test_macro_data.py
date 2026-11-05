"""
Tests de la capa macro del dashboard (sin DB ni red)
====================================================

Cubren los dos errores que dejaron ``macro_indicators`` incompleta:
``InflationPoint`` no tiene ``value``/``year`` (usa ``annual_rate``/``period``)
y el crudo se quedaba sin fuente cuando la OPEP responde 403.
"""

import pytest

from src.dashboard import macro_data
from src.models.market import InflationPoint


class TestInflacionInternacional:
    def test_usa_annual_rate_del_banco_mundial(self, monkeypatch):
        monkeypatch.setattr(macro_data, "_get_cached", lambda key: None)
        monkeypatch.setattr(macro_data, "_save_cached", lambda *a, **k: None)
        monkeypatch.setattr(
            "src.collectors.international.imf_collector.IMFCollector.fetch_inflation",
            lambda self: (_ for _ in ()).throw(RuntimeError("endpoint muerto")),
        )
        monkeypatch.setattr(
            "src.collectors.international.worldbank_collector.WorldBankCollector.fetch_inflation",
            lambda self: [
                InflationPoint(source="world_bank", period="2015-12", annual_rate=180.0),
                InflationPoint(source="world_bank", period="2016-12", annual_rate=254.9),
            ],
        )

        result = macro_data.inflacion_internacional()

        assert result is not None
        assert result["value"] == pytest.approx(254.9)
        assert result["period"] == "2016-12"
        assert result["source"] == "Banco Mundial"

    def test_sin_datos_devuelve_none(self, monkeypatch):
        monkeypatch.setattr(macro_data, "_get_cached", lambda key: None)
        monkeypatch.setattr(macro_data, "_save_cached", lambda *a, **k: None)
        monkeypatch.setattr(
            "src.collectors.international.imf_collector.IMFCollector.fetch_inflation",
            lambda self: (_ for _ in ()).throw(RuntimeError("endpoint muerto")),
        )
        monkeypatch.setattr(
            "src.collectors.international.worldbank_collector.WorldBankCollector.fetch_inflation",
            lambda self: [],
        )

        assert macro_data.inflacion_internacional() is None


class TestCrudo:
    def test_cae_al_brent_local_si_opep_y_pdvsa_fallan(self, monkeypatch):
        monkeypatch.setattr(macro_data, "_get_cached", lambda key: None)
        guardado = []
        monkeypatch.setattr(macro_data, "_save_cached", lambda *a, **k: guardado.append(a))
        monkeypatch.setattr(macro_data, "_brent_from_csv", lambda: 63.5)
        monkeypatch.setattr(
            "src.collectors.international.opec_collector.OPECCollector.fetch_basket_price",
            lambda self: (_ for _ in ()).throw(RuntimeError("403")),
        )
        monkeypatch.setattr(
            "src.collectors.international.pdvsa_collector.PDVSACollector.fetch_basket_price",
            lambda self: (_ for _ in ()).throw(RuntimeError("sin cesta")),
        )

        result = macro_data.produccion_petrolera()

        assert result is not None
        assert result["value"] == pytest.approx(63.5)
        assert result["source"] == "Brent (CSV local)"
        assert guardado and guardado[0][2] == pytest.approx(63.5)

    def test_sin_ninguna_fuente_devuelve_none(self, monkeypatch):
        monkeypatch.setattr(macro_data, "_get_cached", lambda key: None)
        monkeypatch.setattr(macro_data, "_save_cached", lambda *a, **k: None)
        monkeypatch.setattr(macro_data, "_brent_from_csv", lambda: None)
        monkeypatch.setattr(
            "src.collectors.international.opec_collector.OPECCollector.fetch_basket_price",
            lambda self: (_ for _ in ()).throw(RuntimeError("403")),
        )
        monkeypatch.setattr(
            "src.collectors.international.pdvsa_collector.PDVSACollector.fetch_basket_price",
            lambda self: (_ for _ in ()).throw(RuntimeError("sin cesta")),
        )

        assert macro_data.produccion_petrolera() is None
