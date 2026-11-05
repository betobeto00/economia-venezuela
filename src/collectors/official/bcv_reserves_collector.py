"""
Reservas internacionales del BCV
================================

Serie diaria de reservas internacionales del libro ``2_1_1.xlsx``
("Reservas internacionales del BCV") que publica el Banco Central:

    https://www.bcv.org.ve/sites/default/files/indicadores_sector_externo/2_1_1.xlsx

El libro trae una hoja por año (``2026``, ``2025``, ...) y una hoja de apoyo
(``Module1``). Encabezado en las primeras filas::

    FECHA | BCV | FEM (1) | TOTAL | ...
    (Millones de USD)

Se toma la fila más reciente de la primera hoja con datos y se devuelve el
TOTAL (BCV + FEM) convertido a USD. Es dato oficial publicado, sin estimaciones.
"""

import io
import logging
from datetime import date, datetime
from typing import Optional

import httpx
import openpyxl

from src.collectors.errors import CollectorError, CollectorSourceError
from src.collectors.http import http_get_bytes
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

MILLONES = 1_000_000
INDICATOR = "reservas_internacionales"


def _download(url: str) -> bytes:
    """Descarga el libro del BCV.

    El BCV sirve la cadena TLS sin el certificado intermedio, así que httpx
    rechaza el certificado (``unable to get local issuer certificate``);
    curl y los navegadores lo resuelven por AIA y por eso sí funcionan. Se
    reintenta sin verificar el certificado solo en ese caso: es un archivo
    público de estadísticas, sin cookies ni credenciales.
    """
    try:
        return http_get_bytes(url)
    except CollectorError as exc:
        if "CERTIFICATE_VERIFY_FAILED" not in str(exc):
            raise
        logger.warning("BCV: cadena TLS incompleta, descargando sin verificar certificado")
        try:
            with httpx.Client(timeout=30.0, follow_redirects=True, verify=False) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.content
        except httpx.HTTPError as http_exc:
            raise CollectorError(f"No se pudo descargar {url}: {http_exc}") from http_exc


def _to_date(raw) -> Optional[date]:
    """Normaliza la celda de fecha (``04/11/2026(*)`` o ``datetime``)."""
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if not isinstance(raw, str):
        return None
    text = raw.strip().replace("(*)", "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_reserves(xlsx_bytes: bytes, source: str = "bcv") -> IndicatorPoint:
    """Última reserva total (USD) del libro del BCV."""
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(xlsx_bytes), data_only=True, read_only=True
        )
    except Exception as exc:  # noqa: BLE001 - archivo corrupto o no-xlsx
        raise CollectorSourceError(f"BCV: xlsx de reservas ilegible ({exc})") from exc

    latest: Optional[tuple] = None
    for sheet in workbook.worksheets:
        for row in sheet.iter_rows(values_only=True):
            if not row or len(row) < 4:
                continue
            fecha = _to_date(row[0])
            if fecha is None:
                continue
            try:
                total = float(row[3])
            except (TypeError, ValueError):
                continue
            if total <= 0:
                continue
            if latest is None or fecha > latest[0]:
                latest = (fecha, total)
        if latest is not None:
            break  # la primera hoja con datos es el año en curso

    workbook.close()
    if latest is None:
        raise CollectorSourceError("BCV: el libro de reservas no trae filas con dato")

    fecha, total_millones = latest
    return IndicatorPoint(
        source=source,
        indicator=INDICATOR,
        value=total_millones * MILLONES,
        period=fecha.isoformat(),
        unit="USD",
    )


class BCVReservesCollector:
    """Reservas internacionales de Venezuela (BCV + FEM)."""

    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.BCV_RESERVES_URL

    def fetch_reserves(self) -> IndicatorPoint:
        """Último dato publicado de reservas internacionales (USD)."""
        return parse_reserves(_download(self.url))
