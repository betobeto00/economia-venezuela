"""
Tests de la capa de datos del dashboard de Encuestas
====================================================

Cubre la lógica pura de ``surveys_data.py`` (sin Streamlit/Plotly):
- kpi_cards, series_df
- split_periods y compare_periods (deltas)
- build_contrast
- build_report (informe ejecutivo)
- segment_label
"""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from src.dashboard.surveys_data import (
    build_contrast,
    build_report,
    compare_periods,
    kpi_cards,
    segment_label,
    series_df,
    split_periods,
)
from src.models.survey import SurveyResponse


def _resp(survey_type, submitted_at, answers, survey_id=1):
    return SurveyResponse(
        survey_id=survey_id, submitted_at=submitted_at,
        respondent_segment=survey_type, raw_answers=answers,
    )


PRE = "¿En el último mes los precios subieron?"
AHORRO = "¿Puedes ahorrar este mes?"
VENTAS = "¿Cómo evolucionaron tus ventas este mes?"


class TestSegmentLabel:
    def test_labels(self):
        assert segment_label("persona_comun") == "Persona Común"
        assert segment_label("comerciante") == "Comerciante"
        assert segment_label("otro") == "Otro"


class TestKPICards:
    def test_kpi_cards_agrega(self):
        responses = [
            _resp("persona_comun", datetime(2026, 8, 19), {PRE: "Mucho"}),
            _resp("persona_comun", datetime(2026, 8, 20), {PRE: "Poco"}),
        ]
        kpis = kpi_cards(responses)
        assert kpis["percepcion_inflacion"].mean == 66.5
        assert kpis["percepcion_inflacion"].n_responses == 2

    def test_kpi_cards_vacio(self):
        assert kpi_cards([]) == {}


class TestSeries:
    def test_series_df_estructura(self):
        base = datetime(2026, 8, 1)
        responses = [
            _resp("persona_comun", base + timedelta(days=d),
                  {PRE: "Mucho" if d % 2 == 0 else "Poco"})
            for d in range(5)
        ]
        df = series_df(responses, freq="D", min_responses=1)
        assert {"kpi", "date", "mean", "n"} <= set(df.columns)
        assert "percepcion_inflacion" in df["kpi"].values
        assert (df["n"] == 1).all()  # una respuesta por día

    def test_series_df_min_responses_filtra(self):
        base = datetime(2026, 8, 1)
        responses = [_resp("comerciante", base, {VENTAS: "Mejor"})]
        df = series_df(responses, freq="D", min_responses=5)
        assert df.empty

    def test_series_df_vacio(self):
        assert series_df([]).empty


class TestPeriodos:
    def test_split_periods(self):
        now = datetime.now()
        current = _resp("persona_comun", now - timedelta(days=5), {PRE: "Mucho"})
        previous = _resp("persona_comun", now - timedelta(days=45), {PRE: "Poco"})
        antiguo = _resp("persona_comun", now - timedelta(days=200), {PRE: "Nada"})
        cur, prev = split_periods([current, previous, antiguo], current_days=30)
        assert len(cur) == 1 and cur[0] is current
        assert len(prev) == 1 and prev[0] is previous

    def test_compare_periods_delta(self):
        cur = {"a": kpi_result(80), "b": kpi_result(50)}
        prev = {"a": kpi_result(70), "b": kpi_result(50)}
        deltas = compare_periods(cur, prev)
        assert deltas["a"] == 10.0
        assert deltas["b"] == 0.0

    def test_compare_periods_solo_comunes(self):
        cur = {"a": kpi_result(80)}
        prev = {"b": kpi_result(70)}
        assert compare_periods(cur, prev) == {}


def kpi_result(mean):
    from src.analyzers.surveys.indicators import KPIResult
    return KPIResult(key="x", label="X", mean=mean, std=1.0, n_responses=10)


class TestContraste:
    def test_build_contrast_con_percepcion(self):
        responses = [_resp("persona_comun", datetime(2026, 8, 19), {PRE: "Mucho"})]
        result = build_contrast(responses, official=25, ovf=60)
        assert result is not None
        assert result["perceived"] == 100.0
        assert result["official"] == 25.0

    def test_build_contrast_sin_percepcion(self):
        responses = [_resp("comerciante", datetime(2026, 8, 19), {VENTAS: "Mejor"})]
        assert build_contrast(responses, official=25) is None

    def test_build_contrast_vacio(self):
        assert build_contrast([], official=25) is None


class TestReport:
    def test_build_report_contenido(self):
        responses = [
            _resp("persona_comun", datetime(2026, 8, 19),
                  {PRE: "Mucho", AHORRO: "Sí"}),
        ]
        contrast = build_contrast(responses, official=25)
        md = build_report(
            "persona_comun", responses, contrast=contrast,
            period="Agosto 2026", ai_enabled=False,
        )
        assert "Informe Ejecutivo" in md
        assert "Persona Común" in md
        assert "Percepción de inflación" in md

    def test_build_report_vacio(self):
        md = build_report("comerciante", [], ai_enabled=False)
        assert "Sin KPIs calculados" in md