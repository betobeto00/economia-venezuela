"""
Módulo de Causalidad y Cointegración
====================================

Análisis de relaciones entre series temporales:
- Prueba de Causalidad de Granger
- Cointegración de Johansen
- Modelo VECM (Vector Error Correction Model)

Especialmente útil para Venezuela:
- Relación entre dólar oficial y paralelo
- Efecto del petróleo en el tipo de cambio
- Transmisión de precios
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from statsmodels.tsa.vector_ar.vecm import VECM, coint_johansen, select_order
from statsmodels.tsa.stattools import grangercausalitytests, coint
from statsmodels.tsa.api import VAR
import warnings

warnings.filterwarnings('ignore')


@dataclass
class GrangerResult:
    """Resultado de prueba de Causalidad de Granger"""
    cause: str
    effect: str
    lags_tested: int
    f_statistic: float
    p_value: float
    causes_granger: bool
    significance_level: float
    interpretation: str


@dataclass
class CointegrationResult:
    """Resultado de prueba de cointegración"""
    test_type: str
    test_statistic: float
    critical_values: Dict[str, float]
    p_value: Optional[float]
    is_cointegrated: bool
    n_vectors: int
    interpretation: str


@dataclass
class VECMResult:
    """Resultado del modelo VECM"""
    alpha: np.ndarray  # Velocidad de ajuste
    beta: np.ndarray   # Vectores de cointegración
    gamma: np.ndarray  # Coeficientos de corto plazo
    residuals: np.ndarray
    summary: str
    lag_order: int
    coint_rank: int


class GrangerCausalityTester:
    """
    Tester de Causalidad de Granger.
    
    Determina si una serie "causa" otra en el sentido de Granger,
    es decir, si los valores pasados de una serie ayudan a predecir
    la otra serie.
    
    Ejemplo para Venezuela:
        tester = GrangerCausalityTester()
        
        # ¿El dólar paralelo causa el oficial?
        result = tester.test_granger_causality(
            parallel_series, 
            official_series,
            cause_name="Dólar Paralelo",
            effect_name="Dólar Oficial"
        )
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
    
    def test_granger_causality(
        self,
        cause_series: pd.Series,
        effect_series: pd.Series,
        max_lags: int = 10,
        cause_name: str = "X",
        effect_name: str = "Y"
    ) -> GrangerResult:
        """
        Prueba causalidad de Granger.
        
        H0: X no causa en el sentido de Granger a Y
        H1: X causa en el sentido de Granger a Y
        
        Args:
            cause_series: Serie causal (X)
            effect_series: Serie efecto (Y)
            max_lags: Número máximo de rezagos a probar
            cause_name: Nombre de la serie causal
            effect_name: Nombre de la serie efecto
            
        Returns:
            GrangerResult con resultados de la prueba
        """
        # Preparar datos
        data = pd.concat([effect_series, cause_series], axis=1).dropna()
        data.columns = [effect_name, cause_name]
        
        # Realizar prueba de Granger
        # test='ssr_ftest' usa el test F de razón de verosimilitud
        results = grangercausalitytests(data, maxlag=max_lags, verbose=False)
        
        # Encontrar el mejor rezago (menor p-value)
        best_lag = None
        best_pvalue = 1.0
        best_fstat = 0
        
        for lag in range(1, max_lags + 1):
            test_result = results[lag][0]
            f_stat = test_result['ssr_ftest'][0]
            p_value = test_result['ssr_ftest'][1]
            
            if p_value < best_pvalue:
                best_pvalue = p_value
                best_fstat = f_stat
                best_lag = lag
        
        # Determinar causalidad
        causes_granger = best_pvalue < self.significance_level
        
        # Interpretación
        if causes_granger:
            interpretation = (
                f"{cause_name} SÍ causa en el sentido de Granger a {effect_name} "
                f"(p-value={best_pvalue:.4f} < {self.significance_level}). "
                f"Los valores pasados de {cause_name} ayudan a predecir {effect_name}."
            )
        else:
            interpretation = (
                f"{cause_name} NO causa en el sentido de Granger a {effect_name} "
                f"(p-value={best_pvalue:.4f} >= {self.significance_level}). "
                f"No hay evidencia de causalidad predictiva."
            )
        
        return GrangerResult(
            cause=cause_name,
            effect=effect_name,
            lags_tested=best_lag,
            f_statistic=best_fstat,
            p_value=best_pvalue,
            causes_granger=causes_granger,
            significance_level=self.significance_level,
            interpretation=interpretation
        )
    
    def bidirectional_test(
        self,
        series_a: pd.Series,
        series_b: pd.Series,
        name_a: str = "Serie A",
        name_b: str = "Serie B",
        max_lags: int = 10
    ) -> Dict:
        """
        Prueba de causalidad bidireccional.
        
        Args:
            series_a: Primera serie
            series_b: Segunda serie
            name_a: Nombre de la primera serie
            name_b: Nombre de la segunda serie
            max_lags: Máximo de rezagos
            
        Returns:
            Diccionario con resultados bidireccionales
        """
        result_a_to_b = self.test_granger_causality(
            series_a, series_b, max_lags, name_a, name_b
        )
        
        result_b_to_a = self.test_granger_causality(
            series_b, series_a, max_lags, name_b, name_a
        )
        
        # Determinar tipo de relación
        if result_a_to_b.causes_granger and result_b_to_a.causes_granger:
            relationship = "Feedback (bidireccional)"
        elif result_a_to_b.causes_granger:
            relationship = f"{name_a} -> {name_b} (unidireccional)"
        elif result_b_to_a.causes_granger:
            relationship = f"{name_b} -> {name_a} (unidireccional)"
        else:
            relationship = "Sin causalidad de Granger"
        
        return {
            'a_to_b': result_a_to_b,
            'b_to_a': result_b_to_a,
            'relationship_type': relationship,
            'summary': self._create_summary(result_a_to_b, result_b_to_a, name_a, name_b)
        }
    
    def _create_summary(self, result_ab, result_ba, name_a, name_b) -> str:
        """Crea resumen de la prueba bidireccional"""
        return f"""
=== Prueba de Causalidad de Granger ===

{name_a} → {name_b}:
  - F-statistic: {result_ab.f_statistic:.4f}
  - p-value: {result_ab.p_value:.4f}
  - Causalidad: {'SÍ' if result_ab.causes_granger else 'NO'}

{name_b} → {name_a}:
  - F-statistic: {result_ba.f_statistic:.4f}
  - p-value: {result_ba.p_value:.4f}
  - Causalidad: {'SÍ' if result_ba.causes_granger else 'NO'}

Tipo de relación: {self._get_relationship_type(result_ab, result_ba)}
"""
    
    def _get_relationship_type(self, result_ab, result_ba) -> str:
        if result_ab.causes_granger and result_ba.causes_granger:
            return "Feedback (bidireccional)"
        elif result_ab.causes_granger:
            return "Unidireccional"
        elif result_ba.causes_granger:
            return "Unidireccional inversa"
        else:
            return "Sin causalidad"


class CointegrationAnalyzer:
    """
    Analizador de cointegración para series temporales.
    
    La cointegración indica que series no estacionarias comparten
    una relación de equilibrio a largo plazo.
    
    Ejemplo para Venezuela:
        analyzer = CointegrationAnalyzer()
        
        # ¿El dólar oficial y paralelo están cointegrados?
        result = analyzer.test_cointegration(official, parallel)
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
    
    def test_engle_granger(
        self,
        series_y: pd.Series,
        series_x: pd.Series,
        name_y: str = "Y",
        name_x: str = "X"
    ) -> CointegrationResult:
        """
        Prueba de cointegración de Engle-Granger.
        
        H0: No hay cointegración
        H1: Hay cointegración
        
        Args:
            series_y: Serie dependiente
            series_x: Serie independiente
            name_y: Nombre de la serie Y
            name_x: Nombre de la serie X
            
        Returns:
            CointegrationResult
        """
        # Eliminar NaN
        data = pd.concat([series_y, series_x], axis=1).dropna()
        
        # Realizar prueba de cointegración
        score, pvalue, crit_values = coint(data.iloc[:, 0], data.iloc[:, 1])
        
        # Determinar cointegración
        is_cointegrated = pvalue < self.significance_level
        
        # Interpretación
        if is_cointegrated:
            interpretation = (
                f"Las series {name_y} y {name_x} SÍ están cointegradas "
                f"(p-value={pvalue:.4f}). Existe una relación de equilibrio "
                f"a largo plazo entre ellas."
            )
        else:
            interpretation = (
                f"Las series {name_y} y {name_x} NO están cointegradas "
                f"(p-value={pvalue:.4f}). No hay relación de equilibrio estable."
            )
        
        return CointegrationResult(
            test_type="Engle-Granger",
            test_statistic=score,
            critical_values={
                '1%': crit_values[0],
                '5%': crit_values[1],
                '10%': crit_values[2]
            },
            p_value=pvalue,
            is_cointegrated=is_cointegrated,
            n_vectors=1,
            interpretation=interpretation
        )
    
    def test_johansen(
        self,
        data: pd.DataFrame,
        det_order: int = 0,
        k_ar_diff: int = 2
    ) -> Dict:
        """
        Prueba de cointegración de Johansen.
        
        Más robusta que Engle-Granger para múltiples series.
        
        Args:
            data: DataFrame con las series (cada columna es una serie)
            det_order: Orden del determinante (-1, 0, 1)
            k_ar_diff: Rezagos en diferencias
            
        Returns:
            Diccionario con resultados de la prueba
        """
        # Eliminar NaN
        clean_data = data.dropna()
        
        # Realizar prueba de Johansen
        result = coint_johansen(clean_data, det_order, k_ar_diff)
        
        # Interpretar resultados
        trace_stat = result.lr1  # Trace statistic
        max_eig_stat = result.lr2  # Maximum eigenvalue statistic
        
        # Valores críticos
        trace_crit = result.cvt  # Critical values para trace
        max_eig_crit = result.cvm  # Critical values para max eigen
        
        # Determinar número de vectores de cointegración
        n_vectors_trace = sum(trace_stat > trace_crit[:, 1])  # Al nivel del 5%
        n_vectors_max_eig = sum(max_eig_stat > max_eig_crit[:, 1])
        
        return {
            'trace_statistic': trace_stat,
            'trace_critical_values': trace_crit,
            'max_eigenvalue_statistic': max_eig_stat,
            'max_eigenvalue_critical_values': max_eig_crit,
            'n_vectors_trace': n_vectors_trace,
            'n_vectors_max_eig': n_vectors_max_eig,
            'eigenvalues': result.eig,
            'summary': self._create_johansen_summary(
                trace_stat, trace_crit, max_eig_stat, max_eig_crit,
                n_vectors_trace, n_vectors_max_eig
            )
        }
    
    def _create_johansen_summary(
        self, trace_stat, trace_crit, max_eig_stat, max_eig_crit,
        n_vectors_trace, n_vectors_max_eig
    ) -> str:
        """Crea resumen de la prueba de Johansen"""
        summary = "=== Prueba de Cointegración de Johansen ===\n\n"
        
        summary += "Trace Test:\n"
        for i, (stat, crit) in enumerate(zip(trace_stat, trace_crit)):
            summary += f"  r <= {i}: Stat={stat:.4f}, Crit(5%)={crit[1]:.4f}, "
            summary += f"{'Rechazar H0' if stat > crit[1] else 'No rechazar H0'}\n"
        
        summary += f"\nMáximo Eigenvalue Test:\n"
        for i, (stat, crit) in enumerate(zip(max_eig_stat, max_eig_crit)):
            summary += f"  r <= {i}: Stat={stat:.4f}, Crit(5%)={crit[1]:.4f}, "
            summary += f"{'Rechazar H0' if stat > crit[1] else 'No rechazar H0'}\n"
        
        summary += f"\nVectores de cointegración (Trace): {n_vectors_trace}"
        summary += f"\nVectores de cointegración (Max Eigen): {n_vectors_max_eig}"
        
        return summary


class VECMAnalyzer:
    """
    Analizador VECM (Vector Error Correction Model).
    
    Modela la dinámica de series cointegradas, separando:
    - Componente de largo plazo (vectores de cointegración)
    - Componente de corto plazo (coeficientes AR)
    - Velocidad de ajuste (alpha)
    
    Ejemplo para Venezuela:
        analyzer = VECMAnalyzer()
        
        # Analizar relación oficial-paralelo
        result = analyzer.fit_vecm(official, parallel)
        
        # La alpha indica qué tan rápido se corrige el mercado
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
        self.coint_analyzer = CointegrationAnalyzer(significance_level)
    
    def fit_vecm(
        self,
        series_1: pd.Series,
        series_2: pd.Series,
        name_1: str = "Serie 1",
        name_2: str = "Serie 2",
        coint_rank: Optional[int] = None,
        lag_order: Optional[int] = None
    ) -> Dict:
        """
        Ajusta un modelo VECM a dos series cointegradas.
        
        Args:
            series_1: Primera serie
            series_2: Segunda serie
            name_1: Nombre de la primera serie
            name_2: Nombre de la segunda serie
            coint_rank: Rango de cointegración (None = automático)
            lag_order: Orden de rezagos (None = automático)
            
        Returns:
            Diccionario con resultados del VECM
        """
        # Preparar datos
        data = pd.concat([series_1, series_2], axis=1).dropna()
        data.columns = [name_1, name_2]
        
        # Verificar cointegración primero
        coint_result = self.coint_analyzer.test_engle_granger(
            series_1, series_2, name_1, name_2
        )
        
        if not coint_result.is_cointegrated:
            return {
                'error': f"Las series no están cointegradas (p-value={coint_result.p_value:.4f}). "
                        f"No se puede aplicar VECM.",
                'cointegration_test': coint_result
            }
        
        # Seleccionar orden de rezagos automáticamente si no se especifica
        if lag_order is None:
            select_result = select_order(data, maxlags=10)
            lag_order = select_result.aic
        
        # Seleccionar rango de cointegración automáticamente si no se especifica
        if coint_rank is None:
            johansen_result = self.coint_analyzer.test_johansen(data)
            coint_rank = johansen_result['n_vectors_trace']
            if coint_rank == 0:
                coint_rank = 1  # Forzar al menos 1 para el modelo
        
        # Ajustar VECM
        vecm = VECM(
            data,
            coint_rank=coint_rank,
            deterministic="ci",
            k_ar_diff=lag_order
        )
        
        vecm_fit = vecm.fit()
        
        # Extraer resultados
        alpha = vecm_fit.alpha  # Velocidad de ajuste
        beta = vecm_fit.beta    # Vectores de cointegración
        gamma = vecm_fit.gamma  # Coeficientos de corto plazo
        
        # Calcular métricas adicionales
        residuals = vecm_fit.resid
        
        # Crear interpretación
        interpretation = self._interpret_vecm(
            alpha, beta, gamma, name_1, name_2, coint_rank
        )
        
        return {
            'model': vecm_fit,
            'alpha': alpha,
            'beta': beta,
            'gamma': gamma,
            'residuals': residuals,
            'summary': vecm_fit.summary(),
            'lag_order': lag_order,
            'coint_rank': coint_rank,
            'cointegration_test': coint_result,
            'interpretation': interpretation,
            'adjustment_speed': self._calculate_adjustment_speed(alpha)
        }
    
    def _interpret_vecm(self, alpha, beta, gamma, name_1, name_2, coint_rank) -> str:
        """Interpreta los resultados del VECM"""
        interpretation = "=== Interpretación del VECM ===\n\n"
        
        # Interpretar alpha (velocidad de ajuste)
        interpretation += "Velocidad de Ajuste (Alpha):\n"
        for i in range(coint_rank):
            for j, name in enumerate([name_1, name_2]):
                if alpha[j, i] != 0:
                    interpretation += f"  {name}: {alpha[j, i]:.4f} "
                    interpretation += f"({abs(alpha[j, i])*100:.2f}% de ajuste por período)\n"
        
        interpretation += "\nVectores de Cointegración (Beta):\n"
        for i in range(coint_rank):
            interpretation += f"  Vector {i+1}: "
            for j, name in enumerate([name_1, name_2]):
                interpretation += f"{name}={beta[j, i]:.4f} "
            interpretation += "\n"
        
        return interpretation
    
    def _calculate_adjustment_speed(self, alpha) -> Dict:
        """Calcula métricas de velocidad de ajuste"""
        speeds = {}
        for i in range(alpha.shape[1]):
            for j in range(alpha.shape[0]):
                speed = abs(alpha[j, i])
                half_life = np.log(2) / speed if speed > 0 else np.inf
                speeds[f'variable_{j}_vec_{i}'] = {
                    'alpha': alpha[j, i],
                    'adjustment_rate': speed,
                    'half_life_periods': half_life
                }
        
        return speeds
    
    def impulse_response(
        self,
        vecm_result: Dict,
        periods: int = 20
    ) -> pd.DataFrame:
        """
        Calcula funciones de impulso-respuesta (IRF).
        
        Muestra cómo responde una variable ante un shock en otra.
        
        Args:
            vecm_result: Resultado del VECM
            periods: Períodos a proyectar
            
        Returns:
            DataFrame con las IRFs
        """
        if 'model' not in vecm_result:
            return pd.DataFrame()
        
        model = vecm_result['model']
        
        # Calcular IRF
        irf = model.irf(periods)
        
        return irf


def analyze_dollar_market(
    official_rate: pd.Series,
    parallel_rate: pd.Series,
    binance_rate: Optional[pd.Series] = None
) -> Dict:
    """
    Análisis completo del mercado cambiario venezolano.
    
    Args:
        official_rate: Tasa oficial del BCV
        parallel_rate: Tasa paralela (DólarToday)
        binance_rate: Tasa Binance P2P (opcional)
        
    Returns:
        Diccionario con análisis completo
    """
    results = {}
    
    # 1. Prueba de causalidad de Granger
    granger_tester = GrangerCausalityTester()
    results['granger'] = granger_tester.bidirectional_test(
        parallel_rate, official_rate,
        "Dólar Paralelo", "Dólar Oficial"
    )
    
    # 2. Prueba de cointegración
    coint_analyzer = CointegrationAnalyzer()
    results['cointegration'] = coint_analyzer.test_engle_granger(
        official_rate, parallel_rate,
        "Oficial", "Paralelo"
    )
    
    # 3. VECM si están cointegrados
    if results['cointegration'].is_cointegrated:
        vecm_analyzer = VECMAnalyzer()
        results['vecm'] = vecm_analyzer.fit_vecm(
            official_rate, parallel_rate,
            "Oficial", "Paralelo"
        )
    
    # 4. Spread analysis
    spread = (parallel_rate - official_rate) / official_rate * 100
    results['spread'] = {
        'current': spread.iloc[-1],
        'mean': spread.mean(),
        'std': spread.std(),
        'trend': 'increasing' if spread.iloc[-1] > spread.mean() else 'decreasing'
    }
    
    return results
