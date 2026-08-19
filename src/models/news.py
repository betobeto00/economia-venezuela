"""
Modelos de noticias y redes sociales (Fase A)
=============================================

Entidades normalizadas para el contenido informativo y social que alimenta
los análisis de sentimiento y contexto macroeconómico.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class NewsArticle(BaseModel):
    """Artículo de noticias de un feed RSS.

    Atributos:
        source: Nombre del medio/feed.
        title: Título del artículo.
        url: URL del artículo.
        published: Fecha de publicación (opcional).
        summary: Resumen/descripción (opcional).
    """

    source: str
    title: str
    url: str
    published: Optional[datetime] = None
    summary: Optional[str] = None


class SocialPost(BaseModel):
    """Publicación de una red social (p.ej. Reddit).

    Atributos:
        source: Red social (``reddit`` por defecto).
        channel: Comunidad/canal (subreddit, etc.).
        title: Título de la publicación.
        url: URL de la publicación.
        text: Cuerpo de la publicación (opcional).
        score: Votos/puntuación (opcional).
        num_comments: Número de comentarios (opcional).
        published: Fecha de publicación (opcional).
    """

    source: str = "reddit"
    channel: str
    title: str
    url: str
    text: Optional[str] = None
    score: Optional[int] = None
    num_comments: Optional[int] = None
    published: Optional[datetime] = None


class SentimentScore(BaseModel):
    """Puntaje de sentimiento de un ítem de texto (noticia o post).

    Atributos:
        item_type: ``news`` (artículo) o ``social`` (post).
        item_id: Id del ítem en su tabla (news_articles / social_posts).
        text: Texto analizado (título o título+resumen).
        score: Valor en [-1, 1] (positivo = optimista/positivo).
        label: ``positive``, ``neutral`` o ``negative``.
        analyzed_at: Fecha del análisis (opcional, se asigna al persistir).
    """

    item_type: str
    item_id: int
    text: str
    score: float
    label: str
    analyzed_at: Optional[datetime] = None