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