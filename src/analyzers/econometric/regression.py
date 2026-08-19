"""
Módulo de Regresión con Errores Robustos (Newey-West)
====================================================

Modelos de regresión con corrección de:
- Heterocedasticidad
- Autocorrelación serial

Especialmente útil para series financieras venezolanas
donde estas suposiciones casi nunca se cumplen.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
import statsmodels.api as sm
from statsmodels.regression.linear_model import OLS
from statsmodels.stats.sandwich_covariance import cov_hac
from scipy import stats
import warnings

warnings.filterwarnings('ignore')


@dataclass
class RegressionResult:
    """Resultado de regresión"""
    model_name: str
    coefficients: Dict[str, float]
    std_errors: Dict[str, float]
    p_values: Dict[str, float]
    r_squared: float
    adj_r_squared: float
    f_statistic: float
    f_pvalue: float
    dw_statistic: float
    n_observations: int
    residuals: pd.Series
    predictions: pd.Series
    confidence_intervals: pd.DataFrame
    summary: str


@dataclass
class CausalityAnalysis:
    """Análisis de causalidad entre variables"""
    dependent_var: str
    independent_vars: List[str]
    significant_vars: List[str]
    elasticities: Dict[str, float]
    interpretation: str


class NeweyWestRegressor:
    """
    Regresor con errores estándar robustos de Newey-West.
    
    Corrige heterocedasticidad y autocorrelación serial
    usando la estimación HAC (Heteroscedasticity and Autocorrelation Consistent).
    
    Ejemplo para Venezuela:
        regressor = NeweyWestRegressor()
        
        # ¿La base monetaria (M2) explica la inflación?
        result = regressor.regress_inflation_m2(inflation, m2_supply)
        
        # ¿El petróleo afecta el tipo de cambio?
        result = regressor.regress_oil_dollar(oil_price, dollar_rate)
    """
    
    def __init__(self, maxlags: int = 4, significance_level: float = 0.05):
        """
        Args:
            maxlags: Número máximo de rezagos para Newey-West
            significance_level: Nivel de significancia
        """
        self.maxlags = maxlags
        self.significance_level = significance_level
    
    def newey_west_ols(
        self,
        y: pd.Series,
        X: pd.DataFrame,
        add_constant: bool = True,
        maxlags: Optional[int] = None
    ) -> RegressionResult:
        """
        Regresión OLS con errores estándar Newey-West.
        
        Args:
            y: Variable dependiente
            X: Variables independientes
            add_constant: Si agregar constante
            maxlags: Rezagos para Newey-West (None = usar self.maxlags)
            
        Returns:
            RegressionResult
        """
        if maxlags is None:
            maxlags = self.maxlags
        
        # Alinear datos
        data = pd.concat([y, X], axis=1).dropna()
        y_clean = data.iloc[:, 0]
        X_clean = data.iloc[:, 1:]
        
        # Agregar constante si se solicita
        if add_constant:
            X_clean = sm.add_constant(X_clean)
        
        # Ajustar modelo OLS
        model = OLS(y_clean, X_clean)
        results = model.fit()
        
        # Calcular errores estándar robustos Newey-West
        cov_matrix = cov_hac(results, nlags=maxlags)
        robust_se = np.sqrt(np.diag(cov_matrix))
        
        # Recalcular estadísticos t y p-values con errores robustos
        t_stats = results.params / robust_se
        p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=len(y_clean) - len(X_clean)))
        
        # Calcular intervalos de confianza robustos
        ci_lower = results.params - 1.96 * robust_se
        ci_upper = results.params + 1.96 * robust_se
        
        # Durbin-Watson
        from statsmodels.stats.stattools import durbin_watson
        dw = durbin_watson(results.resid)
        
        # Crear diccionarios de resultados
        coefficients = results.params.to_dict()
        std_errors_dict = dict(zip(X_clean.columns, robust_se))
        p_values_dict = dict(zip(X_clean.columns, p_values))
        
        # Confidence intervals DataFrame
        ci_df = pd.DataFrame({
            'lower': ci_lower,
            'upper': ci_upper
        }, index=X_clean.columns)
        
        return RegressionResult(
            model_name="Newey-West OLS",
            coefficients=coefficients,
            std_errors=std_errors_dict,
            p_values=p_values_dict,
            r_squared=results.rsquared,
            adj_r_squared=results.rsquared_adj,
            f_statistic=results.fvalue,
            f_pvalue=results.f_pvalue,
            dw_statistic=dw,
            n_observations=len(y_clean),
            residuals=results.resid,
            predictions=results.fittedvalues,
            confidence_intervals=ci_df,
            summary=results.summary().as_text()
        )
    
    def regress_inflation_m2(
        self,
        inflation: pd.Series,
        m2_supply: pd.Series,
        oil_price: Optional[pd.Series] = None,
        exchange_rate: Optional[pd.Series] = None
    ) -> Dict:
        """
        Regresión de inflación sobre base monetaria y otros factores.
        
        Modelo: Inflación = β0 + β1*M2 + β2*Petroleo + β3*TipoCambio + ε
        
        Args:
            inflation: Serie de inflación mensual
            m2_supply: Serie de masa monetaria M2
            oil_price: Precio del petróleo (opcional)
            exchange_rate: Tipo de cambio (opcional)
            
        Returns:
            Diccionario con resultados y análisis de causalidad
        """
        # Preparar datos
        data = pd.DataFrame({
            'inflation': inflation,
            'm2': m2_supply
        })
        
        if oil_price is not None:
            data['oil'] = oil_price
        if exchange_rate is not None:
            data['exchange_rate'] = exchange_rate
        
        data = data.dropna()
        
        # Variables
        y = data['inflation']
        X = data.drop('inflation', axis=1)
        
        # Regresión
        result = self.newey_west_ols(y, X)
        
        # Análisis de causalidad
        causal_analysis = self._analyze_causal_relationships(
            result, "inflation", X.columns.tolist()
        )
        
        # Interpretación para Venezuela
        interpretation = self._interpret_inflation_model(result, causal_analysis)
        
        return {
            'regression': result,
            'causal_analysis': causal_analysis,
            'interpretation': interpretation,
            'economic_meaning': self._get_economic_meaning_inflation(result)
        }
    
    def regress_oil_dollar(
        self,
        oil_price: pd.Series,
        dollar_rate: pd.Series,
        controls: Optional[pd.DataFrame] = None
    ) -> Dict:
        """
        Regresión del tipo de cambio sobre precio del petróleo.
        
        Modelo: TipoCambio = β0 + β1*Petroleo + controles + ε
        
        Para Venezuela, el petróleo es el principal motor económico,
        por lo que esta relación es fundamental.
        """
        data = pd.DataFrame({
            'dollar': dollar_rate,
            'oil': oil_price
        })
        
        if controls is not None:
            data = pd.concat([data, controls], axis=1)
        
        data = data.dropna()
        
        y = data['dollar']
        X = data.drop('dollar', axis=1)
        
        result = self.newey_west_ols(y, X)
        
        # Interpretación
        interpretation = self._interpret_oil_dollar_model(result)
        
        return {
            'regression': result,
            'interpretation': interpretation,
            'elasticity': self._calculate_oil_elasticity(result)
        }
    
    def regress_wage_inflation(
        self,
        wages: pd.Series,
        inflation: pd.Series,
        productivity: Optional[pd.Series] = None
    ) -> Dict:
        """
        Regresión de salarios sobre inflación.
        
        Analiza la indexación salarial y pérdida de poder adquisitivo.
        
        Modelo: Salarios = β0 + β1*Inflación + β2*Productividad + ε
        """
        data = pd.DataFrame({
            'wages': wages,
            'inflation': inflation
        })
        
        if productivity is not None:
            data['productivity'] = productivity
        
        data = data.dropna()
        
        y = data['wages']
        X = data.drop('wages', axis=1)
        
        result = self.newey_west_ols(y, X)
        
        # Calcular poder adquisitivo real
        if 'inflation' in result.coefficients:
            beta_inflation = result.coefficients['inflation']
            purchasing_power_loss = 1 - beta_inflation
            
            interpretation = (
                f"Por cada 1% de inflación, los salarios aumentan "
                f"{beta_inflation*100:.1f}%. "
            )
            
            if beta_inflation < 1:
                interpretation += (
                    f"Los salarios NO compensan completamente la inflación. "
                    f"Pérdida de poder adquisitivo: {purchasing_power_loss*100:.1f}%."
                )
            else:
                interpretation += (
                    f"Los salarios compensan la inflación con un aumento adicional "
                    f"de {(beta_inflation-1)*100:.1f}%."
                )
        else:
            interpretation = "No se pudo calcular la elasticidad salarial."
        
        return {
            'regression': result,
            'interpretation': interpretation,
            'purchasing_power_impact': purchasing_power_loss if 'inflation' in result.coefficients else None
        }
    
    def _analyze_causal_relationships(
        self,
        result: RegressionResult,
        dep_var: str,
        indep_vars: List[str]
    ) -> CausalityAnalysis:
        """Analiza relaciones causales basado en significancia estadística"""
        significant_vars = [
            var for var, pval in result.p_values.items()
            if pval < self.significance_level and var != 'const'
        ]
        
        # Calcular elasticidades
        elasticities = {}
        for var in indep_vars:
            if var in result.coefficients:
                # Asumiendo variables en log o interpretación lineal
                elasticities[var] = result.coefficients[var]
        
        # Interpretación
        if significant_vars:
            interpretation = (
                f"Variables significativas que explican {dep_var}: "
                f"{', '.join(significant_vars)}. "
            )
        else:
            interpretation = (
                f"No hay variables estadísticamente significativas "
                f"que expliquen {dep_var}."
            )
        
        return CausalityAnalysis(
            dependent_var=dep_var,
            independent_vars=indep_vars,
            significant_vars=significant_vars,
            elasticities=elasticities,
            interpretation=interpretation
        )
    
    def _interpret_inflation_model(
        self,
        result: RegressionResult,
        causal: CausalityAnalysis
    ) -> str:
        """Interpreta el modelo de inflación para Venezuela"""
        interpretation = "=== Interpretación del Modelo de Inflación ===\n\n"
        
        # R-cuadrado
        interpretation += f"R-cuadrado: {result.r_squared:.4f} "
        interpretation += f"({result.r_squared*100:.1f}% de la variación explicada)\n"
        
        # Coeficientes significativos
        for var, coef in result.coefficients.items():
            if var == 'const':
                continue
            pval = result.p_values.get(var, 1)
            significance = "***" if pval < 0.01 else ("**" if pval < 0.05 else ("*" if pval < 0.1 else ""))
            
            interpretation += f"\n{var}:\n"
            interpretation += f"  Coeficiente: {coef:.4f} {significance}\n"
            interpretation += f"  p-value: {pval:.4f}\n"
            
            # Interpretación económica
            if 'm2' in var.lower():
                if coef > 0:
                    interpretation += (
                        f"  Interpretación: Un aumento del 1% en M2 se asocia con "
                        f"un aumento de {coef:.2f}% en inflación.\n"
                    )
                else:
                    interpretation += (
                        f"  Interpretación: Relación inversa inusual. "
                        f"Revisar especificación del modelo.\n"
                    )
        
        return interpretation
    
    def _interpret_oil_dollar_model(self, result: RegressionResult) -> str:
        """Interpreta el modelo petróleo-tipo de cambio"""
        interpretation = "=== Interpretación: Petróleo vs Tipo de Cambio ===\n\n"
        
        if 'oil' in result.coefficients:
            coef = result.coefficients['oil']
            pval = result.p_values.get('oil', 1)
            
            interpretation += f"Coeficiente del petróleo: {coef:.4f}\n"
            interpretation += f"p-value: {pval:.4f}\n"
            
            if pval < self.significance_level:
                if coef < 0:
                    interpretation += (
                        "Relación negativa significativa: Aumento del precio del petróleo "
                        "tiende a apreciar el bolívar (reducir tipo de cambio).\n"
                        "Esto es consistente con la economía petrolera de Venezuela."
                    )
                else:
                    interpretation += (
                        "Relación positiva inusual. Posible endogeneidad o "
                        "factores omitidos importantes."
                    )
            else:
                interpretation += "Relación no estadísticamente significativa."
        
        return interpretation
    
    def _get_economic_meaning_inflation(self, result: RegressionResult) -> Dict:
        """Obtiene significado económico del modelo de inflación"""
        meanings = {}
        
        for var, coef in result.coefficients.items():
            if var == 'const':
                meanings['intercept'] = (
                    "Tendencia base de inflación no explicada por las variables del modelo"
                )
            elif 'm2' in var.lower():
                meanings[var] = (
                    "Elasticidad inflación-M2: Cuánto cambia la inflación por cada "
                    "unidad de cambio en la base monetaria"
                )
            elif 'oil' in var.lower():
                meanings[var] = (
                    "Efecto del petróleo sobre inflación a través de "
                    "ingresos y gasto público"
                )
            elif 'exchange' in var.lower():
                meanings[var] = (
                    "Efecto de passthrough cambiario: Trasmisión de cambios "
                    "en tipo de cambio a precios internos"
                )
        
        return meanings
    
    def _calculate_oil_elasticity(self, result: RegressionResult) -> float:
        """Calcula elasticidad del tipo de cambio respecto al petróleo"""
        if 'oil' in result.coefficients:
            return result.coefficients['oil']
        return 0.0


class MultipleRegressionAnalyzer:
    """
    Analizador de regresión múltiple para modelos complejos.
    """
    
    def __init__(self, maxlags: int = 4):
        self.maxlags = maxlags
        self.regressor = NeweyWestRegressor(maxlags=maxlags)
    
    def panel_regression(
        self,
        data: pd.DataFrame,
        dependent_var: str,
        independent_vars: List[str],
        group_var: Optional[str] = None
    ) -> Dict:
        """
        Regresión de panel de datos.
        
        Útil para comparar múltiples mercados o regiones.
        """
        # Por ahora, regresión pooled OLS con errores robustos
        y = data[dependent_var]
        X = data[independent_vars]
        
        result = self.regressor.newey_west_ols(y, X)
        
        return {
            'regression': result,
            'n_groups': data[group_var].nunique() if group_var else 1,
            'interpretation': f"Regresión panel: {dependent_var} sobre {independent_vars}"
        }
    
    def difference_in_differences(
        self,
        data: pd.DataFrame,
        outcome_var: str,
        treatment_var: str,
        time_var: str,
        post_var: str
    ) -> Dict:
        """
        Difference-in-Differences (DID).
        
        Útil para evaluar impacto de políticas económicas.
        """
        # Crear interacción treatment x post
        data = data.copy()
        data['did'] = data[treatment_var] * data[post_var]
        
        y = data[outcome_var]
        X = data[[treatment_var, post_var, 'did']]
        
        result = self.regressor.newey_west_ols(y, X)
        
        # El coeficiente de 'did' es el estimador DID
        did_effect = result.coefficients.get('did', 0)
        did_pvalue = result.p_values.get('did', 1)
        
        interpretation = (
            f"Efecto DID: {did_effect:.4f} "
            f"(p-value={did_pvalue:.4f}). "
        )
        
        if did_pvalue < 0.05:
            interpretation += (
                f"El tratamiento tuvo un efecto estadísticamente significativo "
                f"de {did_effect:.2f} unidades."
            )
        else:
            interpretation += (
                f"No hay evidencia de efecto del tratamiento."
            )
        
        return {
            'regression': result,
            'did_effect': did_effect,
            'did_pvalue': did_pvalue,
            'interpretation': interpretation
        }


def create_regression_report(
    result: RegressionResult,
    model_name: str = "Modelo"
) -> str:
    """
    Genera reporte de regresión formateado.
    """
    report = f"""
=== REPORTE DE REGRESIÓN: {model_name} ===

Método: {result.model_name}
Observaciones: {result.n_observations}
R-cuadrado: {result.r_squared:.4f}
R-cuadrado ajustado: {result.adj_r_squared:.4f}
F-statistic: {result.f_statistic:.4f} (p-value={result.f_pvalue:.4f})
Durbin-Watson: {result.dw_statistic:.4f}

--- Coeficientes (con errores robustos Newey-West) ---

"""
    
    for var in result.coefficients:
        coef = result.coefficients[var]
        se = result.std_errors.get(var, 0)
        pval = result.p_values.get(var, 1)
        
        # Significancia
        if pval < 0.01:
            sig = "***"
        elif pval < 0.05:
            sig = "**"
        elif pval < 0.1:
            sig = "*"
        else:
            sig = ""
        
        report += f"{var:20s} {coef:10.4f} ({se:10.4f}) {sig}  p={pval:.4f}\n"
    
    report += f"""
--- Interpretación ---
"""
    
    # Agregar interpretación básica
    significant_vars = [
        var for var, pval in result.p_values.items()
        if pval < 0.05 and var != 'const'
    ]
    
    if significant_vars:
        report += f"Variables significativas: {', '.join(significant_vars)}\n"
    else:
        report += "No hay variables estadísticamente significativas al nivel del 5%.\n"
    
    return report
