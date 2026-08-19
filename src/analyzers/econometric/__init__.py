"""
Módulo de Econometría para Economía Venezuela
==============================================

Análisis econométrico avanzado para series temporales económicas:
- Pruebas de estacionariedad (ADF, KPSS)
- Pronóstico (ARIMA, SARIMA)
- Causalidad (Granger, VECM)
- Volatilidad (GARCH)
- Diagnósticos de residuos
- Regresión con errores robustos (Newey-West)

Desarrollado específicamente para las características
de la economía venezolana (alta inflación, dualidad cambiaria).
"""

from .stationarity import (
    StationarityTester,
    StationarityResult,
    quick_stationarity_test
)

from .forecasting import (
    InflationForecaster,
    DollarRateForecaster,
    ForecastResult,
    ModelComparison,
    create_forecast_report
)

from .causality import (
    GrangerCausalityTester,
    CointegrationAnalyzer,
    VECMAnalyzer,
    GrangerResult,
    CointegrationResult,
    VECMResult,
    analyze_dollar_market
)

from .volatility import (
    GARCHVolatilityAnalyzer,
    VolatilityResult,
    RiskMetrics,
    create_volatility_report
)

from .diagnostics import (
    ResidualDiagnostics,
    DiagnosticResult,
    ModelDiagnostics,
    create_diagnostics_report
)

from .regression import (
    NeweyWestRegressor,
    MultipleRegressionAnalyzer,
    RegressionResult,
    CausalityAnalysis,
    create_regression_report
)


__all__ = [
    # Stationarity
    'StationarityTester',
    'StationarityResult',
    'quick_stationarity_test',
    
    # Forecasting
    'InflationForecaster',
    'DollarRateForecaster',
    'ForecastResult',
    'ModelComparison',
    'create_forecast_report',
    
    # Causality
    'GrangerCausalityTester',
    'CointegrationAnalyzer',
    'VECMAnalyzer',
    'GrangerResult',
    'CointegrationResult',
    'VECMResult',
    'analyze_dollar_market',
    
    # Volatility
    'GARCHVolatilityAnalyzer',
    'VolatilityResult',
    'RiskMetrics',
    'create_volatility_report',
    
    # Diagnostics
    'ResidualDiagnostics',
    'DiagnosticResult',
    'ModelDiagnostics',
    'create_diagnostics_report',
    
    # Regression
    'NeweyWestRegressor',
    'MultipleRegressionAnalyzer',
    'RegressionResult',
    'CausalityAnalysis',
    'create_regression_report'
]


# Versión del módulo
__version__ = '0.1.0'
