"""Verificación de datos locales
================================

Railway se dio de baja, así que la base local no se restaura desde un dump:
se repuebla desde las fuentes (``collect_market``, ``collect_news``,
``backfill_rates``, ``refresh_macro``...). Este CLI audita qué hay realmente
en la base después de cada corrida: filas por tabla, rango de fechas de cada
serie y cuántos registros son recientes.

Uso:
    python -m src.scripts.verify_data
    python -m src.scripts.verify_data --json
    python -m src.scripts.verify_data --fail-on-empty   # exit 1 si falta lo esencial
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import inspect, text

from src.db.session import get_engine

#: Tablas sin las cuales el sistema no puede producir informes útiles.
CORE_TABLES = ("exchange_rates", "inflation_points", "news_articles")

#: Orden estable del informe.
TABLES = (
    "exchange_rates",
    "inflation_points",
    "news_articles",
    "social_posts",
    "sentiment_scores",
    "macro_indicators",
    "ibc_index",
    "ibc_components",
    "venezuelan_tickers",
    "surveys",
    "survey_responses",
)

#: Nombres candidatos a columna temporal, por prioridad.
DATE_COLUMNS = ("date", "published_at", "submitted_at", "created_at", "timestamp")


def _date_column(columns: Dict[str, str]) -> Optional[str]:
    """Primera columna temporal conocida en la tabla."""
    for name in DATE_COLUMNS:
        if name in columns:
            return name
    return None


def _is_temporal(type_name: str) -> bool:
    """True si el tipo SQL es fecha/hora (no texto tipo ``2026-08``)."""
    upper = type_name.upper()
    return "DATE" in upper or "TIME" in upper


def collect(days: int = 30) -> List[Dict[str, Any]]:
    """Audita las tablas conocidas.

    Args:
        days: Ventana para contar registros recientes.

    Returns:
        Una fila de resultado por tabla, con ``exists``, ``rows``,
        ``first``, ``last`` y ``recent`` (``None`` si no aplica).
    """
    engine = get_engine()
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results: List[Dict[str, Any]] = []

    for table in TABLES:
        if table not in existing:
            results.append(
                {"table": table, "exists": False, "rows": 0,
                 "first": None, "last": None, "recent": None, "date_column": None}
            )
            continue

        columns = {c["name"]: str(c["type"]) for c in inspector.get_columns(table)}
        date_column = _date_column(columns)
        first = last = None
        recent: Optional[int] = None

        with engine.connect() as conn:
            rows = conn.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar() or 0
            if date_column and rows:
                try:
                    first, last = conn.execute(
                        text(
                            f'SELECT MIN("{date_column}"), MAX("{date_column}") '
                            f'FROM "{table}"'
                        )
                    ).one()
                    if _is_temporal(columns[date_column]):
                        recent = conn.execute(
                            text(
                                f'SELECT COUNT(*) FROM "{table}" '
                                f'WHERE "{date_column}" >= :cutoff'
                            ),
                            {"cutoff": cutoff},
                        ).scalar() or 0
                except Exception as exc:  # noqa: BLE001 - auditoría, no debe caerse
                    results.append(
                        {"table": table, "exists": True, "rows": rows,
                         "first": None, "last": None, "recent": None,
                         "date_column": date_column, "error": str(exc)[:200]}
                    )
                    continue

        results.append(
            {
                "table": table,
                "exists": True,
                "rows": rows,
                "first": str(first) if first is not None else None,
                "last": str(last) if last is not None else None,
                "recent": recent,
                "date_column": date_column,
            }
        )
    return results


def _format(rows: List[Dict[str, Any]], days: int) -> str:
    header = f"{'tabla':<20} {'filas':>7}  {'desde':<20} {'hasta':<20} {'últimos ' + str(days) + 'd':>12}"
    lines = [header, "-" * len(header)]
    for row in rows:
        if not row["exists"]:
            lines.append(f"{row['table']:<20} {'—':>7}  {'(tabla ausente)':<20}")
            continue
        recent = "—" if row["recent"] is None else str(row["recent"])
        lines.append(
            f"{row['table']:<20} {row['rows']:>7}  "
            f"{(row['first'] or '—')[:20]:<20} {(row['last'] or '—')[:20]:<20} "
            f"{recent:>12}"
        )
    return "\n".join(lines)


def main(argv=None) -> int:
    """Punto de entrada del CLI."""
    parser = argparse.ArgumentParser(
        description="Audita conteos y frescura de la base de datos local."
    )
    parser.add_argument("--json", action="store_true", help="Salida en JSON")
    parser.add_argument(
        "--fail-on-empty",
        action="store_true",
        help="Sale con código 1 si alguna tabla esencial está vacía",
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Ventana de 'registros recientes' en días (default: 30)",
    )
    args = parser.parse_args(argv)

    try:
        rows = collect(days=args.days)
    except Exception as exc:  # noqa: BLE001 - sin DB no hay auditoría posible
        print(f"ERROR: no se pudo consultar la base de datos: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        print(_format(rows, args.days))

    empty_core = [
        row["table"] for row in rows
        if row["table"] in CORE_TABLES and row["rows"] == 0
    ]
    if empty_core:
        print(
            "\nFaltan datos en tablas esenciales: " + ", ".join(empty_core),
            file=sys.stderr,
        )
        return 1 if args.fail_on_empty else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
