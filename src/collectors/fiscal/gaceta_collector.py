"""
Collector Gaceta Oficial de la República Bolivariana de Venezuela
=================================================================

``gacetaoficial.gob.ve`` publica el índice de la Gaceta Oficial:
- ``/``: calendario anual con los días que tienen gacetas
  (``.calendar-day.has-gaceta``).
- ``/gacetas/dia?year=&month=&day=``: JSON con las gacetas de una fecha
  (``numero_gaceta``, ``categoria``, ``fecha_gaceta``, ``ruta_archivo`` PDF).
- ``/gacetas/filtro-avanzado?texto=``: búsqueda en texto de gacetas y
  sumarios; devuelve una tabla con N° de gaceta, tipo, fecha y páginas.

El PDF sigue el patrón ``/storage/{año}/{numero}-{YYYY-MM-DD}-{TIPO}.pdf``.
"""

import logging
import re
from datetime import date, datetime, timedelta
from typing import List, Optional

from src.collectors.http import http_get_text, http_get_json
from src.config import settings
from src.models.market import FiscalDocument

logger = logging.getLogger(__name__)

DIA_ENDPOINT = "/gacetas/dia"
BUSQUEDA_ENDPOINT = "/gacetas/filtro-avanzado"
DETALLE_ENDPOINT = "/gacetas/"

_CALENDAR_DAY_RE = re.compile(
    r'<div class="[^"]*calendar-day[^"]*has-gaceta[^"]*"[^>]*>'
)
_ATTR_RE = re.compile(r'data-(year|month|day)="(\d+)"')
_DETAIL_LINK_RE = re.compile(r"/gacetas/(\d+)")


def _strip(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


class GacetaOficialCollector:
    """Índice y PDFs de la Gaceta Oficial de Venezuela."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.GACETA_OFICIAL_BASE_URL).rstrip("/")

    def fetch_gacetas_dia(self, year: int, month: int, day: int) -> List[dict]:
        """Gacetas publicadas en una fecha (JSON de ``/gacetas/dia``)."""
        return http_get_json(
            self.base_url + DIA_ENDPOINT,
            params={"year": year, "month": month, "day": day},
        )

    def fetch_calendario(self) -> List[dict]:
        """Días con gacetas del calendario anual de la portada."""
        html = http_get_text(self.base_url + "/")
        days: List[dict] = []
        for tag in _CALENDAR_DAY_RE.finditer(html):
            attrs = {
                key: int(value)
                for key, value in _ATTR_RE.findall(tag.group(0))
            }
            if {"year", "month", "day"} <= attrs.keys():
                days.append(attrs)
        logger.info("Gaceta: %d días con gacetas en el calendario", len(days))
        return days

    def _parse_busqueda(self, html: str) -> List[dict]:
        """Filas de la tabla de resultados de búsqueda avanzada."""
        rows: List[dict] = []
        for tr in re.findall(r"<tr>.*?</tr>", html, re.S):
            cells = re.findall(r"<td>(.*?)</td>", tr, re.S)
            if len(cells) < 8:
                continue
            detail = _DETAIL_LINK_RE.search(cells[7])
            if not detail:
                continue
            numero = detail.group(1)
            tipo = _strip(cells[1])
            fecha_raw = _strip(cells[3])
            try:
                fecha = datetime.strptime(fecha_raw, "%d/%m/%Y").date()
            except ValueError:
                continue
            rows.append(
                {
                    "numero": int(numero),
                    "tipo": tipo,
                    "fecha": fecha,
                    "pagina_inicio": _strip(cells[4]),
                    "pagina_fin": _strip(cells[5]),
                    "url": f"{self.base_url}{DETALLE_ENDPOINT}{numero}",
                }
            )
        return rows

    def fetch_busqueda(self, texto: str) -> List[dict]:
        """Gacetas cuya sumario/texto contiene ``texto`` (búsqueda avanzada)."""
        html = http_get_text(
            self.base_url + BUSQUEDA_ENDPOINT, params={"texto": texto}
        )
        return self._parse_busqueda(html)

    def _pdf_url(self, numero: int, fecha: date, tipo: str) -> str:
        iso = fecha.isoformat()
        return (
            f"{self.base_url}/storage/{fecha.year}/{numero}-{iso}-{tipo.upper()}.pdf"
        )

    def fetch_documentos(self, keywords: List[str]) -> List[FiscalDocument]:
        """Catálogo de gacetas que mencionan las palabras clave.

        Para cada palabra se consulta la búsqueda avanzada y se construye el
        enlace al PDF con el patrón de almacenamiento.
        """
        docs: List[FiscalDocument] = []
        seen: set = set()
        for kw in keywords:
            for g in self.fetch_busqueda(kw):
                numero = g["numero"]
                if numero in seen:
                    continue
                seen.add(numero)
                docs.append(
                    FiscalDocument(
                        source="gaceta",
                        title=f"Gaceta N° {numero} ({g['tipo']})",
                        url=self._pdf_url(numero, g["fecha"], g["tipo"]),
                        year=g["fecha"].year,
                    )
                )
        logger.info("Gaceta: %d gacetas con keywords %s", len(docs), keywords)
        return docs

    def fetch_recientes(self, days: int = 30) -> List[FiscalDocument]:
        """Gacetas publicadas en los últimos ``days`` días (por calendario)."""
        hoy = date.today()
        docs: List[FiscalDocument] = []
        for i in range(days - 1, -1, -1):
            d = hoy - timedelta(days=i)
            for g in self.fetch_gacetas_dia(d.year, d.month, d.day):
                numero = g["numero_gaceta"]
                docs.append(
                    FiscalDocument(
                        source="gaceta",
                        title=f"Gaceta N° {numero} ({g.get('categoria', '')})",
                        url=f"{self.base_url}{g['ruta_archivo']}",
                        year=d.year,
                    )
                )
        logger.info("Gaceta: %d gacetas en los últimos %d días", len(docs), days)
        return docs