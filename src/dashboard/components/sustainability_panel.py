"""
Panel de Control de Sostenibilidad
====================================

Unifica public_debt, balance_of_payments y sovereign_risk en un
dashboard de vulnerabilidad externa.

Mide:
- Capacidad de pago: reservas / deuda de corto plazo
- Proyección del déficit fiscal y su efecto sobre la deuda
- Riesgo soberano en tiempo real
- Balanza de pagos y cobertura de reservas
"""

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def render_sustainability_panel():
    """Renderiza el panel de sostenibilidad en el dashboard."""
    st.subheader("🏛️ Panel de Sostenibilidad")

    # Inputs del usuario
    col1, col2, col3 = st.columns(3)
    with col1:
        total_debt = st.number_input(
            "Deuda Total (USD B)",
            min_value=0.0,
            value=150.0,
            step=10.0,
            key="sust_debt",
        ) * 1e9
        gdp = st.number_input(
            "PIB (USD B)",
            min_value=0.0,
            value=95.0,
            step=5.0,
            key="sust_gdp",
        ) * 1e9
    with col2:
        reserves = st.number_input(
            "Reservas (USD M)",
            min_value=0.0,
            value=5000.0,
            step=100.0,
            key="sust_reserves",
        ) * 1e6
        oil_price = st.number_input(
            "Precio Petróleo (USD)",
            min_value=0.0,
            value=65.0,
            step=5.0,
            key="sust_oil",
        )
    with col3:
        deficit_pct = st.number_input(
            "Déficit Fiscal (% PIB)",
            min_value=-20.0,
            value=5.0,
            step=0.5,
            key="sust_deficit",
        )
        oil_production = st.number_input(
            "Producción (mbd)",
            min_value=0.0,
            value=1.0,
            step=0.1,
            key="sust_prod",
        )

    if st.button("🔄 Calcular Sostenibilidad", key="btn_sust"):
        _calculate_and_display(
            total_debt, gdp, reserves, oil_price, deficit_pct, oil_production
        )


def _calculate_and_display(
    total_debt, gdp, reserves, oil_price, deficit_pct, oil_production
):
    """Calcula y muestra los resultados de sostenibilidad."""
    from src.analyzers.balance_of_payments import BalanceOfPaymentsAnalyzer
    from src.analyzers.public_debt import PublicDebtAnalyzer
    from src.analyzers.sovereign_risk import SovereignRiskIndex

    # 1. Balanza de Pagos
    bop = BalanceOfPaymentsAnalyzer()
    bop_result = bop.analyze(
        reserves=reserves,
        oil_production_mbd=oil_production,
        oil_price_usd=oil_price,
        imports_monthly=reserves / 6 if reserves > 0 else 1e9,  # Estimación
    )

    # 2. Deuda Pública
    debt_analyzer = PublicDebtAnalyzer()
    debt_result = debt_analyzer.analyze(
        total_debt_usd=total_debt,
        gdp_usd=gdp,
        external_debt_usd=total_debt * 0.7,  # Estimación: 70% externa
        fiscal_deficit_pct=deficit_pct,
        oil_revenues_usd=oil_production * oil_price * 365,
        oil_price=oil_price,
    )

    # 3. Riesgo Soberano
    sovereign = SovereignRiskIndex()
    spread = 30.0  # Estimación de brecha cambiaria
    risk_result = sovereign.calculate(
        spread_pct=spread,
        annual_inflation=150.0,  # Estimación
        reserves_months=bop_result.reserves.months_coverage,
        debt_gdp_pct=debt_result.debt_gdp_ratio or 0,
        oil_production_mbd=oil_production,
    )

    # --- Dashboard ---
    st.markdown("---")

    # Score principal
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        _render_risk_gauge("Riesgo Soberano", risk_result.score, risk_result.level)

    with col_b:
        debt_gdp = debt_result.debt_gdp_ratio or 0
        color = "🔴" if debt_gdp > 300 else "🟡" if debt_gdp > 100 else "🟢"
        st.metric("Deuda/PIB", f"{debt_gdp:.0f}%", delta=f"{debt_result.sustainability}")
        st.caption(f"{color} {debt_result.sustainability.upper()}")

    with col_c:
        months = bop_result.reserves.months_coverage
        color = "🔴" if months < 3 else "🟡" if months < 6 else "🟢"
        st.metric("Reservas", f"{months:.1f} meses", delta=f"Cobertura importaciones")
        st.caption(f"{color} {'CRÍTICO' if months < 3 else 'INSUFICIENTE' if months < 6 else 'ACEPTABLE'}")

    # Desglose de deuda
    st.markdown("#### 💰 Estructura de Deuda")
    col_d, col_e = st.columns(2)

    with col_d:
        st.metric("Deuda Externa", f"${debt_result.structure.external_usd/1e9:.1f}B")
        st.metric("Deuda Interna", f"${debt_result.structure.internal_usd/1e9:.1f}B")

    with col_e:
        st.metric("Tasa Ponderada", f"{debt_result.structure.weighted_interest_rate:.1f}%")
        st.metric("Riesgo Rollover", f"{debt_result.maturity.rollover_risk.upper()}")

    # Escenarios de estrés
    if debt_result.stress_scenarios:
        st.markdown("#### 🔥 Escenarios de Estrés")
        for sc in debt_result.stress_scenarios:
            color = "🔴" if sc.sustainability == "insostenible" else "🟡" if sc.sustainability == "en_riesgo" else "🟢"
            st.info(
                f"{color} **{sc.name}**: Deuda/PIB proyectada = {sc.projected_debt_gdp:.0f}% "
                f"({sc.sustainability.upper()})\n\n"
                f"_{sc.interpretation}_"
            )

    # Ciclo petrolero
    if bop_result.oil_cycle.interpretation:
        st.markdown("#### 🛢️ Ciclo Petrolero")
        col_f, col_g, col_h = st.columns(3)
        with col_f:
            st.metric("Ingresos Brutos", f"${bop_result.oil_cycle.gross_revenues/1e9:.1f}B")
        with col_g:
            st.metric("Ingresos Netos", f"${bop_result.oil_cycle.net_revenues/1e9:.1f}B")
        with col_h:
            st.metric("Flujo Efectivo", f"${bop_result.oil_cycle.effective_cash_flow/1e9:.1f}B")
        st.caption(bop_result.oil_cycle.interpretation)

    # Interpretación general
    st.markdown("#### 📋 Resumen")
    st.info(risk_result.interpretation)
    st.info(debt_result.interpretation)

    # Factor dominante
    if risk_result.dominant_factor:
        risk_labels = {
            "spread": "brecha cambiaria",
            "volatility": "volatilidad cambiaria",
            "inflation": "inflación",
            "reserves": "bajas reservas",
            "debt": "deuda elevada",
            "oil": "baja producción petrolera",
            "political": "riesgo político",
            "uncertainty": "incertidumbre macroeconómica",
        }
        st.warning(
            f"⚠️ **Factor dominante de riesgo**: {risk_labels.get(risk_result.dominant_factor, risk_result.dominant_factor)}"
        )


def _render_risk_gauge(title: str, score: float, level: str):
    """Renderiza un gauge de riesgo."""
    if score < 25:
        color = "🟢"
        bar_color = "green"
    elif score < 50:
        color = "🟡"
        bar_color = "orange"
    elif score < 75:
        color = "🟠"
        bar_color = "darkorange"
    else:
        color = "🔴"
        bar_color = "red"

    st.metric(f"{color} {title}", f"{score:.0f}/100", delta=f"{level.upper()}")
    st.progress(score / 100)
