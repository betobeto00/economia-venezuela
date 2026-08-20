"""
Collector de Tickers Venezolanos Relevantes (Yahoo Finance)
============================================================

Obtiene datos de acciones venezolanas que cotizan en Yahoo Finance y que
NO son componentes del IBC (esos se obtienen de Investing.com).

Sirve para monitorear empresas relevantes fuera del índice.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Tickers venezolanos que SÍ funcionan en Yahoo Finance (NO son IBC)
VENEZUELAN_TICKERS = {
    "CCC": "Cemento Caracas",
    "BAM": "Banco Mercantil",
    "BIV": "Banco de Venezuela",
    "BRO": "Banco Regional",
    "DIA": "Diario de Caracas",
    "CAR": "C.A. Venoco",
    "CVI": "C.A. Venezolana de Cementos",
    "CNC": "Corporación CNC",
    "BNC": "Banco Nacional de Crédito",
    "CAS": "Cementos Argos",
    "FAB": "Fábrica de Abastos",
    "BCV": "Banco Central",
    "CTM": "Corp. Tv Marte",
    "FUN": "Fundo Valencia",
    "EMP": "Empresas Polar",
    "FAN": "Fana",
    "BOC": "Banco Occidental",
    "CMP": "Cementos Panam",
    "EDC": "Electricidad de Caracas",
    "CRE": "Credicard",
}


@dataclass
class TickerPerf:
    """Rendimiento de un ticker venezolano."""
    ticker: str
    name: str
    close: float
    change_pct: float
    avg_volume: float


def fetch_tickers_for_date(target_date: datetime) -> List[TickerPerf]:
    """Obtiene datos de tickers venezolanos para un día específico.

    Yahoo Finance retorna el dato más cercano al día solicitado
    (si es fin de semana, retorna el viernes anterior).

    Args:
        target_date: Fecha objetivo.

    Returns:
        Lista de TickerPerf con datos del día más cercano disponible.
    """
    import yfinance as yf

    results: List[TickerPerf] = []
    # Pedimos 5 días para cubrir fines de semana
    start = (target_date - timedelta(days=3)).strftime("%Y-%m-%d")
    end = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    target_str = target_date.strftime("%Y-%m-%d")

    for ticker, name in VENEZUELAN_TICKERS.items():
        try:
            data = yf.Ticker(ticker).history(start=start, end=end)
            if len(data) < 1:
                continue

            # Buscar el dato más cercano al target_date
            # El índice de yfinance es timezone-aware
            best_row = None
            best_diff = timedelta(days=999)
            for idx in data.index:
                row_date = idx.date()
                diff = abs(row_date - target_date.date())
                if diff < best_diff:
                    best_diff = diff
                    best_row = data.loc[idx]

            if best_row is None:
                continue

            close = float(best_row["Close"])
            volume = int(best_row["Volume"])

            # Calcular cambio % (necesitamos el día anterior)
            if len(data) > 1:
                prev_idx = data.index.get_loc(data.index[data.index <= best_row.name][-1])
                if prev_idx > 0:
                    prev_close = float(data.iloc[prev_idx - 1]["Close"])
                    change_pct = ((close - prev_close) / prev_close) * 100.0 if prev_close else 0.0
                else:
                    change_pct = 0.0
            else:
                change_pct = 0.0

            results.append(TickerPerf(
                ticker=ticker,
                name=name,
                close=close,
                change_pct=round(change_pct, 2),
                avg_volume=volume,
            ))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ticker %s no disponible para %s: %s", ticker, target_str, exc)

    return results


def fetch_venezuelan_tickers(period: str = "1mo", top_n: int = 5) -> Dict[str, List[TickerPerf]]:
    """Obtiene rendimiento de tickers venezolanos relevantes (Yahoo Finance).

    Args:
        period: Período de historial (default: 1 mes).
        top_n: Cantidad de top/bottom performers a retornar.

    Returns:
        Dict con 'gainers', 'losers' como listas de TickerPerf.
    """
    import yfinance as yf

    performances: List[TickerPerf] = []

    for ticker, name in VENEZUELAN_TICKERS.items():
        try:
            data = yf.Ticker(ticker).history(period=period)
            if len(data) < 2:
                continue
            close_init = float(data.iloc[0]["Close"])
            close_final = float(data.iloc[-1]["Close"])
            pct = ((close_final - close_init) / close_init) * 100.0 if close_init else 0.0
            avg_vol = float(data["Volume"].mean())
            performances.append(TickerPerf(
                ticker=ticker,
                name=name,
                close=close_final,
                change_pct=round(pct, 2),
                avg_volume=avg_vol,
            ))
        except Exception as exc:  # noqa: BLE001
            logger.debug("Ticker %s no disponible: %s", ticker, exc)

    if not performances:
        return {"gainers": [], "losers": []}

    by_change = sorted(performances, key=lambda s: s.change_pct, reverse=True)

    return {
        "gainers": by_change[:top_n],
        "losers": by_change[-top_n:][::-1],
    }
