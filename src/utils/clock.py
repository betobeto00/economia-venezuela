"""Reloj del proyecto: hora local de Venezuela
============================================

Todas las etiquetas visibles (informes, cabeceras, dashboard) deben usar
``local_now``; las marcas de tiempo que van a la base de datos siguen en UTC.

Venezuela usa UTC-4 todo el año (no hay horario de verano desde 2016), así que
``America/Caracas`` equivale siempre a ``-04:00``. En Windows no hay base de
datos IANA, por eso se cae a un offset fijo si ``zoneinfo`` no encuentra la
zona: el resultado es idéntico.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

from src.config import settings

try:  # pragma: no cover - depende de la plataforma
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover - Python < 3.9
    ZoneInfo = None  # type: ignore[assignment]

#: UTC-4 con nombre, equivalente a ``America/Caracas``.
FIXED_VET = timezone(timedelta(hours=-4), "VET")


@lru_cache(maxsize=4)
def tz(name: Optional[str] = None):
    """Zona horaria solicitada (por defecto ``settings.TIMEZONE``).

    Args:
        name: Nombre IANA (``America/Caracas``). ``None`` usa la configurada.

    Returns:
        ``tzinfo`` de la zona; si no se puede cargar, el offset fijo ``-04:00``.
    """
    name = name or settings.TIMEZONE
    if ZoneInfo is not None:
        try:
            return ZoneInfo(name)
        except Exception:  # noqa: BLE001 - sin tzdata en Windows
            pass
    return FIXED_VET


def local_now(name: Optional[str] = None) -> datetime:
    """Ahora en hora local de Venezuela (con zona)."""
    return datetime.now(tz(name))


def local_today(name: Optional[str] = None) -> date:
    """Fecha de hoy en hora local de Venezuela."""
    return local_now(name).date()


def utc_now() -> datetime:
    """Ahora en UTC (para persistencia y comparaciones en base)."""
    return datetime.now(timezone.utc)


def as_local(value: datetime, name: Optional[str] = None) -> datetime:
    """Convierte ``value`` a hora local.

    Los ``datetime`` sin zona se interpretan como UTC, que es como se guardan
    en la base de datos.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(tz(name))


def tz_label(name: Optional[str] = None) -> str:
    """Etiqueta legible para cabeceras, p.ej. ``hora Caracas (UTC-4)``."""
    offset = local_now(name).utcoffset() or timedelta(0)
    hours = int(offset.total_seconds() // 3600)
    return f"hora Caracas (UTC{hours:+d})"
