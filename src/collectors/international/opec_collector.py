"""
Collector OPEP (Organización de Países Exportadores de Petróleo)
=================================================================

Dos datos de interés para Venezuela:
- Precio de la cesta OPEP (USD/barril), publicado en la home.
- Producción de petróleo de Venezuela (mbd).

Se obtiene la página de datos del OPEP y se extraen los números mediante
patrones defensivos (sin API pública estable).
"""

import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

BASKET_RE = re.compile(
    r"(?:cesta|basket)[^%$]*?\$?\s*([\d]+(?:[.,]\d+)?)", re.IGNORECASE
)
BASKET_ALT_RE = re.compile(r"OPEC Reference Basket[^$]*?\$([\d.]+)", re.IGNORECASE)


def parse_basket_price(html: str, source: str = "opec") -> IndicatorPoint:
    """Precio de la cesta OPEP (USD/barril) desde el HTML de la home."""
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    match = BASKET_ALT_RE.search(text) or BASKET_RE.search(text)
    if not match:
        raise CollectorSourceError("OPEP: no se localizó el precio de la cesta")
    return IndicatorPoint(
        source=source,
        indicator="cesta_opep",
        value=float(match.group(1).replace(",", ".")),
        period="",
        unit="USD/bbl",
    )


class OPECCollector:
    """Cesta OPEP y producción de Venezuela."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OPEC_BASE_URL).rstrip("/")

    def fetch_basket_price(self) -> IndicatorPoint:
        html = http_get_text(self.base_url + "/opec_web/en/")
        point = parse_basket_price(html)
        logger.info("OPEP cesta: %.2f USD/bbl", point.value)
        return point