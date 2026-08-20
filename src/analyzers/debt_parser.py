"""
Parser de datos de Deuda Pública desde archivos OCR (.md)
==========================================================

Extrae información estructurada de los documentos OCR de la BVC:
- Bonos de la Deuda Pública Nacional (DPN)
- Letras del Tesoro
- Bonos BCV, PDVSA, gubernamentales
- Instrumentos de renta fija

Los documentos están en data/ocr/bvc/ con frontmatter YAML.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OCR_DIR = PROJECT_ROOT / "data" / "ocr" / "bvc" / "2026"


@dataclass
class DebtEmission:
    """Una emisión de deuda pública."""
    code: str = ""  # Código ISIN o SIBE
    isin: str = ""  # Código ISIN
    sibe: str = ""  # Código SIBE
    decree_date: str = ""  # Fecha del decreto
    amount_bs: float = 0.0  # Monto en Bs
    rate_type: str = ""  # Tasa Fija, LT + X%, etc.
    base_rate: str = ""  # Dias Transcurridos, etc.
    payment_frequency: str = ""  # Cada 91 dias, etc.
    start_date: str = ""  # Fecha de inicio
    maturity_date: str = ""  # Fecha de vencimiento
    source_doc: str = ""  # Documento de origen


@dataclass
class DebtSummary:
    """Resumen de deuda pública extraído de documentos OCR."""
    total_emissions: int = 0
    total_amount_bs: float = 0.0
    fixed_rate_count: int = 0
    floating_rate_count: int = 0
    emissions: List[DebtEmission] = field(default_factory=list)
    documents_used: List[str] = field(default_factory=list)
    source: str = "BVC/OCR"


def _parse_bs_amount(text: str) -> float:
    """Parsea un monto en Bs (1.234.567.890,00) a float."""
    if not text:
        return 0.0
    # Remove non-numeric except . , -
    cleaned = re.sub(r"[^\d.,\-]", "", text)
    if not cleaned:
        return 0.0
    # Handle European format: 1.234.567.890,00
    if "," in cleaned and "." in cleaned:
        if cleaned.index(",") < cleaned.index("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts) == 2 and len(parts[1]) <= 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_rate_type(text: str) -> str:
    """Extrae el tipo de tasa del texto."""
    text_lower = text.lower()
    if "tasa fija" in text_lower or "tasfija" in text_lower.replace(" ", ""):
        return "Tasa Fija"
    if "l.t." in text_lower or "lt." in text_lower:
        # Extract spread: "L.T. + 9.50"
        m = re.search(r"[lL]\.?[tT]\.\s*\+?\s*([\d.,]+)", text)
        if m:
            return f"LT + {m.group(1)}%"
        return "LT + spread"
    if "tam" in text_lower:
        return "TAM"
    return text.strip()[:30] if text.strip() else "Desconocido"


def parse_dpn_ocr(text: str) -> DebtSummary:
    """Parsea el texto OCR de Bonos de Deuda Pública Nacional.

    Args:
        text: Texto extraído del PDF (después del frontmatter).

    Returns:
        DebtSummary con las emisiones extraídas.
    """
    summary = DebtSummary(source="BVC/OCR - DPN")
    emissions = []

    # Pattern for DPN lines:
    # CA XXXXX | ISIN | SIBE | Decreto | Fecha | Monto | Tipo | Base | Freq | Inicio
    # Example: CA Daiore rroaore | DPaSos6B6-0013 | 17/07/2008 | 703.514.116.568 | TasaFija | ...

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue

        # Try to match DPN emission pattern
        # Look for lines with "CA" prefix and amounts
        if not re.search(r"CA\s+\d", line) and "DPBS" not in line.upper():
            continue

        # Extract components
        emission = DebtEmission(source_doc="dpn.md")

        # Extract ISIN code
        isin_match = re.search(r"(VEVO?\d{4}[A-Z]{3})", line)
        if isin_match:
            emission.isin = isin_match.group(1)

        # Extract SIBE code
        sibe_match = re.search(r"(DPBS?\d{6}-\d{3})", line, re.IGNORECASE)
        if sibe_match:
            emission.sibe = sibe_match.group(1)

        # Extract date (DD/MM/YYYY)
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", line)
        if dates:
            emission.decree_date = dates[0]
            if len(dates) > 1:
                emission.maturity_date = dates[-1]

        # Extract amount (look for large numbers with dots/commas)
        amounts = re.findall(r"[\d.]+,\d{2}", line)
        if amounts:
            # Take the largest amount
            parsed_amounts = [_parse_bs_amount(a) for a in amounts]
            emission.amount_bs = max(parsed_amounts) if parsed_amounts else 0

        # Extract rate type
        if "Tasa Fija" in line or "TasaFija" in line.replace(" ", ""):
            emission.rate_type = "Tasa Fija"
        elif "L.T." in line or "LT." in line:
            m = re.search(r"[lL]\.?[tT]\.\s*\+?\s*([\d.,]+)", line)
            if m:
                emission.rate_type = f"LT + {m.group(1)}%"
            else:
                emission.rate_type = "LT + spread"
        elif "TAM" in line.upper():
            emission.rate_type = "TAM"

        # Extract payment frequency
        if "91 dias" in line.lower() or "91dias" in line.lower():
            emission.payment_frequency = "Cada 91 días"

        # Only add if we found meaningful data
        if emission.sibe or emission.isin:
            emission.code = emission.sibe or emission.isin
            emissions.append(emission)

    # Build summary
    summary.emissions = emissions
    summary.total_emissions = len(emissions)
    summary.total_amount_bs = sum(e.amount_bs for e in emissions)
    summary.fixed_rate_count = sum(1 for e in emissions if e.rate_type == "Tasa Fija")
    summary.floating_rate_count = summary.total_emissions - summary.fixed_rate_count
    summary.documents_used = ["dpn.md"]

    logger.info(
        "DPN parseado: %d emisiones, $%.0f Bs total, %d tasa fija, %d variable",
        summary.total_emissions,
        summary.total_amount_bs,
        summary.fixed_rate_count,
        summary.floating_rate_count,
    )

    return summary


def parse_bills_ocr(text: str) -> DebtSummary:
    """Parsea el texto OCR de Letras del Tesoro.

    Args:
        text: Texto extraído del PDF.

    Returns:
        DebtSummary con las emisiones de Letras del Tesoro.
    """
    summary = DebtSummary(source="BVC/OCR - Letras del Tesoro")
    emissions = []

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("---"):
            continue

        # Look for LT lines with dates and rates
        if "LT" not in line and "VEV" not in line.upper():
            continue

        emission = DebtEmission(source_doc="bills.md")

        # Extract ISIN
        isin_match = re.search(r"(VEV\d{4}[A-Z]{3})", line, re.IGNORECASE)
        if isin_match:
            emission.isin = isin_match.group(1)

        # Extract dates
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", line)
        if dates:
            emission.decree_date = dates[0]
            if len(dates) > 1:
                emission.maturity_date = dates[-1]

        # Extract rate (percentage)
        rate_match = re.search(r"([\d.,]+)%", line)
        if rate_match:
            emission.rate_type = f"{rate_match.group(1)}%"

        # Extract LT code
        lt_match = re.search(r"(LT\d{6})", line)
        if lt_match:
            emission.code = lt_match.group(1)

        if emission.code or emission.isin:
            emissions.append(emission)

    summary.emissions = emissions
    summary.total_emissions = len(emissions)
    summary.documents_used = ["bills.md"]

    return summary


def load_all_debt_data() -> Dict[str, DebtSummary]:
    """Carga y parsea todos los documentos de deuda del directorio OCR.

    Returns:
        Dict con el resumen de cada tipo de deuda.
    """
    results = {}

    # Parse DPN
    dpn_path = OCR_DIR / "dpn.md"
    if dpn_path.exists():
        text = dpn_path.read_text(encoding="utf-8")
        # Remove frontmatter
        if "---" in text:
            text = text.split("---", 2)[-1]
        results["dpn"] = parse_dpn_ocr(text)

    # Parse Bills
    bills_path = OCR_DIR / "bills.md"
    if bills_path.exists():
        text = bills_path.read_text(encoding="utf-8")
        if "---" in text:
            text = text.split("---", 2)[-1]
        results["bills"] = parse_bills_ocr(text)

    # Parse other debt documents
    for doc_name in ["bcv", "pdvsa", "goverment", "export", "dpn-ticc"]:
        doc_path = OCR_DIR / f"{doc_name}.md"
        if doc_path.exists():
            text = doc_path.read_text(encoding="utf-8")
            if "---" in text:
                text = text.split("---", 2)[-1]
            summary = DebtSummary(source=f"BVC/OCR - {doc_name.upper()}")
            # Simple extraction for smaller docs
            lines = text.split("\n")
            for line in lines:
                line = line.strip()
                if line and not line.startswith("#"):
                    emission = DebtEmission(
                        source_doc=f"{doc_name}.md",
                        code=line[:50],
                    )
                    summary.emissions.append(emission)
            summary.total_emissions = len(summary.emissions)
            results[doc_name] = summary

    # Parse renta fija
    rf_path = OCR_DIR / "INSTRUMENTOS-DE-RENTA-FIJA.md"
    if rf_path.exists():
        text = rf_path.read_text(encoding="utf-8")
        if "---" in text:
            text = text.split("---", 2)[-1]
        summary = DebtSummary(source="BVC/OCR - Renta Fija")
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if "VEV" in line.upper() or "ISIN" in line.upper():
                emission = DebtEmission(source_doc="INSTRUMENTOS-DE-RENTA-FIJA.md")
                isin_match = re.search(r"(VEV\d{4}[A-Z]{3})", line, re.IGNORECASE)
                if isin_match:
                    emission.isin = isin_match.group(1)
                    emission.code = emission.isin
                    summary.emissions.append(emission)
        summary.total_emissions = len(summary.emissions)
        results["renta_fija"] = summary

    return results


def get_debt_totals() -> Dict:
    """Obtiene totales consolidados de deuda desde los datos OCR.

    Returns:
        Dict con totales y desglose.
    """
    all_data = load_all_debt_data()

    total_emissions = sum(d.total_emissions for d in all_data.values())
    total_amount_bs = sum(d.total_amount_bs for d in all_data.values())
    fixed_count = sum(d.fixed_rate_count for d in all_data.values())

    return {
        "total_emissions": total_emissions,
        "total_amount_bs": total_amount_bs,
        "fixed_rate_count": fixed_count,
        "floating_rate_count": total_emissions - fixed_count,
        "documents": {k: v.total_emissions for k, v in all_data.items()},
        "source": "BVC/OCR",
    }
