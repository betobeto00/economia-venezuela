"""
Collector SENIAT (Servicio Nacional Integrado de Administración Aduanera
y Tributaria)
=========================================================================

El portal del SENIAT publica avisos, gacetas, guías y boletines tributarios
y aduaneros (PDF/XLS). Al igual que CGR, se entrega el catálogo de
documentos (``FiscalDocument``) con su URL; el contenido del PDF no se
parsea (sin librería de PDFs).
"""

import logging
from typing import List, Optional

from src.collectors.fiscal.documents import find_documents
from src.collectors.http import http_get_text
from src.config import settings
from src.models.market import FiscalDocument

logger = logging.getLogger(__name__)

DOC_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx")
DOC_KEYWORDS = (
    "recaud", "gaceta", "aviso", "exoneraci", "arancel", "rentas",
)


class SENIATCollector:
    """Catálogo de documentos tributarios y aduaneros del SENIAT."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.SENIAT_BASE_URL).rstrip("/")

    def fetch_documents(self) -> List[FiscalDocument]:
        """Documentos fiscales localizados en la página principal."""
        html = http_get_text(self.base_url + "/")
        docs = find_documents(
            html, self.base_url, source="seniat",
            extensions=DOC_EXTENSIONS, keywords=DOC_KEYWORDS,
        )
        logger.info("SENIAT: %d documentos localizados", len(docs))
        return docs