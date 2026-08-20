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
from typing import List, Optional

from src.collectors.fiscal.documents import find_documents
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import FiscalDocument

logger = logging.getLogger(__name__)

DOC_EXTENSIONS = (".pdf", ".doc", ".docx")
DOC_KEYWORDS = ("informe", "gestión", "gestion", "actuación", "actuacion", "memoria")


class CGRCollector:
    """Catálogo de informes de gestión de la Contraloría General."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.CGR_BASE_URL).rstrip("/")

    def fetch_documents(self) -> List[FiscalDocument]:
        """Informes de gestión localizados en la página principal."""
        html = http_get_text(self.base_url + "/")
        docs = find_documents(html, self.base_url, source="cgr",
                              extensions=DOC_EXTENSIONS, keywords=DOC_KEYWORDS)
        logger.info("CGR: %d documentos localizados", len(docs))
        return docs