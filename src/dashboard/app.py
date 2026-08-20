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
tab_inicio, tab_ibc, tab_noticias, tab_encuestas, tab_informes, tab_macro = st.tabs(
    ["🏠 Inicio", "📈 IBC", "📰 Noticias", "📋 Encuestas", "📊 Informes", "🔬 Macro"]
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: MACRO (Análisis Avanzado)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_macro:
    from src.analyzers.sovereign_risk import SovereignRiskIndex
    from src.analyzers.balance_of_payments import BalanceOfPaymentsAnalyzer
    from src.analyzers.public_debt import PublicDebtAnalyzer
    from src.analyzers.phillips import PhillipsCurveAnalyzer
    from src.analyzers.integrated_forecast import IntegratedForecaster
    from src.analyzers.nowcasting import InflationNowcaster
    from src.analyzers.iae import IAEIndex
    from src.alerts.manager import AlertManager
    from src.dashboard.macro_data import macro_summary

    st.subheader("🔬 Análisis Macro Avanzado")

    # ── Sub-tabs para Macro ──
    macro_tab1, macro_tab2, macro_tab3, macro_tab4, macro_tab5 = st.tabs(
        ["🚨 Riesgo & Sostenibilidad", "🔮 Pronóstico Integral", "📡 Nowcasting & IAE", "🔔 Alertas", "📉 Modelos Econométricos"]
    )

    # ── Sub-tab 1: Riesgo & Sostenibilidad ──
    with macro_tab1:
        st.markdown("### 🚨 Índice de Riesgo Soberano")
        risk = SovereignRiskIndex()
        risk_result = risk.calculate(
            spread_pct=brecha if brecha else 0,
            annual_inflation=metrics["inflacion"].annual_rate if metrics["inflacion"] else 0,
            oil_production_mbd=1.08,
        )

        rc1, rc2 = st.columns([1, 3])
        with rc1:
            score = risk_result.score
            if score < 25:
                color = theme.PALETTE["verde"]
            elif score < 50:
                color = theme.PALETTE["amarillo"]
            elif score < 75:
                color = theme.PALETTE["naranja"]
            else:
                color = theme.PALETTE["rojo"]
            st.markdown(
                f"<div style='text-align:center; padding:20px; border-radius:10px; "
                f"background:rgba(0,0,0,0.05);'>
                f"<div style='font-size:48px; font-weight:bold; color:{color};'>{score:.0f}</div>
                f"<div style='font-size:14px; color:#666;'>/100</div>
                f"<div style='font-size:18px; font-weight:600; color:{color};'>"
                f"{risk_result.level.upper()}</div></div>",
                unsafe_allow_html=True,
            )
            if risk_result.momentum is not None:
                m_color = "🔴" if risk_result.momentum > 5 else "🟢" if risk_result.momentum < -5 else "⚪"
                st.caption(f"{m_color} Momentum: {risk_result.momentum:+.1f} vs período anterior")
        with rc2:
            st.markdown(risk_result.interpretation)
            st.markdown("**Factores:**")
            for factor, value in sorted(risk_result.components.items(), key=lambda x: -x[1]):
                label = {
                    "spread": "Brecha cambiaria",
                    "volatility": "Volatilidad",
                    "inflation": "Inflación",
                    "reserves": "Reservas",
                    "debt": "Deuda",
                    "oil": "Petróleo",
                    "political": "Riesgo político",
                    "uncertainty": "Incertidumbre",
                }.get(factor, factor)
                st.progress(min(value / 100, 1.0), text=f"{label}: {value:.0f}/100")

        # ── Balanza de Pagos ──
        st.markdown("### 💱 Balanza de Pagos")
        bop = BalanceOfPaymentsAnalyzer()
        bop_result = bop.analyze(
            reserves=None,
            oil_production_mbd=1.08,
            oil_price_usd=70,
            imports_monthly=2e9,
        )

        bop_c1, bop_c2, bop_c3, bop_c4 = st.columns(4)
        with bop_c1:
            st.metric("Cuenta Corriente", f"${bop_result.current_account.balance/1e9:.1f}B")
        with bop_c2:
            st.metric("Reservas", f"{bop_result.reserves.months_coverage:.1f} meses")
        with bop_c3:
            st.metric("Ingresos Petróleo", f"${bop_result.current_account.oil_revenues/1e9:.1f}B")
        with bop_c4:
            st.metric("Score Sustentabilidad", f"{bop_result.external_sustainability_score:.0f}/100")

        st.markdown(bop_result.interpretation)

        # Ciclo petrolero
        if bop_result.oil_cycle.interpretation:
            with st.expander("🛢️ Detalle Ciclo Petrolero"):
                oil_c1, oil_c2, oil_c3 = st.columns(3)
                with oil_c1:
                    st.metric("Ingresos Brutos", f"${bop_result.oil_cycle.gross_revenues/1e9:.1f}B")
                with oil_c2:
                    st.metric("Netos Fisco", f"${bop_result.oil_cycle.net_revenues/1e9:.1f}B")
                with oil_c3:
                    st.metric("Flujo Efectivo", f"${bop_result.oil_cycle.effective_cash_flow/1e9:.1f}B")
                st.caption(bop_result.oil_cycle.interpretation)

        # ── Deuda Pública ──
        st.markdown("### 💳 Deuda Pública")
        debt = PublicDebtAnalyzer()
        debt_result = debt.analyze(
            total_debt_usd=240e9,
            gdp_usd=94e9,
            external_debt_usd=180e9,
            fiscal_deficit_pct=5.8,
            oil_revenues_usd=35e9,
            oil_price=70,
            short_term_debt=60e9,
            medium_term_debt=100e9,
            long_term_debt=80e9,
            pdvsa_debt=40e9,
        )

        dc1, dc2, dc3, dc4 = st.columns(4)
        with dc1:
            st.metric("Deuda/PIB", f"{debt_result.debt_gdp_ratio:.0f}%" if debt_result.debt_gdp_ratio else "—")
        with dc2:
            st.metric("Sostenibilidad", debt_result.sustainability.upper())
        with dc3:
            st.metric("Riesgo Rollover", debt_result.maturity.rollover_risk.upper())
        with dc4:
            if debt_result.structure.weighted_interest_rate > 0:
                st.metric("Tasa Promedio", f"{debt_result.structure.weighted_interest_rate:.1f}%")

        st.markdown(debt_result.interpretation)

        # Escenarios de estrés
        if debt_result.stress_scenarios:
            with st.expander("🔥 Escenarios de Estrés"):
                for sc in debt_result.stress_scenarios:
                    icon = "🔴" if sc.sustainability == "insostenible" else "🟡" if sc.sustainability == "en_riesgo" else "🟢"
                    st.info(
                        f"{icon} **{sc.name}**: Deuda/PIB = {sc.projected_debt_gdp:.0f}% "
                        f"({sc.sustainability.upper()}) — {sc.interpretation}"
                    )

        # Pasivos contingentes
        if debt_result.structure.external_ratio > 0:
            with st.expander("⚠️ Pasivos Contingentes"):
                st.markdown(
                    f"- **PDVSA**: $40B estimado\n"
                    f"- **Empresas estatales**: pendiente\n"
                    f"- **Pensiones no fondeadas**: pendiente\n"
                    f"- **Garantías gubernamentales**: pendiente"
                )

    # ── Sub-tab 2: Pronóstico Integral ──
    with macro_tab2:
        st.markdown("### 🔮 Pronóstico Integral")
        st.caption("Combina SVAR + Nowcast + Phillips para escenarios macro")

        # Inputs del usuario
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            oil_input = st.number_input("Precio Petróleo (USD)", value=65.0, step=5.0, key="fc_oil")
        with fc2:
            spread_input = st.number_input("Brecha Cambiaria (%)", value=30.0, step=5.0, key="fc_spread")
        with fc3:
            gdp_input = st.number_input("Crecimiento PIB (%)", value=3.0, step=0.5, key="fc_gdp")

        if st.button("🔮 Generar Escenarios", key="btn_forecast"):
            forecaster = IntegratedForecaster()
            forecast_result = forecaster.scenario_analysis(
                macro_data=pd.DataFrame(),
                base_oil=oil_input,
                base_inflation=metrics["inflacion"].monthly_rate if metrics["inflacion"] else 10.0,
                base_gdp=gdp_input,
                base_spread=spread_input,
                base_exchange=metrics["oficial"] if metrics["oficial"] else 500.0,
            )

            # Escenarios
            sc1, sc2, sc3 = st.columns(3)
            with sc1:
                st.markdown("#### 🟢 Optimista")
                opt = forecast_result.optimistic_scenario
n                st.metric("Inflación", f"{opt.inflation_forecast:.1f}%")
                st.metric("TC", f"{opt.exchange_rate_forecast:.0f} Bs./USD")
                st.caption(opt.interpretation)
            with sc2:
                st.markdown("#### 🟡 Central")
                cen = forecast_result.central_scenario
                st.metric("Inflación", f"{cen.inflation_forecast:.1f}%")
                st.metric("TC", f"{cen.exchange_rate_forecast:.0f} Bs./USD")
                st.caption(cen.interpretation)
            with sc3:
                st.markdown("#### 🔴 Pesimista")
                pes = forecast_result.pessimistic_scenario
                st.metric("Inflación", f"{pes.inflation_forecast:.1f}%")
                st.metric("TC", f"{pes.exchange_rate_forecast:.0f} Bs./USD")
                st.caption(pes.interpretation)

            st.info(forecast_result.interpretation)

            # Sensibilidad
            with st.expander("📊 Análisis de Sensibilidad"):
                for var, effects in forecast_result.sensitivity.items():
                    st.markdown(f"**{var}:**")
                    for key, val in effects.items():
                        if key != "impact_on_inflation":
                            st.write(f"  - {key}: {val:+.1f} pp")

    # ── Sub-tab 3: Nowcasting & IAE ──
    with macro_tab4:
        st.markdown("### 📡 Nowcasting & Índice de Actividad Económica")

        # Nowcasting de inflación con datos reales
        st.markdown("#### 🎯 Nowcasting de Inflación")
        nowcaster = InflationNowcaster()

        nc1, nc2 = st.columns(2)
        with nc1:
            st.metric("Modelo", "RandomForest + XGBoost")
            st.caption("Predice inflación mensual con datos de alta frecuencia")
        with nc2:
            if metrics["oficial"] and metrics["paralelo"]:
                brecha_val = (metrics["paralelo"] / metrics["oficial"] - 1) * 100 if metrics["oficial"] > 0 else 0
                st.metric("Brecha cambiaria actual", f"{brecha_val:.1f}%")
                st.caption("Variable proxy principal para nowcasting")
            else:
                st.metric("Variables proxy", "TC paralelo, petróleo, sentimiento")

        # Intentar nowcast con datos disponibles
        try:
            from src.db.session import get_session
            from src.db.repositories import MarketRepository
            from datetime import timedelta

            with get_session() as sess:
                repo = MarketRepository(sess)
                rates = repo.list_rates(since=datetime.now(timezone.utc) - timedelta(days=90), limit=200)

                if len(rates) >= 20:
                    # Construir DataFrame para nowcasting
                    df_now = pd.DataFrame([
                        {"date": r.date, "official_rate": float(r.rate) if r.source == "bcv" else None,
                         "parallel_rate": float(r.rate) if r.source in ("binance", "bybit") else None}
                        for r in rates
                    ])
                    df_now = df_now.groupby("date").mean(numeric_only=True).dropna()

                    if len(df_now) >= 10:
                        st.success(f"✅ {len(df_now)} observaciones disponibles para nowcasting")
                        st.line_chart(df_now[["official_rate", "parallel_rate"]].dropna())
                    else:
                        st.warning("⚠️ Datos insuficientes para nowcasting (mínimo 10 observaciones)")
                else:
                    st.warning("⚠️ Datos insuficientes. Ejecute collect_market para poblar.")
        except Exception as e:
            st.warning(f"⚠️ Nowcasting requiere datos históricos: {e}")

        st.markdown("---")

        # IAE con datos reales
        st.markdown("#### 📊 Índice de Actividad Económica (IAE)")
        iae = IAEIndex()

        # Calcular componentes con datos disponibles
        try:
            if metrics["oficial"] and metrics["paralelo"]:
                # Componente TC
                tc_score = iae.calculate_exchange_rate_component(
                    current_rate=metrics["paralelo"],
                    avg_rate_30d=metrics["oficial"]  # Proxy: usar oficial como promedio
                )
                # Componente petróleo (estimado)
                oil_score = iae.calculate_oil_component(1.08, 1.0)
                # Componente sentimiento (estimado desde noticias)
                sentiment_score = 50  # Neutral por defecto
                # Componente noticias
                news_score = 50  # Neutral por defecto
                # Componente inflación
                infl_score = iae.calculate_inflation_component(
                    metrics["inflacion"].monthly_rate if metrics["inflacion"] else 10
                )

                # IAE compuesto
                iae_value = (
                    tc_score * iae.weights["exchange_rate"] +
                    oil_score * iae.weights["oil_production"] +
                    sentiment_score * iae.weights["sentiment"] +
                    news_score * iae.weights["news_frequency"] +
                    infl_score * iae.weights["inflation"]
                )

                iae_c1, iae_c2, iae_c3, iae_c4 = st.columns(4)
                with iae_c1:
                    color = "🟢" if iae_value > 60 else "🟡" if iae_value > 40 else "🔴"
                    st.metric(f"{color} IAE", f"{iae_value:.1f}")
                    st.caption("Índice compuesto (0-100+)")
                with iae_c2:
                    st.metric("TC", f"{tc_score:.0f}")
                    st.caption("Estabilidad cambiaria")
                with iae_c3:
                    st.metric("Petróleo", f"{oil_score:.0f}")
                    st.caption("Producción")
                with iae_c4:
                    st.metric("Inflación", f"{infl_score:.0f}")
                    st.caption("Estabilidad de precios")

                # Interpretación
                if iae_value > 70:
                    st.success("📈 **Expansión económica**: El IAE indica actividad positiva.")
                elif iae_value > 40:
                    st.info("➡️ **Actividad estable**: El IAE indica condiciones normales.")
                else:
                    st.warning("📉 **Contracción económica**: El IAE indica debilidad.")
            else:
                st.warning("⚠️ IAE requiere datos de tipo de cambio.")
        except Exception as e:
            st.warning(f"⚠️ IAE no disponible: {e}")

    # ── Sub-tab 4: Alertas ──
    with macro_tab5:
        st.markdown("### 🔔 Sistema de Alertas Económicas")

        alert_mgr = AlertManager()

        # Verificar alertas con datos actuales
        if metrics["oficial"] and metrics["paralelo"]:
            alerts = alert_mgr.check_exchange_rate(
                parallel_rate=metrics["paralelo"],
                official_rate=metrics["oficial"],
            )

            if alerts:
                for alert in alerts:
                    if alert.level.value == "critical":
                        st.error(f"🚨 **{alert.title}**: {alert.message}")
                    elif alert.level.value == "warning":
                        st.warning(f"⚠️ **{alert.title}**: {alert.message}")
                    else:
                        st.info(f"ℹ️ **{alert.title}**: {alert.message}")
            else:
                st.success("✅ No hay alertas activas. Todos los indicadores dentro de rangos normales.")

        # Reglas de alerta configuradas
        st.markdown("#### ⚙️ Reglas Configuradas")
        rules_df = pd.DataFrame([
            {"Indicador": r.indicator, "Tipo": r.type.value,
             "Warning": r.warning_threshold, "Critical": r.critical_threshold,
             "Descripción": r.description}
            for r in alert_mgr.rules
        ])
        st.dataframe(rules_df, use_container_width=True)

        # Resumen de umbrales
        st.markdown("#### 📊 Umbrales de Alerta")
        th_c1, th_c2, th_c3, th_c4 = st.columns(4)
        with th_c1:
            st.metric("TC Paralelo", "⚠️ 20%", "🔴 50%")
            st.caption("Variación diaria")
        with th_c2:
            st.metric("Brecha", "⚠️ 30%", "🔴 50%")
            st.caption("Oficial vs paralelo")
        with th_c3:
            st.metric("Inflación", "⚠️ 20%", "🔴 50%")
            st.caption("Mensual")
        with th_c4:
            st.metric("IBC", "⚠️ 5%", "🔴 10%")
            st.caption("Variación")

    # ── Sub-tab 5: Modelos Econométricos ──
    with macro_tab3:
        st.markdown("### 📉 Modelos Econométricos")

        # Curva de Phillips con datos reales
        st.markdown("#### 📉 Curva de Phillips")
        phillips = PhillipsCurveAnalyzer()

        try:
            from src.db.session import get_session
            from src.db.repositories import MarketRepository
            from datetime import timedelta

            with get_session() as sess:
                repo = MarketRepository(sess)
                rates = repo.list_rates(since=datetime.now(timezone.utc) - timedelta(days=365), limit=1000)

                if len(rates) >= 50:
                    # Construir series para Phillips
                    df_ph = pd.DataFrame([
                        {"date": r.date, "rate": float(r.rate), "source": r.source}
                        for r in rates if r.source == "bcv"
                    ])
                    df_ph = df_ph.groupby("date").mean(numeric_only=True)

                    if len(df_ph) >= 20:
                        # Usar variación del TC como proxy de inflación
                        inflation_series = df_ph["rate"].pct_change().dropna() * 100
                        # Usar nivel del TC como proxy de actividad
                        activity_series = df_ph["rate"].dropna()

                        result = phillips.fit_basic(inflation_series, activity_series)
                        if result:
                            pc1, pc2 = st.columns(2)
                            with pc1:
                                st.metric("Pendiente", f"{result.slope:.4f}")
                                st.caption("Negativa = trade-off clásico")
                            with pc2:
                                st.metric("R²", f"{result.r_squared:.3f}")
                                st.caption("Bondad de ajuste")
                            st.info(result.interpretation)

                            # Gráfico
                            fig_ph = go.Figure()
                            fig_ph.add_trace(go.Scatter(
                                x=activity_series.values, y=inflation_series.values,
                                mode='markers', name='Datos'
                            ))
                            fig_ph.update_layout(
                                title='Curva de Phillips (Proxy: TC vs Variación)',
                                xaxis_title='Nivel TC (Proxy actividad)',
                                yaxis_title='Variación TC % (Proxy inflación)'
                            )
                            st.plotly_chart(fig_ph, use_container_width=True)
                        else:
                            st.warning("⚠️ Datos insuficientes para ajustar Phillips")
                    else:
                        st.warning("⚠️ Necesita al menos 20 observaciones")
                else:
                    st.warning("⚠️ Datos insuficientes. Ejecute collect_market para poblar.")
        except Exception as e:
            st.warning(f"⚠️ Phillips requiere datos históricos: {e}")

        st.markdown("---")

        # SVAR con datos reales
        st.markdown("#### 🔗 SVAR - Shocks Estructurales")

        try:
            from src.db.session import get_session
            from src.db.repositories import MarketRepository
            from src.analyzers.svar import SVARAnalyzer
            from datetime import timedelta

            with get_session() as sess:
                repo = MarketRepository(sess)
                rates = repo.list_rates(since=datetime.now(timezone.utc) - timedelta(days=365), limit=1000)

                if len(rates) >= 100:
                    # Construir DataFrame multivariado
                    df_svar = pd.DataFrame([
                        {"date": r.date, "rate": float(r.rate), "source": r.source}
                        for r in rates
                    ])
                    df_pivot = df_svar.pivot_table(index="date", columns="source", values="rate", aggfunc="mean")
                    df_pivot = df_pivot.dropna()

                    if len(df_pivot) >= 50 and "bcv" in df_pivot.columns:
                        svar = SVARAnalyzer(max_lags=3)
                        fit_result = svar.fit(df_pivot[["bcv"]])

                        if "error" not in fit_result:
                            st.success(f"✅ VAR ajustado: {fit_result['optimal_lags']} rezagos, AIC={fit_result['aic']:.2f}")

                            # Resumen
                            sc1, sc2, sc3 = st.columns(3)
                            with sc1:
                                st.metric("Variables", fit_result['variables'])
                            with sc2:
                                st.metric("Rezagos óptimos", fit_result['optimal_lags'])
                            with sc3:
                                st.metric("Observaciones", fit_result['n_obs'])

                            # FEVD placeholder
                            st.info(
                                "*FEVD e IRF se calcularán cuando haya múltiples variables "
                                "(inflación, TC, petróleo) en la serie.*"
                            )
                        else:
                            st.warning(f"⚠️ VAR no pudo ajustarse: {fit_result['error']}")
                    else:
                        st.warning("⚠️ Necesita al menos 50 observaciones con múltiples variables")
                else:
                    st.warning("⚠️ Datos insuficientes. Ejecute collect_market para poblar.")
        except Exception as e:
            st.warning(f"⚠️ SVAR requiere datos históricos: {e}")

        st.markdown("---")

        # Regional
        st.markdown("#### 🌎 Comparación Regional")
        try:
            from src.analyzers.regional import RegionalAnalyzer
            regional = RegionalAnalyzer()
            st.info(
                "*Las comparaciones regionales se activarán cuando se integren "
                "los datos de World Bank (wbgapi) con el dashboard.*"
            )
        except Exception:
            st.info("*Módulo regional disponible pero sin datos aún.*")

    # ── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>Economía Venezuela v0.1.0 | Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
    unsafe_allow_html=True
)
