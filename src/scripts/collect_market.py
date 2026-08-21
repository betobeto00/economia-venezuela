"""
Recolección de Datos de Mercado (CLI)
=====================================

Orquesta los collectors de Fase A y persiste en PostgreSQL:

    python -m src.scripts.collect_market [--period 2026-08]

La lógica reutilizable es ``run_market_pipeline(session, ...)`` (usada por el
CLI y el scheduler) con dependencias inyectadas para tests.
"""

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import List, Optional

from src.collectors.market.bcv_collector import BCVCollector
from src.collectors.market.binance_collector import BinanceCollector
from src.collectors.market.bvc_collector import BVCCollector
from src.collectors.market.ibc_components_collector import fetch_ibc_from_investing
from src.collectors.market.ovf_collector import OVFCollector
from src.db.repositories import MarketRepository, IBCIndexRepository
from src.models.market import ExchangeRate, InflationPoint, IndexPoint

logger = logging.getLogger(__name__)

CURRENT_MONTH = datetime.now(timezone.utc).strftime("%Y-%m")


def run_market_pipeline(
    session,
    bcv: Optional[BCVCollector] = None,
    ovf: Optional[OVFCollector] = None,
    binance: Optional[BinanceCollector] = None,
    period: Optional[str] = None,
) -> dict:
    """Recolecta tasas e IPC de los collectors y los persiste.

    Cada fuente se intenta de forma independiente: un fallo en una no
    impide guardar las demás (degradación parcial).

    Returns:
        Dict de resumen: {source: {"type": ..., "saved": n}}.
    """
    bcv = bcv or BCVCollector()
    ovf = ovf or OVFCollector()
    binance = binance or BinanceCollector()
    bvc = BVCCollector()
    period = period or CURRENT_MONTH

    repo = MarketRepository(session)
    ibc_repo = IBCIndexRepository(session)
    summary: dict = {}

    def _save(name: str, kind: str, items: List) -> None:
        if not items:
            return
        if kind == "rate":
            saved = repo.save_rates(items)
        elif kind == "inflation":
            saved = repo.save_inflation(items)
        elif kind == "ibc_index":
            # Save IBC index using IBCIndexRepository
            saved = 0
            for item in items:
                if isinstance(item, IndexPoint):
                    if ibc_repo.save_index(item.date, item.value):
                        saved += 1
        else:
            saved = 0
        summary[name] = {"type": kind, "saved": saved}

    # BCV: tasa oficial + IPC
    try:
        rate = bcv.fetch_official_rate()
        _save("bcv_rate", "rate", [rate])
    except Exception as exc:  # noqa: BLE001
        logger.warning("BCV tasa no disponible: %s", exc)
    try:
        ipc = bcv.fetch_ipc(period)
        _save("bcv_ipc", "inflation", [ipc])
    except Exception as exc:  # noqa: BLE001
        logger.warning("BCV IPC no disponible: %s", exc)

    # OVF: IPC alternativo
    try:
        ovf_ipc = ovf.fetch_ipc(period)
        _save("ovf_ipc", "inflation", [ovf_ipc])
    except Exception as exc:  # noqa: BLE001
        logger.warning("OVF IPC no disponible: %s", exc)

    # Binance P2P: tasa paralela digital
    try:
        p2p = binance.fetch_usdt_rate()
        _save("binance_usdt", "rate", [p2p])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Binance P2P no disponible: %s", exc)

    # BVC: Índice IBC (Bolsa de Valores de Caracas) — índice en PUNTOS, no tasa de cambio
    try:
        ibc = bvc.fetch_index()
        _save("bvc_ibc", "ibc_index", [ibc])
    except Exception as exc:  # noqa: BLE001
        logger.warning("BVC IBC no disponible: %s", exc)

    # BVC: Componentes del IBC desde Investing.com
    try:
        ibc_data = fetch_ibc_from_investing()
        if ibc_data:
            n_comp = len(ibc_data.components)
            summary["bvc_ibc_components"] = {"type": "ibc_components", "saved": n_comp}
    except Exception as exc:  # noqa: BLE001
        logger.warning("IBC componentes no disponibles: %s", exc)

    logger.info("Resumen recolección de mercado: %s", summary)
    return summary


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recolección de datos de mercado (Fase A)"
    )
    parser.add_argument(
        "--period", default=CURRENT_MONTH,
        help="Período para IPC (YYYY-MM). Por defecto: mes actual.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from src.db.session import session_scope

    with session_scope() as session:
        summary = run_market_pipeline(session, period=args.period)
        if not summary:
            logger.error(
                "No se recolectó nada. Revisa red o las URLs en .env "
                "(BCV_RATE_API_URL, BCV_IPC_API_URL, OVF_BASE_URL, BINANCE_P2P_URL)."
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())