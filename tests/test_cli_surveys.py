"""
Tests del CLI de encuestas y del scheduler
==========================================

- ``run_survey_pipeline``: orquesta collector→persistencia→KPIs (con dobles).
- ``register_survey_job``: registra el job periódico con el intervalo correcto.
"""

from datetime import datetime, timedelta

import pytest
from apscheduler.schedulers.background import BackgroundScheduler

from src.models.survey import Survey, SurveyResponse
from src.scheduler.jobs import register_survey_job
from src.scripts.collect_surveys import run_survey_pipeline

SURVEY = Survey(
    id=1, survey_type="persona_comun", form_id="form", sheet_id="sheet",
    name="Encuesta Persona Común",
)


def _response(days_ago=1):
    return SurveyResponse(
        survey_id=1,
        submitted_at=datetime(2026, 8, 19) - timedelta(days=days_ago),
        respondent_segment="persona_comun",
        raw_answers={"¿En el último mes los precios subieron?": "Mucho"},
    )


class FakeCollector:
    """Collector de prueba que devuelve respuestas sin tocar gspread."""

    def __init__(self, responses):
        self._responses = responses

    def fetch_new_responses(self, survey):
        return self._responses


class FakeRegistry:
    def __init__(self, surveys):
        self._surveys = surveys

    def list_surveys(self):
        return self._surveys


@pytest.fixture
def session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from src.db.models import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    s = factory()
    yield s
    s.close()


class TestRunSurveyPipeline:
    def test_pipeline_persiste_y_resume(self, session):
        responses = [_response(), _response(days_ago=2)]
        summary = run_survey_pipeline(
            session,
            FakeCollector(responses),
            registry=FakeRegistry([SURVEY]),
        )
        assert "persona_comun" in summary
        info = summary["persona_comun"]
        assert info["collected"] == 2
        assert info["saved"] == 2
        assert info["total_responses"] == 2
        assert info["kpis"]["percepcion_inflacion"] == 100.0

    def test_pipeline_idempotente(self, session):
        collector = FakeCollector([_response()])
        run_survey_pipeline(session, collector, registry=FakeRegistry([SURVEY]))
        summary = run_survey_pipeline(session, collector, registry=FakeRegistry([SURVEY]))
        info = summary["persona_comun"]
        assert info["collected"] == 1
        assert info["saved"] == 0  # duplicada: no se vuelve a insertar
        assert info["total_responses"] == 1

    def test_pipeline_sin_formularios(self, session):
        summary = run_survey_pipeline(
            session, FakeCollector([]), registry=FakeRegistry([])
        )
        assert summary == {}

    def test_pipeline_filtra_por_segmento(self, session):
        comerciante = Survey(
            id=2, survey_type="comerciante", form_id="f2", sheet_id="s2",
            name="Encuesta Comerciante",
        )
        summary = run_survey_pipeline(
            session,
            FakeCollector([]),
            registry=FakeRegistry([SURVEY, comerciante]),
            segment="persona_comun",
        )
        assert set(summary) == {"persona_comun"}


class TestRegisterSurveyJob:
    def test_registra_job_intervalo(self):
        scheduler = BackgroundScheduler()
        register_survey_job(scheduler)
        job = scheduler.get_job("collect_surveys")
        assert job is not None
        assert job.trigger.interval.total_seconds() == 60 * 60  # default 60 min
        assert job.max_instances == 1

    def test_registrar_dos_veces_no_duplica(self):
        scheduler = BackgroundScheduler()
        register_survey_job(scheduler)
        register_survey_job(scheduler)
        ids = [j.id for j in scheduler.get_jobs()]
        assert ids.count("collect_surveys") == 1

    def test_collect_surveys_job_no_falla_sin_credenciales(self):
        # Sin GOOGLE_CREDENTIALS_PATH ni formularios configurados debe devolver {}
        from src.scheduler.jobs import collect_surveys_job

        result = collect_surveys_job()
        assert isinstance(result, dict)