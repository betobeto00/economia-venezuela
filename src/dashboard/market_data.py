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

import pandas as pd

from src.models.market import ExchangeRate, InflationPoint

logger = logging.getLogger(__name__)

# Fuentes canónicas para las tarjetas del dashboard
OFFICIAL_SOURCE = "bcv"
OFFICIAL_CURRENCY = "usd"
PARALLEL_SOURCE = "binance"   # proxy digital (P2P); usa moneda "usdt"
PARALLEL_CURRENCY = "usdt"
BYBIT_SOURCE = "bybit"        # P2P Bybit (misma moneda usdt)
BYBIT_CURRENCY = "usdt"
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


def list_rates(source: Optional[str] = None, currency: Optional[str] = None,
               limit: Optional[int] = None) -> list:
    """Serie de tasas desde la base (para gráficos históricos)."""
    try:
        from src.db.repositories import MarketRepository
        from src.db.session import session_scope

        with session_scope() as session:
            return MarketRepository(session).list_rates(
                source=source, currency=currency, limit=limit
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("list_rates(%s) no disponible: %s", source, exc)
        return []


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
        bybit (ExchangeRate|None), inflacion (InflationPoint|None).
    """
    return {
        "oficial": latest_rate(OFFICIAL_SOURCE, OFFICIAL_CURRENCY),
        "paralelo": latest_rate(PARALLEL_SOURCE, PARALLEL_CURRENCY),
        "bybit": latest_rate(BYBIT_SOURCE, BYBIT_CURRENCY),
        "inflacion": latest_inflation(INFLATION_SOURCE)
        or latest_inflation(INFLATION_FALLBACK_SOURCE),
    }


def brecha_porcentaje(oficial: Optional[ExchangeRate],
                      paralelo: Optional[ExchangeRate]) -> Optional[float]:
    """Brecha entre el dólar paralelo (P2P) y el oficial, en %.

    Returns:
        Porcentaje > 0 si el paralelo cotiza por encima del oficial,
        o None si falta alguno de los dos valores.
    """
    if oficial is None or paralelo is None or oficial.rate <= 0:
        return None
    return (paralelo.rate / oficial.rate - 1) * 100


def brecha_series(source: str, since_days: int = 180) -> pd.DataFrame:
    """Brecha cambiaria diaria (paralelo/oficial - 1) para un rango de días."""
    try:
        import pandas as pd
        from datetime import timedelta

        from src.db.repositories import MarketRepository
        from src.db.session import session_scope

        since = datetime.now(timezone.utc) - timedelta(days=since_days)
        with session_scope() as session:
            repo = MarketRepository(session)
            oficial = repo.list_rates(
                OFFICIAL_SOURCE, OFFICIAL_CURRENCY, since=since
            )
            paralelo = repo.list_rates(source, PARALLEL_CURRENCY, since=since)
        if not oficial or not paralelo:
            return pd.DataFrame()
        df_of = pd.DataFrame(
            [(r.date.date(), r.rate) for r in oficial], columns=["fecha", "oficial"]
        ).set_index("fecha")
        df_par = pd.DataFrame(
            [(r.date.date(), r.rate) for r in paralelo], columns=["fecha", "paralelo"]
        ).set_index("fecha")
        df = df_of.join(df_par, how="inner")
        df["brecha_%"] = (df["paralelo"] / df["oficial"] - 1) * 100
        return df
    except Exception as exc:  # noqa: BLE001
        logger.warning("brecha_series no disponible: %s", exc)
        return pd.DataFrame()


def format_metric(value: Optional[float], suffix: str = "") -> str:
    """Formato legible de una métrica ("9,63" + sufijo) o "—" si no hay dato."""
    if value is None:
        return "—"
    return f"{value:,.2f}{suffix}"