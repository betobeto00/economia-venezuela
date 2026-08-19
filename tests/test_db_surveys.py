"""
Tests de la Capa de Base de Datos de Encuestas
==============================================

Cubre el modelo de datos surveys / survey_responses en SQLite (mismo esquema
que PostgreSQL/TimescaleDB):

- init_db crea las tablas.
- Round-trip de Survey (insert/update/get/list).
- Round-trip de SurveyResponse (JSON, marcas de tiempo, calidad).
- Idempotencia: duplicados (constraint única) se omiten.
- Filtros y conteo.
"""

from datetime import datetime, timedelta

import pytest
import sqlalchemy
from sqlalchemy.orm import sessionmaker

from src.db import get_engine, init_db
from src.db.models import SurveyORM, SurveyResponseORM
from src.db.repositories import SurveyRepository
from src.models.survey import Survey, SurveyResponse


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test_economia_ve.db'}"
    init_db(url)
    factory = sessionmaker(bind=get_engine(url), future=True)
    s = factory()
    yield s
    s.close()


def _survey(survey_id=1, survey_type="persona_comun", form_id="form1", sheet_id="sheet1"):
    return Survey(
        id=survey_id, survey_type=survey_type,
        form_id=form_id, sheet_id=sheet_id, name=f"{survey_type} test",
    )


def _response(survey_id=1, ts=None, answers=None, segment="persona_comun"):
    return SurveyResponse(
        survey_id=survey_id,
        submitted_at=ts or datetime(2026, 8, 19, 14, 30),
        respondent_segment=segment,
        raw_answers=answers or {"¿Puedes ahorrar?": "Sí"},
        quality_score=0.8,
    )


class TestSchema:
    def test_init_db_crea_tablas(self, tmp_path):
        url = f"sqlite:///{tmp_path / 'schema.db'}"
        init_db(url)
        inspector = sqlalchemy.inspect(get_engine(url))
        assert "surveys" in inspector.get_table_names()
        assert "survey_responses" in inspector.get_table_names()

    def test_constraint_unica_definida(self, session):
        constraint = SurveyResponseORM.__table__.constraints
        names = {c.name for c in constraint}
        assert "uq_survey_response_idempotencia" in names


class TestSurveyRepository:
    def test_save_and_get_survey(self, session):
        repo = SurveyRepository(session)
        saved = repo.save_survey(_survey())
        assert saved.id == 1
        assert saved.form_version == 1
        assert repo.get_survey(1).survey_type == "persona_comun"

    def test_update_survey(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        updated = repo.save_survey(
            Survey(id=1, survey_type="persona_comun", form_id="formX",
                   sheet_id="sheetX", form_version=2, active=False)
        )
        assert updated.form_version == 2
        assert updated.active is False
        assert repo.get_survey(1).form_id == "formX"

    def test_list_surveys_activas(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey(1, "persona_comun"))
        repo.save_survey(_survey(2, "comerciante", form_id="f2", sheet_id="s2"))
        repo.save_survey(Survey(id=3, survey_type="empresa", form_id="f3",
                                sheet_id="s3", active=False))
        active = repo.list_surveys()
        assert [s.id for s in active] == [1, 2]

    def test_upsert_surveys(self, session):
        repo = SurveyRepository(session)
        saved = repo.upsert_surveys([
            _survey(1), _survey(2, "comerciante", form_id="f2", sheet_id="s2")
        ])
        assert len(saved) == 2
        assert len(repo.list_surveys()) == 2


class TestResponseRepository:
    def test_save_and_roundtrip(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        ts = datetime(2026, 8, 19, 14, 30, 0)
        response = _response(ts=ts)
        saved = repo.save_responses([response])
        assert saved == 1

        rows = repo.list_responses()
        assert len(rows) == 1
        row = rows[0]
        assert row.id is not None
        assert row.submitted_at.replace(tzinfo=None) == ts
        assert row.raw_answers == {"¿Puedes ahorrar?": "Sí"}
        assert row.quality_score == 0.8
        assert row.source == "google_forms"

    def test_json_roundtrip_con_unicode(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        repo.save_responses([_response(
            answers={
                "¿En el último mes los precios subieron?": "Mucho",
                "Monto (USD)": 120.5,
                "Zona": "Caracas",
            }
        )])
        row = repo.list_responses()[0]
        assert row.raw_answers["Monto (USD)"] == 120.5
        assert row.raw_answers["Zona"] == "Caracas"

    def test_idempotencia_duplicados(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        response = _response()
        assert repo.save_responses([response]) == 1
        # Misma respuesta (misma survey, ts y raw_answers) → se omite
        assert repo.save_responses([response]) == 0
        assert repo.count_responses() == 1

    def test_idempotencia_no_mezcla_lotes(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        ts = datetime(2026, 8, 19, 14, 30)
        dup = _response(ts=ts)
        otro = _response(ts=ts + timedelta(minutes=5), answers={"¿Puedes ahorrar?": "No"})
        # Un lote con un duplicado y una nueva: la nueva sí se guarda
        assert repo.save_responses([dup, dup, otro]) == 2
        assert repo.count_responses() == 2

    def test_filtros_por_segmento_y_fecha(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey(1, "persona_comun"))
        repo.save_survey(_survey(2, "comerciante", form_id="f2", sheet_id="s2"))
        base = datetime(2026, 8, 1)
        responses = []
        for day, segment in [(1, "persona_comun"), (2, "comerciante"), (3, "persona_comun")]:
            responses.append(_response(
                survey_id=1 if segment == "persona_comun" else 2,
                ts=base + timedelta(days=day), segment=segment,
            ))
        repo.save_responses(responses)

        assert repo.count_responses() == 3
        assert repo.count_responses(survey_id=1) == 2
        assert len(repo.list_responses(segment="comerciante")) == 1
        since = base + timedelta(days=2)
        assert len(repo.list_responses(since=since)) == 2

    def test_delete_all(self, session):
        repo = SurveyRepository(session)
        repo.save_survey(_survey())
        repo.save_responses([_response(), _response(
            ts=datetime(2026, 8, 20), answers={"X": "Y"})])
        assert repo.delete_all_responses() == 2
        assert repo.count_responses() == 0


# ---------------------------------------------------------------------------
# Integración: collector (hoja simulada) → repositorio → indicadores
# ---------------------------------------------------------------------------

class FakeWorksheet:
    def __init__(self, values):
        self._values = values

    def get_all_values(self):
        return [list(row) for row in self._values]


class TestPipelineIntegracion:
    HEADER = ["Marca de tiempo", "¿En el último mes los precios subieron?", "¿Puedes ahorrar?"]

    def test_collector_repositorio_indicadores(self, session, tmp_path):
        from src.analyzers.surveys.indicators import SurveyIndicators
        from src.collectors.surveys.survey_collector import (
            SurveyCheckpoint,
            SurveyCollector,
        )

        # Configura la sesión de tests sobre SQLite (mismo esquema)
        repo = SurveyRepository(session)
        saved_survey = repo.save_survey(_survey())

        values = [
            self.HEADER,
            ["19/08/2026 14:30:00", "Mucho", "Sí"],
            ["19/08/2026 15:10:00", "Algo", "No"],
        ]
        collector = SurveyCollector(
            credentials_path="creds_dummy.json",  # nunca se usa (worksheet fake)
            checkpoint=SurveyCheckpoint(tmp_path / "checkpoint.json"),
        )
        collector._open_worksheet = lambda survey: FakeWorksheet(values)

        # Recolecta
        responses = collector.fetch_new_responses(saved_survey)
        assert len(responses) == 2

        # Persiste (idempotente)
        assert repo.save_responses(responses) == 2
        assert repo.save_responses(responses) == 0  # duplicado omitido

        # Analiza desde la base
        stored = repo.list_responses(survey_id=saved_survey.id)
        kpis = SurveyIndicators().compute_all(stored)
        assert kpis["percepcion_inflacion"].mean == 83.0  # Mucho(100) + Algo(66)
        assert kpis["percepcion_inflacion"].n_responses == 2