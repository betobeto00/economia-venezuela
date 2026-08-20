"""
Datos de capitalización del mercado BVC desde archivos OCR
==========================================================

Parsea los archivos .md de capitalización para extraer:
- Capitalización por sector
- Variación mensual
- Tendencia histórica (ENERO→MAYO 2026)
"""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OCR_DIR = PROJECT_ROOT / "data" / "ocr" / "bvc" / "2026"


def _parse_bs_number(text: str) -> float:
    """Parsea número en formato BS (1.234.567.890,00)."""
    if not text:
        return 0.0
    cleaned = text.strip().replace(" ", "")
    # Remove non-numeric except . , -
    cleaned = re.sub(r"[^\d.,\-]", "", cleaned)
    if not cleaned:
        return 0.0
    # European format: dots = thousands, comma = decimal
    # 311.350.202.920,00 → 311350202920.00
    if "," in cleaned:
        parts = cleaned.split(",")
        integer_part = parts[0].replace(".", "")  # Remove thousands dots
        decimal_part = parts[1] if len(parts) > 1 else ""
        if decimal_part:
            cleaned = f"{integer_part}.{decimal_part}"
        else:
            cleaned = integer_part
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts) > 2:
            # Multiple dots = thousands separators
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_capitalization_md(filepath: Path) -> Dict:
    """Parsea un archivo .md de capitalización BVC.

    Returns:
        Dict con sector → {capitalization, share_pct, change_pct}
    """
    content = filepath.read_text(encoding="utf-8")

    # Remove frontmatter
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]

    sectors = {}
    lines = content.split("\n")

    # Known sector names (from BVC reports) - include OCR artifacts
    sector_names = [
        "Agricultura y Alimentos Procesados",
        "Agricuituray Alimentos Procesados",  # OCR typo
        "fAgricuituray Alimentos Procesados",  # OCR artifact
        "Bancos",
        "Bancario",
        "Industria Manufacturera y Construccion",
        "Industria Manufacturera",
        "Compañias de Bienes Inmuebles",
        "Companias de Bienes Inmuebles",
        "Compañías de Bienes Inmuebles",
        "Compaiiias de Bienes Inmuebles",  # OCR artifact
        "Otros Establecimientos Financieros",
        "Electricidad, Gas, Agua y Servicios",
        "Electricidad, Gas y Agua",
        "Petróleo",
        "Petrolero",
        "Comercio",
        "Servicios",
        "Telecomunicaciones",
        "Transporte",
        "Minería",
    ]

    current_sector = None
    sector_values = []
    waiting_for_values = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Check if line is a sector name
        is_sector = False
        for sn in sector_names:
            if sn.lower() in line.lower() and len(line) < 80:
                # Save previous sector
                if current_sector and sector_values:
                    total_val = sector_values[0] if sector_values else 0
                    sectors[current_sector] = {
                        "capitalization": total_val,
                        "values": sector_values,
                    }
                current_sector = line
                sector_values = []
                waiting_for_values = True  # Values will be on next lines
                is_sector = True
                # Check if values are on the same line (some formats)
                nums = re.findall(r"[\d.]+,\d{2}", line)
                for num_str in nums:
                    val = _parse_bs_number(num_str)
                    if val > 100_000:
                        sector_values.append(val)
                break

        # If not a sector and waiting for values, collect them
        if not is_sector and current_sector:
            nums = re.findall(r"[\d.]+,\d{2}", line)
            for num_str in nums:
                val = _parse_bs_number(num_str)
                if val > 100_000:  # At least 100K
                    sector_values.append(val)

    # Save last sector
    if current_sector and sector_values:
        total_val = sector_values[0] if sector_values else 0
        sectors[current_sector] = {
            "capitalization": total_val,
            "values": sector_values,
        }

    return sectors


def load_capitalization_history() -> List[Dict]:
    """Carga historial de capitalización desde todos los archivos .md disponibles.

    Returns:
        Lista de dicts ordenados por fecha, cada uno con month, total, sectors.
    """
    if not OCR_DIR.exists():
        return []

    cap_files = sorted(OCR_DIR.glob("CAPITALIZACION*.md"))

    history = []
    for f in cap_files:
        # Extract month from filename
        name = f.stem.upper()
        if "ENERO" in name:
            month = "2026-01"
        elif "FEBRERO" in name:
            month = "2026-02"
        elif "MARZO" in name:
            month = "2026-03"
        elif "ABRIL" in name:
            month = "2026-04"
        elif "MAYO" in name:
            month = "2026-05"
        elif "JUNIO" in name:
            month = "2026-06"
        else:
            month = name

        # Skip duplicate files (same month)
        if any(h["month"] == month for h in history):
            continue

        sectors = parse_capitalization_md(f)
        total = sum(s.get("capitalization", 0) for s in sectors.values())

        history.append({
            "month": month,
            "total": total,
            "sectors": sectors,
            "file": f.name,
        })

    return sorted(history, key=lambda x: x["month"])


def get_capitalization_summary() -> Dict:
    """Resumen de capitalización del mercado BVC.

    Returns:
        Dict con total, tendencia, sector principal, etc.
    """
    history = load_capitalization_history()

    if not history:
        return {"available": False}

    latest = history[-1]
    prev = history[-2] if len(history) > 1 else None

    # Calculate total change
    total_change = 0
    if prev and prev["total"] > 0:
        total_change = ((latest["total"] - prev["total"]) / prev["total"]) * 100

    # Find largest sector
    largest_sector = ""
    largest_value = 0
    for name, data in latest.get("sectors", {}).items():
        val = data.get("capitalization", 0)
        if val > largest_value:
            largest_value = val
            largest_sector = name

    # Sector breakdown for pie chart
    sector_breakdown = []
    total_cap = latest.get("total", 0)
    for name, data in latest.get("sectors", {}).items():
        val = data.get("capitalization", 0)
        pct = (val / total_cap * 100) if total_cap > 0 else 0
        sector_breakdown.append({
            "sector": name,
            "capitalization": val,
            "percentage": round(pct, 1),
        })
    sector_breakdown.sort(key=lambda x: x["capitalization"], reverse=True)

    # Sector history: each sector's cap across months
    all_sectors = set()
    for h in history:
        all_sectors.update(h.get("sectors", {}).keys())

    sector_history = {}
    for sname in all_sectors:
        series = []
        for h in history:
            sdata = h.get("sectors", {}).get(sname, {})
            series.append({
                "month": h["month"],
                "capitalization": sdata.get("capitalization", 0),
            })
        sector_history[sname] = series

    return {
        "available": True,
        "latest_month": latest["month"],
        "total_bs": latest["total"],
        "total_change_pct": round(total_change, 2),
        "largest_sector": largest_sector,
        "largest_sector_bs": largest_value,
        "months_available": len(history),
        "history": [{"month": h["month"], "total": h["total"]} for h in history],
        "sector_breakdown": sector_breakdown,
        "sector_history": sector_history,
    }
