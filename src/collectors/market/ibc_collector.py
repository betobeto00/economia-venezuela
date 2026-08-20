"""
Collector unificado del IBC (Índice Bursátil Caracas)
=====================================================

Fuentes:
1. Yahoo Finance (`IBC.CR`): dato actual (info),历史 via history()
2. Investing.com (Playwright): fallback para dato actual e histórico

Flujo:
- fetch_ibc_current(): Yahoo Finance → Playwright fallback
- fetch_ibc_history(): Playwright scraping de Investing.com
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

logger = logging.getLogger(__name__)


def fetch_ibc_current() -> Optional[dict]:
    """Obtiene el valor actual del IBC (multi-fuente).

    Returns:
        Dict con value, change, change_pct, source, o None si falla.
    """
    # 1. Intentar Yahoo Finance (info)
    try:
        import yfinance as yf
        ticker = yf.Ticker("IBC.CR")
        info = ticker.info
        price = info.get("regularMarketPrice") or info.get("previousClose")
        if price and price > 0:
            return {
                "value": float(price),
                "change": float(info.get("regularMarketChange", 0)),
                "change_pct": float(info.get("regularMarketChangePercent", 0)),
                "source": "yahoo",
                "date": datetime.now(timezone.utc),
            }
    except Exception as exc:
        logger.debug("Yahoo IBC falló: %s", exc)

    # 2. Fallback: Playwright (Investing.com)
    try:
        from src.collectors.market.ibc_history import fetch_ibc_current_playwright
        result = fetch_ibc_current_playwright()
        if result and result.get("value", 0) > 0:
            return {
                "value": result["value"],
                "change": result.get("change", 0),
                "change_pct": result.get("change_pct", 0),
                "source": "investing",
                "date": datetime.now(timezone.utc),
                "components": result.get("components", []),
            }
    except Exception as exc:
        logger.debug("Playwright IBC falló: %s", exc)

    return None


def fetch_ibc_history(months: int = 6) -> List[dict]:
    """Obtiene datos históricos del IBC.

    Args:
        months: Meses de historial.

    Returns:
        Lista de dicts con date, value, change_pct.
    """
    # 1. Intentar Yahoo Finance history
    try:
        import yfinance as yf
        ticker = yf.Ticker("IBC.CR")
        data = ticker.history(period=f"{months}mo")
        if not data.empty:
            results = []
            for idx, row in data.iterrows():
                results.append({
                    "date": idx.to_pydatetime(),
                    "value": float(row["Close"]),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "change_pct": 0.0,  # Yahoo no da change_pct en history
                })
            return results
    except Exception as exc:
        logger.debug("Yahoo IBC history falló: %s", exc)

    # 2. Fallback: Playwright (Investing.com)
    try:
        from src.collectors.market.ibc_history import fetch_ibc_history_playwright
        return fetch_ibc_history_playwright(months=months)
    except Exception as exc:
        logger.debug("Playwright IBC history falló: %s", exc)

    return []
