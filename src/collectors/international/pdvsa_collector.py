"""
Collector PDVSA (Petróleos de Venezuela)
========================================

Publica el precio semanal de la cesta venezolana de petróleo (USD/bbl) en
su portal. Se extrae el número mediante patrones defensivos (sin API
pública estable), igual que el collector de la cesta OPEP.
"""

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

BASKET_RE = re.compile(
    r"(?:cesta|canasta)[^%$]*?\$?\s*([\d]+(?:[.,]\d+)?)", re.IGNORECASE
)
BASKET_ALT_RE = re.compile(
    r"Venezuelan[^$]*?\$([\d.,]+)", re.IGNORECASE
)


def parse_basket_price(html: str, source: str = "pdvsa") -> IndicatorPoint:
    """Precio de la cesta venezolana (USD/barril) desde el HTML del portal."""
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    match = BASKET_ALT_RE.search(text) or BASKET_RE.search(text)
    if not match:
        raise CollectorSourceError("PDVSA: no se localizó el precio de la cesta")
    return IndicatorPoint(
        source=source,
        indicator="cesta_venezolana",
        value=float(match.group(1).replace(",", ".")),
        period="",
        unit="USD/bbl",
    )


class PDVSACollector:
    """Precio de la cesta venezolana de petróleo."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.PDVSA_BASE_URL).rstrip("/")

    def fetch_basket_price(self) -> IndicatorPoint:
        html = http_get_text(self.base_url + "/")
        point = parse_basket_price(html)
        logger.info("PDVSA cesta: %.2f USD/bbl", point.value)
        return point