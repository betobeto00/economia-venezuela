"""
Collector PDVSA (Petróleos de Venezuela)
========================================

La fuente principal es el portal de la Junta Administradora Ad Hoc
(``pdvsa-adhoc.com``, accesible; ``www.pdvsa.com`` suele fallar por DNS):
publica comunicados y resultados operacionales (CITGO, producción) en
``/documentacion-de-interes/``. Se entrega el catálogo como
``FiscalDocument`` con su URL.

Adicionalmente se conserva la extracción del precio de la cesta venezolana
(USD/bbl) con patrones defensivos (sin API pública estable), igual que el
collector de la cesta OPEP; si la página no lo contiene, devuelve error y
el pipeline degrada sin inventar datos.
"""

import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from src.collectors.errors import CollectorSourceError
from src.collectors.fiscal.documents import find_documents
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import FiscalDocument, IndicatorPoint

logger = logging.getLogger(__name__)

DOC_EXTENSIONS = (".pdf", ".doc", ".docx")
DOC_KEYWORDS = (
    "resultados", "operacionales", "operativos", "producci", "comunicado",
    "petróleo", "petroleo", "crudo", "balance", "utilidad",
)

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
    """Documentos de la Junta Ad Hoc de PDVSA y cesta venezolana."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.PDVSA_BASE_URL).rstrip("/")

    def fetch_documents(self) -> List[FiscalDocument]:
        """Comunicados y resultados localizados en la documentación."""
        html = http_get_text(self.base_url + "/documentacion-de-interes/")
        docs = find_documents(
            html, self.base_url, source="pdvsa",
            extensions=DOC_EXTENSIONS, keywords=DOC_KEYWORDS,
        )
        logger.info("PDVSA: %d documentos localizados", len(docs))
        return docs

    def fetch_basket_price(self) -> IndicatorPoint:
        html = http_get_text(self.base_url + "/")
        point = parse_basket_price(html)
        logger.info("PDVSA cesta: %.2f USD/bbl", point.value)
        return point