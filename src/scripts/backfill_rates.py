"""
Backfill Histórico de Tasas (Fase A)
====================================

Carga las tasas diarias de los últimos meses desde el dataset abierto de
``usdt.com.ve`` (CC-BY-4.0): ``https://www.usdt.com.ve/data/usdt-ves-historical.csv``.

El CSV trae snapshots cada ~5 minutos de tres fuentes:
- ``binance``: USDT/VES P2P (dólar paralelo digital).
- ``bybit``: USDT/VES P2P en Bybit.
- ``bcv``: tasa oficial USD/VES del BCV.

Este script agrega a **promedio diario** por fuente y los guarda como
``ExchangeRate`` con ``source``/``currency`` compatibles con el resto del
sistema (``binance/usdt``, ``bybit/usdt``, ``bcv/usd``). La inserción es
idempotente (única por source/currency/date): re-ejecutar no duplica.

Uso:
    python -m src.scripts.backfill_rates [--days 180] [--csv URL] [--no-save]
"""

import argparse
import logging
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import httpx

from src.db.repositories import MarketRepository
from src.models.market import ExchangeRate

logger = logging.getLogger(__name__)

DEFAULT_CSV_URL = "https://www.usdt.com.ve/data/usdt-ves-historical.csv"
DEFAULT_DAYS = 180

# source del CSV -> (source, currency) del sistema.
SOURCE_MAP = {
    "binance": ("binance", "usdt"),
    "bybit": ("bybit", "usdt"),
    "bcv": ("bcv", "usd"),
}


def _parse_ts(raw: str) -> datetime:
    """Fecha ISO 8601 con offset (UTC) a datetime naive UTC."""
    dt = datetime.fromisoformat(raw)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def download_csv(csv_url: str = DEFAULT_CSV_URL, timeout: float = 120.0) -> str:
    """Descarga el CSV completo y devuelve el texto (filtra comentarios #)."""
    resp = httpx.get(csv_url, timeout=timeout, follow_redirects=True)
    resp.raise_for_status()
    lines = [
        ln for ln in resp.text.splitlines()
        if ln and not ln.startswith("#")
    ]
    return "\n".join(lines)


def aggregate_daily(csv_text: str, since: Optional[datetime] = None) -> List[ExchangeRate]:
    """Agrega los snapshots del CSV a promedio diario por (source, currency).

    Args:
        csv_text: Contenido CSV (con cabecera ``captured_at,source,buy_rate,sell_rate``).
        since: Fecha mínima (inclusive); si es None toma todo.

    Returns:
        Lista de ``ExchangeRate``, uno por día y fuente, ordenados por fecha.
    """
    import csv
    import io

    bucket: Dict[tuple, List[float]] = defaultdict(list)
    seen: Dict[tuple, datetime] = {}
    reader = csv.DictReader(io.StringIO(csv_text))
    for row in reader:
        src = (row.get("source") or "").strip().lower()
        if src not in SOURCE_MAP:
            continue
        try:
            price = float((row.get("buy_rate") or "").replace(",", "."))
        except (TypeError, ValueError):
            continue
        if price <= 0:
            continue
        ts = _parse_ts(row["captured_at"])
        if since is not None and ts.date() < since.date():
            continue
        key = (src, ts.date())
        bucket[key].append(price)
        if key not in seen or ts > seen[key]:
            seen[key] = ts

    rates: List[ExchangeRate] = []
    for (src, day), prices in bucket.items():
        source, currency = SOURCE_MAP[src]
        rates.append(ExchangeRate(
            source=source,
            currency=currency,
            rate=sum(prices) / len(prices),
            date=datetime(day.year, day.month, day.day),
        ))
    rates.sort(key=lambda r: r.date)
    return rates


def backfill_rates(
    session,
    days: int = DEFAULT_DAYS,
    csv_url: str = DEFAULT_CSV_URL,
    persist: bool = True,
) -> Dict[str, int]:
    """Descarga, agrega y guarda el histórico de tasas en la base.

    Args:
        session: Sesión SQLAlchemy.
        days: Ventana en días hacia atrás desde hoy.
        csv_url: URL del dataset (testeable).
        persist: Si False, no guarda (solo retorna conteos).

    Returns:
        Dict {source: n_tasas} o {"saved": n} si persist=False.
    """
    since = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)
    logger.info("Descargando dataset desde %s", csv_url)
    csv_text = download_csv(csv_url)
    rates = aggregate_daily(csv_text, since=since)
    logger.info("Promedios diarios calculados: %d", len(rates))

    if not persist:
        counts: Dict[str, int] = {}
        for r in rates:
            counts[r.source] = counts.get(r.source, 0) + 1
        return counts

    saved = MarketRepository(session).save_rates(rates)
    return {"saved": saved}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de tasas históricas desde usdt.com.ve"
    )
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help="Ventana en días (default: 180 ≈ 6 meses)")
    parser.add_argument("--csv", default=DEFAULT_CSV_URL,
                        help="URL o ruta del CSV histórico")
    parser.add_argument("--no-save", action="store_true",
                        help="Solo calcular conteos, sin escribir en la DB")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from src.db.session import session_scope

    with session_scope() as session:
        result = backfill_rates(session, days=args.days, csv_url=args.csv,
                                persist=not args.no_save)
        logger.info("Resultado: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())