"""
OCR y extracción de texto de Gacetas Oficiales
===============================================

Extrae texto de PDFs de la Gaceta Oficial y clasifica automáticamente
si un decreto afecta: aranceles, impuestos (IGTF), exoneraciones, etc.

Flujo:
1. Intentar extracción de texto directa (pdfplumber) — más rápido
2. Si el texto es muy corto (PDF escaneado), usar OCR (pytesseract)
3. Clasificar el contenido con keywords y expresiones regulares
"""

import logging
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Keywords para clasificación de decretos
CLASIFICACION_KEYWORDS = {
    "aranceles": [
        "arancel", "aranceles", "derechos de importación",
        "derechos de exportación", "tarifa", "clasificación arancelaria",
    ],
    "impuestos": [
        "igtf", "impuesto", "iva", "islr", "renta",
        "retención", "contribución", "gravamen",
    ],
    "exoneraciones": [
        "exoneración", "exento", "exención", "libre de impuestos",
        "beneficio fiscal", "incentivo fiscal",
    ],
    "presupuesto": [
        "presupuesto", "aprobación", "crédito adicional",
        "transferencia", "reformado presupuestario",
    ],
    "laboral": [
        "salario", "mínimo", "trabajador", "empleo",
        "nómina", "prestación", "beneficio social",
    ],
    "petrolero": [
        "petróleo", "petrolero", "pdvsa", "hidrocarburos",
        "producción", "exportación", "refinación",
    ],
    "comercial": [
        "comercio", "importación", "exportación", "comercial",
        "mercantil", "empresa", "sociedad",
    ],
}


@dataclass
class GacetaClassification:
    """Resultado de la clasificación de una Gaceta Oficial."""
    text_preview: str = ""
    categories: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_text_length: int = 0
    method: str = "pdfplumber"  # o "ocr"


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF usando pdfplumber, con fallback a OCR.

    Args:
        pdf_bytes: Contenido del PDF en bytes.

    Returns:
        Texto extraído (puede estar vacío si falla).
    """
    # 1. Intentar extracción directa con pdfplumber
    text = ""
    try:
        import pdfplumber
        import io

        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        text = "\n".join(text_parts)
    except Exception as exc:
        logger.debug("pdfplumber falló: %s", exc)

    # 2. Si el texto es muy corto, intentar OCR
    if len(text.strip()) < 100:
        logger.info("PDF escaneado detectado (%d chars), intentando OCR...", len(text))
        ocr_text = extract_text_ocr(pdf_bytes)
        if len(ocr_text) > len(text):
            text = ocr_text

    return text


def _find_tesseract_cmd() -> Optional[str]:
    """Encuentra el ejecutable de Tesseract en el sistema."""
    import shutil
    import sys

    # Intentar encontrar tesseract en PATH
    tesseract = shutil.which("tesseract")
    if tesseract:
        return tesseract

    # Windows: buscar en ubicaciones comunes
    if sys.platform == "win32":
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in possible_paths:
            if os.path.exists(path):
                return path

    return None


def extract_text_ocr(pdf_bytes: bytes) -> str:
    """Extrae texto de un PDF escaneado usando OCR.

    Requiere: pip install pytesseract Pillow
    Y: Tesseract OCR instalado en el sistema.

    Args:
        pdf_bytes: Contenido del PDF en bytes.

    Returns:
        Texto extraído por OCR.
    """
    try:
        import pytesseract
        from PIL import Image
        import io

        # Configurar ruta de Tesseract
        tesseract_cmd = _find_tesseract_cmd()
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

        # Convertir PDF a imágenes y hacer OCR
        images = []
        try:
            # Intentar con PyMuPDF primero (no necesita poppler)
            import pymupdf
            doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
            for i, page in enumerate(doc):
                if i >= 5:  # Limitar a 5 páginas
                    break
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                images.append(img)
            logger.info("PDF convertido a %d imágenes con PyMuPDF", len(images))
        except Exception as exc_pymupdf:
            logger.debug("PyMuPDF falló: %s, intentando pdf2image", exc_pymupdf)
            try:
                from pdf2image import convert_from_bytes
                images = convert_from_bytes(pdf_bytes, dpi=150, first_page=1, last_page=5)
                logger.info("PDF convertido a %d imágenes con pdf2image", len(images))
            except Exception as exc_p2i:
                logger.warning("Ni pdf2image ni PyMuPDF funcionan: %s / %s", exc_pymupdf, exc_p2i)
                return ""

        text_parts = []
        for i, img in enumerate(images):
            # Usar español + inglés para mejor detección
            text = pytesseract.image_to_string(img, lang="spa+eng")
            if text.strip():
                text_parts.append(text)
            if i % 2 == 0:
                logger.info("OCR: página %d/%d procesada", i + 1, len(images))

        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pytesseract no instalado. Ejecuta: pip install pytesseract Pillow")
        return ""
    except Exception as exc:
        logger.warning("OCR falló: %s", exc)
        return ""


def classify_gaceta(text: str) -> GacetaClassification:
    """Clasifica el contenido de una Gaceta Oficial.

    Args:
        text: Texto extraído de la gaceta.

    Returns:
        GacetaClassification con categorías detectadas.
    """
    text_lower = text.lower()
    categories = []

    for category, keywords in CLASIFICACION_KEYWORDS.items():
        matches = sum(1 for kw in keywords if kw in text_lower)
        if matches >= 2:  # Al menos 2 keywords para clasificar
            categories.append(category)

    # Calcular confianza
    total_keywords = sum(len(v) for v in CLASIFICACION_KEYWORDS.values())
    matched = sum(
        1 for cats in CLASIFICACION_KEYWORDS.values()
        for kw in cats if kw in text_lower
    )
    confidence = min(matched / max(total_keywords * 0.1, 1), 1.0)

    # Preview del texto (primeros 500 chars)
    preview = text[:500].strip()
    if len(text) > 500:
        preview += "..."

    return GacetaClassification(
        text_preview=preview,
        categories=categories,
        confidence=confidence,
        raw_text_length=len(text),
        method="pdfplumber",
    )


def process_gaceta_pdf(pdf_bytes: bytes, use_ocr: bool = True) -> GacetaClassification:
    """Procesa un PDF de Gaceta Oficial: extrae texto y clasifica.

    Args:
        pdf_bytes: Contenido del PDF.
        use_ocr: Si True, usa OCR como fallback para PDFs escaneados.

    Returns:
        GacetaClassification con el resultado.
    """
    # 1. Intentar extracción directa
    text = extract_text_from_pdf(pdf_bytes)

    # 2. Si el texto es muy corto, intentar OCR
    if len(text.strip()) < 100 and use_ocr:
        logger.info("Texto extraído muy corto (%d chars), intentando OCR...", len(text))
        ocr_text = extract_text_ocr(pdf_bytes)
        if len(ocr_text) > len(text):
            text = ocr_text

    # 3. Clasificar
    classification = classify_gaceta(text)
    if len(text.strip()) < 100:
        classification.method = "none"

    return classification
