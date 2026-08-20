"""
Genera informes económicos periódicos (diario/semanal/mensual/trimestral/semestral/anual)
=========================================================================================

Uso:
    python -m src.scripts.generate_report --cadence semanal --format md,pdf
    python -m src.scripts.generate_report --cadence diario --format pdf --no-ai
    python -m src.scripts.generate_report --since 2026-08-10 --until 2026-08-14 --format md
"""

import argparse
import logging
import sys
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera informes económicos de Venezuela en Markdown y PDF."
    )
    parser.add_argument(
        "--cadence", default="semanal", dest="cadence",
        choices=["diario", "semanal", "mensual", "trimestral", "semestral", "anual"],
        help="Cadencia del informe (default: semanal).",
    )
    parser.add_argument(
        "--format", default="md,pdf", dest="formats",
        help="Formatos separados por coma: md, pdf (default: md,pdf).",
    )
    parser.add_argument(
        "--output-dir", default=None, dest="output_dir",
        help="Carpeta de salida (default: data/reports).",
    )
    parser.add_argument(
        "--no-ai", action="store_true",
        help="Omite el resumen ejecutivo por IA.",
    )
    parser.add_argument(
        "--since", default=None, dest="since",
        help="Fecha de inicio (YYYY-MM-DD). Sobreescribe la cadencia.",
    )
    parser.add_argument(
        "--until", default=None, dest="until",
        help="Fecha de fin (YYYY-MM-DD). Sobreescribe la cadencia.",
    )
    return parser.parse_args(argv)


def _parse_date(s: str) -> datetime:
    """Parsea YYYY-MM-DD a datetime UTC."""
    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main(argv=None) -> int:
    args = parse_args(argv)
    formats = tuple(f.strip().lower() for f in args.formats.split(",") if f.strip())

    from src.analyzers.reports.periodic import generate_periodic_report

    snapshot_kwargs = {}
    if args.since:
        snapshot_kwargs["since"] = _parse_date(args.since)
    if args.until:
        snapshot_kwargs["until"] = _parse_date(args.until)

    try:
        result = generate_periodic_report(
            cadence=args.cadence,
            output_dir=args.output_dir,
            formats=formats,
            with_ai=not args.no_ai,
            **snapshot_kwargs,
        )
    except Exception as exc:  # noqa: BLE001 - el CLI debe reportar el error
        logging.error("Fallo al generar el informe: %s", exc)
        return 1

    for fmt, path in result["paths"].items():
        print(f"[{fmt.upper()}] {path}")
    print(f"Período: {result['snapshot']['period']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())