"""
Datos de mercado para el dashboard (Fase A)
===========================================

Capa pura (sin Streamlit) que lee de la base los últimos valores de
tasas e inflación persistidos por los collectors. Todo acceso a DB se hace
dentro de un contexto de sesión; ante fallo de conexión devuelve ``None``
(la UI degrada a "—" sin romper la página).
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.models.market import ExchangeRate, InflationPoint

logger = logging.getLogger(__name__)

# Fuentes canónicas para las tarjetas del dashboard
OFFICIAL_SOURCE = "bcv"
OFFICIAL_CURRENCY = "usd"
PARALLEL_SOURCE = "binance"   # proxy digital (P2P); usa moneda "usdt"
PARALLEL_CURRENCY = "usdt"
INFLATION_SOURCE = "bcv"
INFLATION_FALLBACK_SOURCE = "ovf"  # si BCV IPC no está disponible


def latest_rate(source: str, currency: str = "usd") -> Optional[ExchangeRate]:
    """Última tasa persistida de una fuente."""
    try:
        from src.db.repositories import MarketRepository
        from src.db.session import session_scope

        with session_scope() as session:
            return MarketRepository(session).latest_rate(source, currency)
    except Exception as exc:  # noqa: BLE001 - DB caída u otro fallo
        logger.warning("latest_rate(%s) no disponible: %s", source, exc)
        return None


def latest_inflation(source: str) -> Optional[InflationPoint]:
    """Último punto de inflación persistido de una fuente."""
    try:
        from src.db.repositories import MarketRepository
        from src.db.session import session_scope

        with session_scope() as session:
            return MarketRepository(session).latest_inflation(source)
    except Exception as exc:  # noqa: BLE001
        logger.warning("latest_inflation(%s) no disponible: %s", source, exc)
        return None


def dashboard_metrics() -> dict:
    """Valores para las tarjetas del Inicio, con degradación segura.

    Returns:
        Dict: oficial (ExchangeRate|None), paralelo (ExchangeRate|None),
        inflacion (InflationPoint|None).
    """
    return {
        "oficial": latest_rate(OFFICIAL_SOURCE, OFFICIAL_CURRENCY),
        "paralelo": latest_rate(PARALLEL_SOURCE, PARALLEL_CURRENCY),
        "inflacion": latest_inflation(INFLATION_SOURCE)
        or latest_inflation(INFLATION_FALLBACK_SOURCE),
    }


def format_metric(value: Optional[float], suffix: str = "") -> str:
    """Formato legible de una métrica ("9,63" + sufijo) o "—" si no hay dato."""
    if value is None:
        return "—"
    return f"{value:,.2f}{suffix}"