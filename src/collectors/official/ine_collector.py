"""
Collector INE (Instituto Nacional de Estadística)
==================================================

Indicadores sociales (empleo, pobreza, población) publicados en el sitio
del INE. No expone API: se obtiene la página y se buscan etiquetas de
indicadores conocidas seguidas de un número.

Estrategia defensiva: se ignoran textos sin los números esperados y se
registra un aviso. Si no se encuentra nada se devuelve una lista vacía.
"""

import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

# Etiquetas de indicadores → (clave interna, unidad)
INDICATORS = {
    "desempleo": ("desempleo", "%"),
    "pobreza": ("pobreza", "%"),
    "población": ("poblacion", "hab"),
    "poblacion": ("poblacion", "hab"),
}

NUMBER_RE = re.compile(r"([\d]+(?:[.,]\d+)?)")


def find_indicators(html: str, source: str = "ine") -> List[IndicatorPoint]:
    """Indicadores (etiqueta → primer número) en el texto visible."""
    text = BeautifulSoup(html, "html.parser").get_text(" ")
    tokens = text.split()
    found: List[IndicatorPoint] = []
    for i, token in enumerate(tokens):
        clean = token.strip(":,.()[]").lower()
        if clean not in INDICATORS:
            continue
        # Busca el primer número en los siguientes 6 tokens
        for next_token in tokens[i + 1:i + 7]:
            match = NUMBER_RE.search(next_token.replace("%", ""))
            if match:
                value = float(match.group(1).replace(",", "."))
                indicator, unit = INDICATORS[clean]
                found.append(
                    IndicatorPoint(
                        source=source, indicator=indicator,
                        value=value, period="", unit=unit,
                    )
                )
                break
    return found


class INECollector:
    """Indicadores sociales del INE."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.INE_BASE_URL).rstrip("/")

    def fetch_indicators(self) -> List[IndicatorPoint]:
        html = http_get_text(self.base_url + "/")
        points = find_indicators(html)
        logger.info("INE: %d indicadores extraídos", len(points))
        return points