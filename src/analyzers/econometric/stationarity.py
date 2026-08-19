"""
Módulo de Pruebas de Estacionariedad
=====================================

Pruebas estadísticas para determinar si una serie temporal es estacionaria:
- ADF (Augmented Dickey-Fuller)
- KPSS (Kwiatkowski-Phillips-Schmidt-Shin)

Importante para Venezuela: Casi todas las variables macro son I(1),
siempre aplicar estas pruebas antes de correr modelos OLS.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from statsmodels.tsa.stattools import adfuller, kpss
from statsmodels.tsa.statespace.tools import diff


@dataclass
class StationarityResult:
    """Resultado de una prueba de estacionariedad"""
    test_name: str
    statistic: float
    p_value: float
    critical_values: Dict[str, float]
    is_stationary: bool
    n_lags: int
    n_observations: int
    interpretation: str


class StationarityTester:
    """
    Clase para realizar pruebas de estacionariedad en series temporales.
    
    Utilizada para determinar el orden de integración de las series
    antes de aplicar modelos econométricos (ARIMA, VECM, etc.)
    
    Ejemplo de uso para Venezuela:
        tester = StationarityTester()
        
        # Probar tasa de cambio del dólar
        result = tester.test_dollar_rate(dollar_series)
        
        # Probar inflación
        result = tester.test_inflation(inflation_series)
    """
    
    def __init__(self, significance_level: float = 0.05):
        """
        Args:
            significance_level: Nivel de significancia para las pruebas (default 0.05)
        """
        self.significance_level = significance_level
    
    def adf_test(self, series: pd.Series, max_lags: Optional[int] = None) -> StationarityResult:
        """
        Prueba ADF (Augmented Dickey-Fuller) de raíz unitaria.
        
        H0: La serie tiene una raíz unitaria (no es estacionaria)
        H1: La serie es estacionaria
        
        Args:
            series: Serie temporal a probar
            max_lags: Número máximo de rezagos (None = automático)
            
        Returns:
            StationarityResult con los resultados de la prueba
        """
        # Eliminar NaN
        clean_series = series.dropna()
        
        # Realizar prueba ADF
        result = adfuller(clean_series, maxlag=max_lags, autolag='AIC')
        
        statistic = result[0]
        p_value = result[1]
        n_lags = result[2]
        n_observations = result[3]
        critical_values = result[4]
        
        # Determinar si es estacionaria
        is_stationary = p_value < self.significance_level
        
        # Interpretación
        if is_stationary:
            interpretation = (
                f"La serie ES estacionaria (p-value={p_value:.4f} < {self.significance_level}). "
                f"Se puede modelar directamente sin diferenciación."
            )
        else:
            interpretation = (
                f"La serie NO es estacionaria (p-value={p_value:.4f} >= {self.significance_level}). "
                f"Se requiere diferenciación otransformación."
            )
        
        return StationarityResult(
            test_name="ADF (Augmented Dickey-Fuller)",
            statistic=statistic,
            p_value=p_value,
            critical_values=critical_values,
            is_stationary=is_stationary,
            n_lags=n_lags,
            n_observations=n_observations,
            interpretation=interpretation
        )
    
    def kpss_test(self, series: pd.Series, n_lags: Optional[int] = None) -> StationarityResult:
        """
        Prueba KPSS de estacionariedad.
        
        H0: La serie es estacionaria (alrededor de una tendencia)
        H1: La serie no es estacionaria
        
        Nota: KPSS es complementaria a ADF. Si ADF dice "no estacionaria"
        y KPSS dice "estacionaria", la serie podría ser tendencialmente estacionaria.
        
        Args:
            series: Serie temporal a probar
            n_lags: Número de rezagos (None = automático)
            
        Returns:
            StationarityResult con los resultados de la prueba
        """
        # Eliminar NaN
        clean_series = series.dropna()
        
        # Realizar prueba KPSS
        # 'ct' = constante y tendencia, 'c' = solo constante
        statistic, p_value, n_lags, critical_values = kpss(
            clean_series, 
            regression='ct',  # Incluir tendencia
            nlags=n_lags
        )
        
        # Determinar si es estacionaria
        # KPSS: Si p_value > significance_level, NO rechazamos H0 (es estacionaria)
        is_stationary = p_value > self.significance_level
        
        n_observations = len(clean_series)
        
        # Interpretación
        if is_stationary:
            interpretation = (
                f"La serie ES estacionaria (p-value={p_value:.4f} > {self.significance_level}). "
                f"No se rechaza H0 de estacionariedad."
            )
        else:
            interpretation = (
                f"La serie NO es estacionaria (p-value={p_value:.4f} <= {self.significance_level}). "
                f"Se rechaza H0 de estacionariedad."
            )
        
        return StationarityResult(
            test_name="KPSS (Kwiatkowski-Phillips-Schmidt-Shin)",
            statistic=statistic,
            p_value=p_value,
            critical_values=critical_values,
            is_stationary=is_stationary,
            n_lags=n_lags,
            n_observations=n_observations,
            interpretation=interpretation
        )
    
    def determine_integration_order(
        self, 
        series: pd.Series, 
        max_order: int = 2
    ) -> Dict:
        """
        Determina el orden de integración I(d) de una serie.
        
        Ejecuta pruebas ADF y KPSS sucesivamente hasta encontrar
        la diferenciación necesaria para hacer la serie estacionaria.
        
        Args:
            series: Serie temporal
            max_order: Orden máximo de integración a probar
            
        Returns:
            Diccionario con el orden de integración y resultados detallados
        """
        results = []
        current_series = series.copy()
        
        for order in range(max_order + 1):
            adf_result = self.adf_test(current_series)
            kpss_result = self.kpss_test(current_series)
            
            results.append({
                'order': order,
                'adf': adf_result,
                'kpss': kpss_result
            })
            
            # Si ambas pruebas coinciden en que es estacionaria, parar
            if adf_result.is_stationary and kpss_result.is_stationary:
                break
            
            # Diferenciar para la siguiente iteración
            if order < max_order:
                current_series = current_series.diff().dropna()
        
        # Determinar orden final
        final_order = len(results) - 1
        
        return {
            'integration_order': final_order,
            'is_stationary_at_order': results[-1]['adf'].is_stationary and results[-1]['kpss'].is_stationary,
            'tests_by_order': results,
            'recommendation': self._generate_recommendation(final_order, results)
        }
    
    def _generate_recommendation(self, order: int, results: list) -> str:
        """Genera recomendación basada en los resultados"""
        if order == 0:
            return "La serie es I(0) - estacionaria en nivel. Modelar directamente."
        elif order == 1:
            return (
                "La serie es I(1) - requiere 1era diferenciación. "
                "Usar ARIMA(d=1) o considerar cointegración si hay múltiples series I(1)."
            )
        elif order == 2:
            return (
                "La serie es I(2) - requiere 2da diferenciación. "
                "Considerar transformación logarítmica primero."
            )
        else:
            return f"La serie es I({order}) - diferenciación múltiple requerida."
    
    def test_dollar_rate(self, series: pd.Series) -> Dict:
        """
        Prueba específica para series de tipo de cambio (oficial/paralelo).
        
        Incluye consideraciones para la dualidad cambiaria venezolana.
        """
        integration = self.determine_integration_order(series)
        
        # Análisis adicional para series de tipo de cambio
        log_returns = np.log(series).diff().dropna()
        volatilidad = log_returns.rolling(window=20).std()
        
        return {
            'integration': integration,
            'log_returns_stats': {
                'mean': log_returns.mean(),
                'std': log_returns.std(),
                'skewness': log_returns.skew(),
                'kurtosis': log_returns.kurtosis()
            },
            'current_volatility': volatilidad.iloc[-1] if len(volatilidad) > 0 else None,
            'recommendation': self._get_dollar_recommendation(integration['integration_order'])
        }
    
    def test_inflation(self, series: pd.Series) -> Dict:
        """
        Prueba específica para series de inflación.
        
        Considera estacionalidad típica de la inflación venezolana
        (picos en diciembre y agosto).
        """
        integration = self.determine_integration_order(series)
        
        # Análisis de estacionalidad
        if len(series) >= 12:
            monthly_avg = series.groupby(series.index.month).mean()
            seasonal_pattern = monthly_avg.to_dict()
        else:
            seasonal_pattern = None
        
        return {
            'integration': integration,
            'seasonal_pattern': seasonal_pattern,
            'recommendation': self._get_inflation_recommendation(
                integration['integration_order'],
                seasonal_pattern
            )
        }
    
    def _get_dollar_recommendation(self, order: int) -> str:
        """Recomendación específica para series de tipo de cambio"""
        if order == 0:
            return "Tipo de cambio estacionario. Usar modelos ARMA directamente."
        elif order == 1:
            return (
                "Tipo de cambio I(1). Considerar VECM si se analiza relación "
                "entre oficial y paralelo. Usar GARCH para volatilidad."
            )
        else:
            return "Serie requiere transformación antes de modelar."
    
    def _get_inflation_recommendation(self, order: int, seasonal: Optional[dict]) -> str:
        """Recomendación específica para series de inflación"""
        base = ""
        if order == 0:
            base = "Inflación estacionaria. Modelar con ARMA."
        elif order == 1:
            base = "Inflación I(1). Usar ARIMA."
        
        if seasonal:
            months_high = [m for m, v in seasonal.items() if v > np.mean(list(seasonal.values()))]
            if months_high:
                month_names = {1:'Ene',2:'Feb',3:'Mar',4:'Abr',5:'May',6:'Jun',
                              7:'Jul',8:'Ago',9:'Sep',10:'Oct',11:'Nov',12:'Dic'}
                high_months = [month_names.get(m, str(m)) for m in months_high]
                base += f" Considerar SARIMA con estacionalidad en: {', '.join(high_months)}."
        
        return base


def quick_stationarity_test(series: pd.Series, name: str = "Serie") -> str:
    """
    Función de conveniencia para prueba rápida de estacionariedad.
    
    Args:
        series: Serie temporal
        name: Nombre de la serie para el reporte
        
    Returns:
        Reporte formateado de la prueba
    """
    tester = StationarityTester()
    
    adf_result = tester.adf_test(series)
    kpss_result = tester.kpss_test(series)
    
    report = f"""
=== Prueba de Estacionariedad: {name} ===

ADF Test:
  - Estadístico: {adf_result.statistic:.4f}
  - p-value: {adf_result.p_value:.4f}
  - Estacionaria: {'SÍ' if adf_result.is_stationary else 'NO'}
  
KPSS Test:
  - Estadístico: {kpss_result.statistic:.4f}
  - p-value: {kpss_result.p_value:.4f}
  - Estacionaria: {'SÍ' if kpss_result.is_stationary else 'NO'}

Interpretación ADF: {adf_result.interpretation}
Interpretación KPSS: {kpss_result.interpretation}
"""
    
    return report
