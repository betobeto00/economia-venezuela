"""
Módulo de Pronóstico con Modelos ARIMA/SARIMA
==============================================

Modelos de series temporales para pronóstico de:
- Inflación mensual (SARIMA)
- Tipo de cambio (ARIMA)
- Producción petrolera (ARIMA/SARIMA)

La inflación en Venezuela tiene un fuerte componente estacional
(diciembre, agosto), por lo que SARIMA es especialmente útil.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass, field
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from itertools import product
import warnings

warnings.filterwarnings('ignore')


@dataclass
class ForecastResult:
    """Resultado de un pronóstico"""
    model_name: str
    predicted_mean: pd.Series
    conf_int: pd.DataFrame
    aic: float
    bic: float
    order: Tuple[int, int, int]
    seasonal_order: Optional[Tuple[int, int, int, int]] = None
    residuals: Optional[pd.Series] = None
    diagnostics: Optional[Dict] = None


@dataclass
class ModelComparison:
    """Comparación de múltiples modelos"""
    models: List[ForecastResult]
    best_aic: ForecastResult
    best_bic: ForecastResult
    summary: pd.DataFrame


class InflationForecaster:
    """
    Pronosticador de inflación para Venezuela.
    
    Utiliza modelos SARIMA considerando la estacionalidad
    típica de la inflación venezolana (picos en diciembre y agosto).
    
    Ejemplo de uso:
        forecaster = InflationForecaster()
        result = forecaster.forecast_inflation(inflation_series, periods=6)
    """
    
    def __init__(self, frequency: str = 'MS'):
        """
        Args:
            frequency: Frecuencia de los datos ('MS' mensual, 'W' semanal)
        """
        self.frequency = frequency
        self.default_order = (1, 1, 1)
        self.default_seasonal_order = (1, 1, 1, 12)
    
    def forecast_inflation(
        self,
        data_series: pd.Series,
        periods: int = 6,
        order: Optional[Tuple[int, int, int]] = None,
        seasonal_order: Optional[Tuple[int, int, int, int]] = None
    ) -> ForecastResult:
        """
        Genera pronóstico de inflación usando SARIMA.
        
        Args:
            data_series: Serie temporal de inflación (variación del IPC)
            periods: Número de períodos a pronosticar
            order: Orden ARIMA (p, d, q)
            seasonal_order: Orden estacional (P, D, Q, s)
            
        Returns:
            ForecastResult con predicciones e intervalos de confianza
        """
        if order is None:
            order = self.default_order
        if seasonal_order is None:
            seasonal_order = self.default_seasonal_order
        
        # Limpiar datos
        clean_data = data_series.dropna()
        
        # Ajustar modelo SARIMA
        model = SARIMAX(
            clean_data,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        
        results = model.fit(disp=False)
        
        # Generar pronóstico
        forecast = results.get_forecast(steps=periods)
        predicted_mean = forecast.predicted_mean
        conf_int = forecast.conf_int()
        
        # Calcular métricas de diagnóstico
        diagnostics = self._calculate_diagnostics(results)
        
        return ForecastResult(
            model_name="SARIMA",
            predicted_mean=predicted_mean,
            conf_int=conf_int,
            aic=results.aic,
            bic=results.bic,
            order=order,
            seasonal_order=seasonal_order,
            residuals(results.resid),
            diagnostics=diagnostics
        )
    
    def auto_arima_selection(
        self,
        data_series: pd.Series,
        max_p: int = 3,
        max_d: int = 2,
        max_q: int = 3,
        seasonal: bool = True,
        period: int = 12
    ) -> ModelComparison:
        """
        Selección automática del mejor modelo ARIMA/SARIMA.
        
        Prueba múltiples combinaciones de parámetros y selecciona
        el mejor según AIC y BIC.
        
        Args:
            data_series: Serie temporal
            max_p: Máximo orden AR
            max_d: Máximo orden de diferenciación
            max_q: Máximo orden MA
            seasonal: Si incluir componente estacional
            period: Período estacional (12 para mensual)
            
        Returns:
            ModelComparison con todos los modelos evaluados
        """
        clean_data = data_series.dropna()
        
        # Generar combinaciones de parámetros
        p_range = range(max_p + 1)
        d_range = range(max_d + 1)
        q_range = range(max_q + 1)
        
        models = []
        
        # ARIMA simple
        for p, d, q in product(p_range, d_range, q_range):
            if p == 0 and q == 0:
                continue  # Saltar modelo sin AR ni MA
            
            try:
                model = ARIMA(clean_data, order=(p, d, q))
                results = model.fit()
                
                forecast = results.get_forecast(steps=1)
                
                models.append(ForecastResult(
                    model_name=f"ARIMA({p},{d},{q})",
                    predicted_mean=forecast.predicted_mean,
                    conf_int=forecast.conf_int(),
                    aic=results.aic,
                    bic=results.bic,
                    order=(p, d, q),
                    residuals(results.resid)
                ))
            except:
                continue
        
        # SARIMA si se solicita
        if seasonal:
            seasonal_params = [(1, 1, 1, period), (1, 0, 1, period), (0, 1, 1, period)]
            
            for p, d, q in product(range(2), range(2), range(2)):
                for seasonal_order in seasonal_params:
                    try:
                        model = SARIMAX(
                            clean_data,
                            order=(p, d, q),
                            seasonal_order=seasonal_order,
                            enforce_stationarity=False,
                            enforce_invertibility=False
                        )
                        results = model.fit(disp=False)
                        
                        forecast = results.get_forecast(steps=1)
                        
                        models.append(ForecastResult(
                            model_name=f"SARIMA({p},{d},{q})x{seasonal_order}",
                            predicted_mean=forecast.predicted_mean,
                            conf_int=forecast.conf_int(),
                            aic=results.aic,
                            bic=results.bic,
                            order=(p, d, q),
                            seasonal_order=seasonal_order,
                            residuals(results.resid)
                        ))
                    except:
                        continue
        
        # Seleccionar mejores modelos
        if models:
            models.sort(key=lambda x: x.aic)
            best_aic = models[0]
            
            models.sort(key=lambda x: x.bic)
            best_bic = models[0]
            
            # Crear resumen
            summary_data = []
            for m in models[:10]:  # Top 10 modelos
                summary_data.append({
                    'Model': m.model_name,
                    'AIC': m.aic,
                    'BIC': m.bic,
                    'Order': str(m.order)
                })
            
            summary = pd.DataFrame(summary_data)
        else:
            best_aic = None
            best_bic = None
            summary = pd.DataFrame()
        
        return ModelComparison(
            models=models,
            best_aic=best_aic,
            best_bic=best_bic,
            summary=summary
        )
    
    def _calculate_diagnostics(self, results) -> Dict:
        """Calcula diagnósticos del modelo"""
        from statsmodels.stats.stattools import durbin_watson, jarque_bera
        
        residuals = results.resid
        
        return {
            'durbin_watson': durbin_watson(residuals),
            'jarque_bera': jarque_bera(residuals),
            'normality_pvalue': jarque_bera(residuals)[1],
            'mean_residual': residuals.mean(),
            'std_residual': residuals.std()
        }
    
    def forecast_with_confidence(
        self,
        data_series: pd.Series,
        periods: int = 6,
        confidence_levels: List[float] = [0.80, 0.90, 0.95]
    ) -> Dict:
        """
        Genera pronóstico con múltiples niveles de confianza.
        
        Args:
            data_series: Serie temporal
            periods: Períodos a pronosticar
            confidence_levels: Niveles de confianza
            
        Returns:
            Diccionario con pronósticos para cada nivel
        """
        result = self.forecast_inflation(data_series, periods)
        
        confidence_intervals = {}
        for level in confidence_levels:
            alpha = 1 - level
            # Recalcular intervalos para este nivel
            model = SARIMAX(
                data_series.dropna(),
                order=self.default_order,
                seasonal_order=self.default_seasonal_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            results = model.fit(disp=False)
            forecast = results.get_forecast(steps=periods)
            
            # Obtener intervalos de confianza personalizados
            cov = forecast.cov_pred
            se = np.sqrt(np.diag(cov))
            z_value = 1.96 if level == 0.95 else (1.645 if level == 0.90 else 1.28)
            
            lower = result.predicted_mean - z_value * se
            upper = result.predicted_mean + z_value * se
            
            confidence_intervals[level] = {
                'lower': lower,
                'upper': upper
            }
        
        return {
            'predicted_mean': result.predicted_mean,
            'confidence_intervals': confidence_intervals,
            'model_aic': result.aic,
            'model_bic': result.bic
        }


class DollarRateForecaster:
    """
    Pronosticador de tipo de cambio para Venezuela.
    
    Considera la dualidad cambiaria (oficial vs paralelo)
    y la alta volatilidad del mercado.
    """
    
    def __init__(self):
        self.default_order = (1, 1, 1)
    
    def forecast_dollar_rate(
        self,
        data_series: pd.Series,
        periods: int = 30,
        order: Optional[Tuple[int, int, int]] = None
    ) -> ForecastResult:
        """
        Pronostica tipo de cambio usando ARIMA.
        
        Args:
            data_series: Serie temporal del tipo de cambio
            periods: Días a pronosticar
            order: Orden ARIMA
            
        Returns:
            ForecastResult
        """
        if order is None:
            order = self.default_order
        
        clean_data = data_series.dropna()
        
        # Modelo ARIMA para tipo de cambio (sin estacionalidad marcada)
        model = ARIMA(clean_data, order=order)
        results = model.fit()
        
        forecast = results.get_forecast(steps=periods)
        
        return ForecastResult(
            model_name="ARIMA",
            predicted_mean=forecast.predicted_mean,
            conf_int=forecast.conf_int(),
            aic=results.aic,
            bic=results.bic,
            order=order,
            residuals(results.resid)
        )
    
    def forecast_both_rates(
        self,
        official_series: pd.Series,
        parallel_series: pd.Series,
        periods: int = 30
    ) -> Dict:
        """
        Pronostica ambos tipos de cambio y calcula el spread esperado.
        
        Returns:
            Diccionario con pronósticos de oficial, paralelo y spread
        """
        official_forecast = self.forecast_dollar_rate(official_series, periods)
        parallel_forecast = self.forecast_dollar_rate(parallel_series, periods)
        
        # Calcular spread esperado
        expected_spread = (
            (parallel_forecast.predicted_mean - official_forecast.predicted_mean) 
            / official_forecast.predicted_mean * 100
        )
        
        return {
            'official': official_forecast,
            'parallel': parallel_forecast,
            'expected_spread': expected_spread,
            'current_spread': (
                (parallel_series.iloc[-1] - official_series.iloc[-1]) 
                / official_series.iloc[-1] * 100
            )
        }


def create_forecast_report(
    inflation_forecast: ForecastResult,
    dollar_forecast: Optional[ForecastResult] = None
) -> str:
    """
    Genera reporte de pronóstico formateado.
    
    Args:
        inflation_forecast: Resultado del pronóstico de inflación
        dollar_forecast: Resultado del pronóstico de tipo de cambio
        
    Returns:
        Reporte en texto formateado
    """
    report = f"""
=== REPORTE DE PRONÓSTICO ECONÓMICO ===

📊 PRONÓSTICO DE INFLACIÓN
Modelo: {inflation_forecast.model_name}
Orden: {inflation_forecast.order}
Estacional: {inflation_forecast.seasonal_order}
AIC: {inflation_forecast.aic:.2f}
BIC: {inflation_forecast.bic:.2f}

Pronósticos:
"""
    
    for i, (date, value) in enumerate(inflation_forecast.predicted_mean.items()):
        lower = inflation_forecast.conf_int.iloc[i, 0]
        upper = inflation_forecast.conf_int.iloc[i, 1]
        report += f"  {date.strftime('%Y-%m')}: {value:.2f}% (IC 95%: [{lower:.2f}%, {upper:.2f}%])\n"
    
    if inflation_forecast.diagnostics:
        report += f"\nDiagnóstico:"
        report += f"\n  Durbin-Watson: {inflation_forecast.diagnostics['durbin_watson']:.4f}"
        report += f"\n  Jarque-Bera p-value: {inflation_forecast.diagnostics['normality_pvalue']:.4f}"
    
    if dollar_forecast:
        report += f"""

💵 PRONÓSTICO DE TIPO DE CAMBIO
Modelo: {dollar_forecast.model_name}
Orden: {dollar_forecast.order}

Pronósticos (próximos 5 días):
"""
        for i, (date, value) in enumerate(list(dollar_forecast.predicted_mean.items())[:5]):
            lower = dollar_forecast.conf_int.iloc[i, 0]
            upper = dollar_forecast.conf_int.iloc[i, 1]
            report += f"  {date.strftime('%Y-%m-%d')}: Bs {value:.2f} (IC 95%: [Bs {lower:.2f}, Bs {upper:.2f}])\n"
    
    return report
