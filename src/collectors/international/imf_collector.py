"""
Collector FMI (Fondo Monetario Internacional)
=============================================

Serie del *World Economic Outlook* (WEO) para Venezuela (``VEN``) servida por
DBnomics, que espeja los datasets del FMI sin API key ni registro:

- Crecimiento del PIB real (``NGDP_RPCH``, % anual).
- Inflación media anual (``PCPIPCH``, %).

Por qué DBnomics: el endpoint de DataMapper
(``www.imf.org/external/datamapper/api/v1/...``) responde ``403 Access Denied``
desde esta red (bloqueo de Akamai) y ``dataservices.imf.org`` ya no resuelve
por DNS. DBnomics publica el mismo WEO y responde sin credenciales.

El JSON tiene la forma::

    {"series": {"docs": [{"period": ["2023", "2024"], "value": ["337.4", "48.9"]}]}}

Los años sin dato o sin proyección llegan como ``"NA"`` y se descartan. Ojo:
las dos últimas filas del WEO suelen ser *proyecciones* del Fondo, no datos
observados; se conservan porque es lo que el FMI publica como vigente.
"""

import logging
from typing import List, Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_json
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

INDICATOR_GDP_GROWTH = "NGDP_RPCH"   # Crecimiento del PIB real (%)
INDICATOR_INFLATION = "PCPIPCH"      # Inflación media anual (%)

_AREA = "VEN"


def parse_dbnomics_series(payload: dict, indicator: str,
                          source: str = "imf") -> List[IndicatorPoint]:
    """Convierte una serie de DBnomics (FMI/WEO) en ``IndicatorPoint``."""
    try:
        docs = payload["series"]["docs"]
    except (KeyError, TypeError):
        raise CollectorSourceError(f"FMI: respuesta sin series ({indicator})")
    if not isinstance(docs, list) or not docs:
        raise CollectorSourceError(f"FMI: respuesta sin series ({indicator})")

    doc = docs[0]
    periods = doc.get("period") or []
    if not isinstance(periods, list) or not periods:
        raise CollectorSourceError(f"FMI: serie sin período ({indicator})")
    values = doc.get("value") or []

    points: List[IndicatorPoint] = []
    for period, raw in zip(periods, values):
        if period is None or raw is None:
            continue
        try:
            value = float(raw)  # "NA" y "" levantan ValueError
        except (TypeError, ValueError):
            continue
        points.append(IndicatorPoint(
            source=source, indicator=indicator, value=value,
            period=str(period), unit="%",
        ))
    points.sort(key=lambda p: p.period)
    return points


class IMFCollector:
    """Indicadores macro de Venezuela desde el WEO del FMI (vía DBnomics)."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.IMF_WEO_API_URL).rstrip("/")

    def fetch_indicator(self, code: str) -> List[IndicatorPoint]:
        """Serie anual de un indicador WEO para Venezuela."""
        url = f"{self.base_url}/{_AREA}.{code}"
        payload = http_get_json(url, params={"observations": "1"})
        return parse_dbnomics_series(payload, code)

    def fetch_gdp_growth(self) -> List[IndicatorPoint]:
        return self.fetch_indicator(INDICATOR_GDP_GROWTH)

    def fetch_inflation(self) -> List[IndicatorPoint]:
        return self.fetch_indicator(INDICATOR_INFLATION)
