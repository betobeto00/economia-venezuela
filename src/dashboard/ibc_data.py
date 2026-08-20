"""
Datos del IBC (Índice Bursátil Caracas) para el dashboard
==========================================================

Capa pura (sin Streamlit) que lee de la base los datos del IBC y sus
componentes persistidos por el backfill. Degradación segura ante fallos.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def ibc_index_series(days: int = 180) -> pd.DataFrame:
    """Serie temporal del índice IBC para gráficos.

    Returns:
        DataFrame con columnas ``date``, ``value``, ``change_pct``.
    """
    try:
        from src.db.repositories import IBCIndexRepository
        from src.db.session import session_scope

        since = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            data = IBCIndexRepository(session).list_index(since=since, limit=500)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data).sort_values("date")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ibc_index_series no disponible: %s", exc)
        return pd.DataFrame()


def ibc_latest() -> Optional[dict]:
    """Último valor del índice IBC."""
    try:
        from src.db.repositories import IBCIndexRepository
        from src.db.session import session_scope

        with session_scope() as session:
            data = IBCIndexRepository(session).list_index(limit=1)
        return data[0] if data else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("ibc_latest no disponible: %s", exc)
        return None


def ibc_components_latest() -> List[dict]:
    """Últimos componentes del IBC (gainers/losers)."""
    try:
        from src.db.repositories import IBCIndexRepository
        from src.db.session import session_scope

        with session_scope() as session:
            repo = IBCIndexRepository(session)
            all_comp = repo.list_components(limit=100)
        if not all_comp:
            return []
        latest_date = max(c["date"] for c in all_comp)
        return [c for c in all_comp if c["date"] == latest_date]
    except Exception as exc:  # noqa: BLE001
        logger.warning("ibc_components_latest no disponible: %s", exc)
        return []


def ibc_components_full_history(days: int = 30) -> pd.DataFrame:
    """Historial completo de componentes del IBC.

    Returns:
        DataFrame con columnas: date, ticker, name, price, change_pct, volume.
    """
    try:
        from src.db.repositories import IBCIndexRepository
        from src.db.session import session_scope

        since = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            repo = IBCIndexRepository(session)
            data = repo.list_components(since=since, limit=500)
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data).sort_values(["date", "ticker"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("ibc_components_full_history no disponible: %s", exc)
        return pd.DataFrame()


def ibc_gainers_losers() -> Dict[str, List[dict]]:
    """Componentes del IBC separados en gainers y losers."""
    components = ibc_components_latest()
    gainers = sorted(
        [c for c in components if c.get("change_pct", 0) > 0],
        key=lambda x: x.get("change_pct", 0), reverse=True,
    )
    losers = sorted(
        [c for c in components if c.get("change_pct", 0) < 0],
        key=lambda x: x.get("change_pct", 0),
    )
    return {"gainers": gainers, "losers": losers}


def ibc_components_all() -> List[dict]:
    """Todos los componentes del IBC (última fecha), ordenados por ticker."""
    components = ibc_components_latest()
    return sorted(components, key=lambda x: x.get("ticker", ""))


def ven_tickers_all(limit: int = 500) -> pd.DataFrame:
    """DataFrame completo de todos los tickers venezolanos.

    Returns:
        DataFrame con columnas: date, ticker, name, close, change_pct, avg_volume.
    """
    try:
        from src.db.repositories import VenezuelanTickerRepository
        from src.db.session import session_scope

        with session_scope() as session:
            repo = VenezuelanTickerRepository(session)
            tickers = repo.list_tickers(limit=limit)
        if not tickers:
            return pd.DataFrame()
        return pd.DataFrame(tickers).sort_values(["date", "ticker"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("ven_tickers_all no disponible: %s", exc)
        return pd.DataFrame()


def ven_tickers_latest_snapshot() -> pd.DataFrame:
    """Último snapshot de cada ticker (el más reciente por ticker).

    Returns:
        DataFrame con columnas: ticker, name, close, change_pct, avg_volume, date.
    """
    df = ven_tickers_all()
    if df.empty:
        return df
    # Keep latest per ticker
    latest = df.sort_values("date").groupby("ticker").last().reset_index()
    return latest.sort_values("change_pct", ascending=False)


def ven_tickers_top(bottom_n: int = 5) -> Dict[str, List[dict]]:
    """Top y bottom performers de tickers venezolanos (fuera del IBC)."""
    try:
        from src.db.repositories import VenezuelanTickerRepository
        from src.db.session import session_scope

        with session_scope() as session:
            tickers = VenezuelanTickerRepository(session).list_tickers(limit=500)
        if not tickers:
            return {"gainers": [], "losers": []}
        # Tomar el precio más reciente de cada ticker
        latest: Dict[str, dict] = {}
        for t in tickers:
            tk = t["ticker"]
            if tk not in latest or t["date"] > latest[tk]["date"]:
                latest[tk] = t
        by_change = sorted(latest.values(), key=lambda x: x["change_pct"], reverse=True)
        return {
            "gainers": by_change[:bottom_n],
            "losers": by_change[-bottom_n:][::-1] if len(by_change) >= bottom_n else [],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("ven_tickers_top no disponible: %s", exc)
        return {"gainers": [], "losers": []}


def ven_tickers_series(ticker: str, days: int = 30) -> pd.DataFrame:
    """Serie histórica de un ticker específico.

    Returns:
        DataFrame con columnas: date, close, change_pct, avg_volume.
    """
    try:
        from src.db.repositories import VenezuelanTickerRepository
        from src.db.session import session_scope

        since = datetime.now(timezone.utc) - timedelta(days=days)
        with session_scope() as session:
            repo = VenezuelanTickerRepository(session)
            tickers = repo.list_tickers(since=since, limit=500)

        if not tickers:
            return pd.DataFrame()

        df = pd.DataFrame(tickers)
        df = df[df["ticker"] == ticker].sort_values("date")
        return df
    except Exception as exc:  # noqa: BLE001
        logger.warning("ven_tickers_series no disponible: %s", exc)
        return pd.DataFrame()
