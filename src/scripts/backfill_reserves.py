"""
Backfill de la serie histórica de reservas internacionales (BCV)
================================================================

Descarga ``2_1_1.xlsx`` una sola vez y guarda en ``reserves_history`` todos los
días publicados desde ``--start-year`` (2020 por defecto). Es idempotente: las
fechas ya guardadas se actualizan, no se duplican.

Uso:
    python -m src.scripts.backfill_reserves
    python -m src.scripts.backfill_reserves --start-year 2024 --json
"""

import argparse
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def backfill_reserves(start_year: int = 2020) -> dict:
    """Descarga y persiste la serie; devuelve un resumen."""
    from src.collectors.official.bcv_reserves_collector import BCVReservesCollector
    from src.db.repositories import ReservesRepository
    from src.db.session import init_db, session_scope

    init_db()
    days = BCVReservesCollector().fetch_history(start_year=start_year)
    with session_scope() as session:
        repo = ReservesRepository(session)
        inserted = repo.save_history([
            {
                "date": day.date,
                "total_usd": day.total_usd,
                "bcv_usd": day.bcv_usd,
                "fem_usd": day.fem_usd,
            }
            for day in days
        ])
        total = repo.count()

    return {
        "days": len(days),
        "inserted": inserted,
        "rows": total,
        "from": days[0].date,
        "to": days[-1].date,
        "last_usd": days[-1].total_usd,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de reservas internacionales del BCV"
    )
    parser.add_argument("--start-year", type=int, default=2020,
                        help="Primer año a guardar (por defecto 2020)")
    parser.add_argument("--json", action="store_true", help="Salida JSON")
    args = parser.parse_args(argv)

    try:
        summary = backfill_reserves(args.start_year)
    except Exception as exc:  # noqa: BLE001 - CLI: cualquier fallo es exit 1
        logger.error("Backfill de reservas falló: %s", exc)
        return 1

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(
            f"Reservas BCV {summary['from']} → {summary['to']}: "
            f"{summary['days']} días ({summary['inserted']} nuevos, "
            f"{summary['rows']} en la tabla). Último: "
            f"${summary['last_usd']:,.0f}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
