"""
Collector MPPEF (Ministerio del Poder Popular de Economía y Finanzas)
=====================================================================

Publica documentos de política económica y fiscal (informes, gacetas,
comunicados) en su portal (WordPress). Se entrega el catálogo de documentos
(``FiscalDocument``) con su URL para descarga y posterior procesamiento.
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
    "presupuesto", "ejecuci", "finanza", "fiscal", "gaceta", "informe",
    "memoria", "recaud", "deuda",
)


class MPPEFCollector:
    """Catálogo de documentos económicos y fiscales del MPPEF."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.MPPEF_BASE_URL).rstrip("/")

    def fetch_documents(self) -> List[FiscalDocument]:
        """Documentos fiscales localizados en la página principal."""
        html = http_get_text(self.base_url + "/")
        docs = find_documents(
            html, self.base_url, source="mppef",
            extensions=DOC_EXTENSIONS, keywords=DOC_KEYWORDS,
        )
        logger.info("MPPEF: %d documentos localizados", len(docs))
        return docs