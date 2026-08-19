"""
Datos de noticias y sentimiento para el dashboard (Fase A)
==========================================================

Capa pura (sin Streamlit) que lee de la base los últimos artículos, posts y
el resumen de sentimiento persistidos por el pipeline. Todo acceso a DB se
hace dentro de un contexto de sesión; ante fallo de conexión degrada a
valores vacíos (la UI muestra mensaje amigable, no rompe la página).
"""

import logging
from typing import List

from src.models.news import NewsArticle

logger = logging.getLogger(__name__)


def sentiment_summary() -> dict:
    """Resumen agregado de sentimiento de noticias y posts.

    Returns:
        Dict con total, positive, neutral, negative y mean_score
        (todo a 0 si no hay datos o la base falla).
    """
    try:
        from src.db.repositories import NewsRepository
        from src.db.session import session_scope

        with session_scope() as session:
            return NewsRepository(session).sentiment_summary()
    except Exception as exc:  # noqa: BLE001 - DB caída u otro fallo
        logger.warning("sentiment_summary no disponible: %s", exc)
        return {"total": 0, "positive": 0, "neutral": 0, "negative": 0,
                "mean_score": 0.0}


def recent_articles(limit: int = 10) -> List[NewsArticle]:
    """Últimos artículos persistidos (vacío si no hay datos o falla la DB)."""
    try:
        from src.db.repositories import NewsRepository
        from src.db.session import session_scope

        with session_scope() as session:
            return NewsRepository(session).list_articles(limit=limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("recent_articles no disponible: %s", exc)
        return []


def sentiment_label(mean_score: float) -> str:
    """Etiqueta legible para un promedio de sentimiento."""
    if mean_score > 0.15:
        return "Positivo"
    if mean_score < -0.15:
        return "Negativo"
    return "Neutral"