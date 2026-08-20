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
    """Extrae texto de un PDF usando pdfplumber.

    Args:
        pdf_bytes: Contenido del PDF en bytes.

    Returns:
        Texto extraído (puede estar vacío si es PDF escaneado).
    """
    try:
        import pdfplumber
        import io

        text_parts = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as exc:
        logger.debug("pdfplumber falló: %s", exc)
        return ""


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

        # Convertir PDF a imágenes y hacer OCR
        try:
            from pdf2image import convert_from_bytes
            images = convert_from_bytes(pdf_bytes, dpi=300)
        except ImportError:
            # Fallback: usar PyMuPDF
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                images = []
                for page in doc:
                    pix = page.get_pixmap(dpi=300)
                    img = Image.open(io.BytesIO(pix.tobytes("png")))
                    images.append(img)
            except ImportError:
                logger.warning("Ni pdf2image ni PyMuPDF disponibles para OCR")
                return ""

        text_parts = []
        for img in images:
            text = pytesseract.image_to_string(img, lang="spa")
            if text.strip():
                text_parts.append(text)

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
