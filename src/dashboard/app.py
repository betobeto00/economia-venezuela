"""
Dashboard Principal - Economía Venezuela
========================================

Layout por capas (skill frontend-visionary-artisan):
- Sidebar: filtros (rango de fechas, métricas, segmento de encuesta).
- Pestañas: Inicio (métricas generales) y Encuestas (Fase B).

Toda métrica sale de la capa de datos; no hay valores hardcodeados.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from src.dashboard import theme
from src.dashboard.components.survey_section import render_survey_section

# Page config
st.set_page_config(
    page_title="Economía Venezuela",
    page_icon="🇻🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(theme.apply_global_css(), unsafe_allow_html=True)

# Title
st.title("🇻🇪 Economía Venezuela")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🔍 Filtros")

    # Date range (aplica a métricas generales; encuestas usan su propia ventana)
    start_date = st.date_input(
        "Fecha inicio",
        value=datetime.now() - timedelta(days=30)
    )
    end_date = st.date_input(
        "Fecha fin",
        value=datetime.now()
    )

    # Metrics selection
    metrics = st.multiselect(
        "Métricas a mostrar",
        ["Dólar Oficial", "Dólar Paralelo", "Inflación", "PIB", "Reservas"],
        default=["Dólar Oficial", "Dólar Paralelo"]
    )

    # Segmento de encuesta
    st.subheader("📋 Encuestas")
    survey_segment = st.radio(
        "Segmento",
        ["persona_comun", "comerciante"],
        format_func=lambda s: {
            "persona_comun": "Persona Común",
            "comerciante": "Comerciante",
        }[s],
        index=0,
    )

# Tabs
tab_inicio, tab_encuestas = st.tabs(["🏠 Inicio", "📋 Encuestas"])

with tab_inicio:
    # Métricas generales (pendientes de Fase A: collectors)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="💵 Dólar Oficial",
            value="—",
            help="Dato pendiente: colector BCV (Fase A)",
        )
    with col2:
        st.metric(
            label="💵 Dólar Paralelo",
            value="—",
            help="Dato pendiente: colector OVF/Binance (Fase A)",
        )
    with col3:
        st.metric(
            label="📈 Inflación Mensual",
            value="—",
            help="Dato pendiente: colector BCV IPC (Fase A)",
        )

    st.info(
        "Las métricas generales se mostrarán cuando estén conectados los "
        "colectores de Fase A (BCV, OVF, BVC, Binance)."
    )

with tab_encuestas:
    render_survey_section(survey_segment)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>Economía Venezuela v0.1.0 | Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
    unsafe_allow_html=True
)