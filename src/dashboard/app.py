"""
Dashboard Principal - Economía Venezuela
========================================

5 tabs:
- 🏠 Inicio: métricas de dólar, inflación, brecha, gráfico histórico
- 📈 IBC: índice bursátil, componentes, gainers/losers, tickers
- 📰 Noticias: sentimiento, distribución, últimos titulares
- 📋 Encuestas: KPIs, serie temporal, contraste, informe ejecutivo
- 📊 Informes: generador de informes periódicos (MD + PDF)

Sidebar: filtros globales y generación rápida de informes.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path for `streamlit run src/dashboard/app.py`
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

from src.dashboard import theme
from src.dashboard.components.news_section import render_news_section
from src.dashboard.components.reports_section import render_reports_section
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

# ─── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 Filtros Globales")

    # Date range
    start_date = st.date_input(
        "Fecha inicio",
        value=datetime.now() - timedelta(days=30),
    )
    end_date = st.date_input(
        "Fecha fin",
        value=datetime.now(),
    )

    st.markdown("---")

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

    st.markdown("---")

    # Quick actions
    st.subheader("⚡ Acciones Rápidas")
    if st.button("🔄 Recolección de mercado", use_container_width=True):
        st.toast("Ejecutando collect_market...", icon="🔄")
    if st.button("📰 Recolectar noticias", use_container_width=True):
        st.toast("Ejecutando collect_news...", icon="📰")

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab_inicio, tab_ibc, tab_noticias, tab_encuestas, tab_informes = st.tabs(
    ["🏠 Inicio", "📈 IBC", "📰 Noticias", "📋 Encuestas", "📊 Informes"]
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: INICIO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_inicio:
    metrics = dashboard_metrics()
    brecha = brecha_porcentaje(metrics["oficial"], metrics["paralelo"])

    # ── Tarjetas principales ──
    c1, c2, c3, c4 = st.columns(4)

    with c1:
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
    with c2:
        st.metric(
            label="💵 Dólar Paralelo (Binance)",
            value=format_metric(metrics["paralelo"].rate if metrics["paralelo"] else None, " Bs"),
            delta=(
                f"{brecha:+.2f}%" if brecha is not None else None
            ),
            help="Última tasa USDT/VES del mercado P2P (Binance)",
        )
    with c3:
        st.metric(
            label="💵 Dólar Bybit",
            value=format_metric(metrics["bybit"].rate if metrics["bybit"] else None, " Bs"),
            help="Última tasa USDT/VES del mercado P2P (Bybit)",
        )
    with c4:
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

    # ── Brecha cambiaria ──
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

    # ── Indicadores macroeconómicos ──
    from src.dashboard.macro_data import macro_summary
    macro = macro_summary()

    has_macro = any(macro.values())
    if has_macro:
        st.subheader("🏛️ Indicadores Macroeconómicos")
        mc1, mc2, mc3, mc4, mc5 = st.columns(5)

        with mc1:
            pib = macro.get("pib")
            if pib:
                st.metric(
                    label=f"💰 PIB ({pib['source']})",
                    value=f"{pib['value']:,.0f}",
                    help=f"Período: {pib['period']} | Unidad: {pib['unit']}",
                )
            else:
                st.metric(label="💰 PIB", value="—")

        with mc2:
            crec = macro.get("pib_crecimiento")
            if crec:
                st.metric(
                    label=f"📈 Crecimiento PIB ({crec['source']})",
                    value=f"{crec['value']:+.1f}%",
                    help=f"Período: {crec['period']}",
                )
            else:
                st.metric(label="📈 Crecimiento PIB", value="—")

        with mc3:
            infl = macro.get("inflacion_int")
            if infl:
                st.metric(
                    label=f"📊 Inflación ({infl['source']})",
                    value=f"{infl['value']:.1f}%",
                    help=f"Período: {infl['period']}",
                )
            else:
                st.metric(label="📊 Inflación Internacional", value="—")

        with mc4:
            petro = macro.get("petroleo")
            if petro:
                st.metric(
                    label=f"🛢️ Petróleo ({petro['source']})",
                    value=f"${petro['value']:,.2f}",
                    help=f"{petro.get('indicator', '')} | {petro['period']}",
                )
            else:
                st.metric(label="🛢️ Petróleo", value="—")

        with mc5:
            onu = macro.get("gasto_onu")
            if onu:
                st.metric(
                    label=f"🇺🇳 Gasto ONU ({onu['source']})",
                    value=f"${onu['value']:,.0f}",
                    help=f"Período: {onu['period']}",
                )
            else:
                st.metric(label="🇺🇳 Gasto ONU", value="—")

    # ── Gráfico histórico (6 meses) ──
    st.subheader("📈 Evolución del Dólar (6 meses)")
    brecha_df = brecha_series(BYBIT_SOURCE, since_days=180)
    if not brecha_df.empty:
        fig = go.Figure()
        series_data = {
            "BCV Oficial": list_rates("bcv", "usd", limit=200),
            "Binance P2P": list_rates("binance", "usdt", limit=200),
            "Bybit P2P": list_rates(BYBIT_SOURCE, "usdt", limit=200),
        }
        colors = {
            "BCV Oficial": "#2CA58D",
            "Binance P2P": "#F2C14E",
            "Bybit P2P": "#C0392B",
        }
        for name, rates in series_data.items():
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: IBC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_ibc:
    from src.dashboard.ibc_data import (
        ibc_gainers_losers,
        ibc_index_series,
        ibc_latest,
        ven_tickers_top,
    )

    st.subheader("📈 Índice Bursátil Caracas (IBC)")

    # Último valor del IBC
    ibc = ibc_latest()
    if ibc:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric(
                label="🎯 IBC Actual",
                value=f"{ibc['value']:,.2f}",
                delta=f"{ibc['change_pct']:+.2f}%" if ibc["change_pct"] else None,
            )
        with c2:
            st.metric(
                label="📊 Cambio",
                value=f"{ibc['change']:+,.2f}",
            )
        with c3:
            st.metric(
                label="📅 Fecha",
                value=ibc["date"].strftime("%d/%m/%Y") if hasattr(ibc["date"], "strftime") else str(ibc["date"]),
            )
    else:
        st.info(
            "📭 No hay datos del IBC. Ejecuta `python -m src.scripts.backfill_ibc` "
            "para poblar esta sección."
        )

    # Gráfico del IBC
    ibc_df = ibc_index_series(days=180)
    if not ibc_df.empty:
        st.subheader("📈 Evolución del IBC (6 meses)")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=ibc_df["date"], y=ibc_df["value"],
            mode="lines+markers",
            name="IBC",
            line=dict(color=theme.PALETTE["azul"], width=2.5),
            marker=dict(size=4),
        ))
        fig.update_layout(
            template=theme.plotly_template(),
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Puntos",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Componentes del IBC
    st.subheader("🏢 Componentes del IBC")
    gl = ibc_gainers_losers()

    if gl["gainers"] or gl["losers"]:
        col_g, col_l = st.columns(2)

        with col_g:
            st.markdown("##### 🟢 Gainers")
            for c in gl["gainers"]:
                st.metric(
                    label=f"{c['ticker']} — {c['name']}",
                    value=f"${c['price']:,.2f}",
                    delta=f"{c['change_pct']:+.2f}%",
                    delta_color="normal",
                )

        with col_l:
            st.markdown("##### 🔴 Losers")
            for c in gl["losers"]:
                st.metric(
                    label=f"{c['ticker']} — {c['name']}",
                    value=f"${c['price']:,.2f}",
                    delta=f"{c['change_pct']:+.2f}%",
                    delta_color="inverse",
                )
    else:
        st.info("No hay datos de componentes del IBC disponibles.")

    # Tickers venezolanos
    st.subheader("🇻🇪 Tickers Venezolanos (fuera del IBC)")
    tk = ven_tickers_top()

    if tk["gainers"] or tk["losers"]:
        col_g, col_l = st.columns(2)

        with col_g:
            st.markdown("##### 🟢 Top Performers")
            for t in tk["gainers"]:
                st.metric(
                    label=f"{t['ticker']} — {t['name']}",
                    value=f"${t['close']:,.2f}",
                    delta=f"{t['change_pct']:+.2f}%",
                )

        with col_l:
            st.markdown("##### 🔴 Bottom Performers")
            for t in tk["losers"]:
                st.metric(
                    label=f"{t['ticker']} — {t['name']}",
                    value=f"${t['close']:,.2f}",
                    delta=f"{t['change_pct']:+.2f}%",
                    delta_color="inverse",
                )
    else:
        st.info("No hay datos de tickers venezolanos disponibles.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: NOTICIAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_noticias:
    render_news_section()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: ENCUESTAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_encuestas:
    render_survey_section(survey_segment)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: INFORMES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_informes:
    render_reports_section()

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>Economía Venezuela v0.1.0 | Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
    unsafe_allow_html=True
)
