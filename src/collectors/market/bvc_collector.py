"""
Collector BVC (Bolsa de Valores de Caracas)
============================================

Índice IBC y acciones vía Yahoo Finance (paquete ``yfinance``, ya en
requirements). Se usa ``yfinance`` porque no hay API pública oficial de la BVC.
"""

import logging
from datetime import datetime
from typing import List, Optional

from src.collectors.errors import CollectorSourceError
from src.models.market import IndexPoint

logger = logging.getLogger(__name__)

IBC_SYMBOL = "IBC"


def _to_index_point(row, symbol: str) -> IndexPoint:
    """Convierte una fila de historial yfinance a ``IndexPoint``."""
    try:
        close = float(row["Close"])
    except (KeyError, TypeError, ValueError) as exc:
        raise CollectorSourceError(f"BVC: fila sin cierre válido: {exc}") from exc
    date = row.name
    if hasattr(date, "to_pydatetime"):
        date = date.to_pydatetime()
    elif isinstance(date, str):
        date = datetime.fromisoformat(date)
    return IndexPoint(source="bvc", symbol=symbol, value=close, date=date)


class BVCCollector:
    """Índice IBC de la Bolsa de Valores de Caracas."""

    def __init__(self, symbol: str = IBC_SYMBOL):
        self.symbol = symbol

    def fetch_index(self, period: str = "1d") -> IndexPoint:
        """Último cierre del índice."""
        history = self._history(period)
        if history.empty:
            raise CollectorSourceError(f"BVC: sin datos para {self.symbol}")
        return _to_index_point(history.iloc[-1], self.symbol)

    def fetch_history(self, period: str = "1y") -> List[IndexPoint]:
        """Serie de cierres para el período indicado."""
        history = self._history(period)
        return [_to_index_point(row, self.symbol) for _, row in history.iterrows()]

    def _history(self, period: str):
        import yfinance as yf  # import diferido: yfinance es pesado

        ticker = yf.Ticker(self.symbol)
        history = ticker.history(period=period)
        return history