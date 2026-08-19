"""
Integración: collectors → modelos econométricos (paso 13)
==========================================================

Conecta los datos normalizados de los collectors de Fase A
(``ExchangeRate``, ``InflationPoint``) con los analizadores econométricos:

1. Construye series pandas a partir de las listas de modelos.
2. Ejecuta pruebas de estacionariedad.
3. Genera pronósticos (dólar e inflación) con ARIMA/SARIMA.
4. Devuelve un resumen + informe en texto.

Si hay muy pocos datos, se devuelve un dict con ``error`` (sin lanzar
excepciones al pipeline).
"""

import logging
from typing import Dict, List, Optional

import pandas as pd

from src.models.market import ExchangeRate, InflationPoint

logger = logging.getLogger(__name__)

MIN_RATE_POINTS = 20
MIN_INFLATION_POINTS = 12


def series_from_rates(rates: List[ExchangeRate]) -> pd.Series:
    """Serie diaria de tasas: valor por fecha (último valor del día)."""
    if not rates:
        return pd.Series(dtype=float)
    df = pd.DataFrame(
        {"date": [r.date for r in rates], "rate": [r.rate for r in rates]}
    ).drop_duplicates(subset="date", keep="last")
    series = df.set_index("date")["rate"].sort_index()
    return series.asfreq("D").ffill()


def series_from_inflation(points: List[InflationPoint]) -> pd.Series:
    """Serie mensual de inflación: usa ``monthly_rate`` del punto."""
    rows = [(p.period, p.monthly_rate) for p in points if p.monthly_rate is not None]
    if not rows:
        return pd.Series(dtype=float)
    series = pd.Series({period: rate for period, rate in rows}).sort_index()
    series.index = pd.to_datetime(series.index + "-01", format="%Y-%m-%d")
    return series.astype(float)


def _forecast_dollar(rates: List[ExchangeRate], periods: int) -> Dict:
    if len(rates) < MIN_RATE_POINTS:
        return {"error": f"Faltan datos de dólar (≥{MIN_RATE_POINTS}, hay {len(rates)})"}
    series = series_from_rates(rates)
    from src.analyzers.econometric.forecasting import DollarRateForecaster

    result = DollarRateForecaster().forecast_dollar_rate(series, periods=periods)
    return {
        "model": result.model_name,
        "aic": result.aic,
        "predicted": result.predicted_mean.tail(periods),
        "conf_int": result.conf_int.tail(periods),
    }


def _forecast_inflation(points: List[InflationPoint], periods: int) -> Dict:
    if len(points) < MIN_INFLATION_POINTS:
        return {
            "error": f"Faltan datos de inflación (≥{MIN_INFLATION_POINTS}, hay {len(points)})"
        }
    series = series_from_inflation(points)
    from src.analyzers.econometric.forecasting import InflationForecaster

    result = InflationForecaster().forecast_inflation(series, periods=periods)
    return {
        "model": result.model_name,
        "aic": result.aic,
        "predicted": result.predicted_mean.tail(periods),
        "conf_int": result.conf_int.tail(periods),
    }


def analyze_market(
    rates: Optional[List[ExchangeRate]] = None,
    inflation: Optional[List[InflationPoint]] = None,
    rate_periods: int = 30,
    inflation_periods: int = 6,
) -> Dict:
    """Pronósticos de dólar e inflación a partir de datos de collectors.

    Returns:
        Dict con ``rates`` e ``inflation`` (cada uno un dict de resultados o
        ``{"error": ...}`` si faltan datos), y ``report`` (texto, opcional).
    """
    result: Dict = {
        "rates": _forecast_dollar(rates or [], rate_periods) if rates else {"error": "Sin datos de tasas"},
        "inflation": (
            _forecast_inflation(inflation or [], inflation_periods)
            if inflation else {"error": "Sin datos de inflación"}
        ),
    }

    try:
        report_parts = []
        if "predicted" in result["rates"]:
            report_parts.append("Pronóstico dólar (ARIMA):")
            report_parts.append(result["rates"]["predicted"].tail(5).to_string())
        if "predicted" in result["inflation"]:
            report_parts.append("Pronóstico inflación (SARIMA):")
            report_parts.append(result["inflation"]["predicted"].tail(5).to_string())
        result["report"] = "\n".join(report_parts) or "Sin pronósticos generados."
    except Exception as exc:  # noqa: BLE001
        logger.warning("No se pudo construir el reporte: %s", exc)
        result["report"] = "Sin pronósticos generados."

    return result