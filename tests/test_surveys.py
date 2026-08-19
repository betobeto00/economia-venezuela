"""
Tests del Pipeline de Encuestas (Fase B)
========================================

Cubre:
- Utils de parseo (to_number, classify, calidad).
- Modelos Survey / SurveyResponse y deduplicación.
- Checkpoint e idempotencia del collector (con hoja simulada).
- Registro de formularios.
- Indicadores (extracción numérica/categórica, agregación, serie).
- Contraste percepción vs realidad.
- Informe ejecutivo Markdown.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.analyzers.surveys.contrast import contrast_perception_inflation
from src.analyzers.surveys.indicators import SurveyIndicators
from src.analyzers.surveys.report import build_markdown_report
from src.collectors.surveys.form_registry import SurveyRegistry
from src.collectors.surveys.survey_collector import (
    SurveyCheckpoint,
    SurveyCollector,
    parse_timestamp,
)
from src.collectors.surveys.utils import (
    classify,
    compute_quality_score,
    to_clamped_percent,
    to_number,
    yes_no,
)
from src.models.survey import Survey, SurveyResponse, dedupe_responses


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

class TestUtils:
    def test_to_number_simple(self):
        assert to_number("42%") == 42.0
        assert to_number("$12,5") == 12.5
        assert to_number(" 300 ") == 300.0
        assert to_number(30) == 30.0

    def test_to_number_range_midpoint(self):
        assert to_number("15 - 20") == 17.5

    def test_to_number_none(self):
        assert to_number("ninguno") is None
        assert to_number(None) is None

    def test_to_clamped_percent(self):
        assert to_clamped_percent("70%") == 70.0
        assert to_clamped_percent("0.75") == 75.0  # fracción
        assert to_clamped_percent("120%") == 100.0  # acota
        assert to_clamped_percent("-5%") == 0.0
        assert to_clamped_percent("alto") is None

    def test_classify(self):
        assert classify("Sí, pude ahorrar", {"sí": 100, "no": 0}) == 100
        assert classify("No", {"sí": 100, "no": 0}) == 0
        assert classify("No aplica", {"sí": 100, "no": 0}) == 0
        assert classify("Mucho", {"mucho": 100, "poco": 0}) == 100
        assert classify("", {"mucho": 100}) is None

    def test_yes_no(self):
        assert yes_no("Sí") == 100
        assert yes_no("No") == 0
        assert yes_no("tal vez") is None

    def test_quality_score(self):
        answers = {"Edad": "30-40", "Ingreso": "500", "Zona": ""}
        assert compute_quality_score(answers) == 0.67
        assert compute_quality_score({}) == 0.0


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------

class TestModels:
    def test_survey_model(self):
        survey = Survey(
            id=1, survey_type="persona_comun",
            form_id="form1", sheet_id="sheet1",
        )
        assert survey.form_version == 1
        assert survey.active is True

    def test_survey_response_defaults(self):
        resp = SurveyResponse(
            survey_id=1, submitted_at=datetime(2026, 8, 19),
            respondent_segment="persona_comun",
            raw_answers={"P1": "Sí"},
        )
        assert resp.source == "google_forms"
        assert resp.id is None
        assert resp.answered() == 1

    def test_dedupe_responses(self):
        ts = datetime(2026, 8, 19)
        base = dict(survey_id=1, submitted_at=ts, respondent_segment="persona_comun")
        r1 = SurveyResponse(**base, raw_answers={"P": "Sí"})
        r2 = SurveyResponse(**base, raw_answers={"P": "Sí"})
        r3 = SurveyResponse(**base, raw_answers={"P": "No"})
        result = dedupe_responses([r1, r2, r3])
        assert len(result) == 2
        assert result[0] is r1


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class FakeWorksheet:
    def __init__(self, values):
        self._values = values

    def get_all_values(self):
        return [list(row) for row in self._values]


HEADER = ["Marca de tiempo", "¿Los precios subieron?", "¿Puedes ahorrar?"]


def _make_survey(sheet_id="sheet1"):
    return Survey(
        id=1, survey_type="persona_comun",
        form_id="form1", sheet_id=sheet_id, name="Persona Común",
    )


class TestCollector:
    def _collector(self, tmp_path, values):
        checkpoint = SurveyCheckpoint(tmp_path / "checkpoint.json")
        collector = SurveyCollector(
            credentials_path=str(tmp_path / "creds.json"),  # nunca se usa
            checkpoint=checkpoint,
        )
        collector._open_worksheet = lambda survey: FakeWorksheet(values)
        return collector, checkpoint

    def test_process_response_normaliza(self, tmp_path):
        collector, _ = self._collector(tmp_path, [])
        survey = _make_survey()
        resp = collector.process_response(
            ["19/08/2026 14:30:00", "Mucho", "Sí"], HEADER, survey
        )
        assert resp is not None
        assert resp.survey_id == 1
        assert resp.submitted_at == datetime(2026, 8, 19, 14, 30, 0)
        assert resp.raw_answers == {
            "¿Los precios subieron?": "Mucho",
            "¿Puedes ahorrar?": "Sí",
        }
        assert resp.quality_score == 1.0

    def test_process_response_ignora_vacia(self, tmp_path):
        collector, _ = self._collector(tmp_path, [])
        survey = _make_survey()
        assert collector.process_response([], HEADER, survey) is None
        assert collector.process_response(["", "", ""], HEADER, survey) is None

    def test_process_response_ignora_sin_timestamp(self, tmp_path):
        collector, _ = self._collector(tmp_path, [])
        survey = _make_survey()
        assert collector.process_response(["fecha inválida", "Mucho", "Sí"], HEADER, survey) is None

    def test_process_response_marca_temporal_variable(self, tmp_path):
        # Google usa encabezados distintos según idioma/versión
        # ("Marca temporal", "Timestamp", etc.). El parseo debe ser tolerante.
        collector, _ = self._collector(tmp_path, [])
        survey = _make_survey()
        for header in [
            ["Marca temporal", "¿Los precios subieron?", "¿Puedes ahorrar?"],
            ["Timestamp", "¿Los precios subieron?", "¿Puedes ahorrar?"],
            ["Fecha y hora", "¿Los precios subieron?", "¿Puedes ahorrar?"],
        ]:
            resp = collector.process_response(
                ["19/08/2026 14:30:00", "Mucho", "Sí"], header, survey
            )
            assert resp is not None
            assert resp.submitted_at == datetime(2026, 8, 19, 14, 30, 0)
            assert resp.raw_answers == {
                "¿Los precios subieron?": "Mucho",
                "¿Puedes ahorrar?": "Sí",
            }

    def test_fetch_new_responses_idempotente(self, tmp_path):
        values = [
            HEADER,
            ["19/08/2026 14:30:00", "Mucho", "Sí"],
            ["19/08/2026 15:10:00", "Algo", "No"],
        ]
        collector, checkpoint = self._collector(tmp_path, values)
        survey = _make_survey()

        first = collector.fetch_new_responses(survey)
        assert len(first) == 2
        assert checkpoint.get_last_row(survey.sheet_id) == 2

        # Segunda ejecución: sin filas nuevas (idempotente)
        second = collector.fetch_new_responses(survey)
        assert second == []

    def test_fetch_avanza_checkpoint_con_filas_invalidas(self, tmp_path):
        values = [
            HEADER,
            ["fecha rara", "Mucho", "Sí"],          # inválida → se omite
            ["19/08/2026 15:10:00", "Algo", "No"],  # válida
        ]
        collector, checkpoint = self._collector(tmp_path, values)
        survey = _make_survey()

        responses = collector.fetch_new_responses(survey)
        assert len(responses) == 1
        assert checkpoint.get_last_row(survey.sheet_id) == 2  # cursor avanza

    def test_parse_timestamp_formatos(self):
        assert parse_timestamp("19/08/2026 14:30:00") == datetime(2026, 8, 19, 14, 30, 0)
        assert parse_timestamp("2026-08-19 14:30:00") == datetime(2026, 8, 19, 14, 30, 0)
        assert parse_timestamp("") is None
        assert parse_timestamp("basura") is None

    def test_checkpoint_persistencia(self, tmp_path):
        path = tmp_path / "chk.json"
        cp = SurveyCheckpoint(path)
        cp.set_last_row("sheet1", 5)
        cp.save()
        reloaded = SurveyCheckpoint(path)
        assert reloaded.get_last_row("sheet1") == 5

    def test_checkpoint_archivo_corrupto(self, tmp_path):
        path = tmp_path / "chk.json"
        path.write_text("{corrupto", encoding="utf-8")
        cp = SurveyCheckpoint(path)
        assert cp.get_last_row("sheet1") == 0


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_sin_config_no_devuelve_encuestas(self):
        cfg = SimpleNamespace(
            SURVEY_PERSONA_COMUN_FORM_ID=None,
            SURVEY_PERSONA_COMUN_SHEET_ID=None,
            SURVEY_COMERCIANTE_FORM_ID=None,
            SURVEY_COMERCIANTE_SHEET_ID=None,
        )
        registry = SurveyRegistry(cfg)
        assert registry.list_surveys() == []
        assert registry.get_survey("persona_comun") is None

    def test_config_parcial(self):
        cfg = SimpleNamespace(
            SURVEY_PERSONA_COMUN_FORM_ID="f1",
            SURVEY_PERSONA_COMUN_SHEET_ID="s1",
            SURVEY_COMERCIANTE_FORM_ID=None,
            SURVEY_COMERCIANTE_SHEET_ID=None,
        )
        registry = SurveyRegistry(cfg)
        surveys = registry.list_surveys()
        assert len(surveys) == 1
        assert surveys[0].survey_type == "persona_comun"
        assert registry.get_survey("persona_comun").form_id == "f1"

    def test_config_completa(self):
        cfg = SimpleNamespace(
            SURVEY_PERSONA_COMUN_FORM_ID="f1",
            SURVEY_PERSONA_COMUN_SHEET_ID="s1",
            SURVEY_COMERCIANTE_FORM_ID="f2",
            SURVEY_COMERCIANTE_SHEET_ID="s2",
        )
        registry = SurveyRegistry(cfg)
        assert len(registry.list_surveys()) == 2


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------

def _resp(survey_type, submitted_at, answers, survey_id=1):
    return SurveyResponse(
        survey_id=survey_id, submitted_at=submitted_at,
        respondent_segment=survey_type, raw_answers=answers,
    )


class TestIndicators:
    def test_extraccion_categorica_y_numerica(self):
        indicators = SurveyIndicators()
        resp = _resp(
            "persona_comun", datetime(2026, 8, 19),
            {
                "¿En el último mes los precios subieron?": "Mucho",
                "¿Puedes ahorrar este mes?": "Sí",
                "¿Qué % de tu ingreso destinas a comida?": "80%",
            },
        )
        kpis = indicators.extract_all(resp)
        assert kpis["percepcion_inflacion"] == 100
        assert kpis["capacidad_ahorro"] == 100
        assert kpis["presion_canasta"] == 80

    def test_extraccion_responde_None_sin_match(self):
        indicators = SurveyIndicators()
        resp = _resp(
            "persona_comun", datetime(2026, 8, 19),
            {"Pregunta irrelevante": "42"},
        )
        assert indicators.extract_all(resp) == {}

    def test_extraccion_case_insensitive_y_term_min_specific(self):
        # La pregunta real usa mayúscula inicial ("Ajustaste tus precios") y
        # "tus ventas" aparece tanto en la pregunta de dolarización como en la
        # de clima de negocios. El término más específico debe ganar.
        indicators = SurveyIndicators()
        resp = _resp(
            "comerciante", datetime(2026, 8, 19),
            {
                "¿Cómo está tu demanda actualmente?": "Normal",
                "¿Ajustaste tus precios durante el mes?": "Sí",
                "¿Tienes acceso a crédito para tu negocio?": "Sí",
                "¿Cómo cambió tu margen en el último mes?": "Peor",
                "¿Qué porcentaje de tus ventas cobras en dólares?": "41% - 60%",
                "¿Cómo evolucionaron tus ventas este mes vs el anterior?": "Igual",
            },
        )
        kpis = indicators.extract_all(resp)
        assert kpis["ajuste_precios"] == 100        # "Sí" → SIN_NO_MAP
        assert kpis["clima_negocios"] == 50         # "Igual" → MEJOR_PEOR_MAP
        assert kpis["demanda"] == 50
        assert kpis["margen"] == 0
        assert kpis["acceso_credito"] == 100
        assert kpis["dolarizacion_ventas"] == pytest.approx(50.5)

    def test_compute_all_agrega(self):
        indicators = SurveyIndicators()
        responses = [
            _resp("persona_comun", datetime(2026, 8, 19),
                  {"¿En el último mes los precios subieron?": "Mucho"}),
            _resp("persona_comun", datetime(2026, 8, 20),
                  {"¿En el último mes los precios subieron?": "Poco"}),
            _resp("persona_comun", datetime(2026, 8, 21),
                  {"¿En el último mes los precios subieron?": "Nada"}),
        ]
        result = indicators.compute_all(responses)
        kpi = result["percepcion_inflacion"]
        assert kpi.n_responses == 3
        assert kpi.mean == pytest.approx((100 + 33 + 0) / 3, abs=0.01)

    def test_compute_series_agrupa_por_periodo(self):
        indicators = SurveyIndicators()
        base = datetime(2026, 8, 1)
        responses = []
        for day in range(3):
            responses.append(
                _resp("comerciante", base + timedelta(days=day),
                      {"¿Cómo evolucionaron tus ventas este mes?": "Mejor"})
            )
        series = indicators.compute_series(responses, freq="W")
        assert not series.empty
        assert "kpi" in series.columns and "mean" in series.columns
        clima = series[series["kpi"] == "clima_negocios"]
        assert clima["n"].sum() == 3
        assert (clima["mean"] == 100.0).all()

    def test_compute_series_vacia(self):
        series = SurveyIndicators().compute_series([], freq="W")
        assert series.empty


# ---------------------------------------------------------------------------
# Contraste
# ---------------------------------------------------------------------------

class TestContrast:
    def test_brecha_grande(self):
        result = contrast_perception_inflation(perceived=80, official=25, ovf=60)
        assert result["gap_vs_official"] == 55.0
        assert result["gap_vs_ovf"] == 20.0
        assert "Brecha de 55.0 puntos" in result["interpretation"]

    def test_coincidencia(self):
        result = contrast_perception_inflation(perceived=30, official=28, ovf=30)
        assert "coincide" in result["interpretation"]

    def test_sin_oficial(self):
        result = contrast_perception_inflation(perceived=80, official=None)
        assert result["official"] is None
        assert "Sin medición oficial" in result["interpretation"]


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------

class TestReport:
    def test_build_markdown(self):
        indicators = SurveyIndicators()
        resp = _resp(
            "persona_comun", datetime(2026, 8, 19),
            {"¿En el último mes los precios subieron?": "Mucho"},
        )
        kpis = indicators.compute_all([resp])
        contrast = contrast_perception_inflation(perceived=100, official=25)
        md = build_markdown_report(
            "persona_comun", kpis, contrast, n_responses=1,
            period="Agosto 2026",
        )
        assert "Informe Ejecutivo" in md
        assert "Persona Común" in md
        assert "Brecha de 75.0 puntos" in md
        assert "N=1" in md

    def test_build_markdown_sin_kpis(self):
        md = build_markdown_report("comerciante", {}, n_responses=0)
        assert "Sin KPIs calculados" in md


# ---------------------------------------------------------------------------
# Sanity: el pipeline no depende de gspread en import
# ---------------------------------------------------------------------------

def test_gspread_no_necesario_para_imports():
    # Corre en subproceso: otros tests (p.ej. el job del scheduler) ya pueden
    # haber importado gspread en este proceso, lo que rompería la aserción.
    import subprocess
    import sys

    code = (
        "import sys; "
        "import src.collectors.surveys.survey_collector as m; "
        "sys.exit(1 if 'gspread' in sys.modules else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        cwd=sys.path[0] or None,
    )
    assert result.returncode == 0, result.stderr.decode()