"""
Recolección de noticias y redes (Fase A)
==========================================

Collectors de contenido informativo: RSS, LLM-powered web search y redes sociales.
"""

from src.collectors.news.rss_collector import RSSCollector, parse_feed
from src.collectors.news.llm_news_collector import LLMNewsCollector, fetch_news_llm

__all__ = [
    "RSSCollector",
    "parse_feed",
    "LLMNewsCollector",
    "fetch_news_llm",
]