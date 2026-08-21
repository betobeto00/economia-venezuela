from src.collectors.news.llm_news_collector import LLMNewsCollector, _fetch_ddg_html, _fetch_ddg_news, _llm_analyze_articles

# Test 1: DuckDuckGo web search
print("=== Test 1: DuckDuckGo Web Search ===")
results = _fetch_ddg_html("Venezuela economia inflacion dolar 2024", max_results=5)
for r in results:
    print(f"  - {r['title'][:80]}")
    print(f"    URL: {r['url']}")
    print(f"    Snippet: {r['snippet'][:100] if r['snippet'] else 'N/A'}")
    print()

# Test 2: DuckDuckGo News
print("\n=== Test 2: DuckDuckGo News ===")
news_results = _fetch_ddg_news("Venezuela economia BCV reservas", max_results=5)
for r in news_results:
    print(f"  - {r['title'][:80]}")
    print(f"    URL: {r['url']}")
    print(f"    Source: {r.get('source', 'N/A')}")
    print(f"    Snippet: {r['snippet'][:100] if r['snippet'] else 'N/A'}")
    print()

# Test 3: LLM Analysis
print("\n=== Test 3: LLM Analysis ===")
all_web = results + news_results
if all_web:
    analyzed = _llm_analyze_articles(all_web[:8], "Noticias economicas Venezuela")
    print(f"Articulos analizados por LLM: {len(analyzed)}")
    for a in analyzed:
        print(f"  - [{a.source}] {a.title[:80]}")
        print(f"    URL: {a.url}")
        print(f"    Resumen: {a.summary[:100] if a.summary else 'N/A'}")
        print()

# Test 4: Full collector
print("\n=== Test 4: Full Collector (RSS + Web + LLM) ===")
collector = LLMNewsCollector(use_llm_analysis=True)
articles = collector.fetch_articles(max_rss_per_feed=3, max_search_per_query=3, since_hours=168)
print(f"Total articulos unicos: {len(articles)}")
for a in articles[:10]:
    print(f"  - [{a.source}] {a.title[:80]}")
    print(f"    URL: {a.url}")
    if a.published:
        print(f"    Publicado: {a.published}")
    print()