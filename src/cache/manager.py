"""
Cache Manager — Gestión centralizada de caché de datos
======================================================

Maneja:
- PDFs descargados (dedup por hash SHA256)
- Resultados OCR (.md con frontmatter YAML)
- Respuestas de APIs (TTL configurable)
- Estadísticas y garbage collection

Estructura:
  data/pdfs/{fuente}/{year}/{filename}.pdf
  data/ocr/{fuente}/{year}/{filename}.md
  data/cache/api/{endpoint}.json
  data/pdfs/manifest.json  →  hash → metadata
  data/ocr/index.json      →  list of processed files
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PDF_DIR = DATA_DIR / "pdfs"
OCR_DIR = DATA_DIR / "ocr"
CACHE_DIR = DATA_DIR / "cache"
MANIFEST_PATH = PDF_DIR / "manifest.json"
OCR_INDEX_PATH = OCR_DIR / "index.json"


def _ensure_dirs():
    """Crea directorios si no existen."""
    for d in [PDF_DIR, OCR_DIR, CACHE_DIR, CACHE_DIR / "api", CACHE_DIR / "queries"]:
        d.mkdir(parents=True, exist_ok=True)


def _file_hash(filepath: Path) -> str:
    """Calcula hash SHA256 de un archivo."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return f"sha256:{sha256.hexdigest()[:16]}"


def _bytes_hash(data: bytes) -> str:
    """Calcula hash SHA256 de bytes."""
    sha256 = hashlib.sha256(data)
    return f"sha256:{sha256.hexdigest()[:16]}"


# ─── Manifest de PDFs ───────────────────────────────────────────────────────


def load_manifest() -> Dict[str, Dict]:
    """Carga el manifest de PDFs descargados."""
    if MANIFEST_PATH.exists():
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_manifest(manifest: Dict[str, Dict]):
    """Guarda el manifest de PDFs."""
    _ensure_dirs()
    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False, default=str)


def is_downloaded(url: str) -> Optional[Dict]:
    """Verifica si un URL ya fue descargado."""
    manifest = load_manifest()
    return manifest.get(url)


def register_download(url: str, filepath: str, hash_val: str, metadata: Optional[Dict] = None):
    """Registra una descarga en el manifest."""
    manifest = load_manifest()
    manifest[url] = {
        "filepath": filepath,
        "hash": hash_val,
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "size_bytes": os.path.getsize(filepath) if os.path.exists(filepath) else 0,
        **(metadata or {}),
    }
    save_manifest(manifest)


# ─── Descarga de PDFs con dedup ─────────────────────────────────────────────


def download_pdf(
    url: str,
    source: str,
    filename: str,
    year: Optional[int] = None,
    force: bool = False,
) -> Optional[Path]:
    """Descarga un PDF con dedup por hash.

    Args:
        url: URL del PDF.
        source: Fuente (gacetas, bvc, other).
        filename: Nombre del archivo.
        year: Año (default: actual).
        force: Si True, re-descarga aunque exista.

    Returns:
        Path del archivo descargado, o None si ya existía/skipped.
    """
    import requests

    _ensure_dirs()

    # Check manifest
    if not force:
        existing = is_downloaded(url)
        if existing:
            filepath = Path(existing["filepath"])
            if filepath.exists():
                logger.info("Cache HIT: %s (ya descargado)", filename)
                return filepath
            else:
                logger.info("Manifest dice descargado pero archivo no existe: %s", filepath)

    # Download
    year = year or datetime.now().year
    dest_dir = PDF_DIR / source / str(year)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / filename

    try:
        logger.info("Descargando: %s → %s", url, dest_path)
        resp = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        if len(resp.content) < 100:
            logger.warning("PDF muy pequeño (%d bytes), saltando", len(resp.content))
            return None

        # Write
        with open(dest_path, "wb") as f:
            f.write(resp.content)

        # Hash
        hash_val = _bytes_hash(resp.content)

        # Register
        register_download(
            url=url,
            filepath=str(dest_path.relative_to(PROJECT_ROOT)),
            hash_val=hash_val,
            metadata={
                "source": source,
                "year": year,
                "size_bytes": len(resp.content),
                "content_type": resp.headers.get("Content-Type", ""),
            },
        )

        logger.info("Descargado: %s (%d bytes, %s)", filename, len(resp.content), hash_val)
        return dest_path

    except Exception as exc:
        logger.warning("Error descargando %s: %s", url, exc)
        return None


# ─── OCR y generación de .md ────────────────────────────────────────────────


def load_ocr_index() -> List[Dict]:
    """Carga el índice de archivos OCR procesados."""
    if OCR_INDEX_PATH.exists():
        with open(OCR_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_ocr_index(index: List[Dict]):
    """Guarda el índice de archivos OCR."""
    _ensure_dirs()
    with open(OCR_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False, default=str)


def is_ocr_processed(pdf_hash: str) -> Optional[Dict]:
    """Verifica si un PDF ya fue procesado con OCR."""
    index = load_ocr_index()
    for entry in index:
        if entry.get("pdf_hash") == pdf_hash:
            return entry
    return None


def process_and_save_ocr(
    pdf_bytes: bytes,
    pdf_url: str,
    source: str,
    filename: str,
    year: Optional[int] = None,
    metadata: Optional[Dict] = None,
    force: bool = False,
) -> Optional[Path]:
    """Procesa un PDF con OCR y guarda el resultado como .md con frontmatter.

    Args:
        pdf_bytes: Contenido del PDF.
        pdf_url: URL original del PDF.
        source: Fuente (gacetas, bvc, etc.).
        filename: Nombre base (sin extensión).
        year: Año.
        metadata: Metadata adicional (number, type, categories, etc.).
        force: Si True, re-procesa aunque exista.

    Returns:
        Path del .md generado, o None si ya existía.
    """
    from src.collectors.fiscal.gaceta_ocr import extract_text_from_pdf, classify_gaceta

    _ensure_dirs()
    year = year or datetime.now().year

    # Hash for dedup
    pdf_hash = _bytes_hash(pdf_bytes)

    # Check if already processed
    if not force:
        existing = is_ocr_processed(pdf_hash)
        if existing:
            md_path = Path(existing["md_path"])
            if md_path.exists():
                logger.info("Cache HIT OCR: %s (ya procesado)", filename)
                return md_path

    # Extract text
    text = extract_text_from_pdf(pdf_bytes)

    # Classify
    classification = classify_gaceta(text) if text else None

    # Build frontmatter
    meta = metadata or {}
    frontmatter = {
        "source": source,
        "pdf_url": pdf_url,
        "pdf_hash": pdf_hash,
        "date": meta.get("date", datetime.now().strftime("%Y-%m-%d")),
        "number": meta.get("number", ""),
        "type": meta.get("type", ""),
        "categories": classification.categories if classification else [],
        "ocr_method": classification.method if classification else "unknown",
        "ocr_chars": len(text),
        "confidence": round(classification.confidence, 3) if classification else 0,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Build .md content
    md_content = "---\n"
    for key, value in frontmatter.items():
        if isinstance(value, list):
            md_content += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
        else:
            md_content += f"{key}: {value}\n"
    md_content += "---\n\n"

    md_content += f"# Gaceta Oficial N° {meta.get('number', 'N/A')}\n\n"
    if classification and classification.categories:
        md_content += f"**Categorías:** {', '.join(classification.categories)}\n\n"

    md_content += "## Texto extraído (OCR)\n\n"
    md_content += text if text else "*No se pudo extraer texto.*\n"

    # Save .md
    ocr_dest_dir = OCR_DIR / source / str(year)
    ocr_dest_dir.mkdir(parents=True, exist_ok=True)
    md_path = ocr_dest_dir / f"{filename}.md"

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    # Register in index
    index = load_ocr_index()
    index.append({
        "pdf_hash": pdf_hash,
        "md_path": str(md_path.relative_to(PROJECT_ROOT)),
        "source": source,
        "filename": filename,
        "year": year,
        "categories": classification.categories if classification else [],
        "ocr_chars": len(text),
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })
    save_ocr_index(index)

    logger.info("OCR guardado: %s (%d chars, %s)", md_path.name, len(text), classification.method if classification else "unknown")
    return md_path


# ─── Caché de APIs ──────────────────────────────────────────────────────────


def cache_api_response(key: str, data: Any, ttl_hours: int = 24):
    """Guarda una respuesta de API en caché con TTL."""
    _ensure_dirs()
    cache_file = CACHE_DIR / "api" / f"{key}.json"
    cache_data = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "ttl_hours": ttl_hours,
        "data": data,
    }
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, indent=2, ensure_ascii=False, default=str)


def get_cached_api(key: str) -> Optional[Any]:
    """Obtiene una respuesta de API del caché (si no expiró)."""
    cache_file = CACHE_DIR / "api" / f"{key}.json"
    if not cache_file.exists():
        return None

    with open(cache_file, "r", encoding="utf-8") as f:
        cache_data = json.load(f)

    cached_at = datetime.fromisoformat(cache_data["cached_at"])
    ttl_hours = cache_data.get("ttl_hours", 24)

    if datetime.now(timezone.utc) - cached_at > timedelta(hours=ttl_hours):
        logger.info("Cache EXPIRED: %s (age: %s)", key, datetime.now(timezone.utc) - cached_at)
        return None

    return cache_data["data"]


# ─── Estadísticas y GC ──────────────────────────────────────────────────────


def get_cache_stats() -> Dict:
    """Retorna estadísticas del caché."""
    _ensure_dirs()

    # PDFs
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    pdf_size = sum(f.stat().st_size for f in pdf_files if f.exists())

    # OCR
    ocr_files = list(OCR_DIR.rglob("*.md"))
    ocr_size = sum(f.stat().st_size for f in ocr_files if f.exists())

    # API cache
    api_files = list((CACHE_DIR / "api").glob("*.json"))
    api_size = sum(f.stat().st_size for f in api_files if f.exists())

    # Manifest
    manifest = load_manifest()
    ocr_index = load_ocr_index()

    return {
        "pdfs": {
            "count": len(pdf_files),
            "size_mb": round(pdf_size / 1024 / 1024, 2),
            "manifest_entries": len(manifest),
        },
        "ocr": {
            "count": len(ocr_files),
            "size_mb": round(ocr_size / 1024 / 1024, 2),
            "index_entries": len(ocr_index),
        },
        "api_cache": {
            "count": len(api_files),
            "size_mb": round(api_size / 1024 / 1024, 2),
        },
    }


def gc_cache(max_age_days: int = 90) -> Dict:
    """Elimina archivos del caché con más de max_age_days días."""
    _ensure_dirs()
    cutoff = datetime.now() - timedelta(days=max_age_days)
    removed = {"pdfs": 0, "ocr": 0, "api": 0}

    # GC API cache
    for f in (CACHE_DIR / "api").glob("*.json"):
        if f.stat().st_mtime < cutoff.timestamp():
            f.unlink()
            removed["api"] += 1

    logger.info("GC completado: eliminados %d archivos API cache", removed["api"])
    return removed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    stats = get_cache_stats()
    print("\n=== Estadísticas del Caché ===")
    for category, info in stats.items():
        print(f"\n{category.upper()}:")
        for key, value in info.items():
            print(f"  {key}: {value}")
