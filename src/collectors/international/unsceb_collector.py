"""
Collector UNSCEB (UN System Chief Executives Board)
====================================================

Publica CSVs del sistema de las Naciones Unidas. El dataset
``expenses_by_country_region_sub_agency.csv`` (~10MB) desglosa el gasto de
las agencias de la ONU por país, y Venezuela aparece como
"Venezuela (Bolivarian Republic of)". Se filtra ese país y se agrega el
gasto total por (año, moneda) como ``IndicatorPoint``
(``gasto_onu_venezuela``), una proxy de los flujos de cooperación
internacional hacia el país.
"""

import csv
import io
import logging
from typing import List, Optional

from src.collectors.http import http_get_bytes
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

EXPENSES_CSV = "/assets/data/FS/expenses_by_country_region_sub_agency.csv"
COUNTRY = "Venezuela"
AMOUNT_COL = "amount"
CURRENCY_COL = "_currency_amount"
YEAR_COL = "calendar_year"
COUNTRY_COL = "country/territory"


def parse_expenses(content: bytes, country: str = COUNTRY) -> List[dict]:
    """Filas de gasto por país del CSV de UNSCEB (UTF-8, con BOM tolerado)."""
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows: List[dict] = []
    for row in reader:
        name = (row.get(COUNTRY_COL) or "").strip()
        if not name.startswith(country):
            continue
        rows.append(row)
    return rows


def aggregate_by_year(rows: List[dict]) -> List[IndicatorPoint]:
    """Gasto total de la ONU por (año, moneda) para el país."""
    totals: dict = {}
    for row in rows:
        year = (row.get(YEAR_COL) or "").strip()
        currency = (row.get(CURRENCY_COL) or "").strip()
        raw = (row.get(AMOUNT_COL) or "").strip()
        if not year or not currency:
            continue
        try:
            amount = float(raw)
        except ValueError:
            continue
        totals[(year, currency)] = totals.get((year, currency), 0.0) + amount
    points = [
        IndicatorPoint(
            source="unsceb",
            indicator="gasto_onu_venezuela",
            value=total,
            period=year,
            unit=_currency,
        )
        for (year, _currency), total in sorted(totals.items())
    ]
    return points


class UNSCEBCollector:
    """Gasto del sistema ONU en Venezuela desde los CSVs de UNSCEB."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.UNSCEB_BASE_URL).rstrip("/")

    def fetch_expenses(self, country: str = COUNTRY) -> List[dict]:
        """Filas de gasto del país desde el CSV de gastos por país."""
        content = http_get_bytes(self.base_url + EXPENSES_CSV)
        rows = parse_expenses(content, country)
        logger.info("UNSCEB: %d filas de gasto para %s", len(rows), country)
        return rows

    def fetch_venezuela_expenses(self) -> List[IndicatorPoint]:
        """Gasto anual del sistema ONU en Venezuela (por año y moneda)."""
        rows = self.fetch_expenses()
        points = aggregate_by_year(rows)
        logger.info("UNSCEB: %d observaciones agregadas para Venezuela", len(points))
        return points