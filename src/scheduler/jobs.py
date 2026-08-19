"""
Jobs del Scheduler
==================

Tareas periódicas del sistema (APScheduler):
- Recolección periódica de encuestas (Fase B).

Los jobs se registran con un id fijo y ``replace_existing`` para poder
re-registrarlos sin duplicados al recargar la configuración.
"""

import logging

from src.config import settings

logger = logging.getLogger(__name__)


def collect_surveys_job() -> dict:
    """Ejecuta el pipeline de recolección de encuestas (una vez por intervalo).

    Un fallo no debe tumbar el scheduler: se registra y se devuelve dict vacío.
    """
    from src.collectors.surveys.survey_collector import SurveyCollector
    from src.db.session import session_scope
    from src.scripts.collect_surveys import run_survey_pipeline

    try:
        collector = SurveyCollector()
        with session_scope() as session:
            summary = run_survey_pipeline(session, collector)
            for survey_type, info in summary.items():
                logger.info(
                    "Job encuestas %s: %d nuevas, total %d",
                    survey_type, info["saved"], info["total_responses"],
                )
            return summary
    except Exception as exc:  # noqa: BLE001 - el scheduler no debe caerse
        logger.exception("Job de recolección de encuestas falló: %s", exc)
        return {}


def collect_market_job() -> dict:
    """Ejecuta el pipeline de recolección de datos de mercado (una vez por intervalo)."""
    from src.db.session import session_scope
    from src.scripts.collect_market import run_market_pipeline

    try:
        with session_scope() as session:
            summary = run_market_pipeline(session)
            return summary
    except Exception as exc:  # noqa: BLE001 - el scheduler no debe caerse
        logger.exception("Job de recolección de mercado falló: %s", exc)
        return {}


def collect_news_job() -> dict:
    """Ejecuta el pipeline de noticias/sentimiento (una vez por intervalo)."""
    from src.db.session import session_scope
    from src.scripts.collect_news import run_news_pipeline

    try:
        with session_scope() as session:
            summary = run_news_pipeline(session)
            logger.info(
                "Job noticias: %d artículos, %d posts, %d sentimientos",
                summary["news"]["saved"], summary["social"]["saved"],
                summary["sentiment"]["saved"],
            )
            return summary
    except Exception as exc:  # noqa: BLE001 - el scheduler no debe caerse
        logger.exception("Job de noticias/sentimiento falló: %s", exc)
        return {}


def weekly_report_job() -> dict:
    """Genera el informe semanal automatizado (con resumen IA si hay LLMs).

    Returns:
        Dict con la ruta del informe, o {} si falló.
    """
    from src.analyzers.reports.weekly import generate_weekly_report

    try:
        path = generate_weekly_report()
        logger.info("Informe semanal generado: %s", path)
        return {"report": path}
    except Exception as exc:  # noqa: BLE001 - el scheduler no debe caerse
        logger.exception("Job de informe semanal falló: %s", exc)
        return {}


def register_market_job(scheduler) -> None:
    """Registra la recolección periódica de datos de mercado en el scheduler."""
    existing = scheduler.get_job("collect_market")
    if existing is not None:
        scheduler.remove_job("collect_market")

    scheduler.add_job(
        collect_market_job,
        trigger="interval",
        minutes=settings.MARKET_COLLECT_INTERVAL_MINUTES,
        id="collect_market",
        name="Recolección periódica de datos de mercado (Fase A)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def register_survey_job(scheduler) -> None:
    """Registra la recolección periódica de encuestas en el scheduler.

    Elimina primero cualquier job previo con el mismo id: en APScheduler,
    ``replace_existing`` solo aplica al arrancar y no elimina jobs pendientes.
    """
    existing = scheduler.get_job("collect_surveys")
    if existing is not None:
        scheduler.remove_job("collect_surveys")

    scheduler.add_job(
        collect_surveys_job,
        trigger="interval",
        minutes=settings.SURVEY_COLLECT_INTERVAL_MINUTES,
        id="collect_surveys",
        name="Recolección periódica de encuestas (Fase B)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def register_news_job(scheduler) -> None:
    """Registra la recolección periódica de noticias/sentimiento.

    El intervalo se configura en horas (``NEWS_COLLECT_INTERVAL_HOURS``) y se
    convierte a minutos para el trigger ``interval``.
    """
    existing = scheduler.get_job("collect_news")
    if existing is not None:
        scheduler.remove_job("collect_news")

    scheduler.add_job(
        collect_news_job,
        trigger="interval",
        minutes=settings.NEWS_COLLECT_INTERVAL_HOURS * 60,
        id="collect_news",
        name="Recolección periódica de noticias y sentimiento (Fase A)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def register_weekly_report_job(scheduler) -> None:
    """Registra el informe semanal automatizado.

    Se dispara el día/hora configurados (``WEEKLY_REPORT_DAY``/``WEEKLY_REPORT_HOUR``)
    con trigger ``cron``. Un fallo del informe no afecta al scheduler.
    """
    day = settings.WEEKLY_REPORT_DAY.strip().lower()
    day_abbr = {
        "monday": "mon", "tuesday": "tue", "wednesday": "wed",
        "thursday": "thu", "friday": "fri", "saturday": "sat", "sunday": "sun",
    }.get(day, day)

    existing = scheduler.get_job("weekly_report")
    if existing is not None:
        scheduler.remove_job("weekly_report")

    scheduler.add_job(
        weekly_report_job,
        trigger="cron",
        day_of_week=day_abbr,
        hour=settings.WEEKLY_REPORT_HOUR,
        id="weekly_report",
        name="Informe semanal automatizado con IA (punto 25)",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )