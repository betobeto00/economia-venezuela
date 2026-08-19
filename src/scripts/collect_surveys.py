"""
Recolección y Análisis de Encuestas (CLI)
=========================================

Orquesta el pipeline completo de encuestas (Fase B):
registry → collector (gspread) → persistencia (PostgreSQL) → KPIs → informe.

Uso:
    python -m src.scripts.collect_surveys [--segment persona_comun|comerciante]
                                          [--report out/informe.md]

La función ``run_survey_pipeline`` es la lógica reutilizable (se invoca desde
este CLI o desde el scheduler) y recibe dependencias inyectadas para tests.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from src.analyzers.surveys.indicators import SurveyIndicators
from src.analyzers.surveys.contrast import contrast_perception_inflation
from src.collectors.surveys.form_registry import SurveyRegistry
from src.collectors.surveys.survey_collector import SurveyCollector
from src.db.repositories import SurveyRepository
from src.models.survey import Survey, SurveyResponse

logger = logging.getLogger(__name__)


def run_survey_pipeline(
    session,
    collector: SurveyCollector,
    registry: Optional[SurveyRegistry] = None,
    segment: Optional[str] = None,
) -> dict:
    """Ejecuta el pipeline completo: recolecta, persiste y resume.

    Args:
        session: Sesión SQLAlchemy (persistencia).
        collector: SurveyCollector autenticado.
        registry: Registro de formularios (por defecto lee de settings).
        segment: Filtro opcional por tipo de encuesta.

    Returns:
        Dict de resumen: {survey_type: {collected, saved, kpis}}.
    """
    registry = registry or SurveyRegistry()
    surveys = [
        s for s in registry.list_surveys()
        if segment is None or s.survey_type == segment
    ]
    if not surveys:
        logger.warning("No hay formularios configurados para recolectar.")
        return {}

    repo = SurveyRepository(session)
    summary: dict = {}
    indicators = SurveyIndicators()

    for survey in surveys:
        collected = collector.fetch_new_responses(survey)
        saved = repo.save_responses(collected)

        all_responses = repo.list_responses(survey_id=survey.id)
        kpis = indicators.compute_all(all_responses)

        summary[survey.survey_type] = {
            "survey_id": survey.id,
            "collected": len(collected),
            "saved": saved,
            "total_responses": len(all_responses),
            "kpis": {k: v.mean for k, v in kpis.items()},
        }
        logger.info(
            "Encuesta %s: %d recolectadas, %d nuevas (total %d)",
            survey.survey_type, len(collected), saved, len(all_responses),
        )
    return summary


def _write_report(
    session,
    summary: dict,
    report_path: Optional[Path],
    ai_enabled: bool = False,
) -> None:
    """Genera y escribe (o imprime) los informes ejecutivos por segmento."""
    from src.analyzers.surveys.report import SurveyReport
    from src.dashboard.surveys_data import segment_label

    repo = SurveyRepository(session)
    indicators = SurveyIndicators()
    report_generator = SurveyReport(ai_enabled=ai_enabled)

    reports = []
    for survey_type, info in summary.items():
        responses = repo.list_responses(survey_id=info["survey_id"])
        kpis = indicators.compute_all(responses)
        report = report_generator.generate(
            survey_type=survey_type,
            kpis=kpis,
            contrast=None,
            n_responses=info["total_responses"],
            period="Último período",
        )
        reports.append(f"## {segment_label(survey_type)}\n\n{report}")

    markdown = "\n\n".join(reports)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
        logger.info("Informe guardado en %s", report_path)
    else:
        print(markdown)


def main(argv: Optional[List[str]] = None) -> int:
    """Punto de entrada del CLI."""
    parser = argparse.ArgumentParser(description="Recolección de encuestas (Fase B)")
    parser.add_argument(
        "--segment", choices=["persona_comun", "comerciante"], default=None,
        help="Solo este tipo de encuesta (por defecto: todas).",
    )
    parser.add_argument(
        "--report", default=None,
        help="Ruta opcional para guardar el informe Markdown.",
    )
    parser.add_argument("--ai", action="store_true",
                        help="Intentar resumen con IA (requiere DEEPSEEK_API_KEY).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    collector = SurveyCollector()
    from src.db.session import session_scope
    with session_scope() as session:
        summary = run_survey_pipeline(session, collector, segment=args.segment)
        if not summary:
            logger.error(
                "Nada que recolectar. Configura SURVEY_*_FORM_ID/SHEET_ID y "
                "GOOGLE_CREDENTIALS_PATH en .env (ver .env.example)."
            )
            return 1
        _write_report(
            session, summary,
            Path(args.report) if args.report else None,
            ai_enabled=args.ai,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())