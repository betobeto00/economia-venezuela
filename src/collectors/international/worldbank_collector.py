"""
Collector Banco Mundial (API v2 REST, sin autenticación)
=========================================================

Indicadores de Venezuela vía la API pública del Banco Mundial:
- GDPPoint: PIB, crecimiento, etc.
- InflationPoint: inflación anual (IPC).

La API devuelve ``[meta, rows]`` con filas ``{date, value}``; se descartan
valores nulos y se ordenan cronológicamente.
"""

import logging
from typing import List, Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_json
from src.config import settings
from src.models.market import GDPPoint, InflationPoint

logger = logging.getLogger(__name__)

# Indicadores más usados
INDICATOR_GDP = "NY.GDP.MKTP.CD"      # PIB a precios actuales (USD)
INDICATOR_GDP_GROWTH = "NY.GDP.MKTP.KD.ZG"  # Crecimiento PIB (%)
INDICATOR_INFLATION = "FP.CPI.TOTL.ZG"      # Inflación anual, IPC (%)

_COUNTRY = "VE"


def parse_wb_rows(payload: List) -> List[dict]:
    """Valida y normaliza ``[meta, rows]`` de la API del Banco Mundial."""
    if not isinstance(payload, list) or len(payload) < 2:
        raise CollectorSourceError("Banco Mundial: respuesta sin datos")
    rows = payload[1] or []
    return [
        row for row in rows
        if isinstance(row, dict) and row.get("value") is not None
    ]


class WorldBankCollector:
    """Indicadores económicos de Venezuela desde el Banco Mundial."""

    def __init__(self, api_url: Optional[str] = None, country: str = _COUNTRY):
        self.api_url = (api_url or settings.WORLD_BANK_API_URL).rstrip("/")
        self.country = country

    def fetch_indicator(self, code: str, start: Optional[int] = None,
                        end: Optional[int] = None) -> List[dict]:
        """Filas crudas ``{date, value}`` de un indicador (orden cronológico)."""
        url = f"{self.api_url}/country/{self.country}/indicator/{code}"
        params = {"format": "json", "per_page": "100"}
        if start:
            params["date"] = f"{start}"
            if end:
                params["date"] = f"{start}:{end}"
        payload = http_get_json(url, params=params)
        rows = parse_wb_rows(payload)
        rows.sort(key=lambda r: r.get("date", ""))
        return rows

    def fetch_gdp(self) -> List[GDPPoint]:
        rows = self.fetch_indicator(INDICATOR_GDP)
        return [
            GDPPoint(indicator=INDICATOR_GDP, value=float(row["value"]),
                    year=int(row["date"]), country=self.country)
            for row in rows
        ]

    def fetch_gdp_growth(self) -> List[GDPPoint]:
        rows = self.fetch_indicator(INDICATOR_GDP_GROWTH)
        return [
            GDPPoint(indicator=INDICATOR_GDP_GROWTH, value=float(row["value"]),
                    year=int(row["date"]), country=self.country)
            for row in rows
        ]

    def fetch_inflation(self) -> List[InflationPoint]:
        rows = self.fetch_indicator(INDICATOR_INFLATION)
        return [
            InflationPoint(
                source="world_bank", period=f"{row['date']}-12",
                annual_rate=float(row["value"]),
            )
            for row in rows
        ]