"""
Módulo de Volatilidad con Modelos GARCH
=======================================

Modelos de volatilidad condicional para medir:
- Incertidumbre del mercado cambiario
- Riesgo de inflación
- Volatilidad del precio del petróleo

El "Índice de Nerviosismo Monetario" de Venezuela
se calcula usando GARCH sobre el dólar paralelo.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from arch import arch_model
from arch.univariate import GARCH, EGARCH, ARCH
import warnings

warnings.filterwarnings('ignore')


@dataclass
class VolatilityResult:
    """Resultado de análisis de volatilidad"""
    model_name: str
    model_params: Dict[str, float]
    last_volatility: float  # Volatilidad actual (anualizada)
    volatility_forecast: pd.Series  # Pronóstico de volatilidad
    conditional_variance: pd.Series  # Varianza condicional
    p_value_arch_test: float  # Prueba de efectos ARCH
    is_volatility_clustering: bool
    interpretation: str


@dataclass
class RiskMetrics:
    """Métricas de riesgo derivadas de volatilidad"""
    var_95: float  # Value at Risk al 95%
    var_99: float  # Value at Risk al 99%
    expected_shortfall_95: float  # Expected Shortfall (CVaR)
    annualized_volatility: float
    risk_level: str  # Bajo, Medio, Alto, Muy Alto


class GARCHVolatilityAnalyzer:
    """
    Analizador de volatilidad usando modelos GARCH.
    
    GARCH (Generalized Autoregressive Conditional Heteroskedasticity)
    modela la varianza condicional de series financieras.
    
    Ejemplo para Venezuela:
        analyzer = GARCHVolatilityAnalyzer()
        
        # Analizar volatilidad del dólar paralelo
        result = analyzer.analyze_dollar_volatility(parallel_rate_series)
        
        # Obtener índice de nerviosismo monetario
        risk = analyzer.calculate_risk_metrics(result)
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
    
    def fit_garch(
        self,
        returns: pd.Series,
        p: int = 1,
        q: int = 1,
        mean_model: str = 'Constant',
        vol_model: str = 'GARCH',
        dist: str = 'normal'
    ) -> VolatilityResult:
        """
        Ajusta un modelo GARCH a los retornos.
        
        Args:
            returns: Serie de retornos (en porcentaje)
            p: Orden AR de la varianza
            q: Orden MA de la varianza
            mean_model: Modelo de media ('Constant', 'AR', 'HAR')
            vol_model: Modelo de volatilidad ('GARCH', 'EGARCH', 'ARCH')
            dist: Distribución ('normal', 't', 'skewt')
            
        Returns:
            VolatilityResult con resultados del modelo
        """
        # Limpiar datos
        clean_returns = returns.dropna()
        
        # Seleccionar modelo de volatilidad
        if vol_model == 'GARCH':
            vol = GARCH(p, q)
        elif vol_model == 'EGARCH':
            vol = EGARCH(p, q)
        elif vol_model == 'ARCH':
            vol = ARCH(p)
        else:
            vol = GARCH(p, q)
        
        # Ajustar modelo
        model = arch_model(
            clean_returns,
            vol=vol,
            mean=mean_model,
            dist=dist
        )
        
        results = model.fit(disp='off')
        
        # Obtener volatilidad condicional
        conditional_vol = results.conditional_volatility
        
        # Pronóstico de volatilidad (próximos 5 períodos)
        forecast = results.forecast(horizon=5)
        vol_forecast = np.sqrt(forecast.variance.iloc[-1, :])
        
        # Prueba de efectos ARCH
        arch_test = results.arch_lm_test()
        p_value_arch = arch_test.pval
        
        # Determinar si hay clustering de volatilidad
        is_vol_clustering = p_value_arch < self.significance_level
        
        # Calcular volatilidad anualizada
        last_vol_annualized = conditional_vol.iloc[-1] * np.sqrt(252)  # Para datos diarios
        
        # Interpretación
        interpretation = self._interpret_volatility(
            last_vol_annualized, is_vol_clustering, results.params
        )
        
        return VolatilityResult(
            model_name=f"{vol_model}({p},{q})",
            model_params=results.params.to_dict(),
            last_volatility=last_vol_annualized,
            volatility_forecast=vol_forecast,
            conditional_variance(results.conditional_volatility ** 2),
            p_value_arch_test=p_value_arch,
            is_volatility_clustering=is_vol_clustering,
            interpretation=interpretation
        )
    
    def analyze_dollar_volatility(
        self,
        price_series: pd.Series,
        forecast_horizon: int = 5
    ) -> Dict:
        """
        Análisis de volatilidad específico para tipo de cambio.
        
        Calcula el "Índice de Nerviosismo Monetario" de Venezuela.
        
        Args:
            price_series: Serie de precios del dólar
            forecast_horizon: Horizonte de pronóstico
            
        Returns:
            Diccionario con análisis completo
        """
        # Calcular retornos logarítmicos
        log_returns = np.log(price_series).diff().dropna() * 100
        
        # Ajustar GARCH(1,1)
        garch_result = self.fit_garch(log_returns, p=1, q=1, vol_model='GARCH')
        
        # Ajustar EGARCH para comparar (captura asimetría)
        try:
            egarch_result = self.fit_garch(log_returns, p=1, q=1, vol_model='EGARCH')
            has_leverage = egarch_result.model_params.get('gamma[1]', 0) < 0
        except:
            egarch_result = None
            has_leverage = False
        
        # Calcular métricas de riesgo
        risk_metrics = self._calculate_risk_metrics(
            log_returns, garch_result.last_volatility
        )
        
        # Análisis de estabilidad del mercado
        market_stability = self._assess_market_stability(
            log_returns, garch_result
        )
        
        return {
            'garch': garch_result,
            'egarch': egarch_result,
            'has_leverage_effect': has_leverage,
            'risk_metrics': risk_metrics,
            'market_stability': market_stability,
            'nervousness_index': self._calculate_nervousness_index(garch_result)
        }
    
    def analyze_inflation_volatility(
        self,
        inflation_series: pd.Series
    ) -> Dict:
        """
        Análisis de volatilidad de la inflación.
        
        La volatilidad de la inflación indica incertidumbre
        en los precios y dificulta la planificación económica.
        """
        # Para inflación mensual, usar ARCH simple o GARCH
        # La inflación no tiene retornos como series financieras
        
        # Calcular cambios en la inflación
        inflation_changes = inflation_series.diff().dropna()
        
        # Ajustar GARCH
        garch_result = self.fit_garch(
            inflation_changes, 
            p=1, q=1, 
            vol_model='GARCH',
            mean_model='AR',
            dist='t'  # Distribución t para colas pesadas
        )
        
        # Clasificar nivel de incertidumbre
        uncertainty_level = self._classify_inflation_uncertainty(
            garch_result.last_volatility
        )
        
        return {
            'garch': garch_result,
            'uncertainty_level': uncertainty_level,
            'interpretation': f"Volatilidad de inflación: {uncertainty_level}"
        }
    
    def _interpret_volatility(self, annualized_vol, is_clustering, params) -> str:
        """Interpreta el nivel de volatilidad"""
        # Clasificar volatilidad
        if annualized_vol < 20:
            level = "BAJA"
        elif annualized_vol < 50:
            level = "MODERADA"
        elif annualized_vol < 100:
            level = "ALTA"
        else:
            level = "MUY ALTA"
        
        interpretation = f"Volatilidad Anualizada: {annualized_vol:.2f}% ({level})\n"
        
        if is_clustering:
            interpretation += "Efecto de Clustering: SÍ hay clustering de volatilidad (períodos de alta volatilidad tienden a seguirse)\n"
        else:
            interpretation += "Efecto de Clustering: NO hay clustering significativo\n"
        
        # Interpretar parámetros GARCH
        alpha = params.get('alpha[1]', 0)
        beta = params.get('beta[1]', 0)
        persistence = alpha + beta
        
        interpretation += f"Persistencia: {persistence:.4f} "
        if persistence > 0.99:
            interpretation += "(Volatilidad muy persistente, choques duran mucho)\n"
        elif persistence > 0.9:
            interpretation += "(Volatilidad moderadamente persistente)\n"
        else:
            interpretation += "(Volatilidad se disipa relativamente rápido)\n"
        
        return interpretation
    
    def _calculate_risk_metrics(
        self, 
        returns: pd.Series, 
        current_vol: float
    ) -> RiskMetrics:
        """Calcula métricas de riesgo"""
        # VaR paramétrico (asumiendo normalidad)
        var_95 = -np.percentile(returns, 5)
        var_99 = -np.percentile(returns, 1)
        
        # Expected Shortfall (CVaR)
        var_95_threshold = np.percentile(returns, 5)
        tail_returns = returns[returns <= var_95_threshold]
        expected_shortfall_95 = -tail_returns.mean() if len(tail_returns) > 0 else var_95
        
        # Volatilidad anualizada
        annualized_vol = current_vol
        
        # Clasificar nivel de riesgo
        if annualized_vol < 20:
            risk_level = "BAJO"
        elif annualized_vol < 50:
            risk_level = "MEDIO"
        elif annualized_vol < 100:
            risk_level = "ALTO"
        else:
            risk_level = "MUY ALTO"
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=expected_shortfall_95,
            annualized_volatility=annualized_vol,
            risk_level=risk_level
        )
    
    def _assess_market_stability(
        self, 
        returns: pd.Series, 
        garch_result: VolatilityResult
    ) -> Dict:
        """Evalúa la estabilidad del mercado"""
        # Volatilidad histórica vs actual
        historical_vol = returns.rolling(window=30).std().mean() * np.sqrt(252)
        current_vol = garch_result.last_volatility
        
        vol_ratio = current_vol / historical_vol if historical_vol > 0 else 1
        
        # Tendencia de volatilidad
        vol_trend = garch_result.volatility_forecast.diff().mean()
        
        # Clasificar estabilidad
        if vol_ratio < 0.8:
            stability = "MUY ESTABLE"
        elif vol_ratio < 1.2:
            stability = "ESTABLE"
        elif vol_ratio < 1.5:
            stability = "VOLÁTIL"
        else:
            stability = "MUY VOLÁTIL"
        
        return {
            'stability_level': stability,
            'volatility_ratio': vol_ratio,
            'volatility_trend': 'increasing' if vol_trend > 0 else 'decreasing',
            'historical_volatility': historical_vol,
            'current_volatility': current_vol
        }
    
    def _calculate_nervousness_index(self, garch_result: VolatilityResult) -> Dict:
        """
        Calcula el Índice de Nerviosismo Monetario.
        
        Escala 0-100:
        - 0-20: Calma
        - 20-40: Tranquilidad
        - 40-60: Alerta
        - 60-80: Nerviosismo
        - 80-100: Pánico
        """
        vol = garch_result.last_volatility
        
        # Mapear volatilidad a índice 0-100
        # Asumiendo que vol > 100% es nivel de pánico
        nervousness_index = min(vol, 100)
        
        # Clasificar
        if nervousness_index < 20:
            level = "CALMA"
        elif nervousness_index < 40:
            level = "TRANQUILIDAD"
        elif nervousness_index < 60:
            level = "ALERTA"
        elif nervousness_index < 80:
            level = "NERVIOSISMO"
        else:
            level = "PÁNICO"
        
        return {
            'index': nervousness_index,
            'level': level,
            'description': f"Nivel de nerviosismo monetario: {level} ({nervousness_index:.1f}/100)"
        }
    
    def _classify_inflation_uncertainty(self, volatility: float) -> str:
        """Clasifica la incertidumbre de inflación"""
        if volatility < 2:
            return "BAJA - Inflación predecible"
        elif volatility < 5:
            return "MODERADA - Alguna incertidumbre"
        elif volatility < 10:
            return "ALTA - Difícil de predecir"
        else:
            return "MUY ALTA - Extrema incertidumbre"


def create_volatility_report(analysis_result: Dict) -> str:
    """
    Genera reporte de volatilidad formateado.
    
    Args:
        analysis_result: Resultado de analyze_dollar_volatility
        
    Returns:
        Reporte en texto
    """
    garch = analysis_result['garch']
    risk = analysis_result['risk_metrics']
    stability = analysis_result['market_stability']
    nervousness = analysis_result['nervousness_index']
    
    report = f"""
=== REPORTE DE VOLATILIDAD Y RIESGO ===

📊 ANÁLISIS GARCH
Modelo: {garch.model_name}
Volatilidad Anualizada: {garch.last_volatility:.2f}%
Clustering: {'SÍ' if garch.is_volatility_clustering else 'NO'}
Prueba ARCH p-value: {garch.p_value_arch_test:.4f}

🎯 ÍNDICE DE NERVIOSISMO MONETARIO
Índice: {nervousness['index']:.1f}/100
Nivel: {nervousness['level']}

⚠️ MÉTRICAS DE RIESGO
Value at Risk (95%): {risk.var_95:.2f}%
Value at Risk (99%): {risk.var_99:.2f}%
Expected Shortfall (95%): {risk.expected_shortfall_95:.2f}%
Nivel de Riesgo: {risk.risk_level}

📈 ESTABILIDAD DEL MERCADO
Nivel: {stability['stability_level']}
Ratio Volatilidad Actual/Histórica: {stability['volatility_ratio']:.2f}
Tendencia: {stability['volatility_trend']}

--- Pronóstico de Volatilidad (próximos 5 días) ---
"""
    
    for i, vol in enumerate(garch.volatility_forecast):
        report += f"  Día {i+1}: {vol:.2f}%\n"
    
    report += f"""
--- Interpretación ---
{garch.interpretation}
"""
    
    return report
