"""
Datos fiscales para el dashboard
================================

Capa pura (sin Streamlit) que expone documentos fiscales recientes
(Gaceta Oficial, Asamblea Nacional, etc.) para la sección del dashboard.

Incluye contenido OCR de .md files en data/ocr/.
"""

import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OCR_DIR = PROJECT_ROOT / "data" / "ocr"


def recent_gacetas(days: int = 30, limit: int = 20) -> List[dict]:
    """Gacetas Oficiales recientes del índice (sin sumarios)."""
    try:
        from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector
        collector = GacetaOficialCollector()
        docs = collector.fetch_recientes(days=days)
        return [
            {
                "date": d.date,
                "year": d.year,
                "title": d.title,
                "url": d.url,
                "source": "gaceta",
            }
            for d in docs[:limit]
        ]
    except Exception as exc:  # noqa: BLE001
        logger.debug("recent_gacetas no disponible: %s", exc)
        return []


def enriched_gacetas(days: int = 30, limit: int = 10) -> List[dict]:
    """Gacetas con sumarios enriquecidos (filtradas por impacto económico)."""
    try:
        from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector
        collector = GacetaOficialCollector()
        docs = collector.fetch_recientes(days=days)
        enriched = collector.enrich_con_sumarios(docs, max_docs=limit)
        return [
            {
                "date": d.date,
                "year": d.year,
                "title": d.title,
                "url": d.url,
                "description": d.description,
                "source": "gaceta",
            }
            for d in enriched
        ]
    except Exception as exc:  # noqa: BLE001
        logger.debug("enriched_gacetas no disponible: %s", exc)
        return []


def recent_leyes(limit: int = 10) -> List[dict]:
    """Leyes y actos recientes de la Asamblea Nacional."""
    try:
        from src.collectors.fiscal.an_collector import ANCollector
        collector = ANCollector()
        docs = collector.fetch_documentos(keywords="", max_pages=2)
        return [
            {
                "title": d.title,
                "url": d.url,
                "year": d.year,
                "date": d.date,
                "source": "an",
            }
            for d in docs[:limit]
        ]
    except Exception as exc:  # noqa: BLE001
        logger.debug("recent_leyes no disponible: %s", exc)
        return []


def load_ocr_gacetas() -> List[dict]:
    """Carga gacetas procesadas con OCR desde .md files."""
    gacetas_dir = OCR_DIR / "gacetas" / "2026"
    if not gacetas_dir.exists():
        return []

    results = []
    for md_file in sorted(gacetas_dir.glob("*.md"), reverse=True):
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse frontmatter
            meta = {}
            text = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    text = parts[2]
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            key = key.strip()
                            val = val.strip()
                            if key == "categories":
                                try:
                                    meta[key] = json.loads(val)
                                except Exception:
                                    meta[key] = []
                            elif key in ("ocr_chars", "confidence"):
                                try:
                                    meta[key] = float(val)
                                except Exception:
                                    meta[key] = val
                            else:
                                meta[key] = val

            # Get preview (first 300 chars of text)
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            preview = " ".join(lines[2:8])[:300] if len(lines) > 2 else text[:300]

            results.append({
                "filename": md_file.name,
                "number": meta.get("number", md_file.stem),
                "date": meta.get("date", ""),
                "categories": meta.get("categories", []),
                "ocr_chars": meta.get("ocr_chars", 0),
                "confidence": meta.get("confidence", 0),
                "preview": preview,
                "full_text": text[:2000],  # First 2000 chars for expander
            })
        except Exception as exc:
            logger.debug("Error loading %s: %s", md_file, exc)

    return results


def load_ocr_bvc() -> List[dict]:
    """Carga documentos BVC procesados con OCR desde .md files."""
    bvc_dir = OCR_DIR / "bvc" / "2026"
    if not bvc_dir.exists():
        return []

    results = []
    for md_file in sorted(bvc_dir.glob("*.md")):
        try:
            content = md_file.read_text(encoding="utf-8")

            # Parse frontmatter
            meta = {}
            text = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    fm_text = parts[1]
                    text = parts[2]
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            meta[key.strip()] = val.strip()

            # Get preview
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            preview = " ".join(lines[2:6])[:200] if len(lines) > 2 else text[:200]

            # Determine document type
            text_lower = text.lower()
            if "capitalizacion" in text_lower:
                doc_type = "Capitalización"
            elif "acciones" in text_lower or "circulacion" in text_lower:
                doc_type = "Acciones"
            elif "bono" in text_lower or "deuda" in text_lower:
                doc_type = "Bonos/Deuda"
            elif "reglamento" in text_lower:
                doc_type = "Reglamento"
            elif "letra" in text_lower or "tesoro" in text_lower:
                doc_type = "Letras del Tesoro"
            elif "papel" in text_lower:
                doc_type = "Papeles Comerciales"
            else:
                doc_type = "Otro"

            results.append({
                "filename": md_file.name,
                "doc_type": doc_type,
                "preview": preview,
                "chars": len(text),
            })
        except Exception as exc:
            logger.debug("Error loading %s: %s", md_file, exc)

    return results


def fiscal_summary() -> dict:
    """Resumen del estado de las fuentes fiscales."""
    gacetas = recent_gacetas(days=7, limit=5)
    leyes = recent_leyes(limit=5)
    ocr_gacetas = load_ocr_gacetas()
    ocr_bvc = load_ocr_bvc()

    return {
        "gacetas_count": len(gacetas),
        "leyes_count": len(leyes),
        "gacetas": gacetas,
        "leyes": leyes,
        "ocr_gacetas": ocr_gacetas,
        "ocr_bvc": ocr_bvc,
        "ocr_total_chars": sum(g.get("ocr_chars", 0) for g in ocr_gacetas),
    }