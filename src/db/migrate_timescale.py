"""
Migración TimescaleDB
=====================

Convierte las tablas de series temporales en hypertables y agrega índices
para queries rápidas del dashboard.

Uso:
    python -m src.db.migrate_timescale
    python -m src.db.migrate_timescale --dry-run  # solo muestra el SQL
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SQL_FILE = Path(__file__).parent / "migrations" / "timescale_setup.sql"


def run_migration(dry_run: bool = False) -> None:
    """Ejecuta la migración TimescaleDB."""
    if not SQL_FILE.exists():
        logger.error("Archivo SQL no encontrado: %s", SQL_FILE)
        return

    sql = SQL_FILE.read_text(encoding="utf-8")

    if dry_run:
        print("=== SQL que se ejecutará ===")
        print(sql)
        return

    from src.db.session import get_engine

    engine = get_engine()

    # Verificar si TimescaleDB está disponible
    try:
        with engine.connect() as conn:
            result = conn.execute(
                conn.exec_driver_sql("SELECT extname FROM pg_extension WHERE extname = 'timescaledb'")
            )
            if result.fetchone() is None:
                logger.warning(
                    "TimescaleDB no está instalado en esta BD. "
                    "Usa la imagen timescale/timescaledb en docker-compose."
                )
                logger.info("Ejecutando SQL de todas formas (ignorando errores de TimescaleDB)...")
    except Exception as exc:
        logger.warning("No se pudo verificar TimescaleDB: %s", exc)

    # Ejecutar cada statement por separado para manejar errores
    statements = [s.strip() for s in sql.split(";") if s.strip() and not s.strip().startswith("--")]

    with engine.connect() as conn:
        for i, stmt in enumerate(statements, 1):
            try:
                conn.execute(conn.exec_driver_sql(stmt))
                conn.commit()
                logger.info("Statement %d/%d ejecutado", i, len(statements))
            except Exception as exc:
                # TimescaleDB functions pueden fallar si ya existen
                if "already exists" in str(exc) or "if_not_exists" in str(exc):
                    logger.debug("Statement %d ya existe, omitiendo", i)
                else:
                    logger.warning("Statement %d falló: %s", i, str(exc)[:100])

    logger.info("Migración TimescaleDB completada")


def main() -> int:
    parser = argparse.ArgumentParser(description="Migración TimescaleDB")
    parser.add_argument("--dry-run", action="store_true", help="Mostrar SQL sin ejecutar")
    args = parser.parse_args()

    run_migration(dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
