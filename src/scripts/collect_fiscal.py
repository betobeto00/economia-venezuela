"""Ingesta de Gacetas Oficiales con OCR (fiscal)
==============================================

Cierra el hueco fiscal: hasta ahora el pipeline de OCR existía
(``gaceta_collector`` + ``gaceta_ocr`` + ``cache.manager``) pero no había un
job que lo ejecutara de punta a punta, así que la ingesta dependía de algo
manual y el dashboard leía solo los .md que ya estuvieran en disco.

Qué hace, por cada gaceta publicada en los últimos ``days`` días:

1. Descarga el PDF con dedup por hash (``download_pdf``).
2. Extrae el texto: directo con pdfplumber/pymupdf y OCR (tesseract) como
   respaldo para escaneos.
3. Guarda ``data/ocr/gacetas/<año>/<numero>.md`` con frontmatter y registra la
   entrada en ``data/ocr/index.json`` (el dashboard y los informes leen de ahí).

Uso:
    python -m src.scripts.collect_fiscal [--days 7] [--limit 10] [--force] [--json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Dict, List, Optional

from src.config import settings

logger = logging.getLogger(__name__)

DEFAULT_DAYS = 7
DEFAULT_LIMIT = 10


def _filename_from_url(url: str) -> str:
    """``.../43437-2026-08-14-ORDINARIA.pdf`` → ``43437-2026-08-14-ORDINARIA``."""
    base = url.rstrip("/").rsplit("/", 1)[-1]
    return base[:-4] if base.lower().endswith(".pdf") else base


def _metadata(doc, filename: str) -> Dict:
    """Frontmatter de la gaceta (número, tipo y fecha)."""
    parts = filename.split("-")
    return {
        "number": parts[0] if parts else filename,
        "type": parts[-1] if len(parts) >= 4 else "",
        "date": doc.date.isoformat() if getattr(doc, "date", None) else "",
    }


def collect_fiscal(
    days: int = DEFAULT_DAYS,
    limit: int = DEFAULT_LIMIT,
    force: bool = False,
    collector=None,
) -> Dict[str, int]:
    """Descarga, hace OCR y registra las gacetas recientes.

    Args:
        days: Ventana hacia atrás para buscar gacetas publicadas.
        limit: Máximo de documentos a procesar (el OCR es caro).
        force: Re-procesa aunque el PDF ya esté en el índice.
        collector: Collector inyectable (tests).

    Returns:
        Resumen con ``found``, ``downloaded``, ``processed``, ``skipped`` y
        ``failed``.
    """
    from src.cache.manager import download_pdf, process_and_save_ocr
    from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector

    collector = collector or GacetaOficialCollector()
    summary = {"found": 0, "downloaded": 0, "processed": 0, "skipped": 0, "failed": 0}

    try:
        docs = collector.fetch_recientes(days=days)
    except Exception as exc:  # noqa: BLE001 - fuente externa caída
        logger.error("Gaceta: no se pudo consultar el índice: %s", exc)
        return summary

    summary["found"] = len(docs)
    for doc in docs[: max(1, limit)]:
        filename = _filename_from_url(doc.url)
        try:
            path = download_pdf(
                doc.url,
                source="gacetas",
                filename=f"{filename}.pdf",
                year=getattr(doc, "year", None),
                force=force,
            )
            if path is None:
                summary["failed"] += 1
                continue
            summary["downloaded"] += 1
            md_path = process_and_save_ocr(
                path.read_bytes(),
                pdf_url=doc.url,
                source="gacetas",
                filename=filename,
                year=getattr(doc, "year", None),
                metadata=_metadata(doc, filename),
                force=force,
            )
            if md_path is None:
                summary["skipped"] += 1
            else:
                summary["processed"] += 1
        except Exception as exc:  # noqa: BLE001 - un PDF roto no tumba el job
            logger.warning("Gaceta %s falló: %s", filename, exc)
            summary["failed"] += 1

    logger.info(
        "Gacetas: %d encontradas, %d descargadas, %d procesadas, %d sin cambios, %d fallidas",
        summary["found"], summary["downloaded"], summary["processed"],
        summary["skipped"], summary["failed"],
    )
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Ingesta de gacetas con OCR")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"Ventana en días (default: {DEFAULT_DAYS})")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Máximo de documentos (default: {DEFAULT_LIMIT})")
    parser.add_argument("--force", action="store_true", help="Re-procesar aunque exista")
    parser.add_argument("--json", action="store_true", help="Resumen en JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logger.info("Base de gacetas: %s", settings.GACETA_OFICIAL_BASE_URL)

    summary = collect_fiscal(days=args.days, limit=args.limit, force=args.force)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"Ingesta fiscal completada: {summary}")
    # Un fallo total (nada encontrado) no debe parecer éxito
    return 0 if summary["found"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
