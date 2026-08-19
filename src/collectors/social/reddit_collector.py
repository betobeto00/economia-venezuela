"""
Collector Reddit
================

Publicaciones de subreddits de discusión económica (por defecto r/vzla y
r/venezuela). Usa ``praw`` con credenciales de ``settings`` (REDDIT_CLIENT_ID,
REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT).

El cliente ``praw`` se inyecta para tests (``reddit=None``).
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.config import settings
from src.models.news import SocialPost

logger = logging.getLogger(__name__)

DEFAULT_SUBREDDITS = ("vzla", "venezuela")


class RedditCollector:
    """Publicaciones recientes de subreddits económicos venezolanos."""

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

    def _get_reddit(self):
        if self._reddit is not None:
            return self._reddit
        import praw

        if not self.client_id or not self.client_secret:
            raise RuntimeError(
                "Reddit: faltan REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET en .env"
            )
        self._reddit = praw.Reddit(
            client_id=self.client_id,
            client_secret=self.client_secret,
            user_agent=self.user_agent,
        )
        return self._reddit

    def _post_from_submission(self, submission, channel: str) -> SocialPost:
        published = None
        created = getattr(submission, "created_utc", None)
        if created:
            published = datetime.fromtimestamp(float(created), tz=timezone.utc)
        return SocialPost(
            source="reddit",
            channel=channel,
            title=(getattr(submission, "title", "") or "")[:300],
            url=(getattr(submission, "url", "") or ""),
            text=(getattr(submission, "selftext", "") or "")[:1000] or None,
            score=getattr(submission, "score", None),
            num_comments=getattr(submission, "num_comments", None),
            published=published,
        )

    def fetch_posts(self, subreddits: Optional[List[str]] = None,
                    limit: int = 25) -> List[SocialPost]:
        """Publicaciones recientes de los subreddits indicados."""
        reddit = self._get_reddit()
        targets = subreddits or list(DEFAULT_SUBREDDITS)
        posts: List[SocialPost] = []
        for subreddit_name in targets:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.new(limit=limit):
                    posts.append(self._post_from_submission(submission, subreddit_name))
            except Exception as exc:  # noqa: BLE001 - un sub no debe romper el resto
                logger.warning("Reddit: fallo en r/%s: %s", subreddit_name, exc)
        return posts