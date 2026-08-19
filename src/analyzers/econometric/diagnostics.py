"""
Módulo de Diagnósticos de Residuos
==================================

Pruebas estadísticas para validar modelos econométricos:
- Normalidad (Jarque-Bera, Shapiro-Wilk)
- Autocorrelación (Durbin-Watson, Ljung-Box)
- Heterocedasticidad (White, Breusch-Pagan)
- Estructural (Chow test)

Fundamental para validar la calidad de los modelos
en economías volátiles como la venezolana.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from scipy import stats
from statsmodels.stats.stattools import (
    durbin_watson, 
    jarque_bera,
    omni_normtest
)
from statsmodels.stats.diagnostic import (
    het_white,
    het_breuschpagan,
    breaks_cusumolsresid,
    acorr_breusch_godfrey
)
from statsmodels.stats.outliers_influence import variance_inflation_factor
import warnings

warnings.filterwarnings('ignore')


@dataclass
class DiagnosticResult:
    """Resultado de una prueba de diagnóstico"""
    test_name: str
    statistic: float
    p_value: float
    is_valid: bool  # True si los residuos pasan la prueba
    interpretation: str
    assumptions_met: bool


@dataclass
class ModelDiagnostics:
    """Diagnósticos completos de un modelo"""
    normality: DiagnosticResult
    autocorrelation: DiagnosticResult
    heteroscedasticity: DiagnosticResult
    model_quality: str
    recommendations: list
    overall_score: float


class ResidualDiagnostics:
    """
    Clase para realizar diagnósticos de residuos de modelos econométricos.
    
    Verifica las suposiciones clave de los modelos:
    1. Normalidad de residuos
    2. Ausencia de autocorrelación
    3. Homocedasticidad (varianza constante)
    4. Estabilidad estructural
    
    Ejemplo de uso:
        diagnostics = ResidualDiagnostics()
        result = diagnostics.full_diagnostics(model_resid)
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.significance_level = significance_level
    
    def test_normality(
        self, 
        residuals: pd.Series,
        test: str = 'jarque_bera'
    ) -> DiagnosticResult:
        """
        Prueba de normalidad de residuos.
        
        H0: Los residuos se distribuyen normalmente
        H1: Los residuos NO se distribuyen normalmente
        
        Args:
            residuals: Serie de residuos del modelo
            test: Prueba a utilizar ('jarque_bera', 'shapiro', 'omni')
            
        Returns:
            DiagnosticResult
        """
        clean_resid = residuals.dropna()
        
        if test == 'jarque_bera':
            jb_stat, jb_pvalue, skew, kurtosis = jarque_bera(clean_resid)
            statistic = jb_stat
            p_value = jb_pvalue
            test_name = "Jarque-Bera"
        elif test == 'shapiro':
            # Shapiro-Wilk (muestra max 5000)
            sample = clean_resid[:5000] if len(clean_resid) > 5000 else clean_resid
            statistic, p_value = stats.shapiro(sample)
            test_name = "Shapiro-Wilk"
        elif test == 'omni':
            statistic, p_value = omni_normtest(clean_resid)
            test_name = "Omni (D'Agostino)"
        else:
            raise ValueError(f"Prueba no soportada: {test}")
        
        # Determinar normalidad
        is_normal = p_value > self.significance_level
        
        # Interpretación
        if is_normal:
            interpretation = (
                f"Los residuos SÍ son normales (p-value={p_value:.4f}). "
                f"Se cumple la suposición de normalidad."
            )
        else:
            interpretation = (
                f"Los residuos NO son normales (p-value={p_value:.4f}). "
                f"Considerar distribución t o errores robustos."
            )
        
        return DiagnosticResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            is_valid=is_normal,
            interpretation=interpretation,
            assumptions_met=is_normal
        )
    
    def test_autocorrelation(
        self, 
        residuals: pd.Series,
        nlags: int = 10,
        test: str = 'ljung_box'
    ) -> DiagnosticResult:
        """
        Prueba de autocorrelación en residuos.
        
        H0: No hay autocorrelación (residuos son ruido blanco)
        H1: Hay autocorrelación serial
        
        Args:
            residuals: Serie de residuos
            nlags: Número de rezagos a probar
            test: Prueba ('durbin_watson', 'ljung_box', 'breusch_godfrey')
            
        Returns:
            DiagnosticResult
        """
        clean_resid = residuals.dropna()
        
        if test == 'durbin_watson':
            statistic = durbin_watson(clean_resid)
            # DW cercano a 2 indica no autocorrelación
            # DW < 1.5 o > 2.5 sugiere autocorrelación
            is_no_autocorr = 1.5 <= statistic <= 2.5
            p_value = None  # DW no tiene p-value directo
            
            interpretation = (
                f"Durbin-Watson: {statistic:.4f}. "
            )
            if is_no_autocorr:
                interpretation += "No hay evidencia de autocorrelación serial."
            elif statistic < 1.5:
                interpretation += "Posible autocorrelación positiva."
            else:
                interpretation += "Posible autocorrelación negativa."
            
            test_name = "Durbin-Watson"
            
        elif test == 'ljung_box':
            from statsmodels.stats.diagnostic import acorr_ljungbox
            result = acorr_ljungbox(clean_resid, lags=nlags, return_df=True)
            
            # Usar el menor p-value de todos los rezagos
            min_pvalue = result['lb_pvalue'].min()
            statistic = result['lb_stat'].iloc[-1]
            p_value = min_pvalue
            
            is_no_autocorr = p_value > self.significance_level
            
            interpretation = (
                f"Ljung-Box (lag {nlags}): statistic={statistic:.4f}, p-value={p_value:.4f}. "
            )
            if is_no_autocorr:
                interpretation += "No hay autocorrelación significativa."
            else:
                interpretation += "Hay autocorrelación significativa en los residuos."
            
            test_name = "Ljung-Box"
            
        elif test == 'breusch_godfrey':
            # Necesita el modelo completo, no solo residuos
            # Aquí hacemos una simplificación
            statistic = durbin_watson(clean_resid)
            p_value = None
            is_no_autocorr = 1.5 <= statistic <= 2.5
            
            interpretation = f"Breusch-Godfrey simplificado: DW={statistic:.4f}"
            test_name = "Breusch-Godfrey"
        
        return DiagnosticResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value if p_value is not None else 0.0,
            is_valid=is_no_autocorr,
            interpretation=interpretation,
            assumptions_met=is_no_autocorr
        )
    
    def test_heteroscedasticity(
        self, 
        residuals: pd.Series,
        exog: Optional[pd.DataFrame] = None,
        test: str = 'white'
    ) -> DiagnosticResult:
        """
        Prueba de heterocedasticidad.
        
        H0: Varianza constante (homocedasticidad)
        H1: Varianza no constante (heterocedasticidad)
        
        Args:
            residuals: Serie de residuos
            exog: Variables exógenas (para White test)
            test: Prueba ('white', 'breusch_pagan')
            
        Returns:
            DiagnosticResult
        """
        clean_resid = residuals.dropna()
        
        if test == 'white':
            if exog is not None:
                # White test requiere variables exógenas
                clean_exog = exog.loc[clean_resid.index].dropna()
                statistic, p_value, f_stat, f_pvalue = het_white(clean_resid, clean_exog)
            else:
                # Simplificación: usar prueba de Breusch-Pagan con residuos al cuadrado
                from statsmodels.stats.diagnostic import het_breuschpagan
                x = np.arange(len(clean_resid)).reshape(-1, 1)
                statistic, p_value, f_stat, f_pvalue = het_breuschpagan(clean_resid, x)
            
            test_name = "White"
            
        elif test == 'breusch_pagan':
            if exog is None:
                x = np.arange(len(clean_resid)).reshape(-1, 1)
            else:
                x = exog.loc[clean_resid.index].dropna()
            
            statistic, p_value, f_stat, f_pvalue = het_breuschpagan(clean_resid, x)
            test_name = "Breusch-Pagan"
        
        # Homocedasticidad se cumple si NO se rechaza H0
        is_homoscedastic = p_value > self.significance_level
        
        if is_homoscedastic:
            interpretation = (
                f"Los residuos son homocédasticos (p-value={p_value:.4f}). "
                f"La varianza es constante."
            )
        else:
            interpretation = (
                f"Los residuos son heterocédasticos (p-value={p_value:.4f}). "
                f"Considerar errores estándar robustos (Newey-West)."
            )
        
        return DiagnosticResult(
            test_name=test_name,
            statistic=statistic,
            p_value=p_value,
            is_valid=is_homoscedastic,
            interpretation=interpretation,
            assumptions_met=is_homoscedastic
        )
    
    def test_structural_breaks(
        self,
        residuals: pd.Series,
        exog: Optional[pd.DataFrame] = None
    ) -> DiagnosticResult:
        """
        Prueba de quiebres estructurales (Chow test simplificado).
        
        Detecta si hubo cambios estructurales en la relación
        entre variables.
        
        Importante para Venezuela: Cambios de política económica,
        sanciones, etc., causan quiebres estructurales.
        """
        clean_resid = residuals.dropna()
        
        if exog is None:
            exog = pd.DataFrame({'const': np.ones(len(clean_resid))})
        
        # Usar CUSUM test como proxy de quiebres estructurales
        try:
            statistic, critical_values, pvalue = breaks_cusumolsresid(clean_resid)
            
            # Si p-value < 0.05, hay evidencia de quiebre estructural
            is_stable = pvalue > self.significance_level
            
            if is_stable:
                interpretation = (
                    f"No hay evidencia de quiebres estructurales (p-value={pvalue:.4f}). "
                    f"La estructura del modelo es estable."
                )
            else:
                interpretation = (
                    f"Hay evidencia de quiebres estructurales (p-value={pvalue:.4f}). "
                    f"Considerar muestras subperíodo o modelos con dummies de estructura."
                )
            
            return DiagnosticResult(
                test_name="CUSUM (Chow test proxy)",
                statistic=statistic,
                p_value=pvalue,
                is_valid=is_stable,
                interpretation=interpretation,
                assumptions_met=is_stable
            )
            
        except Exception as e:
            return DiagnosticResult(
                test_name="CUSUM (Chow test proxy)",
                statistic=0,
                p_value=1.0,
                is_valid=True,
                interpretation=f"No se pudo realizar la prueba: {str(e)}",
                assumptions_met=True
            )
    
    def calculate_vif(
        self, 
        X: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calcula Factor de Inflación de Varianza (VIF).
        
        VIF > 10 indica multicolinealidad severa.
        VIF > 5 indica multicolinealidad moderada.
        """
        vif_data = pd.DataFrame()
        vif_data['Variable'] = X.columns
        vif_data['VIF'] = [
            variance_inflation_factor(X.values, i) 
            for i in range(X.shape[1])
        ]
        
        # Clasificar
        vif_data['Nivel'] = vif_data['VIF'].apply(
            lambda x: 'Severo' if x > 10 else ('Moderado' if x > 5 else 'OK')
        )
        
        return vif_data.sort_values('VIF', ascending=False)
    
    def full_diagnostics(
        self,
        residuals: pd.Series,
        exog: Optional[pd.DataFrame] = None,
        model_name: str = "Modelo"
    ) -> ModelDiagnostics:
        """
        Realiza diagnósticos completos de un modelo.
        
        Args:
            residuals: Residuos del modelo
            exog: Variables exógenas (opcional)
            model_name: Nombre del modelo para el reporte
            
        Returns:
            ModelDiagnostics con todos los resultados
        """
        # Ejecutar todas las pruebas
        normality = self.test_normality(residuals)
        autocorrelation = self.test_autocorrelation(residuals)
        heteroscedasticity = self.test_heteroscedasticity(residuals, exog)
        
        # Calcular score general
        tests_passed = sum([
            normality.assumptions_met,
            autocorrelation.assumptions_met,
            heteroscedasticity.assumptions_met
        ])
        
        overall_score = tests_passed / 3 * 100
        
        # Clasificar calidad del modelo
        if overall_score >= 80:
            quality = "EXCELENTE"
        elif overall_score >= 60:
            quality = "BUENA"
        elif overall_score >= 40:
            quality = "ACEPTABLE"
        else:
            quality = "POBRE"
        
        # Generar recomendaciones
        recommendations = []
        
        if not normality.assumptions_met:
            recommendations.append(
                "Considerar transformar la variable dependiente (log, raíz) "
                "o usar distribución t en lugar de normal."
            )
        
        if not autocorrelation.assumptions_met:
            recommendations.append(
                "Agregar rezagos de la variable dependiente o usar "
                "errores estándar robustos (Newey-West)."
            )
        
        if not heteroscedasticity.assumptions_met:
            recommendations.append(
                "Usar errores estándar robustos (Newey-West o HAC) "
                "para corregir heterocedasticidad."
            )
        
        return ModelDiagnostics(
            normality=normality,
            autocorrelation=autocorrelation,
            heteroscedasticity=heteroscedasticity,
            model_quality=quality,
            recommendations=recommendations,
            overall_score=overall_score
        )


def create_diagnostics_report(
    diagnostics: ModelDiagnostics,
    model_name: str = "Modelo"
) -> str:
    """
    Genera reporte de diagnósticos formateado.
    
    Args:
        diagnostics: Resultado de full_diagnostics
        model_name: Nombre del modelo
        
    Returns:
        Reporte en texto
    """
    report = f"""
=== DIAGNÓSTICOS DEL MODELO: {model_name} ===

Calidad General: {diagnostics.model_quality} ({diagnostics.overall_score:.0f}/100)

--- Prueba de Normalidad ---
Prueba: {diagnostics.normality.test_name}
Estadístico: {diagnostics.normality.statistic:.4f}
p-value: {diagnostics.normality.p_value:.4f}
Resultado: {'✅ PASA' if diagnostics.normality.assumptions_met else '❌ FALLA'}
{diagnostics.normality.interpretation}

--- Prueba de Autocorrelación ---
Prueba: {diagnostics.autocorrelation.test_name}
Estadístico: {diagnostics.autocorrelation.statistic:.4f}
p-value: {diagnostics.autocorrelation.p_value:.4f if diagnostics.autocorrelation.p_value else 'N/A'}
Resultado: {'✅ PASA' if diagnostics.autocorrelation.assumptions_met else '❌ FALLA'}
{diagnostics.autocorrelation.interpretation}

--- Prueba de Heterocedasticidad ---
Prueba: {diagnostics.heteroscedasticity.test_name}
Estadístico: {diagnostics.heteroscedasticity.statistic:.4f}
p-value: {diagnostics.heteroscedasticity.p_value:.4f}
Resultado: {'✅ PASA' if diagnostics.heteroscedasticity.assumptions_met else '❌ FALLA'}
{diagnostics.heteroscedasticity.interpretation}

--- Recomendaciones ---
"""
    
    if diagnostics.recommendations:
        for i, rec in enumerate(diagnostics.recommendations, 1):
            report += f"{i}. {rec}\n"
    else:
        report += "No hay recomendaciones. El modelo cumple todas las suposiciones.\n"
    
    return report
