"""
Analiza sentimiento de artículos de noticias en BD.
"""
import sys
sys.path.insert(0, "C:\\Users\\DeadW\\dev\\economia-venezuela")

from src.db.session import get_session
from src.db.repositories import NewsRepository
from src.db.models import NewsArticleORM, SentimentScoreORM
from src.analyzers.sentiment import analyze_batch
from src.models.news import SentimentScore
from sqlalchemy import select

def main():
    with get_session() as session:
        # Obtener artículos que no tienen sentimiento analizado
        stmt = select(NewsArticleORM).where(
            ~NewsArticleORM.id.in_(
                select(SentimentScoreORM.item_id).where(SentimentScoreORM.item_type == 'news')
            )
        ).order_by(NewsArticleORM.published.desc()).limit(100)
        
        articles = session.scalars(stmt).all()
        print(f"Articulos sin analizar: {len(articles)}")
        
        if not articles:
            print("Todos los articulos ya tienen sentimiento analizado")
            return
        
        # Preparar textos
        texts = [f"{a.title}. {a.summary or ''}" for a in articles]
        
        # Analizar en batch
        score_tuples = analyze_batch(texts)
        
        # Guardar
        saved = 0
        for article, (score_val, label) in zip(articles, score_tuples):
            sentiment = SentimentScore(
                item_type="news",
                item_id=article.id,
                text=texts[articles.index(article)][:500],
                score=score_val,
                label=label,
            )
            session.add(SentimentScoreORM(
                item_type=sentiment.item_type,
                item_id=sentiment.item_id,
                text=sentiment.text,
                score=sentiment.score,
                label=sentiment.label,
            ))
            try:
                session.commit()
                saved += 1
            except Exception:
                session.rollback()
        
        print(f"Sentimientos guardados: {saved}")
        
        # Resumen
        from src.db.repositories import NewsRepository
        repo = NewsRepository(session)
        summary = repo.sentiment_summary()
        print(f"Resumen sentimiento: {summary}")

if __name__ == "__main__":
    main()