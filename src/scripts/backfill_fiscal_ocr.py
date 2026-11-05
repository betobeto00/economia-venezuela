"""OCR del archivo histórico de gacetas
=====================================

``collect_fiscal`` solo mira la ventana reciente: los PDF que ya están en
``data/pdfs/gacetas/<año>/`` pero no tienen su ``.md`` en
``data/ocr/gacetas/<año>/`` se quedaban sin procesar para siempre. Este job
recorre ese archivo, detecta los que faltan y los pasa por el mismo pipeline
de OCR (``process_and_save_ocr``), sin volver a descargar nada.

El emparejamiento es por número de gaceta, porque conviven dos convenciones de
nombre: ``43382.md`` (histórico) y ``43382-2026-05-25-ORDINARIA.md`` (actual).

Uso:
    python -m src.scripts.backfill_fiscal_ocr [--source gacetas] [--year 2026]
        [--limit 50] [--force] [--json]

Salida: ``0`` si no hubo fallos, ``1`` si algún PDF no se pudo procesar.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)

DEFAULT_SOURCE = "gacetas"
DEFAULT_LIMIT = 50

_STEM_RE = re.compile(
    r"^(?P<number>\d+)-(?P<date>\d{4}-\d{2}-\d{2})-(?P<type>[A-Za-z]+)$"
)


def _metadata_from_stem(stem: str) -> Dict[str, str]:
    """Frontmatter a partir del nombre del PDF.

    ``43437-2026-08-14-ORDINARIA`` → número, fecha y tipo. Los nombres antiguos
    (solo número) devuelven la fecha y el tipo vacíos en vez de fallar.
    """
    match = _STEM_RE.match(stem)
    if not match:
        return {"number": stem.split("-")[0], "date": "", "type": ""}
    return {
        "number": match["number"],
        "date": match["date"],
        "type": match["type"].upper(),
    }


def _existing_numbers(md_dir: Path) -> set:
    """Números de gaceta que ya tienen ``.md`` en ``md_dir``."""
    if not md_dir.exists():
        return set()
    return {md.stem.split("-")[0] for md in md_dir.glob("*.md")}


def _pdf_url(path: Path, manifest: Dict[str, Dict], base_url: str) -> str:
    """URL original del PDF (del manifest o reconstruida del patrón del sitio)."""
    try:
        rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    except ValueError:  # ruta fuera del proyecto (tests con tmp_path)
        rel = str(path).replace("\\", "/")
    for url, entry in manifest.items():
        if str(entry.get("filepath", "")).replace("\\", "/") == rel:
            return url
    return f"{base_url.rstrip('/')}/storage/{path.parent.name}/{path.name}"


def _pending(
    pdf_root: Path, ocr_root: Path, source: str, year: Optional[int], force: bool
) -> Tuple[List[Tuple[Path, int, Dict[str, str]]], int, int]:
    """PDFs sin ``.md``, total de PDFs revisados y cuántos ya estaban hechos."""
    base = pdf_root / source
    if not base.exists():
        return [], 0, 0

    years = [str(year)] if year else sorted(p.name for p in base.iterdir() if p.is_dir())
    pending: List[Tuple[Path, int, Dict[str, str]]] = []
    total = skipped = 0
    for y in years:
        pdf_dir = base / y
        if not pdf_dir.is_dir():
            continue
        done = set() if force else _existing_numbers(ocr_root / source / y)
        for pdf in sorted(pdf_dir.glob("*.pdf")):
            total += 1
            meta = _metadata_from_stem(pdf.stem)
            if meta["number"] in done:
                skipped += 1
                continue
            pending.append((pdf, int(y), meta))
    return pending, total, skipped


def backfill_ocr(
    source: str = DEFAULT_SOURCE,
    year: Optional[int] = None,
    limit: int = DEFAULT_LIMIT,
    force: bool = False,
    pdf_root: Optional[Path] = None,
    ocr_root: Optional[Path] = None,
) -> Dict[str, int]:
    """Procesa con OCR los PDFs del archivo que no tienen ``.md``.

    Args:
        source: Subcarpeta de ``data/pdfs`` (por defecto ``gacetas``).
        year: Limita a un año (por defecto, todos).
        limit: Máximo de PDFs a procesar en esta corrida.
        force: Re-procesa aunque el ``.md`` ya exista.
        pdf_root: Raíz de PDFs (inyectable en tests).
        ocr_root: Raíz de OCR (inyectable en tests).

    Returns:
        Resumen con ``pdfs``, ``missing``, ``processed``, ``skipped`` y
        ``failed``.
    """
    from src.cache.manager import load_manifest, process_and_save_ocr
    from src.config import settings

    pdf_root = pdf_root or PROJECT_ROOT / "data" / "pdfs"
    ocr_root = ocr_root or PROJECT_ROOT / "data" / "ocr"

    pending, total, skipped = _pending(pdf_root, ocr_root, source, year, force)
    summary = {
        "pdfs": total,
        "missing": len(pending),
        "processed": 0,
        "skipped": skipped,
        "failed": 0,
    }
    if not pending:
        logger.info("OCR histórico: archivo completo (%d PDFs, 0 pendientes)", total)
        return summary

    manifest = load_manifest()
    for pdf, pdf_year, meta in pending[: max(1, limit)]:
        try:
            md_path = process_and_save_ocr(
                pdf.read_bytes(),
                pdf_url=_pdf_url(pdf, manifest, settings.GACETA_OFICIAL_BASE_URL),
                source=source,
                filename=pdf.stem,
                year=pdf_year,
                metadata=meta,
                force=force,
            )
            if md_path is None:
                summary["skipped"] += 1
            else:
                summary["processed"] += 1
        except Exception as exc:  # noqa: BLE001 - un PDF roto no tumba el job
            logger.warning("OCR histórico falló en %s: %s", pdf.name, exc)
            summary["failed"] += 1

    logger.info(
        "OCR histórico: %d PDFs, %d pendientes, %d procesados, %d sin cambios, %d fallidos",
        summary["pdfs"], summary["missing"], summary["processed"],
        summary["skipped"], summary["failed"],
    )
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="OCR del archivo histórico de gacetas"
    )
    parser.add_argument("--source", default=DEFAULT_SOURCE,
                        help=f"Subcarpeta de data/pdfs (default: {DEFAULT_SOURCE})")
    parser.add_argument("--year", type=int, default=None,
                        help="Limitar a un año (default: todos)")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"Máximo de PDFs por corrida (default: {DEFAULT_LIMIT})")
    parser.add_argument("--force", action="store_true",
                        help="Re-procesar aunque el .md exista")
    parser.add_argument("--json", action="store_true", help="Resumen en JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    summary = backfill_ocr(
        source=args.source, year=args.year, limit=args.limit, force=args.force
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"OCR histórico completado: {summary}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
