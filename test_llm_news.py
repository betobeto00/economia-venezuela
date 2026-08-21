from src.collectors.news.llm_news_collector import fetch_news_llm

articles = fetch_news_llm(max_rss_per_feed=5, max_search_per_query=3, since_hours=72, use_llm=True)
print(f'Articulos encontrados: {len(articles)}')
for a in articles[:5]:
    print(f'  - [{a.source}] {a.title[:80]}')
    print(f'    URL: {a.url}')
    print(f'    Publicado: {a.published}')
    summary = a.summary[:100] if a.summary else "N/A"
    print(f'    Resumen: {summary}')
    print()