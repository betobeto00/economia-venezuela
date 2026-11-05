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

``fetch_reserves`` devuelve el último día publicado y ``fetch_history`` la
serie completa desde ``start_year`` (para el gráfico del tab Macro). Los
valores se convierten a USD: es dato oficial, sin estimaciones.
"""

import io
import logging
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterator, List, Optional

import httpx
import openpyxl

from src.collectors.errors import CollectorError, CollectorSourceError
from src.collectors.http import http_get_bytes
from src.config import settings
from src.models.market import IndicatorPoint

logger = logging.getLogger(__name__)

MILLONES = 1_000_000
INDICATOR = "reservas_internacionales"


@dataclass(frozen=True)
class ReservesDay:
    """Un día de la serie de reservas (montos en USD)."""

    date: str                    # YYYY-MM-DD
    total_usd: float
    bcv_usd: Optional[float] = None
    fem_usd: Optional[float] = None


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


def _numeric(raw) -> Optional[float]:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _iter_days(xlsx_bytes: bytes) -> Iterator[ReservesDay]:
    """Recorre todas las hojas y emite cada día con dato de reservas."""
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(xlsx_bytes), data_only=True, read_only=True
        )
    except Exception as exc:  # noqa: BLE001 - archivo corrupto o no-xlsx
        raise CollectorSourceError(f"BCV: xlsx de reservas ilegible ({exc})") from exc

    try:
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                if not row or len(row) < 4:
                    continue
                fecha = _to_date(row[0])
                if fecha is None:
                    continue
                total = _numeric(row[3])
                if total is None:
                    continue
                bcv = _numeric(row[1])
                fem = _numeric(row[2])
                yield ReservesDay(
                    date=fecha.isoformat(),
                    total_usd=total * MILLONES,
                    bcv_usd=bcv * MILLONES if bcv is not None else None,
                    fem_usd=fem * MILLONES if fem is not None else None,
                )
    finally:
        workbook.close()


def parse_reserves(xlsx_bytes: bytes, source: str = "bcv") -> IndicatorPoint:
    """Último día de reservas del libro del BCV (USD)."""
    latest: Optional[ReservesDay] = None
    for day in _iter_days(xlsx_bytes):
        if latest is None or day.date > latest.date:
            latest = day

    if latest is None:
        raise CollectorSourceError("BCV: el libro de reservas no trae filas con dato")

    return IndicatorPoint(
        source=source,
        indicator=INDICATOR,
        value=latest.total_usd,
        period=latest.date,
        unit="USD",
    )


def parse_history(xlsx_bytes: bytes, start_year: int = 2020,
                  source: str = "bcv") -> List[ReservesDay]:
    """Serie completa desde ``start_year`` (una entrada por fecha, ordenada)."""
    days = {}
    for day in _iter_days(xlsx_bytes):
        if int(day.date[:4]) < start_year:
            continue
        days[day.date] = day

    if not days:
        raise CollectorSourceError(
            f"BCV: el libro de reservas no trae datos desde {start_year}"
        )
    return sorted(days.values(), key=lambda d: d.date)


class BCVReservesCollector:
    """Reservas internacionales de Venezuela (BCV + FEM)."""

    def __init__(self, url: Optional[str] = None):
        self.url = url or settings.BCV_RESERVES_URL

    def fetch_reserves(self) -> IndicatorPoint:
        """Último dato publicado de reservas internacionales (USD)."""
        return parse_reserves(_download(self.url))

    def fetch_history(self, start_year: int = 2020) -> List[ReservesDay]:
        """Serie histórica de reservas desde ``start_year``."""
        return parse_history(_download(self.url), start_year=start_year)
