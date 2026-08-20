"""
Dashboard Principal - Economía Venezuela
========================================

8 tabs:
- 🏠 Inicio: métricas de dólar, inflación, brecha, gráfico histórico, macro
- 💱 Mercado: tasas por fuente, serie histórica, brecha, CSV
- 📈 IBC: índice, componentes completos, tickers venezolanos, búsqueda
- 📰 Noticias + Reddit: RSS, sentimiento, posts Reddit con sentimiento
- 📋 Encuestas: KPIs, serie temporal, contraste, informe ejecutivo
- 🏛️ Fiscal: gacetas OCR, categorías, leyes AN
- 📊 Informes: generador de informes periódicos (MD + PDF)
- 🔬 Macro: riesgo, BOP, deuda, pronóstico, nowcasting, alertas

Sidebar: filtros globales, panel de recolectores con time range.
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

    # ── Panel de Recolectores ──
    st.subheader("⚡ Recolectores")

    COLLECTORS = {
        "💰 Mercado (BCV, Binance, Bybit, Bancos)": "collect_market",
        "📰 Noticias (RSS + Reddit)": "collect_news",
        "📈 IBC + Tickers": "backfill_ibc",
        "📋 Encuestas (Google Forms)": "collect_surveys",
        "🏛️ Gacetas Oficiales": "collect_gacetas",
        "🔄 Macro (CEPAL, FMI, OPEP, WB)": "refresh_macro",
        "📊 Informe Periódico": "generate_report",
    }

    selected_collectors = st.multiselect(
        "Seleccionar recolectores",
        options=list(COLLECTORS.keys()),
        default=[list(COLLECTORS.keys())[0]],
        key="sidebar_collectors",
    )

    col_time1, col_time2 = st.columns(2)
    with col_time1:
        since_date = st.date_input(
            "Desde",
            value=datetime.now() - timedelta(days=7),
            key="collector_since",
        )
    with col_time2:
        until_date = st.date_input(
            "Hasta",
            value=datetime.now(),
            key="collector_until",
        )

    if st.button("🚀 Ejecutar", width="stretch", type="primary"):
        if not selected_collectors:
            st.warning("Selecciona al menos un recolector")
        else:
            import subprocess
            import sys as _sys
            results = []
            for label in selected_collectors:
                script = COLLECTORS[label]
                cmd = [_sys.executable, "-m", f"src.scripts.{script}"]
                if script == "backfill_ibc":
                    days = (until_date - since_date).days or 7
                    cmd.extend(["--days", str(days)])
                elif script == "generate_report":
                    cmd.extend(["--cadence", "diario"])
                st.toast(f"Ejecutando {script}...", icon="⏳")
                try:
                    result = subprocess.run(
                        cmd, capture_output=True, text=True, timeout=120,
                        cwd=str(Path(__file__).resolve().parent.parent.parent),
                    )
                    if result.returncode == 0:
                        st.success(f"✅ {label}: completado")
                    else:
                        err = (result.stderr or result.stdout or "")[:200]
                        st.error(f"❌ {label}: {err}")
                except subprocess.TimeoutExpired:
                    st.error(f"⏰ {label}: timeout (120s)")
                except Exception as e:
                    st.error(f"❌ {label}: {e}")

# ─── Tabs ───────────────────────────────────────────────────────────────────
tab_inicio, tab_mercado, tab_ibc, tab_noticias, tab_encuestas, tab_fiscal, tab_informes, tab_macro = st.tabs(
    ["🏠 Inicio", "💱 Mercado", "📈 IBC", "📰 Noticias", "📋 Encuestas", "🏛️ Fiscal", "📊 Informes", "🔬 Macro"]
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
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No hay suficiente serie histórica para graficar la brecha.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: MERCADO
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_mercado:
    from src.dashboard.market_data import (
        list_rates,
        brecha_porcentaje,
        format_metric,
        brecha_series,
        BYBIT_SOURCE,
    )
    from src.db.repositories import MarketRepository
    from src.db.session import session_scope
    import pandas as pd
    from datetime import timedelta, timezone

    st.subheader("💱 Tasas de Cambio Detalladas")

    # All latest rates
    with session_scope() as session:
        repo = MarketRepository(session)
        all_latest = repo.latest_all_sources()

    if all_latest:
        st.markdown("### Últimas Cotizaciones por Fuente")
        for rate in all_latest:
            c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
            with c1:
                st.write(f"**{rate.source.upper()}** ({rate.currency.upper()})")
            with c2:
                st.write(f"{format_metric(rate.rate, ' Bs')}")
            with c3:
                var = rate.variation_pct
                delta = f"{var:+.2f}%" if var is not None else "—"
                st.write(delta)
            with c4:
                st.caption(rate.date.strftime("%Y-%m-%d %H:%M"))

    # Historical table
    st.markdown("### Serie Histórica (último mes)")
    sources = st.multiselect(
        "Fuentes",
        options=["bcv", "binance", "bybit", "banco_venezuela", "banco_bicentenario", "banco_provincial", "banco_mercantil", "banco_exterior"],
        default=["bcv", "binance", "bybit"],
        key="mercado_sources",
    )

    if sources:
        with session_scope() as session:
            repo = MarketRepository(session)
            rates_data = []
            for src in sources:
                rates = repo.list_rates(source=src, currency="usd" if src == "bcv" else "usdt", since=datetime.now(timezone.utc) - timedelta(days=30), limit=100)
                for r in rates:
                    rates_data.append({"Fuente": r.source, "Moneda": r.currency, "Tasa": float(r.rate), "Fecha": r.date.date(), "Variación %": r.variation_pct})
        if rates_data:
            df_rates = pd.DataFrame(rates_data)
            st.dataframe(
                df_rates.sort_values("Fecha", ascending=False),
                width="stretch",
                column_config={
                    "Tasa": st.column_config.NumberColumn("Tasa", format="%.2f"),
                    "Variación %": st.column_config.NumberColumn("Variación %", format="%.2f"),
                },
            )
            # Download button
            csv = df_rates.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", csv, "tasas_cambio.csv", "text/csv")
        else:
            st.info("No hay datos históricos para las fuentes seleccionadas.")
    else:
        st.info("Selecciona al menos una fuente para ver la serie histórica.")

    # Brecha chart
    st.markdown("### Evolución de la Brecha (6 meses)")
    brecha_df = brecha_series(BYBIT_SOURCE, since_days=180)
    if not brecha_df.empty:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=brecha_df.index, y=brecha_df["brecha_%"],
            mode="lines", name="Brecha %",
            line=dict(color=theme.PALETTE["rojo"], width=2),
        ))
        fig.update_layout(
            template=theme.plotly_template(),
            height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            yaxis_title="Brecha %",
        )
        st.plotly_chart(fig, width="stretch")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: IBC
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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
        st.plotly_chart(fig, width="stretch")

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

    # ── Tabla completa de componentes ──
    st.subheader("📋 Tabla Completa de Componentes")
    from src.dashboard.ibc_data import ibc_components_all, ibc_components_full_history
    all_comp = ibc_components_all()
    if all_comp:
        df_comp = pd.DataFrame(all_comp)
        # Search filter
        search_comp = st.text_input("🔍 Buscar componente (ticker o nombre)", key="search_comp")
        if search_comp:
            mask = (
                df_comp["ticker"].str.contains(search_comp, case=False, na=False) |
                df_comp["name"].str.contains(search_comp, case=False, na=False)
            )
            df_comp = df_comp[mask]
        st.dataframe(
            df_comp[["ticker", "name", "price", "change_pct", "volume"]],
            width="stretch",
            column_config={
                "price": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "change_pct": st.column_config.NumberColumn("Cambio %", format="%.2f"),
                "volume": st.column_config.NumberColumn("Volumen"),
            },
            hide_index=True,
        )
        # Historical by component
        with st.expander("📅 Histórico por componente (30 días)"):
            comp_options = [c["ticker"] for c in all_comp]
            selected_comp = st.selectbox("Componente", comp_options, key="hist_comp")
            if selected_comp:
                hist_df = ibc_components_full_history(days=30)
                if not hist_df.empty:
                    comp_hist = hist_df[hist_df["ticker"] == selected_comp]
                    if not comp_hist.empty:
                        fig_h = go.Figure()
                        fig_h.add_trace(go.Scatter(
                            x=comp_hist["date"], y=comp_hist["price"],
                            mode="lines+markers", name=selected_comp,
                            line=dict(color=theme.PALETTE["azul"], width=2),
                        ))
                        fig_h.update_layout(
                            template=theme.plotly_template(), height=300,
                            yaxis_title="Precio ($)",
                        )
                        st.plotly_chart(fig_h, width="stretch")
                    else:
                        st.info(f"No hay histórico para {selected_comp}")
                else:
                    st.info("No hay histórico de componentes")
    else:
        st.info("No hay datos de componentes del IBC disponibles.")

    # ── Tickers venezolanos completos ──
    st.subheader("🇻🇪 Tickers Venezolanos (fuera del IBC)")
    from src.dashboard.ibc_data import ven_tickers_latest_snapshot, ven_tickers_series
    tk_df = ven_tickers_latest_snapshot()

    if not tk_df.empty:
        # Top/bottom summary
        col_g, col_l = st.columns(2)
        with col_g:
            st.markdown("##### 🟢 Top 5 Performers")
            top5 = tk_df.head(5)
            for _, t in top5.iterrows():
                st.metric(
                    label=f"{t['ticker']} — {t.get('name', '')}",
                    value=f"${t['close']:,.2f}",
                    delta=f"{t['change_pct']:+.2f}%",
                )
        with col_l:
            st.markdown("##### 🔴 Bottom 5 Performers")
            bot5 = tk_df.tail(5).iloc[::-1]
            for _, t in bot5.iterrows():
                st.metric(
                    label=f"{t['ticker']} — {t.get('name', '')}",
                    value=f"${t['close']:,.2f}",
                    delta=f"{t['change_pct']:+.2f}%",
                    delta_color="inverse",
                )

        # Full table with search/sort/export
        st.markdown("### 📋 Tabla Completa de Tickers")
        search_tk = st.text_input("🔍 Buscar ticker", key="search_tickers")
        if search_tk:
            mask = (
                tk_df["ticker"].str.contains(search_tk, case=False, na=False) |
                tk_df["name"].str.contains(search_tk, case=False, na=False)
            )
            tk_df_show = tk_df[mask]
        else:
            tk_df_show = tk_df

        st.dataframe(
            tk_df_show[["ticker", "name", "close", "change_pct", "avg_volume"]],
            width="stretch",
            column_config={
                "close": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "change_pct": st.column_config.NumberColumn("Cambio %", format="%.2f"),
                "avg_volume": st.column_config.NumberColumn("Volumen"),
            },
            hide_index=True,
        )
        csv_tk = tk_df_show.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV", csv_tk, "tickers_venezolanos.csv", "text/csv")

        # Historical by ticker
        with st.expander("📅 Histórico por ticker (30 días)"):
            tk_options = sorted(tk_df["ticker"].tolist())
            selected_tk = st.selectbox("Ticker", tk_options, key="hist_ticker")
            if selected_tk:
                tk_hist = ven_tickers_series(selected_tk, days=30)
                if not tk_hist.empty:
                    fig_tk = go.Figure()
                    fig_tk.add_trace(go.Scatter(
                        x=tk_hist["date"], y=tk_hist["close"],
                        mode="lines+markers", name=selected_tk,
                        line=dict(color=theme.PALETTE["verde"], width=2),
                    ))
                    fig_tk.update_layout(
                        template=theme.plotly_template(), height=300,
                        yaxis_title="Precio ($)",
                    )
                    st.plotly_chart(fig_tk, width="stretch")
                else:
                    st.info(f"No hay histórico para {selected_tk}")
    else:
        st.info("No hay datos de tickers venezolanos disponibles.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: NOTICIAS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_noticias:
    render_news_section()

    st.markdown("---")

    # ── Reddit + Sentimiento (fusionado de tab Social) ──
    from src.dashboard.social_data import social_posts_with_sentiment, social_summary, sentiment_by_item

    st.subheader("💬 Reddit — Discusión Económica")

    summary = social_summary()

    # KPIs
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        st.metric("📝 Posts totales", summary["total_posts"])
    with sc2:
        st.metric("👍 Score promedio", f"{summary['avg_score']:.1f}")
    with sc3:
        st.metric("💬 Comentarios prom", f"{summary['avg_comments']:.1f}")
    with sc4:
        sent_mean = summary["sentiment_mean"]
        label = "Positivo" if sent_mean > 0.15 else "Negativo" if sent_mean < -0.15 else "Neutral"
        color = "🟢" if sent_mean > 0.15 else "🔴" if sent_mean < -0.15 else "⚪"
        st.metric(f"{color} Sentimiento", label, f"Score: {sent_mean:.3f}")

    # Sentiment distribution
    if summary["sentiment_dist"]:
        col_chart, col_channels = st.columns([1, 1])
        with col_chart:
            st.markdown("### 📊 Distribución de Sentimiento")
            sent_df = pd.DataFrame([
                {"Etiqueta": k.title(), "Cantidad": v}
                for k, v in summary["sentiment_dist"].items()
            ])
            if not sent_df.empty:
                fig_sent = go.Figure(data=[go.Pie(
                    labels=sent_df["Etiqueta"], values=sent_df["Cantidad"],
                    hole=0.4,
                    marker_colors=[theme.PALETTE.get("verde", "#2CA58D"), theme.PALETTE.get("amarillo", "#F2C14E"), theme.PALETTE.get("rojo", "#C0392B")],
                )])
                fig_sent.update_layout(template=theme.plotly_template(), height=280, showlegend=True)
                st.plotly_chart(fig_sent, width="stretch")
        with col_channels:
            st.markdown("### 📡 Posts por Subreddit")
            if summary["posts_per_channel"]:
                for ch, count in summary["posts_per_channel"].items():
                    st.write(f"**r/{ch}**: {count} posts")
            else:
                st.info("Sin datos por subreddit")

    # Posts table with sentiment
    st.markdown("### 📋 Posts de Reddit con Sentimiento")
    posts = social_posts_with_sentiment(limit=50)
    if posts:
        df_posts = pd.DataFrame(posts)
        search_social = st.text_input("🔍 Buscar en posts", key="search_social")
        if search_social:
            mask = df_posts["title"].str.contains(search_social, case=False, na=False)
            df_posts = df_posts[mask]

        for _, p in df_posts.iterrows():
            sent_icon = "🟢" if p.get("sentiment_label") == "positive" else "🔴" if p.get("sentiment_label") == "negative" else "⚪"
            sent_val = f"{p['sentiment_score']:.3f}" if p.get("sentiment_score") is not None else "—"
            st.markdown(
                f"{sent_icon} **[{p['title']}]({p['url']})**  "
                f"| 👍 {p.get('score', 0) or 0} | 💬 {p.get('num_comments', 0) or 0} | "
                f"Sentimiento: {sent_val}"
            )
            if p.get("text"):
                with st.expander("Ver texto"):
                    st.write(p["text"][:500])
    else:
        st.info("No hay posts de Reddit disponibles. Ejecuta `collect_news` para recolectar.")

    # Sentiment detail
    sent_detail = sentiment_by_item(item_type="social", limit=50)
    if not sent_detail.empty:
        with st.expander("📊 Detalle de Sentimiento por Post"):
            st.dataframe(
                sent_detail[["item_id", "text", "score", "label"]],
                width="stretch",
                column_config={
                    "score": st.column_config.NumberColumn("Score", format="%.3f"),
                },
                hide_index=True,
            )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB: FISCAL (Gacetas OCR + Leyes)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_fiscal:
    from src.dashboard.fiscal_data import fiscal_summary
    import json

    st.subheader("🏛️ Información Fiscal")

    fs = fiscal_summary()

    # KPIs
    fc1, fc2 = st.columns(2)
    with fc1:
        st.metric("📜 Gacetas recientes (7 días)", fs["gacetas_count"])
    with fc2:
        st.metric("⚖️ Leyes / Actos AN", fs["leyes_count"])

    # Gacetas
    st.markdown("### 📜 Gacetas Oficiales Recientes")
    if fs["gacetas"]:
        for g in fs["gacetas"]:
            title = g.get("title", "Gaceta")
            url = g.get("url", "")
            date_str = str(g.get("date", ""))
            desc = g.get("description", "")
            st.markdown(f"**[{title}]({url})** — {date_str}")
            if desc:
                st.caption(desc[:200])
            st.markdown("---")
    else:
        st.info("No hay gacetas disponibles. El collector se ejecuta periódicamente.")

    # OCR section
    st.markdown("### 🔍 OCR de Gacetas Oficiales")
    st.caption("Procesamiento OCR de PDFs escaneados con clasificación automática")

    try:
        from src.collectors.fiscal.gaceta_ocr import process_gaceta_pdf, CLASIFICACION_KEYWORDS
        # Show available categories
        cats = list(CLASIFICACION_KEYWORDS.keys())
        st.write(f"**Categorías detectables**: {', '.join(cats)}")

        # Check if there are processed gacetas in data dir
        import os
        gaceta_dir = "data/gacetas"
        if os.path.exists(gaceta_dir):
            jsons = sorted([f for f in os.listdir(gaceta_dir) if f.endswith(".json")])
            if jsons:
                st.success(f"✅ {len(jsons)} gacetas procesadas con OCR")
                for jf in jsons[-5:]:  # Show last 5
                    try:
                        with open(os.path.join(gaceta_dir, jf), "r", encoding="utf-8") as f:
                            data = json.load(f)
                        categories = data.get("categories", [])
                        method = data.get("method", "unknown")
                        text_len = data.get("raw_text_length", 0)
                        st.markdown(
                            f"- **{jf.replace('.json', '')}** | "
                            f"Categorías: {', '.join(categories) if categories else 'Ninguna'} | "
                            f"Método: {method} | Texto: {text_len:,} chars"
                        )
                    except Exception:
                        pass
            else:
                st.info("No hay gacetas procesadas con OCR aún. Los PDFs se procesan automáticamente.")
        else:
            st.info("Directorio de gacetas no encontrado. Los OCRs se ejecutan con el collector.")
    except Exception as e:
        st.warning(f"Módulo OCR no disponible: {e}")

    # Leyes AN
    st.markdown("### ⚖️ Asamblea Nacional")
    if fs["leyes"]:
        for l in fs["leyes"]:
            title = getattr(l, "title", None) or (l.get("title", "") if hasattr(l, "get") else str(l))
            url = getattr(l, "url", None) or (l.get("url", "") if hasattr(l, "get") else "")
            if url:
                st.markdown(f"- [{title}]({url})")
            else:
                st.markdown(f"- {title}")
    else:
        st.info("No hay leyes/actos de la AN disponibles.")

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
        inflation_rate = (metrics["inflacion"].annual_rate or 0) if metrics.get("inflacion") else 0
        risk_result = risk.calculate(
            spread_pct=brecha if brecha else 0,
            annual_inflation=inflation_rate,
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
                f"background:rgba(0,0,0,0.05);'>"
                f"<div style='font-size:48px; font-weight:bold; color:{color};'>{score:.0f}</div>"
                f"<div style='font-size:14px; color:#666;'>/100</div>"
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
                st.metric("Inflación", f"{opt.inflation_forecast:.1f}%")
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
                brecha_val = (metrics["paralelo"].rate / metrics["oficial"].rate - 1) * 100 if metrics["oficial"] and metrics["oficial"].rate > 0 else 0
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
                parallel_rate=metrics["paralelo"].rate if metrics["paralelo"] else 0,
                official_rate=metrics["oficial"].rate if metrics["oficial"] else 0,
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
        st.dataframe(rules_df, width="stretch")

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
                            st.plotly_chart(fig_ph, width="stretch")
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
