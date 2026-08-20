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
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.dashboard import theme
from src.dashboard.components.news_section import render_news_section
from src.dashboard.components.survey_section import render_survey_section
from src.dashboard.market_data import (
    BYBIT_SOURCE,
    brecha_porcentaje,
    brecha_series,
    dashboard_metrics,
    format_metric,
    list_rates,
)

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
    brecha = brecha_porcentaje(metrics["oficial"], metrics["paralelo"])

    col1, col2, col3, col4 = st.columns(4)

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
            label="💵 Dólar Paralelo (Binance)",
            value=format_metric(metrics["paralelo"].rate if metrics["paralelo"] else None, " Bs"),
            delta=(
                f"{brecha:+.2f}%" if brecha is not None else None
            ),
            help="Última tasa USDT/VES del mercado P2P (Binance)",
        )
    with col3:
        st.metric(
            label="💵 Dólar Paralelo (Bybit)",
            value=format_metric(metrics["bybit"].rate if metrics["bybit"] else None, " Bs"),
            help="Última tasa USDT/VES del mercado P2P (Bybit)",
        )
    with col4:
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

    if not (metrics["oficial"] or metrics["paralelo"] or metrics["inflacion"]):
        st.info(
            "Aún no hay datos de mercado en la base. Ejecuta "
            "`python -m src.scripts.collect_market` (o espera el job del scheduler) "
            "para poblar las tarjetas."
        )

    # Brecha cambiaria
    st.subheader("⚖️ Brecha Cambiaria")
    c1, c2 = st.columns(2)
    with c1:
        st.metric(
            label="Brecha Paralelo vs Oficial",
            value=format_metric(brecha, " %"),
            help="(Dólar paralelo P2P / dólar oficial BCV - 1) * 100",
        )
    with c2:
        brecha_bybit = brecha_porcentaje(metrics["oficial"], metrics["bybit"])
        st.metric(
            label="Brecha Bybit vs Oficial",
            value=format_metric(brecha_bybit, " %"),
            help="(Dólar Bybit / dólar oficial BCV - 1) * 100",
        )

    # Gráfico histórico (6 meses)
    st.subheader("📈 Evolución del Dólar (6 meses)")
    brecha_df = brecha_series(BYBIT_SOURCE, since_days=180)
    if not brecha_df.empty:
        fig = go.Figure()
        series = {
            "BCV Oficial": list_rates("bcv", "usd", limit=200),
            "Binance P2P": list_rates("binance", "usdt", limit=200),
            "Bybit P2P": list_rates(BYBIT_SOURCE, "usdt", limit=200),
        }
        colors = {
            "BCV Oficial": "#2CA58D",
            "Binance P2P": "#F2C14E",
            "Bybit P2P": "#C0392B",
        }
        for name, rates in series.items():
            if not rates:
                continue
            df = pd.DataFrame(
                [(r.date.date(), r.rate) for r in rates], columns=["fecha", "rate"]
            ).sort_values("fecha")
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["rate"], mode="lines",
                name=name, line=dict(color=colors[name], width=2),
            ))
        fig.update_layout(
            template=theme.plotly_template(),
            height=400,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay suficiente serie histórica para graficar la brecha.")

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