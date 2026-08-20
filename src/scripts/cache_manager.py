"""
Cache Manager CLI — Gestión del caché de datos
===============================================

Uso:
    python -m src.scripts.cache_manager stats
    python -m src.scripts.cache_manager scan
    python -m src.scripts.cache_manager gc [--days 90]
    python -m src.scripts.cache_manager verify
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.cache.manager import (
    get_cache_stats,
    gc_cache,
    load_manifest,
    load_ocr_index,
    PDF_DIR,
    OCR_DIR,
    CACHE_DIR,
)


def cmd_stats(args):
    """Muestra estadísticas del caché."""
    stats = get_cache_stats()
    print("\n=== 📊 Estadísticas del Caché ===\n")
    for category, info in stats.items():
        print(f"  {category.upper()}:")
        for key, value in info.items():
            print(f"    {key}: {value}")
        print()


def cmd_scan(args):
    """Escanea directorios y reconstruye manifest."""
    print("\n=== 🔍 Escaneando directorios ===\n")

    # Scan PDFs
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    print(f"  PDFs encontrados: {len(pdf_files)}")
    for f in pdf_files[:10]:
        print(f"    {f.relative_to(PROJECT_ROOT)} ({f.stat().st_size} bytes)")
    if len(pdf_files) > 10:
        print(f"    ... y {len(pdf_files) - 10} más")

    # Scan OCR
    ocr_files = list(OCR_DIR.rglob("*.md"))
    print(f"\n  OCR .md encontrados: {len(ocr_files)}")
    for f in ocr_files[:10]:
        print(f"    {f.relative_to(PROJECT_ROOT)}")
    if len(ocr_files) > 10:
        print(f"    ... y {len(ocr_files) - 10} más")

    # Scan API cache
    api_files = list((CACHE_DIR / "api").glob("*.json"))
    print(f"\n  API cache files: {len(api_files)}")
    for f in api_files:
        print(f"    {f.name}")

    # Manifest
    manifest = load_manifest()
    print(f"\n  Manifest entries: {len(manifest)}")

    # OCR index
    ocr_index = load_ocr_index()
    print(f"  OCR index entries: {len(ocr_index)}")


def cmd_gc(args):
    """Elimina archivos antiguos del caché."""
    days = args.days
    print(f"\n=== 🗑️ GC: eliminando archivos con más de {days} días ===\n")
    removed = gc_cache(max_age_days=days)
    for category, count in removed.items():
        print(f"  {category}: {count} archivos eliminados")


def cmd_verify(args):
    """Verifica integridad de hashes."""
    print("\n=== ✅ Verificando integridad ===\n")
    manifest = load_manifest()

    ok = 0
    broken = 0
    for url, info in manifest.items():
        filepath = PROJECT_ROOT / info.get("filepath", "")
        if filepath.exists():
            ok += 1
        else:
            broken += 1
            print(f"  ❌ FALTA: {info.get('filepath', '?')}")

    print(f"\n  ✅ OK: {ok}")
    print(f"  ❌ FALTANTES: {broken}")


def main():
    parser = argparse.ArgumentParser(description="Cache Manager CLI")
    subparsers = parser.add_subparsers(dest="command", help="Comando a ejecutar")

    # stats
    subparsers.add_parser("stats", help="Mostrar estadísticas del caché")

    # scan
    subparsers.add_parser("scan", help="Escanear directorios")

    # gc
    gc_parser = subparsers.add_parser("gc", help="Eliminar archivos antiguos")
    gc_parser.add_argument("--days", type=int, default=90, help="Días máximos (default: 90)")

    # verify
    subparsers.add_parser("verify", help="Verificar integridad de hashes")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    commands = {
        "stats": cmd_stats,
        "scan": cmd_scan,
        "gc": cmd_gc,
        "verify": cmd_verify,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
