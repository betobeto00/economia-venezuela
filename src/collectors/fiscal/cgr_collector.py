"""
Collector CGR (Contraloría General de la República)
====================================================

Publica informes de gestión y actuaciones fiscales (PDF) en su sitio.
Estrategia similar a ONAPRE: localizar enlaces a documentos, extraer el
título y el año, y devolver ``FiscalDocument``.

No se parsea el contenido del PDF (sin librería de PDFs); se entrega el
catálogo de documentos con su URL para descarga y posterior procesamiento.
"""

import logging
import re
from typing import List, Optional

from bs4 import BeautifulSoup

from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import FiscalDocument

logger = logging.getLogger(__name__)

DOC_EXTENSIONS = (".pdf", ".doc", ".docx")
DOC_KEYWORDS = ("informe", "gestión", "gestion", "actuación", "actuacion", "memoria")

YEAR_RE = re.compile(r"\b(20\d{2})\b")


def find_documents(html: str, base_url: str, source: str = "cgr") -> List[FiscalDocument]:
    """Documentos fiscales con título y URL absoluta desde el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    docs: List[FiscalDocument] = []
    for link in soup.find_all("a", href=True):
        href = link["href"]
        title = " ".join(link.get_text(" ", strip=True).split())
        lower = (title + " " + href).lower()
        is_doc = lower.endswith(DOC_EXTENSIONS) or any(
            k in lower for k in DOC_KEYWORDS
        )
        if not is_doc or not title:
            continue
        absolute = (
            href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        )
        year_match = YEAR_RE.search(title)
        docs.append(
            FiscalDocument(
                source=source,
                title=title[:300],
                url=absolute,
                year=int(year_match.group(1)) if year_match else None,
            )
        )
    return docs


class CGRCollector:
    """Catálogo de informes de gestión de la Contraloría General."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.CGR_BASE_URL).rstrip("/")

    def fetch_documents(self) -> List[FiscalDocument]:
        """Informes de gestión localizados en la página principal."""
        html = http_get_text(self.base_url + "/")
        docs = find_documents(html, self.base_url)
        logger.info("CGR: %d documentos localizados", len(docs))
        return docs