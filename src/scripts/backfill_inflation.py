"""Backfill Histórico de Inflación (IPC)
=======================================

El OVF publica cada mes su medición de inflación en el sitio
(``observatoriodefinanzas.com``), pero no expone serie histórica navegable: la
portada solo enlaza la última publicación. Su WordPress sí expone la API REST
(``/wp-json/wp/v2/posts``), así que este script recorre las publicaciones de
inflación y reconstruye la serie mensual.

Dos reglas para no meter datos falsos:

1. **Período determinable**: el título debe nombrar un mes ("en mayo",
   "abril en cifras"). Si el mes no aparece, el post se descarta.
2. **Validación numérica**: la tasa mensual debe estar entre 0 y 100 %, y si
   hay interanual no puede ser menor que la mensual. Lo que no pase se rechaza
   y se reporta.

Uso:
    python -m src.scripts.backfill_inflation [--pages 5] [--no-save] [--json]
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional

import httpx

# El parseo y la deducción de período viven en el collector para que el job
# en vivo y el backfill no vuelvan a divergir (antes cada uno tenía su regex).
from src.collectors.errors import CollectorSourceError
from src.collectors.market.ovf_collector import parse_bulletin, period_from_title
from src.config import settings
from src.models.market import InflationPoint

logger = logging.getLogger(__name__)

WP_POSTS_ENDPOINT = "/wp-json/wp/v2/posts"
DEFAULT_PAGES = 5
PER_PAGE = 50
SEARCH_TERM = "inflaci"

def validate_rates(monthly: Optional[float], annual: Optional[float]) -> bool:
    """True si las tasas son plausibles para IPC mensual venezolano."""
    if monthly is None or monthly <= 0 or monthly > 100:
        return False
    if annual is not None and annual < monthly:
        return False
    return True


def fetch_posts(
    base_url: Optional[str] = None,
    pages: int = DEFAULT_PAGES,
    timeout: float = 60.0,
) -> List[dict]:
    """Publicaciones de inflación del OVF (más nuevas primero)."""
    base = (base_url or settings.OVF_BASE_URL).rstrip("/")
    posts: List[dict] = []
    for page in range(1, max(1, pages) + 1):
        try:
            resp = httpx.get(
                base + WP_POSTS_ENDPOINT,
                params={
                    "search": SEARCH_TERM,
                    "per_page": PER_PAGE,
                    "page": page,
                    "_fields": "date,link,title,content",
                },
                timeout=timeout,
                follow_redirects=True,
            )
            resp.raise_for_status()
            batch = resp.json()
        except Exception as exc:  # noqa: BLE001 - fuente externa
            logger.warning("OVF WP page %d no disponible: %s", page, exc)
            break
        if not batch:
            break
        posts.extend(batch)
        if len(batch) < PER_PAGE:
            break
    logger.info("OVF: %d publicaciones revisadas", len(posts))
    return posts


def build_points(posts: List[dict]) -> Dict[str, object]:
    """Convierte publicaciones en puntos de inflación validados.

    Args:
        posts: Lista con ``date``, ``title.rendered`` y ``content.rendered``.

    Returns:
        ``{"points": [...], "rejected": n, "sin_periodo": n}``.
    """
    by_period: Dict[str, InflationPoint] = {}
    rejected = 0
    sin_periodo = 0

    for post in posts:
        raw_date = str(post.get("date") or "")
        try:
            published = datetime.fromisoformat(raw_date)
        except ValueError:
            rejected += 1
            continue
        title = ((post.get("title") or {}).get("rendered") or "")
        period = period_from_title(title, published)
        if period is None:
            sin_periodo += 1
            continue

        html = ((post.get("content") or {}).get("rendered") or "")
        try:
            point = parse_bulletin(html, source="ovf", period=period)
        except CollectorSourceError:
            rejected += 1
            continue
        if not validate_rates(point.monthly_rate, point.annual_rate):
            logger.debug("OVF %s rechazado: mensual=%s anual=%s", period,
                         point.monthly_rate, point.annual_rate)
            rejected += 1
            continue

        previous = by_period.get(period)
        # Preferir el punto con interanual disponible
        if previous is None or (previous.annual_rate is None and point.annual_rate is not None):
            by_period[period] = point

    points = [by_period[p] for p in sorted(by_period)]
    return {"points": points, "rejected": rejected, "sin_periodo": sin_periodo}


def backfill_inflation(session, pages: int = DEFAULT_PAGES, persist: bool = True) -> Dict[str, int]:
    """Recorre el archivo del OVF y guarda la serie mensual de IPC.

    Returns:
        Resumen con ``posts``, ``accepted``, ``rejected`` y ``saved``.
    """
    from src.db.repositories import MarketRepository

    posts = fetch_posts(pages=pages)
    result = build_points(posts)
    points: List[InflationPoint] = result["points"]  # type: ignore[assignment]
    summary = {
        "posts": len(posts),
        "accepted": len(points),
        "rejected": int(result["rejected"]),
        "sin_periodo": int(result["sin_periodo"]),
        "saved": 0,
    }
    if persist and points:
        summary["saved"] = MarketRepository(session).save_inflation(points)
    logger.info(
        "Backfill IPC: %d posts, %d aceptados, %d rechazados, %d sin período, %d guardados",
        summary["posts"], summary["accepted"], summary["rejected"],
        summary["sin_periodo"], summary["saved"],
    )
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Backfill de inflación mensual desde el archivo del OVF"
    )
    parser.add_argument("--pages", type=int, default=DEFAULT_PAGES,
                        help=f"Páginas de WP REST a recorrer (default: {DEFAULT_PAGES})")
    parser.add_argument("--no-save", action="store_true", help="No persistir")
    parser.add_argument("--json", action="store_true", help="Resumen en JSON")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from src.db.session import init_db, session_scope

    init_db()
    with session_scope() as session:
        summary = backfill_inflation(session, pages=args.pages, persist=not args.no_save)

    if args.json:
        print(json.dumps(summary, ensure_ascii=False))
    else:
        print(f"Backfill IPC completado: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
