"""
Collector CEPAL (Comisión Económica para América Latina y el Caribe)
===================================================================

Usa la API pública de CEPALSTAT (``api-cepalstat.cepal.org``) para
Venezuela. Datos por defecto: PIB anual a precios constantes en dólares
(indicador 2216, rubro "Producto interno bruto (PIB)"), con la unidad y el
nombre del indicador tomados de la respuesta.

Flujo:
1. ``fetch_dimensions(indicator)``: dimensiones del indicador → mapeo
   id→año (dimensión de años) e id→país (dimensión de países).
2. ``fetch_gdp()``: consulta el endpoint ``/indicator/{id}/data`` con el
   miembro de Venezuela y el rubro del PIB total, y convierte cada
   observación en un ``IndicatorPoint`` (period = año, unit = unidad).
"""

import logging
from typing import Dict, List, Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_json
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

GDP_INDICATOR = 2216          # PIB anual a precios constantes (millones USD)
GDP_RUBRO_TOTAL = 21166       # Rubro "Producto interno bruto (PIB)"
DIM_PAIS = 208                # Dimensión de países
DIM_ANIO = 29117              # Dimensión de años
COUNTRY = "Venezuela"

_APP_PARAMS = {"lang": "es", "format": "json", "app": "dashboard"}


def _navigate(payload: dict, *keys):
    """Navega la respuesta CEPALSTAT de forma defensiva (None si no existe)."""
    current = payload
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def parse_dimensions(payload: dict) -> Dict[int, int]:
    """Mapeos de la respuesta ``/dimensions``: id de país y id→año.

    Returns:
        ``{"years": {member_id: año}, "country": member_id}``.
    """
    dims = _navigate(payload, "body", "dimensions")
    years: Dict[int, int] = {}
    country: Optional[int] = None
    for dim in dims if isinstance(dims, list) else []:
        dim_id = dim.get("id")
        for member in dim.get("members") or []:
            if dim_id == DIM_ANIO:
                try:
                    years[int(member["id"])] = int(member["name"])
                except (KeyError, TypeError, ValueError):
                    continue
            elif dim_id == DIM_PAIS and str(member.get("name") or "").startswith(COUNTRY):
                country = member.get("id")
    if not years:
        raise CollectorSourceError("CEPAL: dimensiones sin años")
    return {"years": years, "country": country}


def parse_data(payload: dict) -> tuple:
    """Observaciones y metadatos de la respuesta ``/indicator/{id}/data``.

    Returns:
        (metadata dict, lista de filas ``{year, value}``).
    """
    body = _navigate(payload, "body") or {}
    metadata = body.get("metadata") or {}
    rows: list = []
    for row in (body.get("data") or []):
        year_id = row.get(f"dim_{DIM_ANIO}")
        try:
            value = float(row["value"])
        except (KeyError, TypeError, ValueError):
            continue
        rows.append({"year": int(year_id), "value": value})
    if not rows:
        raise CollectorSourceError("CEPAL: sin observaciones")
    return metadata, rows


class CEPALCollector:
    """Indicadores macro de Venezuela desde CEPALSTAT."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.CEPALSTAT_BASE_URL).rstrip("/")

    def fetch_dimensions(self, indicator_id: int = GDP_INDICATOR) -> dict:
        """Mapeos de países y años del indicador."""
        url = f"{self.base_url}/indicator/{indicator_id}/dimensions"
        return parse_dimensions(http_get_json(url, params=_APP_PARAMS))

    def fetch_gdp(self, start_year: Optional[int] = None,
                   end_year: Optional[int] = None) -> List[IndicatorPoint]:
        """Serie anual del PIB (millones USD constantes) de Venezuela."""
        dims = self.fetch_dimensions()
        years = dims["years"]
        country = dims["country"]
        if country is None:
            raise CollectorSourceError("CEPAL: no se localizó a Venezuela")

        members = [country, GDP_RUBRO_TOTAL]
        url = f"{self.base_url}/indicator/{GDP_INDICATOR}/data"
        payload = http_get_json(
            url, params={**_APP_PARAMS, "members": ",".join(map(str, members)), "in": "1"}
        )
        metadata, rows = parse_data(payload)

        points: List[IndicatorPoint] = []
        for row in rows:
            year = years.get(row["year"])
            if year is None:
                continue
            if start_year is not None and year < start_year:
                continue
            if end_year is not None and year > end_year:
                continue
            points.append(IndicatorPoint(
                source="cepal",
                indicator="pib_total",
                value=row["value"],
                period=str(year),
                unit=metadata.get("unit") or "Millones de dólares",
            ))
        points.sort(key=lambda p: p.period)
        logger.info("CEPAL: %d observaciones de PIB para Venezuela", len(points))
        return points