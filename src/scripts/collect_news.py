"""
Recolección de Noticias y Sentimiento (CLI)
===========================================

Orquesta los collectors de contenido (RSS + Reddit) y persiste en PostgreSQL,
con análisis de sentimiento léxico sobre lo nuevo recolectado:

    python -m src.scripts.collect_news

La lógica reutilizable es ``run_news_pipeline(session, ...)`` (usada por el
CLI y el scheduler) con dependencias inyectadas para tests. Cada fuente se
intenta de forma independiente: un fallo no impide guardar las demás.
"""

import argparse
import logging
import sys
from typing import List, Optional

from src.collectors.news.rss_collector import RSSCollector
from src.collectors.social.reddit_collector import RedditCollector
from src.db.repositories import NewsRepository

logger = logging.getLogger(__name__)


def run_news_pipeline(
    session,
    rss: Optional[RSSCollector] = None,
    reddit: Optional[RedditCollector] = None,
    per_feed_limit: int = 25,
    reddit_limit: int = 25,
    relevance_min_strong: int = 1,
    relevance_min_weak: int = 2,
) -> dict:
    """Recolecta noticias y posts, filtra por relevancia económica, persiste
    y analiza el sentimiento de lo guardado.

    Args:
        session: Sesión SQLAlchemy (persistencia).
        rss: RSSCollector (por defecto se instancia con feeds configurados).
        reddit: RedditCollector (por defecto se instancia; requiere credenciales).
        per_feed_limit / reddit_limit: Límites por fuente.
        relevance_min_strong / relevance_min_weak: Umbrales del filtro de
            relevancia económica (ver ``analyzers.relevance``).

    Returns:
        Dict de resumen: {news: {fetched, relevant, saved},
        social: {fetched, relevant, saved}, sentiment: {analyzed, saved}}.
    """
    rss = rss or RSSCollector()
    reddit = reddit or RedditCollector()
    repo = NewsRepository(session)

    summary: dict = {
        "news": {"fetched": 0, "relevant": 0, "saved": 0},
        "social": {"fetched": 0, "relevant": 0, "saved": 0},
        "sentiment": {"analyzed": 0, "saved": 0},
    }

    # RSS: noticias → filtro de relevancia económica
    articles: List = []
    try:
        articles = rss.fetch_articles(per_feed_limit=per_feed_limit)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RSS no disponible: %s", exc)
    summary["news"]["fetched"] = len(articles)
    articles = _filter_relevant_articles(articles, relevance_min_strong, relevance_min_weak)
    summary["news"]["relevant"] = len(articles)
    summary["news"]["saved"] = repo.save_articles(articles)

    # Reddit: posts sociales → filtro de relevancia económica
    posts: List = []
    try:
        posts = reddit.fetch_posts(limit=reddit_limit)
    except Exception as exc:  # noqa: BLE001 - sin credenciales o API caída
        logger.warning("Reddit no disponible: %s", exc)
    summary["social"]["fetched"] = len(posts)
    posts = _filter_relevant_posts(posts, relevance_min_strong, relevance_min_weak)
    summary["social"]["relevant"] = len(posts)
    summary["social"]["saved"] = repo.save_posts(posts)

    # Sentimiento sobre lo nuevo recolectado
    sentiment_scores = _build_sentiment(repo, articles, posts)
    summary["sentiment"]["analyzed"] = len(sentiment_scores)
    summary["sentiment"]["saved"] = repo.save_sentiment(sentiment_scores)

    logger.info("Resumen noticias/sentimiento: %s", summary)
    return summary


def _filter_relevant_articles(articles, min_strong: int, min_weak: int) -> List:
    """Conserva solo los artículos económicamente relevantes."""
    from src.analyzers.relevance import is_economically_relevant

    relevant = []
    for article in articles:
        text = article.title
        if article.summary:
            text = f"{text}. {article.summary}"
        if is_economically_relevant(text, min_strong, min_weak):
            relevant.append(article)
        else:
            logger.debug("Artículo sin relevancia económica omitido: %s", article.title[:60])
    return relevant


def _filter_relevant_posts(posts, min_strong: int, min_weak: int) -> List:
    """Conserva solo los posts económicamente relevantes."""
    from src.analyzers.relevance import is_economically_relevant

    relevant = []
    for post in posts:
        text = post.title
        if post.text:
            text = f"{text}. {post.text}"
        if is_economically_relevant(text, min_strong, min_weak):
            relevant.append(post)
    return relevant


def _build_sentiment(repo: NewsRepository, articles, posts) -> List:
    """Construye SentimentScore para artículos y posts nuevos guardados.

    Solo se analizan los ítems insertados (idemponencia del repo): los que ya
    existían se omiten. Reutiliza ``to_sentiment_score`` del analizador.
    """
    from sqlalchemy import select

    from src.analyzers.sentiment import to_sentiment_score
    from src.db.models import NewsArticleORM, SocialPostORM

    scores = []

    # Relación url → id de lo persistido (los insertados en esta corrida)
    for article in articles:
        orm = repo.session.scalar(
            select(NewsArticleORM.id).where(
                NewsArticleORM.source == article.source,
                NewsArticleORM.url == article.url,
            )
        )
        if orm is None:
            continue
        text = article.title
        if article.summary:
            text = f"{text}. {article.summary}"
        score = to_sentiment_score("news", int(orm), text)
        if score is not None:
            scores.append(score)

    for post in posts:
        orm = repo.session.scalar(
            select(SocialPostORM.id).where(
                SocialPostORM.source == post.source,
                SocialPostORM.url == post.url,
            )
        )
        if orm is None:
            continue
        text = post.title
        if post.text:
            text = f"{text}. {post.text}"
        score = to_sentiment_score("social", int(orm), text)
        if score is not None:
            scores.append(score)

    return scores


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recolección de noticias y sentimiento (Fase A)"
    )
    parser.add_argument(
        "--feeds", default=None,
        help="URLs RSS separadas por coma (por defecto: settings.RSS_FEEDS).",
    )
    parser.add_argument(
        "--per-feed-limit", type=int, default=25,
        help="Artículos máximos por feed.",
    )
    parser.add_argument(
        "--reddit-limit", type=int, default=25,
        help="Posts máximos por subreddit.",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    from src.db.session import session_scope

    feeds = None
    if args.feeds:
        feeds = [u for u in args.feeds.split(",") if u.strip()]

    with session_scope() as session:
        summary = run_news_pipeline(
            session,
            rss=RSSCollector(feeds=feeds) if feeds else None,
            per_feed_limit=args.per_feed_limit,
            reddit_limit=args.reddit_limit,
        )
        if not summary["news"]["fetched"] and not summary["social"]["fetched"]:
            logger.error(
                "No se recolectó nada. Revisa red, RSS_FEEDS y las credenciales "
                "REDDIT_CLIENT_ID/SECRET en .env."
            )
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())