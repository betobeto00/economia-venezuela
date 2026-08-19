"""
Economía Venezuela - Punto de Entrada Principal
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src import __version__


def setup_logging():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("economia_ve.log", encoding="utf-8")
        ]
    )
    return logging.getLogger(__name__)


def init_database():
    """Crea el esquema de base de datos si no existe."""
    from src.db.session import init_db
    init_db()


def start_scheduler():
    """Arranca el scheduler de tareas periódicas (mercado, encuestas, noticias, informe)."""
    from apscheduler.schedulers.background import BackgroundScheduler
    from src.scheduler.jobs import (
        register_market_job,
        register_news_job,
        register_survey_job,
        register_weekly_report_job,
    )

    scheduler = BackgroundScheduler()
    register_market_job(scheduler)
    register_survey_job(scheduler)
    register_news_job(scheduler)
    register_weekly_report_job(scheduler)
    scheduler.start()
    logging.getLogger(__name__).info(
        "Scheduler iniciado (mercado cada %d min, encuestas cada %d min, "
        "noticias cada %d h, informe semanal %s %02d:00)",
        settings.MARKET_COLLECT_INTERVAL_MINUTES,
        settings.SURVEY_COLLECT_INTERVAL_MINUTES,
        settings.NEWS_COLLECT_INTERVAL_HOURS,
        settings.WEEKLY_REPORT_DAY,
        settings.WEEKLY_REPORT_HOUR,
    )
    return scheduler


def main():
    """Función principal de la aplicación"""
    logger = setup_logging()
    
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    logger.info(f"Modo debug: {settings.DEBUG}")
    
    # 1. Conectar a base de datos
    try:
        init_database()
        logger.info("Base de datos lista")
    except Exception as exc:
        logger.warning("No se pudo inicializar la base de datos: %s", exc)

    # 2. Iniciar scheduler de recolección periódica
    scheduler = start_scheduler() if settings.ENVIRONMENT != "test" else None
    
    logger.info("Sistema inicializado correctamente")
    logger.info("Presiona Ctrl+C para detener")
    
    try:
        # Mantener el sistema ejecutándose
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")
        if scheduler is not None:
            scheduler.shutdown()


if __name__ == "__main__":
    main()
