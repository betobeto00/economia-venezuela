"""
Backfill de IBC Index, Componentes y Tickers Venezolanos
=========================================================

Recolecta datos históricos y los guarda en la BD para que los informes
puedan consultar datos de fechas pasadas.

Uso:
    python -m src.scripts.backfill_ibc --days 30
    python -m src.scripts.backfill_ibc --since 2026-08-01 --until 2026-08-14
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def backfill_tickers_for_date(session, target_date: datetime) -> int:
    """Recolecta tickers venezolanos para un día específico y los guarda."""
    from src.collectors.market.ibc_stocks_collector import fetch_tickers_for_date
    from src.db.repositories import VenezuelanTickerRepository

    repo = VenezuelanTickerRepository(session)
    date_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    try:
        tickers = fetch_tickers_for_date(target_date)
        if not tickers:
            return 0

        tickers_data = [
            {
                "ticker": t.ticker,
                "name": t.name,
                "close": t.close,
                "change_pct": t.change_pct,
                "avg_volume": int(t.avg_volume),
            }
            for t in tickers
        ]
        n = repo.save_tickers(date_start, tickers_data)
        return n
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error tickers para %s: %s", target_date.date(), exc)
        return 0


def backfill_ibc_current(session) -> dict:
    """Guarda el IBC actual ( Investing.com solo da datos en tiempo real)."""
    from src.collectors.market.ibc_components_collector import fetch_ibc_from_investing
    from src.db.repositories import IBCIndexRepository

    repo = IBCIndexRepository(session)
    summary = {"ibc_index": 0, "ibc_components": 0}

    try:
        ibc = fetch_ibc_from_investing()
        if ibc and ibc.value > 0:
            date = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            saved = repo.save_index(date, ibc.value, ibc.change, ibc.change_pct)
            if saved:
                summary["ibc_index"] = 1

            if ibc.components:
                comps = [
                    {
                        "ticker": c.ticker,
                        "name": c.name,
                        "price": c.price,
                        "change_pct": c.change_pct,
                        "volume": c.volume,
                    }
                    for c in ibc.components
                ]
                n = repo.save_components(date, comps)
                summary["ibc_components"] = n
    except Exception as exc:  # noqa: BLE001
        logger.warning("Error IBC: %s", exc)

    return summary


def run_backfill(session, since: datetime, until: datetime) -> dict:
    """Ejecuta backfill completo: tickers día por día + IBC actual."""
    summary = {"tickers_total": 0, "days_processed": 0}

    # Backfill tickers día por día
    current = since
    while current <= until:
        n = backfill_tickers_for_date(session, current)
        summary["tickers_total"] += n
        summary["days_processed"] += 1
        logger.info(
            "Día %s: %d tickers nuevos",
            current.strftime("%Y-%m-%d"), n,
        )
        current += timedelta(days=1)

    # IBC actual (solo si el rango incluye hoy)
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    if until >= today:
        ibc_summary = backfill_ibc_current(session)
        summary.update(ibc_summary)

    logger.info("Resumen backfill: %s", summary)
    return summary


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill de IBC y tickers venezolanos."
    )
    parser.add_argument(
        "--since", default=None,
        help="Fecha inicio (YYYY-MM-DD). Default: 30 días atrás.",
    )
    parser.add_argument(
        "--until", default=None,
        help="Fecha fin (YYYY-MM-DD). Default: hoy.",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Días hacia atrás si no se especifica --since (default: 30).",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    now = datetime.now(timezone.utc)
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        since = now - timedelta(days=args.days)

    if args.until:
        until = datetime.strptime(args.until, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        until = now

    from src.db.session import session_scope

    with session_scope() as session:
        summary = run_backfill(session, since, until)

    print(f"Backfill completado: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
