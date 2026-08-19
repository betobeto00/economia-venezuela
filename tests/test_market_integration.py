"""
Tests de la integración collectors → modelos econométricos (paso 13)
====================================================================
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from src.analyzers.market_integration import (
    analyze_market,
    series_from_inflation,
    series_from_rates,
)
from src.models.market import ExchangeRate, InflationPoint


def _rates(n=60):
    base = datetime(2026, 6, 1)
    return [
        ExchangeRate(
            source="bcv", currency="usd",
            rate=9.0 + i * 0.02, date=base + timedelta(days=i),
        )
        for i in range(n)
    ]


def _inflation(n=24):
    return [
        InflationPoint(
            source="bcv",
            period=f"{2024 + (m - 1) // 12}-{(m - 1) % 12 + 1:02d}",
            monthly_rate=2.0,
        )
        for m in range(1, n + 1)
    ]


class TestSeries:
    def test_series_from_rates(self):
        series = series_from_rates(_rates(30))
        assert isinstance(series, pd.Series)
        assert len(series) == 30
        assert series.iloc[0] == 9.0

    def test_series_from_rates_vacio(self):
        assert series_from_rates([]).empty

    def test_series_from_inflation(self):
        series = series_from_inflation(_inflation(24))
        assert len(series) == 24
        assert series.index[0].year == 2024

    def test_series_from_inflation_sin_mensual(self):
        points = [InflationPoint(source="ovf", period="2026-07", annual_rate=15.0)]
        assert series_from_inflation(points).empty


class TestAnalyzeMarket:
    def test_faltan_datos(self):
        result = analyze_market(rates=[], inflation=[])
        assert "error" in result["rates"]
        assert "error" in result["inflation"]

    def test_pronostico_dolar(self):
        result = analyze_market(rates=_rates(60))
        assert "predicted" in result["rates"]
        assert len(result["rates"]["predicted"]) == 30
        assert result["rates"]["predicted"].isna().sum() == 0

    def test_pronostico_inflacion(self):
        result = analyze_market(inflation=_inflation(24))
        assert "predicted" in result["inflation"]
        assert len(result["inflation"]["predicted"]) == 6

    def test_pronostico_completo(self):
        result = analyze_market(rates=_rates(60), inflation=_inflation(24))
        assert "predicted" in result["rates"]
        assert "predicted" in result["inflation"]
        assert "report" in result