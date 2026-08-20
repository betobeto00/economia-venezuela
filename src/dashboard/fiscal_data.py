"""
Datos fiscales para el dashboard
=================================

Capa pura (sin Streamlit) que expone documentos fiscales recientes
(Gaceta Oficial, Asamblea Nacional, etc.) para la sección del dashboard.
"""

import logging
from typing import List

logger = logging.getLogger(__name__)


def recent_gacetas(days: int = 30, limit: int = 20) -> List[dict]:
    """Gacetas Oficiales recientes (simula lectura desde archivos guardados)."""
    try:
        from src.collectors.fiscal.gaceta_collector import GacetaOficialCollector
        collector = GacetaOficialCollector()
        return collector.fetch_recientes(days=days)[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.debug("recent_gacetas no disponible: %s", exc)
        return []


def recent_leyes(limit: int = 10) -> List[dict]:
    """Leyes y actos recientes de la Asamblea Nacional."""
    try:
        from src.collectors.fiscal.an_collector import ANCollector
        collector = ANCollector()
        return collector.fetch_documentos(keywords="")[:limit]
    except Exception as exc:  # noqa: BLE001
        logger.debug("recent_leyes no disponible: %s", exc)
        return []


def fiscal_summary() -> dict:
    """Resumen del estado de las fuentes fiscales."""
    gacetas = recent_gacetas(days=7, limit=5)
    leyes = recent_leyes(limit=5)
    return {
        "gacetas_count": len(gacetas),
        "leyes_count": len(leyes),
        "gacetas": gacetas,
        "leyes": leyes,
    }
