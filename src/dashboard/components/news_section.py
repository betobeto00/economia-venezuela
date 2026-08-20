"""
Sección de Noticias y Sentimiento del dashboard (Streamlit)
============================================================

Renderiza el resumen de sentimiento de noticias/posts y los últimos
titulares. Toda la lógica de datos vive en ``news_data.py``; aquí solo hay
presentación con manejo de estados (carga, vacío, error).

Reglas (skill frontend-visionary-artisan):
- Sin valores hardcodeados: todo sale de la capa de datos.
- Resiliencia: si la base no responde o no hay datos, mensaje amigable.
- Caché con TTL para recálculos pesados.
"""

import logging

import streamlit as st

from src.dashboard import theme
from src.dashboard.news_data import (
    recent_articles,
    recent_posts,
    sentiment_label,
    sentiment_summary,
)

logger = logging.getLogger(__name__)


@st.cache_data(ttl=300, show_spinner=False)
def _news_snapshot() -> dict:
    """Snapshot cacheadable de noticias y sentimiento (serializable)."""
    summary = sentiment_summary()
    articles = recent_articles(limit=10)
    posts = recent_posts(limit=10)
    return {
        "summary": summary,
        "articles": [
            {"source": a.source, "title": a.title, "url": a.url,
             "published": a.published.isoformat() if a.published else None}
            for a in articles
        ],
        "posts": [
            {"source": p.source, "channel": p.channel, "title": p.title,
             "url": p.url, "score": p.score, "num_comments": p.num_comments,
             "published": p.published.isoformat() if p.published else None}
            for p in posts
        ],
    }


def _sentiment_tone(mean: float) -> str:
    """Color semáforo para el promedio de sentimiento."""
    if mean > 0.15:
        return theme.PALETTE["verde"]
    if mean < -0.15:
        return theme.PALETTE["rojo"]
    return theme.PALETTE["amarillo"]


def render_news_section() -> None:
    """Renderiza la sección de noticias y sentimiento completa."""
    with st.spinner("Cargando noticias y sentimiento..."):
        try:
            data = _news_snapshot()
        except Exception as exc:  # noqa: BLE001 - nunca romper el dashboard
            logger.warning("Noticias no disponibles: %s", exc)
            st.warning(
                "⚠️ No se pudo acceder a la base de datos de noticias. "
                "Verifica DATABASE_URL y que el servicio esté levantado."
            )
            return

    summary = data["summary"]

    if not summary["total"]:
        st.info(
            "📭 Todavía no hay noticias ni posts analizados. Ejecuta "
            "`python -m src.scripts.collect_news` (o espera el job del scheduler) "
            "para poblar esta sección."
        )
        return

    st.subheader("📰 Noticias y Sentimiento")

    # Tarjetas de sentimiento
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "🎯 Tono general",
        sentiment_label(summary["mean_score"]),
        help=f"Promedio: {summary['mean_score']:+.3f} (escala -1 a +1)",
    )
    c2.metric("🟢 Positivas", summary["positive"])
    c3.metric("🟡 Neutrales", summary["neutral"])
    c4.metric("🔴 Negativas", summary["negative"])

    # Barra de distribución de sentimiento
    st.markdown("### 📊 Distribución del sentimiento")
    tone_color = _sentiment_tone(summary["mean_score"])
    st.markdown(
        f"""
        <div style="display:flex; gap:2px; height:10px; border-radius:5px; overflow:hidden;">
          <div style="width:{_pct(summary['positive'], summary['total'])}%; background:#2CA58D;"></div>
          <div style="width:{_pct(summary['neutral'], summary['total'])}%; background:#F2C14E;"></div>
          <div style="width:{_pct(summary['negative'], summary['total'])}%; background:#C0392B;"></div>
        </div>
        <p style="color:{tone_color}; font-weight:600; margin-top:6px;">
          Tono medio: {summary['mean_score']:+.2f}
        </p>
        """,
        unsafe_allow_html=True,
    )

    # Últimos titulares (con links)
    articles = data["articles"]
    if articles:
        st.markdown("### 🗞️ Últimos titulares")
        for article in articles:
            date = (article["published"] or "")[:10]
            url = article.get("url", "")
            title = article["title"]
            if url:
                st.markdown(
                    f"- [{title}]({url}) — *{article['source']}*"
                    + (f" ({date})" if date else "")
                )
            else:
                st.markdown(
                    f"- **{title}** — *{article['source']}*"
                    + (f" ({date})" if date else "")
                )

    # Posts de Reddit
    posts = data.get("posts", [])
    if posts:
        st.markdown("### 💬 Discusión en Reddit")
        for post in posts:
            date = (post.get("published") or "")[:10]
            url = post.get("url", "")
            title = post["title"]
            channel = post.get("channel", "")
            score = post.get("score") or 0
            comments = post.get("num_comments") or 0
            meta = f"⬆️ {score} | 💬 {comments} | r/{channel}"
            if url:
                st.markdown(f"- [{title}]({url}) — {meta}")
            else:
                st.markdown(f"- **{title}** — {meta}")


def _pct(value: int, total: int) -> float:
    """Porcentaje para la barra de distribución (0 si total es 0)."""
    return round(100 * value / total, 1) if total else 0.0