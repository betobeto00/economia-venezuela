"""
Collector Asamblea Nacional de Venezuela
========================================

La AN publica leyes (vigentes/sancionadas/proyectos), actos legislativos y
noticias en ``asambleanacional.gob.ve`` (Laravel + UIkit):

- ``/leyes/vigentes``: tarjetas paginadas (``?page=N``) con
  ``Fecha: DD/MM/YYYY``, ``Gaceta N°``, título y enlace al detalle.
- ``/actos``: acordeón con tablas de actos (fecha + título + enlace).
- ``/noticias``: portada de noticias (la ingesta de noticias ya la cubre el
  pipeline RSS, así que aquí no se duplica).

El collector extrae leyes y actos como catálogo ``FiscalDocument`` y permite
filtrar por palabras clave fiscales (presupuesto, endeudamiento, ...).
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import FiscalDocument

logger = logging.getLogger(__name__)

BASE = "https://www.asambleanacional.gob.ve"
LEY_DEFAULTS = ("presupuesto", "endeudamiento", "gasto público", "gasto publico")

# Tarjeta de ley: Fecha + Gaceta N° + título/enlace (una por tarjeta)
_FECHA_RE = re.compile(r"Fecha:\s*(\d{2}/\d{2}/\d{4})")
_GACETA_RE = re.compile(r"Gaceta\s*N\s*(?:[º°]|&#176;)?\s*<b>([^<]+)</b>")
_LEY_LINK_RE = re.compile(
    r'<a href="(https://www\.asambleanacional\.gob\.ve/leyes/[^"]+)"[^>]*>'
    r"<b>([^<]*)</b></a>"
)
# Acto legislativo: fila de tabla fecha + título/enlace
_ACTO_RE = re.compile(
    r"<small>(\d{2}/\d{2}/\d{4})</small></td><td[^>]*><p>\s*"
    r"<a href=\"(https://www\.asambleanacional\.gob\.ve/actos/[^\"]+)\"[^>]*>"
    r"([^<]+)</a>"
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip(" .")


def parse_leyes(html: str) -> List[dict]:
    """Tarjetas de leyes: lista de {title, url, date, gaceta}."""
    fechas = _FECHA_RE.findall(html)
    gacetas = _GACETA_RE.findall(html)
    links = _LEY_LINK_RE.findall(html)
    n = min(len(fechas), len(links))
    out = []
    for i in range(n):
        try:
            fecha = datetime.strptime(fechas[i], "%d/%m/%Y").date()
        except ValueError:
            continue
        out.append(
            {
                "title": _clean(links[i][1]),
                "url": links[i][0],
                "date": fecha,
                "gaceta": _clean(gacetas[i]) if i < len(gacetas) else None,
            }
        )
    return out


def parse_actos(html: str) -> List[dict]:
    """Filas de actos legislativos: lista de {title, url, date}."""
    out = []
    for fecha, url, title in _ACTO_RE.findall(html):
        try:
            date = datetime.strptime(fecha, "%d/%m/%Y").date()
        except ValueError:
            continue
        out.append({"title": _clean(title), "url": url, "date": date})
    return out


def _matches(title: str, keywords: Optional[List[str]]) -> bool:
    if not keywords:
        return True
    low = title.lower()
    return any(kw.lower() in low for kw in keywords)


class ANCollector:
    """Leyes y actos de la Asamblea Nacional de Venezuela."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.AN_BASE_URL).rstrip("/")

    def _page(self, path: str, params: Optional[dict] = None) -> str:
        return http_get_text(self.base_url + path, params=params)

    def fetch_leyes(
        self,
        categoria: str = "vigentes",
        keywords: Optional[List[str]] = None,
        max_pages: int = 10,
    ) -> List[FiscalDocument]:
        """Leyes de la sección paginada (vigentes/sancionadas/proyectos).

        Filtra por palabras clave (title) y deja de paginar al llegar al
        final o a ``max_pages``.
        """
        docs: List[FiscalDocument] = []
        for page in range(1, max_pages + 1):
            html = self._page(
                f"/leyes/{categoria}", {"page": page} if page > 1 else None
            )
            cards = parse_leyes(html)
            if not cards:
                break
            for c in cards:
                if not _matches(c["title"], keywords):
                    continue
                docs.append(
                    FiscalDocument(
                        source="an",
                        title=c["title"],
                        url=c["url"],
                        year=c["date"].year,
                    )
                )
            logger.info(
                "AN leyes %s: %d tarjetas en página %d (acumulado %d)",
                categoria, len(cards), page, len(docs),
            )
        logger.info("AN leyes %s: %d documentos con keywords %s",
                    categoria, len(docs), keywords)
        return docs

    def fetch_actos(
        self, keywords: Optional[List[str]] = None
    ) -> List[FiscalDocument]:
        """Actos legislativos del acordeón (acuerdos, informes de comisiones)."""
        html = self._page("/actos")
        rows = parse_actos(html)
        docs = [
            FiscalDocument(
                source="an",
                title=r["title"],
                url=r["url"],
                year=r["date"].year,
            )
            for r in rows
            if _matches(r["title"], keywords)
        ]
        logger.info("AN actos: %d documentos con keywords %s", len(docs), keywords)
        return docs

    def fetch_documentos(
        self,
        keywords: Optional[List[str]] = None,
        categoria: str = "vigentes",
        max_pages: int = 10,
    ) -> List[FiscalDocument]:
        """Catálogo combinado de leyes y actos (deduplicado por URL)."""
        docs = self.fetch_leyes(categoria=categoria, keywords=keywords,
                                max_pages=max_pages)
        docs += self.fetch_actos(keywords=keywords)
        seen: set = set()
        out = []
        for d in docs:
            if d.url in seen:
                continue
            seen.add(d.url)
            out.append(d)
        return out