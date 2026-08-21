from src.collectors.news.llm_news_collector import fetch_news_llm

articles = fetch_news_llm(max_rss_per_feed=3, max_search_per_query=2, since_hours=72, use_llm=False)
print(f'Articulos: {len(articles)}')
for a in articles[:3]:
    print(f'  - [{a.source}] {a.title[:80]}')
    summary = a.summary[:150] if a.summary else "N/A"
    print(f'    Resumen: {summary}')
    print()