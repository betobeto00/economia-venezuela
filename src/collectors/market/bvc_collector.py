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

IBC_SYMBOL = "IBC.CR"


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
        """Último cierre del índice devuelto como IndexPoint.
        
        El índice IBC se obtiene de Yahoo Finance (ticker ``IBC.CR``, ya que
        ``IBC`` no está disponible en Yahoo).
        """
        history = self._history(period)
        if history.empty:
            raise CollectorSourceError(f"BVC: sin datos para {self.symbol}")
        row = history.iloc[-1]
        close = float(row["Close"])
        date = row.name
        if hasattr(date, "to_pydatetime"):
            date = date.to_pydatetime()
        elif isinstance(date, str):
            date = datetime.fromisoformat(date)
        return IndexPoint(
            source="bvc",
            symbol=self.symbol,
            value=close,
            date=date,
        )

    def fetch_history(self, period: str = "1y") -> List[IndexPoint]:
        """Devuelve una serie completa de IndexPoint para el período indicado."""
        history = self._history(period)
        if history.empty:
            return []
        return [
            IndexPoint(
                source="bvc",
                symbol=self.symbol,
                value=float(row["Close"]),
                date=row.name,
            )
            for _, row in history.iterrows()
        ]

    def _history(self, period: str):
        import yfinance as yf  # import diferido: yfinance es pesado

        ticker = yf.Ticker(self.symbol)
        return ticker.history(period=period)