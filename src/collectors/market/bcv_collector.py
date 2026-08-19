"""
Collector BCV (Banco Central de Venezuela)
==========================================

Obtiene:
- Dólar oficial (tasa de referencia BCV) desde una API comunitaria
  (por defecto DolarAPI, sin autenticación).
- IPC oficial mensual desde una API de IPC (URL configurable).

El parseo es tolerante a distintas formas de respuesta para no romper la
serie si el proveedor cambia el esquema.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from src.collectors.errors import CollectorSourceError
from src.collectors.http import http_get_json
from src.config import settings
from src.models.market import ExchangeRate, InflationPoint

logger = logging.getLogger(__name__)


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    # Coma decimal (p.ej. "1,5")
    if isinstance(value, str):
        try:
            return float(value.replace(",", "."))
        except ValueError:
            return None
    return None


def parse_dolarapi(payload: Any, source: str = "bcv") -> ExchangeRate:
    """Normaliza la respuesta de DolarAPI a ``ExchangeRate``.

    Acepta tanto el endpoint oficial (objeto) como listas de monitores.
    Campos posibles de tasa: ``precio``, ``transferencia``, ``venta``,
    ``compra``, ``promedio``, ``cierre``; fecha en ``fecha``, ``cambio.fecha``
    o ``actualizado``.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    if not isinstance(payload, dict):
        raise CollectorSourceError("Respuesta de DolarAPI no parseable")

    rate = None
    for key in ("precio", "transferencia", "venta", "compra", "promedio", "cierre", "price"):
        value = _as_float(payload.get(key))
        if value is not None and value > 0:
            rate = value
            break
    if rate is None:
        raise CollectorSourceError("DolarAPI sin tasa (precio/transferencia/venta/compra)")

    fecha = (
        payload.get("fecha")
        or (payload.get("cambio") or {}).get("fecha")
        or payload.get("actualizado")
        or datetime.now().isoformat()
    )
    date = _parse_date(fecha)

    variation = _as_float(payload.get("variacion") or payload.get("variation"))

    return ExchangeRate(
        source=source,
        currency="usd",
        rate=rate,
        date=date,
        variation_pct=variation,
    )


def _parse_date(raw: str) -> datetime:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        logger.warning("Fecha no reconocida %r, usando ahora", raw)
        return datetime.now()


def parse_ipc(payload: Any, source: str, period: Optional[str] = None) -> InflationPoint:
    """Normaliza una respuesta de IPC (objeto o lista) a ``InflationPoint``.

    Acepta claves: ``period``, ``monthly_rate``/``mensual``/``inflacion_mensual``,
    ``annual_rate``/``anual``/``interanual``, ``index``/``indice``.
    """
    if isinstance(payload, list):
        payload = payload[0] if payload else {}

    if not isinstance(payload, dict):
        raise CollectorSourceError("Respuesta de IPC no parseable")

    effective_period = period or payload.get("period") or payload.get("periodo")
    if not effective_period:
        raise CollectorSourceError("IPC sin período")

    monthly = _as_float(
        payload.get("monthly_rate")
        or payload.get("mensual")
        or payload.get("inflacion_mensual")
    )
    annual = _as_float(
        payload.get("annual_rate") or payload.get("anual") or payload.get("interanual")
    )
    index = _as_float(payload.get("index") or payload.get("indice"))

    return InflationPoint(
        source=source,
        period=str(effective_period),
        monthly_rate=monthly,
        annual_rate=annual,
        index=index,
    )


class BCVCollector:
    """Dólar oficial e IPC del Banco Central de Venezuela."""

    def __init__(self, rate_url: Optional[str] = None, ipc_url: Optional[str] = None):
        self.rate_url = rate_url or settings.BCV_RATE_API_URL
        self.ipc_url = ipc_url or settings.BCV_IPC_API_URL

    def fetch_official_rate(self) -> ExchangeRate:
        """Tasa oficial de cambio USD/VES del día."""
        payload = http_get_json(self.rate_url)
        return parse_dolarapi(payload, source="bcv")

    def fetch_ipc(self, period: Optional[str] = None) -> InflationPoint:
        """IPC oficial mensual para ``period`` (YYYY-MM)."""
        params = {"period": period} if period else None
        payload = http_get_json(self.ipc_url, params=params)
        return parse_ipc(payload, source="bcv", period=period)

    def collect(self, period: Optional[str] = None) -> dict:
        """Recolecta tasa e IPC en una llamada (resume en dict)."""
        result = {"rate": self.fetch_official_rate(), "ipc": self.fetch_ipc(period)}
        logger.info("BCV recolectado: tasa %.2f, IPC %s", result["rate"].rate, period)
        return result