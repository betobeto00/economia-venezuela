"""
Collector OVF (Observatorio Venezolano de Finanzas)
====================================================

IPC alternativo publicado mensualmente por el OVF en su sitio web
(WordPress). Como no expone API, se obtiene la página de inicio, se localiza
la publicación de inflación más reciente y se extraen las tasas del texto.

Estrategia defensiva: si el texto no contiene los números esperados se lanza
``CollectorSourceError`` (para no persistir datos erróneos) y se registra.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import InflationPoint

logger = logging.getLogger(__name__)

# Palabras clave para localizar publicaciones de inflación
POST_KEYWORDS = ("inflaci", "ipc", "índice de precios", "indice de precios", "reporte")

# Extrae el primer porcentaje que siga a la palabra inflación
MONTHLY_RE = re.compile(
    r"inflaci[oó]n[^%\d]{0,40}(?:mensual\s+)?de?\s*([\d]+(?:[.,]\d+)?)\s*%",
    re.IGNORECASE,
)
ANNUAL_RE = re.compile(r"interanual[^%\d]{0,30}?([\d]+(?:[.,]\d+)?)\s*%", re.IGNORECASE)


def _to_float(match: Optional[re.Match]) -> Optional[float]:
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def find_inflation_post(html: str, base_url: str) -> Optional[str]:
    """Localiza la URL de la publicación de inflación más reciente."""
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.find_all("a", href=True):
        text = (link.get_text(" ") or "").lower()
        href = link["href"]
        if any(k in text for k in POST_KEYWORDS) and href.startswith("http"):
            return href
    # Fallback: enlaces relativos
    for link in soup.find_all("a", href=True):
        href = link["href"]
        if any(k in href.lower() for k in POST_KEYWORDS) and href.startswith("/"):
            return base_url.rstrip("/") + href
    return None


def parse_bulletin(html: str, source: str, period: Optional[str] = None) -> InflationPoint:
    """Extrae tasas mensual e interanual del texto de la publicación."""
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    monthly = _to_float(MONTHLY_RE.search(text))
    annual = _to_float(ANNUAL_RE.search(text))

    if monthly is None and annual is None:
        raise CollectorSourceError("OVF: no se encontraron tasas de inflación en el texto")

    if period is None:
        period = datetime.now(timezone.utc).strftime("%Y-%m")

    return InflationPoint(
        source=source,
        period=period,
        monthly_rate=monthly,
        annual_rate=annual,
    )


class OVFCollector:
    """IPC mensual del Observatorio Venezolano de Finanzas."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.OVF_BASE_URL).rstrip("/")

    def fetch_latest_post_url(self) -> Optional[str]:
        """URL de la publicación más reciente de inflación (o None)."""
        html = http_get_text(self.base_url + "/")
        return find_inflation_post(html, self.base_url)

    def fetch_ipc(self, period: Optional[str] = None) -> InflationPoint:
        """IPC alternativo más reciente publicado por el OVF."""
        url = self.fetch_latest_post_url()
        if url is None:
            raise CollectorSourceError(
                f"OVF: no se localizó publicación de inflación en {self.base_url}"
            )
        html = http_get_text(url)
        point = parse_bulletin(html, source="ovf", period=period)
        logger.info("OVF IPC %s: mensual %s, interanual %s",
                    point.period, point.monthly_rate, point.annual_rate)
        return point