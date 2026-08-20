"""
Collector FMI (Fondo Monetario Internacional)
==============================================

API pública SDMX-JSON del FMI (dataservices.imf.org) para Venezuela (área
``VE``) del dataset IFS (International Financial Statistics):

- Crecimiento del PIB real (``NGDP_RPCH``, % anual).
- Inflación IPC fin de período (``PCPIPCH``, %).

El JSON sigue la forma::

    {"CompactData": {"DataSet": {"Series": [{"Obs": [
        {"@TIME_PERIOD": "2020", "@OBS_VALUE": "-30.0"}, ...
    ]}]}}}

Se navega de forma defensiva y se descartan observaciones sin valor.
"""

import logging
from typing import List, Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_json
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

INDICATOR_GDP_GROWTH = "NGDP_RPCH"   # Crecimiento del PIB real (%)
INDICATOR_INFLATION = "PCPIPCH"      # Inflación IPC fin de período (%)

_FREQ = "A"
_AREA = "VE"


def parse_imf_series(payload: dict, indicator: str, source: str = "imf") -> List[IndicatorPoint]:
    """Convierte la respuesta SDMX-JSON del FMI en ``IndicatorPoint``."""
    try:
        dataset = payload["CompactData"]["DataSet"]
    except (KeyError, TypeError):
        raise CollectorSourceError(f"FMI: respuesta sin datos ({indicator})")
    if not isinstance(dataset, dict):
        raise CollectorSourceError(f"FMI: respuesta sin datos ({indicator})")

    series = dataset.get("Series") or []
    if isinstance(series, dict):
        series = [series]

    points: List[IndicatorPoint] = []
    for item in series:
        if item.get("@INDICATOR") and item.get("@INDICATOR") != indicator:
            continue
        for obs in item.get("Obs") or []:
            period = obs.get("@TIME_PERIOD")
            raw = obs.get("@OBS_VALUE")
            if period is None or raw is None:
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            points.append(IndicatorPoint(
                source=source, indicator=indicator, value=value,
                period=str(period), unit="%",
            ))
    points.sort(key=lambda p: p.period)
    return points


class IMFCollector:
    """Indicadores macro de Venezuela desde la API del FMI."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.IMF_SDMX_URL).rstrip("/")

    def fetch_indicator(self, code: str, start: Optional[int] = None,
                        end: Optional[int] = None) -> List[IndicatorPoint]:
        """Serie anual de un indicador IFS para Venezuela."""
        url = f"{self.base_url}/CompactData/IFS/{_FREQ}.{_AREA}.{code}"
        params = {"startPeriod": start, "endPeriod": end} if start else None
        payload = http_get_json(url, params=params)
        return parse_imf_series(payload, code)

    def fetch_gdp_growth(self) -> List[IndicatorPoint]:
        return self.fetch_indicator(INDICATOR_GDP_GROWTH)

    def fetch_inflation(self) -> List[IndicatorPoint]:
        return self.fetch_indicator(INDICATOR_INFLATION)