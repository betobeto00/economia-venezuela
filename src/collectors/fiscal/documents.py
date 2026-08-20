"""
Utilidades compartidas de documentos fiscales
==============================================

Extrae el catálogo de documentos (PDF/XLS/...) de una página de una fuente
fiscal gubernamental (CGR, SENIAT, MPPEF). El texto visible del enlace se usa
como título y se intenta adivinar el año del documento.
"""

import re
from typing import List
from urllib.parse import unquote, urlparse

from bs4 import BeautifulSoup

from src.models.market import FiscalDocument

YEAR_RE = re.compile(r"\b(20\d{2})\b")

# Extensiones y palabras clave por defecto (CGR/ONAPRE)
DEFAULT_EXTENSIONS = (".pdf", ".doc", ".docx")
DEFAULT_KEYWORDS = ("informe", "gestión", "gestion", "actuación", "actuacion", "memoria")


def _title_from_href(href: str) -> str:
    """Título de respaldo derivado del nombre de archivo de la URL."""
    path = unquote(urlparse(href).path)
    filename = path.rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"(?i)\.(pdf|docx?|xlsx?)$", "", filename)
    return " ".join(name.replace("_", " ").replace("-", " ").split())


def find_documents(html: str, base_url: str, source: str = "cgr",
                   extensions: tuple = DEFAULT_EXTENSIONS,
                   keywords: tuple = DEFAULT_KEYWORDS) -> List[FiscalDocument]:
    """Documentos fiscales con título y URL absoluta desde el HTML."""
    soup = BeautifulSoup(html, "html.parser")
    base_host = urlparse(base_url).netloc
    docs: List[FiscalDocument] = []
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href or href == "#" or href.startswith("javascript:"):
            continue
        title = " ".join(link.get_text(" ", strip=True).split())
        if not title:
            title = _title_from_href(href)
        lower = (title + " " + href).lower()
        is_doc = lower.endswith(extensions) or any(k in lower for k in keywords)
        if not is_doc or not title:
            continue
        absolute = (
            href if href.startswith("http") else base_url.rstrip("/") + "/" + href.lstrip("/")
        )
        if urlparse(absolute).netloc != base_host:
            continue
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