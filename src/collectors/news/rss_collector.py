"""
Collector RSS de noticias
==========================

Agrega feeds RSS de medios (por defecto, fuentes económicas venezolanas
configurables en ``RSS_FEEDS``). Usa ``feedparser``.

El parseo es tolerante: las entradas sin título o URL se omiten.
"""

import logging
from datetime import datetime
from typing import List, Optional

import feedparser

from src.config import settings
from src.models.news import NewsArticle

logger = logging.getLogger(__name__)


def _to_article(entry, source: str) -> Optional[NewsArticle]:
    title = (entry.get("title") or "").strip()
    url = entry.get("link")
    if not title or not url:
        return None
    published = None
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            published = datetime(*published_parsed[:6])
        except (TypeError, ValueError):
            published = None
    return NewsArticle(
        source=source,
        title=title[:300],
        url=url,
        published=published,
        summary=(entry.get("summary") or "")[:500] or None,
    )


def parse_feed(xml_text: str, source: str) -> List[NewsArticle]:
    """Convierte XML de un feed RSS en ``NewsArticle`` (tolerante)."""
    parsed = feedparser.parse(xml_text)
    return [a for a in (_to_article(e, source) for e in parsed.entries) if a]


def _default_feeds() -> List[str]:
    return [url for url in settings.RSS_FEEDS.split(",") if url.strip()]


class RSSCollector:
    """Agrega noticias de los feeds RSS configurados."""

    def __init__(self, feeds: Optional[List[str]] = None):
        self.feeds = feeds if feeds is not None else _default_feeds()

    def fetch_articles(self, per_feed_limit: int = 25) -> List[NewsArticle]:
        """Artículos de todos los feeds (limitados por feed)."""
        articles: List[NewsArticle] = []
        for feed_url in self.feeds:
            try:
                parsed = feedparser.parse(feed_url)
                source = (parsed.feed.get("title") or feed_url).strip()
                feed_articles = [
                    a for a in (_to_article(e, source) for e in parsed.entries) if a
                ]
                articles.extend(feed_articles[:per_feed_limit])
            except Exception as exc:  # noqa: BLE001 - un feed no debe romper el resto
                logger.warning("RSS: fallo al leer %s: %s", feed_url, exc)
        return articles