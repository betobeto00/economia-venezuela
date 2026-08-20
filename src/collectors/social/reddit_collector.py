"""
Collector Reddit (multi-fuente)
===============================

Publicaciones de subreddits de discusión económica venezolana.

Fuentes (en orden de preferencia):
1. API JSON pública de Reddit (https://www.reddit.com/r/SUB.json)
   - Gratis, sin credenciales, solo necesita User-Agent descriptivo
   - Rate limits frágiles; se degrada con gracia
2. PRAW (Reddit API oficial) — cuando REDDIT_CLIENT_ID/SECRET están en .env
3. Zernio (ZERNIO_API_KEY) — fallback de pago cuando la pública falla

El cliente se inyecta para tests.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

import httpx

from src.config import settings
from src.models.news import SocialPost

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = ("vzla", "venezuela", "vzlaconomics")

REDDIT_UA = (
    "EconomiaVenezuela/0.1.0 (dashboard economico venezolano; "
    "contacto: dev@local)"
)

FETCH_TIMEOUT = 15.0


def _rss_fetch(subreddit: str, limit: int = 25) -> List[SocialPost]:
    """Fetch vía RSS de Reddit (sin credenciales, más tolerante que JSON)."""
    try:
        import feedparser
    except ImportError:
        logger.debug("feedparser no instalado, omitiendo RSS de Reddit")
        return []

    url = f"https://www.reddit.com/r/{subreddit}/.rss"
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": REDDIT_UA},
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 429:
            logger.warning("Reddit RSS rate limit (429) para r/%s", subreddit)
            return []
        if resp.status_code != 200:
            logger.debug("Reddit RSS %d para r/%s", resp.status_code, subreddit)
            return []
        feed = feedparser.parse(resp.text)
        posts = []
        for entry in feed.entries[:limit]:
            published = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                import calendar
                published = datetime.fromtimestamp(
                    calendar.timegm(entry.published_parsed), tz=timezone.utc
                )
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                import calendar
                published = datetime.fromtimestamp(
                    calendar.timegm(entry.updated_parsed), tz=timezone.utc
                )
            posts.append(SocialPost(
                source="reddit",
                channel=subreddit,
                title=(entry.get("title", "") or "")[:300],
                url=entry.get("link", ""),
                text=(entry.get("summary", "") or "")[:1000] or None,
                score=None,
                num_comments=None,
                published=published,
            ))
        return posts
    except Exception as exc:
        logger.debug("Reddit RSS falló para r/%s: %s", subreddit, exc)
        return []


def _public_json_fetch(url: str) -> Optional[dict]:
    """Fetch de la API JSON pública de Reddit (sin credenciales)."""
    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": REDDIT_UA, "Accept": "application/json"},
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 429:
            logger.warning("Reddit rate limit (429) para %s", url)
            return None
        if resp.status_code != 200:
            logger.warning("Reddit JSON %d para %s", resp.status_code, url)
            return None
        return resp.json()
    except Exception as exc:
        logger.debug("Reddit public JSON falló para %s: %s", url, exc)
        return None


def _extract_posts_from_json(data: dict, subreddit: str) -> List[SocialPost]:
    """Extrae posts de la respuesta JSON de Reddit."""
    children = data.get("data", {}).get("children", [])
    posts = []
    for child in children:
        d = child.get("data", {})
        if not d:
            continue
        created = d.get("created_utc")
        published = None
        if created:
            published = datetime.fromtimestamp(float(created), tz=timezone.utc)
        permalink = d.get("permalink", "")
        url = f"https://www.reddit.com{permalink}" if permalink else d.get("url", "")
        posts.append(SocialPost(
            source="reddit",
            channel=subreddit or d.get("subreddit", ""),
            title=(d.get("title", "") or "")[:300],
            url=url,
            text=(d.get("selftext", "") or "")[:1000] or None,
            score=d.get("score"),
            num_comments=d.get("num_comments"),
            published=published,
        ))
    return posts


def _zernio_fetch(subreddit: str, limit: int = 25) -> List[SocialPost]:
    """Fallback: Zernio API (credit-funded Reddit account)."""
    api_key = getattr(settings, "ZERNIO_API_KEY", None)
    if not api_key:
        return []
    try:
        resp = httpx.get(
            f"https://api.zernio.com/reddit/r/{subreddit}/new",
            params={"limit": min(limit, 25)},
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=FETCH_TIMEOUT,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return _extract_posts_from_json(data, subreddit)
    except Exception as exc:
        logger.debug("Zernio fallback falló para r/%s: %s", subreddit, exc)
        return []


class RedditCollector:
    """Publicaciones recientes de subreddits económicos venezolanos.

    Usa API JSON pública por defecto (sin credenciales).
    Fallback: praw (si REDDIT_CLIENT_ID/SECRET están configurados).
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        user_agent: Optional[str] = None,
        reddit=None,
    ):
        self.client_id = client_id or settings.REDDIT_CLIENT_ID
        self.client_secret = client_secret or settings.REDDIT_CLIENT_SECRET
        self.user_agent = user_agent or settings.REDDIT_USER_AGENT
        self._reddit = reddit

    def _get_praw_reddit(self):
        """Obtiene cliente PRAW (solo si hay credenciales)."""
        if self._reddit is not None:
            return self._reddit
        if not self.client_id or not self.client_secret:
            return None
        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent,
            )
            return self._reddit
        except Exception as exc:
            logger.debug("PRAW no disponible: %s", exc)
            return None

    def _fetch_rss(self, subreddit: str, limit: int = 25) -> List[SocialPost]:
        """Fetch vía RSS (gratis, sin credenciales, más tolerante)."""
        return _rss_fetch(subreddit, limit)

    def _fetch_public_json(self, subreddit: str, limit: int = 25) -> List[SocialPost]:
        """Fetch vía API JSON pública (gratis, sin credenciales)."""
        url = (
            f"https://www.reddit.com/r/{subreddit}/new.json"
            f"?limit={min(max(limit, 1), 25)}"
        )
        data = _public_json_fetch(url)
        if data:
            return _extract_posts_from_json(data, subreddit)
        return []

    def _fetch_praw(self, subreddit: str, limit: int = 25) -> List[SocialPost]:
        """Fetch vía PRAW (credenciales OAuth2)."""
        reddit = self._get_praw_reddit()
        if reddit is None:
            return []
        try:
            sub = reddit.subreddit(subreddit)
            posts = []
            for submission in sub.new(limit=limit):
                created = getattr(submission, "created_utc", None)
                published = None
                if created:
                    published = datetime.fromtimestamp(float(created), tz=timezone.utc)
                posts.append(SocialPost(
                    source="reddit",
                    channel=subreddit,
                    title=(getattr(submission, "title", "") or "")[:300],
                    url=(getattr(submission, "url", "") or ""),
                    text=(getattr(submission, "selftext", "") or "")[:1000] or None,
                    score=getattr(submission, "score", None),
                    num_comments=getattr(submission, "num_comments", None),
                    published=published,
                ))
            return posts
        except Exception as exc:
            logger.warning("Reddit PRAW fallo en r/%s: %s", subreddit, exc)
            return []

    def fetch_posts(
        self,
        subreddits: Optional[List[str]] = None,
        limit: int = 25,
    ) -> List[SocialPost]:
        """Publicaciones recientes de los subreddits indicados.

        Flujo: JSON público → PRAW → Zernio (cada uno como fallback del anterior).
        """
        targets = subreddits or list(DEFAULT_SUBREDDITS)
        all_posts: List[SocialPost] = []

        for subreddit_name in targets:
            subreddit_name = subreddit_name.strip().lstrip("r/")
            if not subreddit_name:
                continue

            posts = []

            # 1. Intentar RSS (gratis, más tolerante que JSON)
            posts = self._fetch_rss(subreddit_name, limit)

            # 2. Fallback: JSON público
            if not posts:
                posts = self._fetch_public_json(subreddit_name, limit)

            # 3. Fallback: PRAW (si hay credenciales)
            if not posts:
                posts = self._fetch_praw(subreddit_name, limit)

            # 4. Fallback: Zernio (pago)
            if not posts:
                posts = _zernio_fetch(subreddit_name, limit)

            if posts:
                all_posts.extend(posts)
                logger.info(
                    "Reddit r/%s: %d posts obtenidos", subreddit_name, len(posts)
                )
            else:
                logger.warning("Reddit r/%s: sin datos de ninguna fuente", subreddit_name)

        return all_posts
