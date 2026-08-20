"""
Datos de redes sociales (Reddit) para el dashboard
===================================================

Capa pura (sin Streamlit) que lee posts y sentimiento de Reddit.
"""

import logging
from typing import List

import pandas as pd
from src.models.news import SocialPost
from src.db.models import SocialPostORM, SentimentScoreORM
from sqlalchemy import select, desc

logger = logging.getLogger(__name__)


def recent_posts(limit: int = 20) -> List[dict]:
    """Últimos posts de Reddit con sus scores de sentimiento."""
    try:
        from src.db.session import session_scope

        with session_scope() as session:
            stmt = (
                select(SocialPostORM)
                .order_by(desc(SocialPostORM.published))
                .limit(limit)
            )
            posts = session.scalars(stmt).all()
            
            result = []
            for p in posts:
                # Get sentiment for this post
                sent_stmt = select(SentimentScoreORM).where(
                    SentimentScoreORM.item_type == "social",
                    SentimentScoreORM.item_id == p.id
                )
                sent = session.scalars(sent_stmt).first()
                
                result.append({
                    "id": p.id,
                    "source": p.source,
                    "channel": p.channel,
                    "title": p.title,
                    "url": p.url,
                    "text": p.text,
                    "score": p.score,
                    "num_comments": p.num_comments,
                    "published": p.published,
                    "sentiment_score": sent.score if sent else None,
                    "sentiment_label": sent.label if sent else None,
                })
            return result
    except Exception as exc:
        logger.warning("recent_posts no disponible: %s", exc)
        return []


def social_posts_with_sentiment(limit: int = 50) -> List[dict]:
    """Alias para compatibilidad con dashboard."""
    return recent_posts(limit)


def social_summary() -> dict:
    """Resumen completo para dashboard: posts + sentimiento."""
    try:
        from src.db.session import session_scope

        with session_scope() as session:
            # Posts
            stmt = (
                select(SocialPostORM)
                .order_by(desc(SocialPostORM.published))
                .limit(100)
            )
            posts = session.scalars(stmt).all()
            
            if not posts:
                return {
                    "total_posts": 0,
                    "avg_score": 0,
                    "avg_comments": 0,
                    "sentiment_mean": 0.0,
                    "sentiment_dist": {},
                    "posts_per_channel": {},
                }
            
            # Sentiment for social posts
            post_ids = [p.id for p in posts]
            sent_stmt = select(SentimentScoreORM).where(
                SentimentScoreORM.item_type == "social",
                SentimentScoreORM.item_id.in_(post_ids)
            )
            scores = session.scalars(sent_stmt).all()
            
            # Stats
            total_posts = len(posts)
            avg_score = sum(p.score or 0 for p in posts) / total_posts
            avg_comments = sum(p.num_comments or 0 for p in posts) / total_posts
            
            if scores:
                sentiment_mean = sum(s.score for s in scores) / len(scores)
                positive = sum(1 for s in scores if s.label == "positive")
                neutral = sum(1 for s in scores if s.label == "neutral")
                negative = sum(1 for s in scores if s.label == "negative")
                sentiment_dist = {
                    "positive": positive,
                    "neutral": neutral,
                    "negative": negative,
                }
            else:
                sentiment_mean = 0.0
                sentiment_dist = {"positive": 0, "neutral": 0, "negative": 0}
            
            # Posts per channel
            posts_per_channel = {}
            for p in posts:
                posts_per_channel[p.channel] = posts_per_channel.get(p.channel, 0) + 1
            
            return {
                "total_posts": total_posts,
                "avg_score": round(avg_score, 1),
                "avg_comments": round(avg_comments, 1),
                "sentiment_mean": round(sentiment_mean, 4),
                "sentiment_dist": sentiment_dist,
                "posts_per_channel": posts_per_channel,
            }
    except Exception as exc:
        logger.warning("social_summary no disponible: %s", exc)
        return {
            "total_posts": 0,
            "avg_score": 0,
            "avg_comments": 0,
            "sentiment_mean": 0.0,
            "sentiment_dist": {},
            "posts_per_channel": {},
        }


def sentiment_by_item(item_type: str = "social", limit: int = 50) -> pd.DataFrame:
    """DataFrame con detalle de sentimiento por ítem."""
    try:
        from src.db.session import session_scope

        with session_scope() as session:
            stmt = (
                select(SentimentScoreORM)
                .where(SentimentScoreORM.item_type == item_type)
                .order_by(desc(SentimentScoreORM.analyzed_at))
                .limit(limit)
            )
            scores = session.scalars(stmt).all()
            
            if not scores:
                return pd.DataFrame(columns=["item_id", "text", "score", "label"])
            
            return pd.DataFrame([
                {
                    "item_id": s.item_id,
                    "text": s.text,
                    "score": float(s.score),
                    "label": s.label,
                }
                for s in scores
            ])
    except Exception as exc:
        logger.warning("sentiment_by_item no disponible: %s", exc)
        return pd.DataFrame(columns=["item_id", "text", "score", "label"])


def posts_by_channel(limit: int = 50) -> dict:
    """Posts agrupados por subreddit/canal."""
    try:
        from src.db.session import session_scope

        with session_scope() as session:
            stmt = (
                select(SocialPostORM)
                .order_by(desc(SocialPostORM.published))
                .limit(limit)
            )
            posts = session.scalars(stmt).all()
            
            by_channel = {}
            for p in posts:
                if p.channel not in by_channel:
                    by_channel[p.channel] = []
                by_channel[p.channel].append({
                    "title": p.title,
                    "url": p.url,
                    "published": p.published,
                    "score": p.score,
                    "num_comments": p.num_comments,
                })
            return by_channel
    except Exception as exc:
        logger.warning("posts_by_channel no disponible: %s", exc)
        return {}