"""
LLM-Powered News Collector con Web Search
==========================================

Combina:
1. Google News RSS (gratis, sin API key) - feeds de noticias venezolanas
2. DuckDuckGo HTML scraping - búsqueda web general
3. LLM chain - análisis, filtrado y enriquecimiento de contenido

No requiere NEWS_API_KEY ni credenciales externas.
"""

import logging
import re
import time
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from urllib.parse import quote_plus, urljoin

import feedparser
import httpx
from bs4 import BeautifulSoup

from src.config import settings
from src.analyzers.llm import chat_completion, LLMError
from src.models.news import NewsArticle

logger = logging.getLogger(__name__)

# Google News RSS feeds para Venezuela/economía
GOOGLE_NEWS_RSS = [
    "https://news.google.com/rss/search?q=venezuela+econom%C3%ADa&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=venezuela+inflaci%C3%B3n&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=venezuela+d%C3%B3lar&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=venezuela+petr%C3%B3leo&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=venezuela+BCV&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=venezuela+reservas&hl=es-419&gl=VE&ceid=VE:es-419",
    "https://news.google.com/rss/search?q=Venezuela+economy&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Venezuela+oil&hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/search?q=Venezuela+IMF&hl=en-US&gl=US&ceid=US:en",
]

# DuckDuckGo search URLs
DDG_SEARCH_URL = "https://html.duckduckgo.com/html/"
DDG_NEWS_URL = "https://duckduckgo.com/html/"

# Keywords para búsqueda web
WEB_SEARCH_QUERIES = [
    "Venezuela economia 2024 2025 noticias",
    "Venezuela inflacion dolar paralelo hoy",
    "Venezuela reservas internacionales BCV",
    "Venezuela produccion petrolera PDVSA",
    "Venezuela FMI IMF articulo 4",
    "Venezuela riesgo pais bonos soberanos",
    "Venezuela economia dolar today",
    "crisis economica Venezuela ultimas noticias",
]

USER_AGENT = "EconomiaVenezuela/0.1.0 (news collector; contacto: dev@local)"
FETCH_TIMEOUT = 20.0
MAX_ARTICLES_PER_SOURCE = 20


def _clean_html(text: str) -> str:
    """Limpia HTML y devuelve texto plano."""
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    # Obtener texto y limpiar espacios
    cleaned = soup.get_text(separator=" ", strip=True)
    # Normalizar espacios múltiples
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned[:500]


def _parse_rss_entry(entry, source: str) -> Optional[NewsArticle]:
    """Convierte entrada RSS a NewsArticle."""
    title = (entry.get("title") or "").strip()
    url = entry.get("link")
    if not title or not url:
        return None

    published = None
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            published = datetime(*published_parsed[:6], tzinfo=timezone.utc)
        except (TypeError, ValueError):
            published = None

    # Limpiar HTML del summary
    raw_summary = entry.get("summary") or entry.get("description") or ""
    summary = _clean_html(raw_summary) or None

    return NewsArticle(
        source=source,
        title=title[:300],
        url=url,
        published=published,
        summary=summary,
    )


def _fetch_rss_feed(feed_url: str, max_items: int = MAX_ARTICLES_PER_SOURCE) -> List[NewsArticle]:
    """Fetch un feed RSS de Google News."""
    try:
        parsed = feedparser.parse(feed_url)
        source = (parsed.feed.get("title") or "Google News").strip()
        articles = []
        for entry in parsed.entries[:max_items]:
            article = _parse_rss_entry(entry, source)
            if article:
                articles.append(article)
        logger.info("Google News RSS '%s': %d artículos", source, len(articles))
        return articles
    except Exception as exc:
        logger.warning("Google News RSS falló para %s: %s", feed_url, exc)
        return []


def _fetch_ddg_html(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Busca en DuckDuckGo y extrae resultados (HTML scraping)."""
    try:
        params = {"q": query, "kl": "ve-es", "df": "d"}  # Venezuela, español, último día
        headers = {"User-Agent": USER_AGENT}
        resp = httpx.get(DDG_SEARCH_URL, params=params, headers=headers, timeout=FETCH_TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            logger.debug("DDG search %d para '%s'", resp.status_code, query)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        # Buscar resultados en .result__snippet o .result__title
        for result in soup.select(".result"):
            title_elem = result.select_one(".result__title a, .result__snippet")
            url_elem = result.select_one(".result__title a, .result__url")
            snippet_elem = result.select_one(".result__snippet")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = url_elem.get("href", "") if url_elem else ""
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            # Filtrar solo resultados con URL válida
            if url and title and url.startswith("http"):
                results.append({
                    "title": title[:300],
                    "url": url,
                    "snippet": snippet[:500] if snippet else None,
                })
                if len(results) >= max_results:
                    break

        logger.info("DDG search '%s': %d resultados", query, len(results))
        return results

    except Exception as exc:
        logger.warning("DDG search falló para '%s': %s", query, exc)
        return []


def _fetch_ddg_news(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Busca en la pestaña 'News' de DuckDuckGo."""
    try:
        params = {"q": query, "kl": "ve-es", "df": "d", "ia": "news"}
        headers = {"User-Agent": USER_AGENT}
        resp = httpx.get(DDG_NEWS_URL, params=params, headers=headers, timeout=FETCH_TIMEOUT, follow_redirects=True)
        if resp.status_code != 200:
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results = []

        for result in soup.select(".result--news"):
            title_elem = result.select_one(".result__title a")
            url_elem = result.select_one(".result__title a")
            snippet_elem = result.select_one(".result__snippet")
            source_elem = result.select_one(".result__source")
            time_elem = result.select_one(".result__date")

            if not title_elem:
                continue

            title = title_elem.get_text(strip=True)
            url = url_elem.get("href", "") if url_elem else ""
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else None
            source = source_elem.get_text(strip=True) if source_elem else "DuckDuckGo News"

            if url and title and url.startswith("http"):
                results.append({
                    "title": title[:300],
                    "url": url,
                    "snippet": snippet[:500] if snippet else None,
                    "source": source,
                })
                if len(results) >= max_results:
                    break

        logger.info("DDG News '%s': %d resultados", query, len(results))
        return results

    except Exception as exc:
        logger.debug("DDG News falló para '%s': %s", query, exc)
        return []


def _llm_analyze_articles(articles: List[Dict[str, Any]], query_context: str = "") -> List[NewsArticle]:
    """
    Usa LLM para filtrar, clasificar y enriquecer artículos.
    Devuelve solo los relevantes para economía venezolana.
    """
    if not articles:
        return []

    # Preparar prompt para el LLM
    articles_text = "\n\n".join([
        f"{i+1}. Título: {a['title']}\nURL: {a['url']}\nResumen: {a.get('snippet', 'N/A')[:300]}\nFuente: {a.get('source', 'N/A')}"
        for i, a in enumerate(articles)
    ])

    system_prompt = (
        "Eres un analista de noticias económicas especializado en Venezuela. "
        "Tu tarea es filtrar y clasificar artículos de noticias. "
        "Responde SOLO con JSON válido."
    )

    user_prompt = f"""
Contexto: {query_context}

Analiza estos {len(articles)} artículos y devuelve SOLO los que sean RELEVANTES para:
- Economía de Venezuela (inflación, dólar, PIB, reservas, petróleo, BCV, FMI, bonos, riesgo país)
- Política económica venezolana
- Indicadores macroeconómicos de Venezuela

DESCARTA: deportes, entretenimiento, crímenes comunes, opinión sin datos, artículos > 7 días.

Para cada artículo RELEVANTE, devuelve un objeto JSON con:
- title: título limpio (máx 300 chars)
- url: URL original
- source: nombre del medio/fuente
- summary: resumen en 1 frase (máx 200 chars)
- relevance: "high" | "medium" | "low" (relevancia económica)
- topics: lista de temas (ej: ["inflacion", "dolar", "petroleo", "reservas", "fmi", "riesgo_pais", "pib", "bcv"])
- published_estimate: fecha estimada ISO 8601 si se puede inferir, si no null

Formato de respuesta: JSON array de objetos. Si ninguno es relevante, devuelve [].
"""

    try:
        response = chat_completion(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )

        if not response:
            logger.warning("LLM no respondió para análisis de noticias")
            return _fallback_filter(articles)

        # Parsear respuesta JSON
        import json
        # Buscar el primer array JSON en la respuesta
        match = re.search(r'\[.*\]', response, re.DOTALL)
        if not match:
            logger.warning("LLM no devolvió JSON array válido")
            return _fallback_filter(articles)

        analyzed = json.loads(match.group(0))
        if not isinstance(analyzed, list):
            return _fallback_filter(articles)

        # Convertir a NewsArticle
        result = []
        for item in analyzed:
            if not isinstance(item, dict):
                continue
            if item.get("relevance") not in ("high", "medium", "low"):
                continue

            published = None
            pe = item.get("published_estimate")
            if pe:
                try:
                    published = datetime.fromisoformat(pe.replace("Z", "+00:00"))
                except (ValueError, AttributeError):
                    pass

            result.append(NewsArticle(
                source=item.get("source", "Web Search"),
                title=item.get("title", "")[:300],
                url=item.get("url", ""),
                published=published,
                summary=item.get("summary"),
            ))

        logger.info("LLM analizó %d artículos, %d relevantes", len(articles), len(result))
        return result

    except (LLMError, json.JSONDecodeError, Exception) as exc:
        logger.warning("LLM analysis falló: %s, usando fallback", exc)
        return _fallback_filter(articles)


def _fallback_filter(articles: List[Dict[str, Any]]) -> List[NewsArticle]:
    """Filtro heurístico simple cuando el LLM falla."""
    keywords = [
        "venezuela", "economía", "economia", "inflación", "inflacion", "dólar", "dolar",
        "bcv", "petróleo", "petroleo", "pdvsa", "reservas", "fmi", "imf", "bonos",
        "riesgo país", "riesgo pais", "pib", "crecimiento", "recesión", "recesion",
        "tipo de cambio", "paralelo", "oficial", "dicom", "sistema cambiario"
    ]

    result = []
    for a in articles:
        text = f"{a['title']} {a.get('snippet', '')}".lower()
        if any(kw in text for kw in keywords):
            result.append(NewsArticle(
                source=a.get("source", "Web Search"),
                title=a["title"][:300],
                url=a["url"],
                published=None,
                summary=a.get("snippet"),
            ))
    return result


def _deduplicate_articles(articles: List[NewsArticle]) -> List[NewsArticle]:
    """Elimina duplicados por URL y títulos similares."""
    seen_urls = set()
    seen_titles = set()
    unique = []

    for article in articles:
        url_key = article.url.strip().rstrip("/").lower()
        title_key = re.sub(r'[^\w\s]', '', article.title.lower())[:80]

        if url_key in seen_urls or title_key in seen_titles:
            continue

        seen_urls.add(url_key)
        seen_titles.add(title_key)
        unique.append(article)

    return unique


class LLMNewsCollector:
    """
    Collector de noticias potenciado por LLM con búsqueda web.

    Flujo:
    1. Google News RSS (feeds temáticos Venezuela/economía)
    2. DuckDuckGo HTML search (consultas específicas)
    3. DuckDuckGo News tab (noticias recientes)
    4. LLM analysis: filtrado, clasificación, enriquecimiento
    5. Deduplicación y retorno
    """

    def __init__(
        self,
        rss_feeds: Optional[List[str]] = None,
        search_queries: Optional[List[str]] = None,
        use_llm_analysis: bool = True,
    ):
        self.rss_feeds = rss_feeds or GOOGLE_NEWS_RSS
        self.search_queries = search_queries or WEB_SEARCH_QUERIES
        self.use_llm_analysis = use_llm_analysis

    def fetch_from_rss(self, max_per_feed: int = MAX_ARTICLES_PER_SOURCE) -> List[NewsArticle]:
        """Obtiene artículos de feeds RSS de Google News."""
        all_articles = []
        for feed_url in self.rss_feeds:
            articles = _fetch_rss_feed(feed_url, max_per_feed)
            all_articles.extend(articles)
            time.sleep(1)  # Rate limit amable
        return all_articles

    def fetch_from_web_search(self, max_per_query: int = 8) -> List[Dict[str, Any]]:
        """Busca en web (DuckDuckGo) y devuelve resultados crudos."""
        all_results = []
        for query in self.search_queries:
            # Búsqueda general
            results = _fetch_ddg_html(query, max_per_query)
            all_results.extend(results)

            # Búsqueda en pestaña News
            news_results = _fetch_ddg_news(query, max_per_query)
            all_results.extend(news_results)

            time.sleep(2)  # Rate limit
        return all_results

    def fetch_articles(
        self,
        max_rss_per_feed: int = MAX_ARTICLES_PER_SOURCE,
        max_search_per_query: int = 8,
        since_hours: int = 48,
    ) -> List[NewsArticle]:
        """
        Obtiene artículos combinando RSS + búsqueda web + análisis LLM.

        Args:
            max_rss_per_feed: Límite por feed RSS
            max_search_per_query: Límite por query de búsqueda
            since_hours: Filtrar artículos más recientes que X horas (aprox)

        Returns:
            Lista de NewsArticle únicos y relevantes
        """
        all_articles: List[NewsArticle] = []
        raw_web_results: List[Dict[str, Any]] = []

        # 1. Google News RSS
        logger.info("Fetching Google News RSS (%d feeds)...", len(self.rss_feeds))
        rss_articles = self.fetch_from_rss(max_rss_per_feed)
        all_articles.extend(rss_articles)

        # 2. Web Search (DuckDuckGo)
        logger.info("Fetching web search (%d queries)...", len(self.search_queries))
        raw_web_results = self.fetch_from_web_search(max_search_per_query)

        # 3. LLM Analysis para resultados web
        if self.use_llm_analysis and raw_web_results:
            logger.info("Analizando %d resultados web con LLM...", len(raw_web_results))
            analyzed = _llm_analyze_articles(
                raw_web_results,
                query_context="Noticias económicas de Venezuela última semana"
            )
            all_articles.extend(analyzed)
        elif raw_web_results:
            # Fallback sin LLM
            fallback = _fallback_filter(raw_web_results)
            all_articles.extend(fallback)

        # 4. Filtrar por fecha aproximada (últimos N horas)
        if since_hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
            filtered = []
            for a in all_articles:
                if a.published is None:
                    filtered.append(a)  # Sin fecha, mantener
                elif a.published >= cutoff:
                    filtered.append(a)
            all_articles = filtered

        # 5. Deduplicar
        unique = _deduplicate_articles(all_articles)
        logger.info("Total artículos únicos: %d (RSS: %d, Web: %d)",
                    len(unique), len(rss_articles), len(all_articles) - len(rss_articles))

        return unique


def fetch_news_llm(
    max_rss_per_feed: int = MAX_ARTICLES_PER_SOURCE,
    max_search_per_query: int = 8,
    since_hours: int = 48,
    use_llm: bool = True,
) -> List[NewsArticle]:
    """Función de conveniencia para usar el collector directamente."""
    collector = LLMNewsCollector(use_llm_analysis=use_llm)
    return collector.fetch_articles(max_rss_per_feed, max_search_per_query, since_hours)