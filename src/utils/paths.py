"""Rutas de datos sin años fijos
==============================

Los directorios de OCR se organizan por año (``data/ocr/bvc/2026``). Fijar el
año en el código hacía que, al cambiar de año, la lectura devolviera vacío en
silencio. Aquí se resuelve siempre el directorio más reciente que exista.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

from src.utils.clock import local_today

logger = logging.getLogger(__name__)


def year_dirs(root: Path) -> List[Path]:
    """Subdirectorios de ``root`` cuyo nombre es un año, de más nuevo a más viejo."""
    if not root.exists():
        return []
    found: Iterable[Path] = (
        path for path in root.iterdir() if path.is_dir() and path.name.isdigit()
    )
    return sorted(found, key=lambda path: int(path.name), reverse=True)


def latest_year_dir(root: Path, year: int | None = None) -> Path:
    """Directorio del año pedido, o el más reciente disponible, o el actual.

    Args:
        root: Carpeta que contiene un subdirectorio por año.
        year: Año explícito; si se indica y existe, se usa ese.

    Returns:
        ``root/<año>``. Nunca falla: si no hay carpetas devuelve el año actual
        (la ruta puede no existir, y quien la use ya maneja el caso vacío).
    """
    if year is not None:
        candidate = root / str(year)
        if candidate.exists():
            return candidate
    candidates = year_dirs(root)
    if candidates:
        return candidates[0]
    return root / str(local_today().year)
