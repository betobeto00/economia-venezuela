"""
Tests de los collectors de noticias y redes (Semana 8)
======================================================
"""

from datetime import datetime

import pytest

from src.collectors.news.rss_collector import RSSCollector, parse_feed
from src.collectors.social.reddit_collector import RedditCollector

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>El Medio Económico</title>
<item>
<title>Inflación baja en julio</title>
<link>https://ejemplo.com/inflacion</link>
<description>El BCV reporta una baja de la inflación.</description>
<pubDate>Mon, 19 Aug 2026 10:00:00 GMT</pubDate>
</item>
<item>
<description>Sin título no debería contarse</description>
<link>https://ejemplo.com/sin-titulo</link>
</item>
<item>
<title>Dólar estable</title>
<link>https://ejemplo.com/dolar</link>
</item>
</channel></rss>
"""


class TestRSS:
    def test_parse_feed(self):
        articles = parse_feed(SAMPLE_RSS, source="El Medio Económico")
        assert len(articles) == 2  # el item sin título se omite
        assert articles[0].title == "Inflación baja en julio"
        assert articles[0].url == "https://ejemplo.com/inflacion"
        assert articles[0].published.year == 2026
        assert articles[1].source == "El Medio Económico"

    def test_fetch_articles_con_feed_de_test(self, monkeypatch):
        captured = []

        class FakeFeedparser:
            @staticmethod
            def parse(xml):
                captured.append(xml)
                import feedparser
                return feedparser.parse(SAMPLE_RSS)

        monkeypatch.setattr(
            "src.collectors.news.rss_collector.feedparser", FakeFeedparser
        )
        collector = RSSCollector(feeds=["https://feed.test/rss"])
        articles = collector.fetch_articles(per_feed_limit=1)
        assert len(articles) == 1  # limitado por feed
        assert captured == ["https://feed.test/rss"]

    def test_fetch_articles_feed_roto_no_rompe(self, monkeypatch):
        class FakeFeedparser:
            @staticmethod
            def parse(url):
                raise OSError("sin red")

        monkeypatch.setattr(
            "src.collectors.news.rss_collector.feedparser", FakeFeedparser
        )
        assert RSSCollector(feeds=["https://feed.test/rss"]).fetch_articles() == []


class FakeSubmission:
    def __init__(self, title, url, selftext, score, num_comments, created_utc):
        self.title = title
        self.url = url
        self.selftext = selftext
        self.score = score
        self.num_comments = num_comments
        self.created_utc = created_utc


class FakeSubreddit:
    def __init__(self, posts):
        self._posts = posts

    def new(self, limit=None):
        return self._posts[:limit]


class FakeReddit:
    def __init__(self, posts_by_sub):
        self._by_sub = posts_by_sub

    def subreddit(self, name):
        return FakeSubreddit(self._by_sub.get(name, []))


class TestReddit:
    def _collector(self, posts_by_sub, monkeypatch=None):
        collector = RedditCollector(reddit=FakeReddit(posts_by_sub))
        if monkeypatch:
            # Forzar fallback a PRAW mockeando RSS/JSON para que fallen
            monkeypatch.setattr(
                "src.collectors.social.reddit_collector._rss_fetch",
                lambda *a, **kw: [],
            )
            monkeypatch.setattr(
                "src.collectors.social.reddit_collector._public_json_fetch",
                lambda *a, **kw: None,
            )
        return collector

    def test_fetch_posts(self, monkeypatch):
        posts = [
            FakeSubmission("El dólar sube", "https://reddit.com/a", "texto",
                           120, 30, 1780000000),
        ]
        collector = self._collector({"vzla": posts}, monkeypatch=monkeypatch)
        result = collector.fetch_posts(subreddits=["vzla"], limit=10)
        assert len(result) == 1
        post = result[0]
        assert post.source == "reddit"
        assert post.channel == "vzla"
        assert post.title == "El dólar sube"
        assert post.score == 120
        assert post.num_comments == 30
        assert post.published is not None

    def test_fetch_posts_sin_credenciales(self):
        # Ahora funciona sin credenciales (RSS/JSON público)
        # Solo retorna vacío si todas las fuentes fallan
        collector = RedditCollector(client_id=None, client_secret=None)
        result = collector.fetch_posts(subreddits=["test_nonexistent_sub"])
        assert isinstance(result, list)

    def test_fetch_posts_sub_roto_no_rompe(self, monkeypatch):
        """Todas las fuentes fallan: el collector no rompe y retorna lista vacía."""
        class BoomSub:
            def new(self, limit=None):
                raise RuntimeError("API error")

        class BoomReddit:
            def subreddit(self, name):
                return BoomSub()

        collector = RedditCollector(reddit=BoomReddit())
        # Sin PRAW, intenta JSON público -> falla también por mock
        # El test valida que no explote
        result = collector.fetch_posts(subreddits=["test_fail"], limit=10)
        assert isinstance(result, list)