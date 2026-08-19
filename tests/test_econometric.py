"""
Tests para Módulos Econométricos
================================

Tests unitarios y de integración para:
- Stationarity (ADF, KPSS)
- Forecasting (ARIMA, SARIMA)
- Causality (Granger, VECM)
- Volatility (GARCH)
- Diagnostics
- Regression (Newey-West)
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importar módulos a testear
from src.analyzers.econometric.stationarity import (
    StationarityTester,
    quick_stationarity_test
)
from src.analyzers.econometric.forecasting import (
    InflationForecaster,
    DollarRateForecaster,
    create_forecast_report
)
from src.analyzers.econometric.causality import (
    GrangerCausalityTester,
    CointegrationAnalyzer,
    VECMAnalyzer,
    analyze_dollar_market
)
from src.analyzers.econometric.volatility import (
    GARCHVolatilityAnalyzer,
    create_volatility_report
)
from src.analyzers.econometric.diagnostics import (
    ResidualDiagnostics,
    create_diagnostics_report
)
from src.analyzers.econometric.regression import (
    NeweyWestRegressor,
    create_regression_report
)


# ============================================
# Fixtures (Datos de prueba)
# ============================================

@pytest.fixture
def inflation_series():
    """Serie sintética de inflación mensual"""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=60, freq='MS')
    # Inflación con tendencia y ruido
    trend = np.linspace(5, 15, 60)  # Tendencia creciente
    seasonal = 2 * np.sin(np.arange(60) * 2 * np.pi / 12)  # Estacionalidad
    noise = np.random.normal(0, 1, 60)
    inflation = trend + seasonal + noise
    return pd.Series(inflation, index=dates, name='inflation')


@pytest.fixture
def dollar_official():
    """Serie sintética de dólar oficial"""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=1000, freq='D')
    # Random walk
    returns = np.random.normal(0.0001, 0.01, 1000)
    price = 10 * np.exp(np.cumsum(returns))
    return pd.Series(price, index=dates, name='official')


@pytest.fixture
def dollar_parallel():
    """Serie sintética de dólar paralelo (correlacionado con oficial)"""
    np.random.seed(43)
    dates = pd.date_range(start='2020-01-01', periods=1000, freq='D')
    # Similar al oficial pero con más volatilidad
    returns = np.random.normal(0.0002, 0.015, 1000)
    price = 15 * np.exp(np.cumsum(returns))
    return pd.Series(price, index=dates, name='parallel')


@pytest.fixture
def returns_series():
    """Serie sintética de retornos logarítmicos"""
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=500, freq='D')
    # Retornos con clustering de volatilidad
    vol = np.ones(500)
    for i in range(1, 500):
        vol[i] = 0.1 + 0.8 * abs(np.random.normal(0, vol[i-1]))
    returns = np.random.normal(0, vol)
    return pd.Series(returns, index=dates, name='returns')


@pytest.fixture
def regression_data():
    """Datos para regresión"""
    np.random.seed(42)
    n = 100
    X1 = np.random.normal(0, 1, n)
    X2 = np.random.normal(0, 1, n)
    y = 2 + 1.5 * X1 + 0.8 * X2 + np.random.normal(0, 0.5, n)
    
    dates = pd.date_range(start='2020-01-01', periods=n, freq='MS')
    
    return {
        'y': pd.Series(y, index=dates, name='y'),
        'X': pd.DataFrame({'X1': X1, 'X2': X2}, index=dates)
    }


# ============================================
# Tests de Stationarity
# ============================================

class TestStationarityTester:
    """Tests para la clase StationarityTester"""
    
    def test_adf_test_stationary(self):
        """Test ADF en serie estacionaria"""
        np.random.seed(42)
        stationary = pd.Series(np.random.normal(0, 1, 100))
        
        tester = StationarityTester()
        result = tester.adf_test(stationary)
        
        assert result.test_name == "ADF (Augmented Dickey-Fuller)"
        assert result.p_value < 0.05  # Debería ser estacionaria
        assert result.is_stationary
    
    def test_adf_test_non_stationary(self):
        """Test ADF en serie no estacionaria (random walk)"""
        np.random.seed(42)
        random_walk = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
        
        tester = StationarityTester()
        result = tester.adf_test(random_walk)
        
        # Random walk debería no ser estacionaria
        assert result.p_value > 0.05
        assert not result.is_stationary
    
    def test_kpss_test(self):
        """Test KPSS en serie estacionaria"""
        np.random.seed(42)
        stationary = pd.Series(np.random.normal(0, 1, 100))
        
        tester = StationarityTester()
        result = tester.kpss_test(stationary)
        
        assert result.test_name == "KPSS (Kwiatkowski-Phillips-Schmidt-Shin)"
        assert result.p_value > 0.05  # KPSS: no rechazar H0 = estacionaria
        assert result.is_stationary
    
    def test_determine_integration_order(self):
        """Test determinación de orden de integración"""
        np.random.seed(42)
        # Serie I(1) - random walk
        series = pd.Series(np.cumsum(np.random.normal(0, 1, 200)))
        
        tester = StationarityTester()
        result = tester.determine_integration_order(series)
        
        # Debería determinar que es I(1)
        assert result['integration_order'] >= 1
    
    def test_quick_stationarity_test(self):
        """Test función de conveniencia"""
        np.random.seed(42)
        series = pd.Series(np.random.normal(0, 1, 100))
        
        report = quick_stationarity_test(series, "Test Series")
        
        assert "Test Series" in report
        assert "ADF Test" in report
        assert "KPSS Test" in report


# ============================================
# Tests de Forecasting
# ============================================

class TestInflationForecaster:
    """Tests para la clase InflationForecaster"""
    
    def test_forecast_inflation(self, inflation_series):
        """Test pronóstico de inflación"""
        forecaster = InflationForecaster()
        
        result = forecaster.forecast_inflation(inflation_series, periods=6)
        
        assert result.model_name == "SARIMA"
        assert len(result.predicted_mean) == 6
        assert result.aic is not None
        assert result.bic is not None
    
    def test_auto_arima_selection(self, inflation_series):
        """Test selección automática de ARIMA"""
        forecaster = InflationForecaster()
        
        result = forecaster.auto_arima_selection(
            inflation_series,
            max_p=2,
            max_d=1,
            max_q=2,
            seasonal=False  # Para speed
        )
        
        assert len(result.models) > 0
        assert result.best_aic is not None


class TestDollarRateForecaster:
    """Tests para la clase DollarRateForecaster"""
    
    def test_forecast_dollar_rate(self, dollar_official):
        """Test pronóstico de tipo de cambio"""
        forecaster = DollarRateForecaster()
        
        result = forecaster.forecast_dollar_rate(dollar_official, periods=30)
        
        assert result.model_name == "ARIMA"
        assert len(result.predicted_mean) == 30


# ============================================
# Tests de Causality
# ============================================

class TestGrangerCausality:
    """Tests para la clase GrangerCausalityTester"""
    
    def test_granger_causality(self, dollar_official, dollar_parallel):
        """Test causalidad de Granger"""
        tester = GrangerCausalityTester()
        
        result = tester.test_granger_causality(
            dollar_parallel,
            dollar_official,
            cause_name="Paralelo",
            effect_name="Oficial"
        )
        
        assert result.cause == "Paralelo"
        assert result.effect == "Oficial"
        assert result.p_value >= 0
    
    def test_bidirectional_test(self, dollar_official, dollar_parallel):
        """Test causalidad bidireccional"""
        tester = GrangerCausalityTester()
        
        result = tester.bidirectional_test(
            dollar_official,
            dollar_parallel,
            "Oficial",
            "Paralelo"
        )
        
        assert 'a_to_b' in result
        assert 'b_to_a' in result
        assert 'relationship_type' in result


class TestCointegration:
    """Tests para la clase CointegrationAnalyzer"""
    
    def test_engle_granger(self, dollar_official, dollar_parallel):
        """Test cointegración de Engle-Granger"""
        analyzer = CointegrationAnalyzer()
        
        result = analyzer.test_engle_granger(
            dollar_official,
            dollar_parallel,
            "Oficial",
            "Paralelo"
        )
        
        assert result.test_type == "Engle-Granger"
        assert result.p_value >= 0
    
    def test_johansen(self, dollar_official, dollar_parallel):
        """Test cointegración de Johansen"""
        analyzer = CointegrationAnalyzer()
        
        data = pd.concat([dollar_official, dollar_parallel], axis=1).dropna()
        data.columns = ['Oficial', 'Paralelo']
        
        result = analyzer.test_johansen(data, det_order=0, k_ar_diff=2)
        
        assert 'trace_statistic' in result
        assert 'n_vectors_trace' in result


# ============================================
# Tests de Volatility
# ============================================

class TestGARCHVolatility:
    """Tests para la clase GARCHVolatilityAnalyzer"""
    
    def test_fit_garch(self, returns_series):
        """Test ajuste de modelo GARCH"""
        analyzer = GARCHVolatilityAnalyzer()
        
        result = analyzer.fit_garch(returns_series, p=1, q=1)
        
        assert result.model_name == "GARCH(1,1)"
        assert result.last_volatility > 0
        assert result.p_value_arch_test >= 0
    
    def test_analyze_dollar_volatility(self, dollar_parallel):
        """Test análisis de volatilidad del dólar"""
        analyzer = GARCHVolatilityAnalyzer()
        
        # Calcular retornos
        returns = np.log(dollar_parallel).diff().dropna() * 100
        
        result = analyzer.analyze_dollar_volatility(dollar_parallel)
        
        assert 'garch' in result
        assert 'risk_metrics' in result
        assert 'nervousness_index' in result
    
    def test_nervousness_index(self, returns_series):
        """Test índice de nerviosismo monetario"""
        analyzer = GARCHVolatilityAnalyzer()
        
        garch_result = analyzer.fit_garch(returns_series)
        nervousness = analyzer._calculate_nervousness_index(garch_result)
        
        assert 'index' in nervousness
        assert 'level' in nervousness
        assert 0 <= nervousness['index'] <= 100


# ============================================
# Tests de Diagnostics
# ============================================

class TestResidualDiagnostics:
    """Tests para la clase ResidualDiagnostics"""
    
    def test_normality(self):
        """Test normalidad de residuos"""
        np.random.seed(42)
        residuals = pd.Series(np.random.normal(0, 1, 200))
        
        diagnostics = ResidualDiagnostics()
        result = diagnostics.test_normality(residuals)
        
        assert result.test_name == "Jarque-Bera"
        assert result.is_valid  # Debería ser normal
    
    def test_autocorrelation(self):
        """Test autocorrelación"""
        np.random.seed(42)
        residuals = pd.Series(np.random.normal(0, 1, 200))
        
        diagnostics = ResidualDiagnostics()
        result = diagnostics.test_autocorrelation(residuals)
        
        assert result.test_name in ["Durbin-Watson", "Ljung-Box"]
    
    def test_full_diagnostics(self):
        """Test diagnósticos completos"""
        np.random.seed(42)
        residuals = pd.Series(np.random.normal(0, 1, 200))
        
        diagnostics = ResidualDiagnostics()
        result = diagnostics.full_diagnostics(residuals, model_name="Test Model")
        
        assert result.normality is not None
        assert result.autocorrelation is not None
        assert result.heteroscedasticity is not None
        assert result.model_quality in ["EXCELENTE", "BUENA", "ACEPTABLE", "POBRE"]


# ============================================
# Tests de Regression
# ============================================

class TestNeweyWestRegressor:
    """Tests para la clase NeweyWestRegressor"""
    
    def test_newey_west_ols(self, regression_data):
        """Test regresión Newey-West"""
        regressor = NeweyWestRegressor()
        
        result = regressor.newey_west_ols(
            regression_data['y'],
            regression_data['X']
        )
        
        assert result.model_name == "Newey-West OLS"
        assert result.r_squared > 0
        assert 'X1' in result.coefficients
        assert 'X2' in result.coefficients
    
    def test_regression_inflation_m2(self, inflation_series):
        """Test regresión inflación-M2"""
        np.random.seed(42)
        m2 = pd.Series(
            np.random.normal(100, 10, len(inflation_series)),
            index=inflation_series.index
        )
        
        regressor = NeweyWestRegressor()
        result = regressor.regress_inflation_m2(inflation_series, m2)
        
        assert 'regression' in result
        assert 'interpretation' in result


# ============================================
# Tests de Reportes
# ============================================

class TestReports:
    """Tests para generación de reportes"""
    
    def test_create_diagnostics_report(self):
        """Test creación de reporte de diagnósticos"""
        np.random.seed(42)
        residuals = pd.Series(np.random.normal(0, 1, 200))
        
        diagnostics = ResidualDiagnostics()
        result = diagnostics.full_diagnostics(residuals, model_name="Test")
        
        report = create_diagnostics_report(result, "Test Model")
        
        assert "Test Model" in report
        assert "Normalidad" in report or "normalidad" in report.lower()


# ============================================
# Tests de Integración
# ============================================

class TestIntegration:
    """Tests de integración completos"""
    
    def test_full_analysis_pipeline(self, dollar_official, dollar_parallel):
        """Test pipeline completo de análisis"""
        # 1. Estacionariedad
        tester = StationarityTester()
        adf_result = tester.adf_test(dollar_official)
        assert adf_result is not None
        
        # 2. Causalidad
        granger = GrangerCausalityTester()
        granger_result = granger.bidirectional_test(
            dollar_parallel, dollar_official
        )
        assert granger_result is not None
        
        # 3. Cointegración
        coint = CointegrationAnalyzer()
        coint_result = coint.test_engle_granger(
            dollar_official, dollar_parallel
        )
        assert coint_result is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
