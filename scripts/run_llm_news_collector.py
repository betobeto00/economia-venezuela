"""
Script para ejecutar el collector LLM de noticias y persistir en BD.
"""
import sys
sys.path.insert(0, "C:\\Users\\DeadW\\dev\\economia-venezuela")

from src.collectors.news.llm_news_collector import fetch_news_llm
from src.db.session import get_session
from src.db.repositories import NewsRepository

def main():
    print("=== Ejecutando LLM News Collector ===")
    
    # 1. Obtener artículos
    articles = fetch_news_llm(
        max_rss_per_feed=10,
        max_search_per_query=5,
        since_hours=72,
        use_llm=True
    )
    print(f"Articulos obtenidos: {len(articles)}")
    
    if not articles:
        print("No hay articulos nuevos")
        return
    
    # 2. Persistir en BD
    with get_session() as session:
        repo = NewsRepository(session)
        saved = repo.save_articles(articles)
        print(f"Articulos guardados en BD: {saved}")
        
        # Verificar total en BD
        total = repo.count_articles()
        print(f"Total articulos en BD: {total}")
        
        # Mostrar últimos 5
        recent = repo.list_articles(limit=5)
        print("\nUltimos 5 articulos:")
        for a in recent:
            print(f"  - [{a.source}] {a.title[:80]}")
            if a.published:
                print(f"    Publicado: {a.published}")

if __name__ == "__main__":
    main()