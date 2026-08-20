"""
Collector de Consumo Masivo
============================

Recolecta datos de consumo masivo de firmas de consultoría:
- Atenas Grupo Consultor (reportes de retail)
- Ansa (noticias económicas con datos de consumo)

Estos datos son el termómetro real del comercio retail en Venezuela.
El volumen de ventas en supermercados refleja mejor la actividad económica
que los indicadores oficiales.

Fuentes:
- https://ansaes.com (noticias económicas)
- Reportes públicos de Atenas Grupo Consultor
- Twitter/X de analistas económicos
"""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional

import httpx

logger = logging.getLogger(__name__)

ATENAS_URL = "https://atenasgc.com"
ANSA_URL = "https://ansaes.com"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
}


@dataclass
class ConsumoDataPoint:
    """Punto de datos de consumo masivo."""
    indicador: str
    valor: float
    periodo: str
    unidad: str
    fuente: str
    sector: str = ""  # retail, alimentos, general
    notas: str = ""


def fetch_ansa_economic_news(limit: int = 10) -> List[dict]:
    """Obtiene noticias económicas de ANSA con datos de consumo."""
    try:
        resp = httpx.get(
            f"{ANSA_URL}/economia/",
            headers=HEADERS,
            timeout=30,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []

        # Extraer enlaces de noticias
        links = re.findall(
            r'href=["\']([^"\']*economia[^"\']*)["\']',
            resp.text,
            re.IGNORECASE,
        )

        news = []
        for link in links[:limit]:
            if not link.startswith("http"):
                link = f"{ANSA_URL}{link}"
            news.append({
                "url": link,
                "source": "ansa",
                "title": link.split("/")[-1].replace("-", " ").title(),
            })

        return news
    except Exception as exc:
        logger.debug("ANSA no disponible: %s", exc)
        return []


def fetch_atenas_reports() -> List[dict]:
    """Obtiene reportes públicos de Atenas Grupo Consultor."""
    try:
        resp = httpx.get(
            ATENAS_URL,
            headers=HEADERS,
            timeout=30,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return []

        # Buscar reportes o publicaciones
        reports = []
        links = re.findall(
            r'href=["\']([^"\']*(?:reporte|estudio|analisis|consumo)[^"\']*)["\']',
            resp.text,
            re.IGNORECASE,
        )
        for link in links[:5]:
            if not link.startswith("http"):
                link = f"{ATENAS_URL}{link}"
            reports.append({
                "url": link,
                "source": "atenas",
                "title": link.split("/")[-1].replace("-", " ").title(),
            })

        return reports
    except Exception as exc:
        logger.debug("Atenas no disponible: %s", exc)
        return []


def estimate_consumption_indicators(
    news: List[dict],
    reports: List[dict],
) -> List[ConsumoDataPoint]:
    """Estima indicadores de consumo a partir de noticias y reportes.

    Returns:
        Lista de ConsumoDataPoint con indicadores disponibles.
    """
    indicators = []

    # Contar noticias por sector
    if news:
        indicators.append(ConsumoDataPoint(
            indicador="noticias_economicas",
            valor=len(news),
            periodo="actual",
            unidad="count",
            fuente="ansa",
            sector="general",
        ))

    # Contar reportes de Atenas
    if reports:
        indicators.append(ConsumoDataPoint(
            indicador="reportes_consumo",
            valor=len(reports),
            periodo="actual",
            unidad="count",
            fuente="atenas",
            sector="retail",
        ))

    return indicators


def consumption_summary() -> dict:
    """Resumen del estado del consumo masivo."""
    news = fetch_ansa_economic_news()
    reports = fetch_atenas_reports()
    indicators = estimate_consumption_indicators(news, reports)

    return {
        "news_count": len(news),
        "reports_count": len(reports),
        "indicators": indicators,
        "news": news[:5],
        "reports": reports[:5],
    }
