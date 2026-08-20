"""
Tests para módulos de análisis macroeconómico:
- balance_of_payments.py
- phillips.py
- public_debt.py
- sovereign_risk.py
- svar.py
- integrated_forecast.py
"""

import numpy as np
import pandas as pd
import pytest


# ─── Balance of Payments ────────────────────────────────────────────────────

class TestBalanceOfPayments:
    """Tests para BalanceOfPaymentsAnalyzer."""

    def setup_method(self):
        from src.analyzers.balance_of_payments import BalanceOfPaymentsAnalyzer
        self.analyzer = BalanceOfPaymentsAnalyzer()

    def test_estimate_oil_revenues(self):
        result = self.analyzer.estimate_oil_revenues(production_mbd=1.0, oil_price_usd=70)
        expected = 1.0 * 70 * 365
        assert result == expected

    def test_estimate_non_oil_exports(self):
        result = self.analyzer.estimate_non_oil_exports(
            gold_exports=5e8, agricultural_exports=2e8
        )
        assert result == 7e8

    def test_current_account_surplus(self):
        ca = self.analyzer.current_account(
            oil_revenues=25e9,
            non_oil_exports=2e9,
            imports=20e9,
            services_net=-1e9,
            remittances=3e9,
        )
        assert ca.balance > 0
        assert ca.oil_revenues == 25e9
        assert ca.imports == 20e9

    def test_current_account_deficit(self):
        ca = self.analyzer.current_account(
            oil_revenues=10e9,
            non_oil_exports=1e9,
            imports=20e9,
        )
        assert ca.balance < 0

    def test_reserves_coverage(self):
        months = self.analyzer.reserves_coverage(6e9, 1e9)
        assert months == 6.0

    def test_reserves_coverage_zero_imports(self):
        months = self.analyzer.reserves_coverage(6e9, 0)
        assert months == 0

    def test_oil_cycle(self):
        result = self.analyzer.oil_cycle(
            production_mbd=1.0,
            oil_price_usd=70,
            extraction_cost_per_barrel=15,
        )
        assert result.gross_revenues > 0
        assert result.net_revenues > 0
        assert result.interpretation != ""

    def test_analyze_complete(self):
        result = self.analyzer.analyze(
            reserves=5e9,
            oil_production_mbd=1.0,
            oil_price_usd=70,
            imports_monthly=2e9,
        )
        assert result.reserves.months_coverage == 2.5
        assert result.current_account.oil_revenues > 0
        assert result.external_sustainability_score >= 0
        assert result.external_sustainability_score <= 100

    def test_reserves_breakdown(self):
        res = self.analyzer.reserves_breakdown(
            total_reserves=5e9,
            foreign_currencies=3e9,
            gold_usd=1.5e9,
            monthly_imports=1e9,
            annual_debt_service=12e9,
        )
        assert res.total_usd == 5e9
        assert res.months_coverage == 5.0
        assert res.months_debt_service == 5.0


# ─── Phillips Curve ─────────────────────────────────────────────────────────

class TestPhillipsCurve:
    """Tests para PhillipsCurveAnalyzer."""

    def setup_method(self):
        from src.analyzers.phillips import PhillipsCurveAnalyzer
        self.analyzer = PhillipsCurveAnalyzer()

    def test_fit_basic(self):
        np.random.seed(42)
        n = 50
        unemployment = pd.Series(np.random.uniform(10, 25, n))
        inflation = pd.Series(50 - 1.5 * unemployment + np.random.normal(0, 5, n))

        result = self.analyzer.fit_basic(inflation, unemployment)
        assert result is not None
        assert result.slope < 0  # Trade-off negativo
        assert result.r_squared > 0
        assert result.model_type == "basic"

    def test_fit_basic_insufficient_data(self):
        inflation = pd.Series([10, 20, 30])
        unemployment = pd.Series([15, 16, 17])
        result = self.analyzer.fit_basic(inflation, unemployment)
        assert result is None

    def test_fit_with_expectations(self):
        np.random.seed(42)
        n = 50
        unemployment = pd.Series(np.random.uniform(10, 25, n))
        inflation = pd.Series(np.random.uniform(5, 20, n))

        result = self.analyzer.fit_with_expectations(inflation, unemployment)
        assert result is not None
        assert result.model_type == "expectations"
        assert "inercia" in result.interpretation.lower()

    def test_fit_hybrid(self):
        np.random.seed(42)
        n = 50
        unemployment = pd.Series(np.random.uniform(10, 25, n))
        inflation = pd.Series(np.random.uniform(5, 20, n))
        oil_change = pd.Series(np.random.normal(0, 5, n))
        exch_change = pd.Series(np.random.normal(0, 10, n))

        result = self.analyzer.fit_hybrid(inflation, unemployment, oil_change, exch_change)
        assert result is not None
        assert result.r_squared >= 0

    def test_fit_nonlinear(self):
        np.random.seed(42)
        n = 50
        unemployment = pd.Series(np.random.uniform(10, 25, n))
        inflation = pd.Series(50 - 1.5 * unemployment + np.random.normal(0, 5, n))

        result = self.analyzer.fit_nonlinear(inflation, unemployment)
        assert result is not None
        assert result.model_type == "nonlinear"

    def test_detect_stagflation(self):
        # Crear datos con estanflación
        inflation = pd.Series([5] * 20 + [30] * 10)
        unemployment = pd.Series([10] * 20 + [15] * 10)

        result = self.analyzer.detect_stagflation(
            inflation, unemployment,
            inflation_threshold=20, unemployment_threshold=12
        )
        assert result["stagflation_episodes"] > 0
        assert result["current"] is True

    def test_detect_no_stagflation(self):
        inflation = pd.Series([5] * 30)
        unemployment = pd.Series([10] * 30)
        result = self.analyzer.detect_stagflation(
            inflation, unemployment,
            inflation_threshold=20, unemployment_threshold=12
        )
        assert result["stagflation_episodes"] == 0
        assert result["current"] is False


# ─── Public Debt ────────────────────────────────────────────────────────────

class TestPublicDebt:
    """Tests para PublicDebtAnalyzer."""

    def setup_method(self):
        from src.analyzers.public_debt import PublicDebtAnalyzer
        self.analyzer = PublicDebtAnalyzer()

    def test_analyze_structure(self):
        result = self.analyzer.analyze_structure(
            total_debt_usd=240e9,
            external_debt_usd=180e9,
        )
        assert result.total_usd == 240e9
        assert result.external_usd == 180e9
        assert result.internal_usd == 60e9
        assert result.external_ratio == 75.0

    def test_analyze_maturities(self):
        result = self.analyzer.analyze_maturities(
            short_term=60e9,
            medium_term=100e9,
            long_term=80e9,
        )
        assert result.short_term == 60e9
        assert result.rollover_risk in ("bajo", "medio", "alto", "crítico")

    def test_stress_test(self):
        scenarios = self.analyzer.stress_test(
            current_debt=240e9,
            gdp_usd=94e9,
            scenarios=[
                {"name": "Base", "gdp_growth": 3, "interest_rate": 0.05, "deficit_pct": 5, "years": 5},
            ],
        )
        assert len(scenarios) == 1
        assert scenarios[0].name == "Base"
        assert scenarios[0].projected_debt_gdp > 0

    def test_stress_test_multiple(self):
        scenarios = self.analyzer.stress_test(
            current_debt=240e9,
            gdp_usd=94e9,
            scenarios=[
                {"name": "Optimista", "gdp_growth": 8, "interest_rate": 0.03, "deficit_pct": 2, "years": 3},
                {"name": "Pesimista", "gdp_growth": -2, "interest_rate": 0.08, "deficit_pct": 10, "years": 3},
            ],
        )
        assert len(scenarios) == 2
        # Optimista debería tener mejor deuda/PIB que pesimista
        assert scenarios[0].projected_debt_gdp < scenarios[1].projected_debt_gdp

    def test_project_debt(self):
        projections = self.analyzer.project_debt(
            current_debt=100e9,
            annual_deficit=5e9,
            interest_rate=0.05,
            years=3,
        )
        assert len(projections) == 3
        assert projections[0]["debt"] > 100e9
        assert projections[2]["debt"] > projections[0]["debt"]

    def test_analyze_contingent(self):
        result = self.analyzer.analyze_contingent_liabilities(
            pdvsa_debt=40e9,
            state_enterprise_debt=10e9,
        )
        assert result.total == 50e9
        assert result.pdvsa_debt == 40e9

    def test_analyze_complete(self):
        result = self.analyzer.analyze(
            total_debt_usd=240e9,
            gdp_usd=94e9,
            external_debt_usd=180e9,
            fiscal_deficit_pct=5.8,
            oil_revenues_usd=35e9,
            oil_price=70,
            pdvsa_debt=40e9,
        )
        assert result.debt_gdp_ratio is not None
        assert result.debt_gdp_ratio > 200
        assert result.sustainability in ("sostenible", "en_riesgo", "insostenible")
        assert len(result.stress_scenarios) > 0


# ─── Sovereign Risk ─────────────────────────────────────────────────────────

class TestSovereignRisk:
    """Tests para SovereignRiskIndex."""

    def setup_method(self):
        from src.analyzers.sovereign_risk import SovereignRiskIndex
        self.index = SovereignRiskIndex()

    def test_calculate_low_risk(self):
        result = self.index.calculate(
            spread_pct=5,
            annual_inflation=5,
            reserves_months=12,
            debt_gdp_pct=30,
            oil_production_mbd=2.0,
        )
        assert result.score < 30
        assert result.level == "bajo"

    def test_calculate_high_risk(self):
        result = self.index.calculate(
            spread_pct=80,
            annual_inflation=500,
            reserves_months=1,
            debt_gdp_pct=400,
            oil_production_mbd=0.5,
        )
        assert result.score > 50
        assert result.level in ("medio", "alto", "extremo")

    def test_score_components(self):
        result = self.index.calculate(
            spread_pct=30,
            annual_inflation=150,
            reserves_months=2.5,
            debt_gdp_pct=253,
            oil_production_mbd=1.0,
        )
        assert "inflation" in result.components
        assert "spread" in result.components
        assert "reserves" in result.components
        assert all(0 <= v <= 100 for v in result.components.values())

    def test_political_risk(self):
        result = self.index.calculate(
            sanctions_level=80,
            social_unrest=60,
            governance_score=20,
        )
        assert result.components["political"] > 50

    def test_uncertainty_index(self):
        result = self.index.calculate(
            sentiment_volatility=0.8,
            survey_dispersion=70,
            forecast_error=25,
        )
        assert result.components["uncertainty"] > 30

    def test_momentum_tracking(self):
        r1 = self.index.calculate(spread_pct=30, annual_inflation=100)
        r2 = self.index.calculate(spread_pct=50, annual_inflation=200)
        assert r2.momentum is not None
        assert r2.momentum > 0  # Riesgo aumentó

    def test_dominant_factor(self):
        result = self.index.calculate(
            spread_pct=90,
            annual_inflation=5,
            reserves_months=12,
            debt_gdp_pct=30,
            oil_production_mbd=2.0,
        )
        assert result.dominant_factor == "spread"

    def test_update_weights_pca(self):
        # Datos insuficientes -> retorna weights por defecto
        weights = self.index.update_weights_pca([{"spread": 50}])
        assert "spread" in weights

    def test_inflation_saturation(self):
        # Hiperinflación extrema
        r_extreme = self.index.calculate(annual_inflation=100000)
        assert r_extreme.components["inflation"] <= 100


# ─── SVAR ───────────────────────────────────────────────────────────────────

class TestSVAR:
    """Tests para SVARAnalyzer."""

    def setup_method(self):
        from src.analyzers.svar import SVARAnalyzer
        self.analyzer = SVARAnalyzer(max_lags=2)

    def test_fit_basic(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
            "oil_price": np.random.normal(70, 10, n),
        })
        result = self.analyzer.fit(data)
        assert "error" not in result
        assert self.analyzer.fitted is True

    def test_impulse_response(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
        })
        self.analyzer.fit(data)
        irf = self.analyzer.impulse_response("exchange_rate", "inflation", periods=5)
        assert irf is not None
        assert len(irf) == 6  # periods + 1

    def test_fevd(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
        })
        self.analyzer.fit(data)
        fevd = self.analyzer.forecast_error_variance_decomposition("inflation", periods=5)
        assert fevd is not None
        assert "inflation" in fevd
        assert abs(sum(fevd.values()) - 100) < 1  # Debe sumar ~100%

    def test_analyze_shock(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
        })
        self.analyzer.fit(data)
        result = self.analyzer.analyze_shock(
            "exchange_rate", "inflation", periods=5, use_bootstrap=False
        )
        assert result is not None
        assert result.variable == "inflation"
        assert result.shock_source == "exchange_rate"
        assert len(result.impulse_responses) == 6

    def test_robustness_check(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
        })
        self.analyzer.fit(data)
        result = self.analyzer.robustness_check("exchange_rate", "inflation", periods=5)
        assert result is not None
        assert len(result.orderings) >= 1
        assert len(result.irf_mean) == 6

    def test_summary(self):
        np.random.seed(42)
        n = 100
        data = pd.DataFrame({
            "inflation": np.random.normal(10, 3, n),
            "exchange_rate": np.random.normal(500, 50, n),
        })
        self.analyzer.fit(data)
        summary = self.analyzer.summary()
        assert summary is not None
        assert "variables" in summary
        assert "aic" in summary

    def test_fit_insufficient_data(self):
        data = pd.DataFrame({"x": [1, 2, 3]})
        result = self.analyzer.fit(data)
        assert "error" in result


# ─── Integrated Forecast ────────────────────────────────────────────────────

class TestIntegratedForecast:
    """Tests para IntegratedForecaster."""

    def setup_method(self):
        from src.analyzers.integrated_forecast import IntegratedForecaster
        self.forecaster = IntegratedForecaster()

    def test_build_scenario(self):
        scenario = self.forecaster.build_scenario(
            name="Test",
            oil_price=70,
            gdp_growth=3,
            current_inflation=10,
            exchange_spread=30,
            current_exchange_rate=500,
        )
        assert scenario.name == "Test"
        assert scenario.inflation_forecast > 0
        assert scenario.exchange_rate_forecast > 0
        assert "inflation" in scenario.confidence_lower
        assert "exchange_rate" in scenario.confidence_upper

    def test_scenario_analysis(self):
        result = self.forecaster.scenario_analysis(
            macro_data=pd.DataFrame(),
            base_oil=70,
            base_inflation=10,
            base_gdp=3,
            base_spread=30,
            base_exchange=500,
        )
        assert result.central_scenario.inflation_forecast > 0
        assert result.optimistic_scenario.inflation_forecast < result.pessimistic_scenario.inflation_forecast
        assert len(result.sensitivity) > 0
        assert result.interpretation != ""

    def test_what_if(self):
        base_data = pd.DataFrame({
            "inflation": [10, 12, 15, 18, 20],
            "oil_price": [60, 65, 70, 68, 72],
        })
        result = self.forecaster.what_if(
            base_data,
            scenario_changes={"oil_price": 0.20},
            target_variable="inflation",
        )
        assert "base" in result
        assert "scenario" in result
        assert "impact" in result
        assert result["interpretation"] != ""
