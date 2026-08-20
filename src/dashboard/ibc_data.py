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
            # Obtener la fecha más reciente con componentes
            all_comp = repo.list_components(limit=50)
        if not all_comp:
            return []
        # Agrupar por fecha y tomar la más reciente
        latest_date = max(c["date"] for c in all_comp)
        return [c for c in all_comp if c["date"] == latest_date]
    except Exception as exc:  # noqa: BLE001
        logger.warning("ibc_components_latest no disponible: %s", exc)
        return []


def ibc_gainers_losers() -> Dict[str, List[dict]]:
    """Componentes del IBC separados en gainers y losers."""
    components = ibc_components_latest()
    gainers = sorted(
        [c for c in components if c["change_pct"] > 0],
        key=lambda x: x["change_pct"], reverse=True,
    )
    losers = sorted(
        [c for c in components if c["change_pct"] < 0],
        key=lambda x: x["change_pct"],
    )
    return {"gainers": gainers, "losers": losers}


def ven_tickers_top(bottom_n: int = 5) -> Dict[str, List[dict]]:
    """Top y bottom performers de tickers venezolanos (fuera del IBC)."""
    try:
        from src.db.repositories import VenezuelanTickerRepository
        from src.db.session import session_scope

        with session_scope() as session:
            tickers = VenezuelanTickerRepository(session).list_tickers(limit=200)
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
