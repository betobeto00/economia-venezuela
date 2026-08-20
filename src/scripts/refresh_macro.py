"""
Refresh del cache de indicadores macroeconómicos
=================================================

Descarga los indicadores de World Bank, IMF, CEPAL, OPEP y UNSCEB,
y los guarda en la tabla macro_indicators para que el dashboard
los cargue instantáneamente.

Uso:
    python -m src.scripts.refresh_macro
    python -m src.scripts.refresh_macro --force
"""

import argparse
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Refresh cache de indicadores macro")
    parser.add_argument("--force", action="store_true", help="Forzar refresh aunque no esté stale")
    args = parser.parse_args(argv)

    # Asegurar que las tablas existan
    from src.db.session import init_db
    init_db()

    from src.dashboard.macro_data import refresh_macro_cache

    logger.info("Refrescando indicadores macroeconómicos...")
    results = refresh_macro_cache()

    for name, ok in results.items():
        status = "OK" if ok else "FALLÓ"
        logger.info("  %s: %s", name, status)

    total_ok = sum(1 for v in results.values() if v)
    logger.info("Refresh completado: %d/%d exitosos", total_ok, len(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())
