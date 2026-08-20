"""
Datos sociales (Reddit + Sentimiento) para el dashboard
========================================================

Capa pura (sin Streamlit) que lee de la base los posts de Reddit,
puntajes de sentimiento y resúmenes agregados. Degradación segura ante fallos.
"""

import logging
from typing import Dict, List

import pandas as pd

logger = logging.getLogger(__name__)


def social_posts_with_sentiment(limit: int = 50) -> List[dict]:
    """Posts de Reddit con sentimiento asociado (si existe).

    Returns:
        Lista de dicts con: channel, title, url, text, score,
        num_comments, published, sentiment_score, sentiment_label.
    """
    try:
        from src.db.repositories import NewsRepository
        from src.db.session import session_scope

        with session_scope() as session:
            repo = NewsRepository(session)
            posts = repo.list_posts(limit=limit)
            # SocialPost no tiene id; usar ORM directamente para sentimental mapping
            from src.db.models import SocialPostORM, SentimentScoreORM
            from sqlalchemy import select

            posts_orm = session.scalars(
                select(SocialPostORM).order_by(SocialPostORM.published.desc()).limit(limit)
            ).all()
            # Map sentiment by item_id (ORM id)
            sent_map = {}
            for s in session.scalars(
                select(SentimentScoreORM).where(SentimentScoreORM.item_type == "social")
            ).all():
                sent_map[s.item_id] = s

        result = []
        for p in posts_orm:
            sent = sent_map.get(p.id)
            result.append({
                "channel": p.channel,
                "title": p.title,
                "url": p.url,
                "text": p.text or "",
                "score": p.score,
                "num_comments": p.num_comments,
                "published": p.published,
                "sentiment_score": float(sent.score) if sent else None,
                "sentiment_label": sent.label if sent else None,
            })
        return result
    except Exception as exc:  # noqa: BLE001
        logger.warning("social_posts_with_sentiment no disponible: %s", exc)
        return []


def sentiment_by_item(item_type: str = "social", limit: int = 50) -> pd.DataFrame:
    """DataFrame de sentimiento por ítem (noticias o social).

    Returns:
        DataFrame con columnas: item_id, text, score, label, analyzed_at.
    """
    try:
        from src.db.repositories import NewsRepository
        from src.db.session import session_scope

        with session_scope() as session:
            repo = NewsRepository(session)
            scores = repo.list_sentiment(item_type=item_type, limit=limit)

        if not scores:
            return pd.DataFrame()

        return pd.DataFrame([
            {
                "item_id": s.item_id,
                "text": s.text,
                "score": s.score,
                "label": s.label,
                "analyzed_at": s.analyzed_at,
            }
            for s in scores
        ])
    except Exception as exc:  # noqa: BLE001
        logger.warning("sentiment_by_item no disponible: %s", exc)
        return pd.DataFrame()


def social_summary() -> Dict[str, object]:
    """Resumen agregado de actividad social y sentimiento.

    Returns:
        Dict con: total_posts, avg_score, avg_comments, sentiment_dist,
        sentiment_mean, posts_per_channel.
    """
    try:
        from sqlalchemy import func, select
        from src.db.models import SocialPostORM, SentimentScoreORM
        from src.db.session import session_scope

        with session_scope() as session:
            # Posts stats
            total_posts = session.scalar(
                select(func.count(SocialPostORM.id))
            ) or 0

            avg_score = session.scalar(
                select(func.avg(SocialPostORM.score))
            )
            avg_comments = session.scalar(
                select(func.avg(SocialPostORM.num_comments))
            )

            # Posts per channel
            channel_rows = session.execute(
                select(SocialPostORM.channel, func.count(SocialPostORM.id))
                .group_by(SocialPostORM.channel)
            ).all()
            posts_per_channel = {ch: int(n) for ch, n in channel_rows}

            # Sentiment distribution
            sent_rows = session.execute(
                select(SentimentScoreORM.label, func.count(SentimentScoreORM.id))
                .where(SentimentScoreORM.item_type == "social")
                .group_by(SentimentScoreORM.label)
            ).all()
            sentiment_dist = {label: int(n) for label, n in sent_rows}

            mean_score = session.scalar(
                select(func.avg(SentimentScoreORM.score))
                .where(SentimentScoreORM.item_type == "social")
            )

        return {
            "total_posts": int(total_posts),
            "avg_score": round(float(avg_score or 0), 1),
            "avg_comments": round(float(avg_comments or 0), 1),
            "sentiment_dist": sentiment_dist,
            "sentiment_mean": round(float(mean_score or 0), 4),
            "posts_per_channel": posts_per_channel,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("social_summary no disponible: %s", exc)
        return {
            "total_posts": 0,
            "avg_score": 0,
            "avg_comments": 0,
            "sentiment_dist": {},
            "sentiment_mean": 0,
            "posts_per_channel": {},
        }
