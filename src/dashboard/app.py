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
from src.dashboard.components.news_section import render_news_section
from src.dashboard.components.survey_section import render_survey_section
from src.dashboard.market_data import dashboard_metrics, format_metric

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
tab_inicio, tab_noticias, tab_encuestas = st.tabs(
    ["🏠 Inicio", "📰 Noticias", "📋 Encuestas"]
)

with tab_inicio:
    # Métricas generales (Fase A: datos persistidos por los collectors)
    metrics = dashboard_metrics()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="💵 Dólar Oficial (BCV)",
            value=format_metric(metrics["oficial"].rate if metrics["oficial"] else None, " Bs"),
            delta=(
                f"{metrics['oficial'].variation_pct:+.2f}%"
                if metrics["oficial"] and metrics["oficial"].variation_pct is not None
                else None
            ),
            help="Última tasa oficial persistida por el colector BCV",
        )
    with col2:
        st.metric(
            label="💵 Dólar Paralelo (P2P)",
            value=format_metric(metrics["paralelo"].rate if metrics["paralelo"] else None, " Bs"),
            help="Última tasa USDT/VES del mercado P2P (Binance)",
        )
    with col3:
        infl_source = (
            metrics["inflacion"].source.upper()
            if metrics["inflacion"] else "BCV/OVF"
        )
        st.metric(
            label=f"📈 Inflación Mensual ({infl_source})",
            value=format_metric(
                metrics["inflacion"].monthly_rate if metrics["inflacion"] else None, " %"
            ),
            help="Último IPC mensual persistido (BCV oficial, fallback OVF)",
        )

    if not metrics["oficial"] and not metrics["paralelo"] and not metrics["inflacion"]:
        st.info(
            "Aún no hay datos de mercado en la base. Ejecuta "
            "`python -m src.scripts.collect_market` (o espera el job del scheduler) "
            "para poblar las tarjetas."
        )

with tab_noticias:
    render_news_section()

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