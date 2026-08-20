"""
SVAR - Modelo Estructural de Vectores Autorregresivos
======================================================

Identifica shocks estructurales y sus efectos dinámicos sobre
variables macroeconómicas. Permite responder preguntas como:
- ¿Cuál es el efecto de un shock al precio del petróleo sobre la inflación?
- ¿Cómo afecta una devaluación a la actividad económica?
- ¿Cuánto tarda un shock monetario en transmitirse a precios?

Implementación simplificada usando VAR reducido + descomposición de
varianza de error (FEVD) e impulsos respuesta (IRF).
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ShockResult:
    """Resultado de un shock estructural."""
    variable: str
    shock_source: str
    impulse_responses: List[float]  # IRF en cada período
    variance_decomposition: Dict[str, float]  # % de varianza explicada
    periods: int
    cumulative_effect: float


class SVARAnalyzer:
    """Analizador SVAR para shocks estructurales."""

    def __init__(self, max_lags: int = 4):
        self.max_lags = max_lags
        self.model = None
        self.var_names = []
        self.fitted = False

    def fit(self, data: pd.DataFrame, var_names: Optional[List[str]] = None) -> dict:
        """Ajusta un modelo VAR a los datos.

        Args:
            data: DataFrame con las variables endógenas (columnas = variables, filas = tiempo).
            var_names: Nombres de las variables.

        Returns:
            Dict con información del ajuste.
        """
        from statsmodels.tsa.api import VAR

        self.var_names = var_names or list(data.columns)

        # Limpiar datos
        clean_data = data.dropna()
        if len(clean_data) < self.max_lags + 5:
            logger.warning("Datos insuficientes para SVAR: %d observaciones", len(clean_data))
            return {"error": "datos_insuficientes"}

        # Seleccionar orden óptimo
        model = VAR(clean_data)
        try:
            lag_order = model.select_order(maxlags=min(self.max_lags, len(clean_data) // 3))
            optimal_lags = lag_order.aic
            if optimal_lags is None or optimal_lags < 1:
                optimal_lags = 1
        except Exception:
            optimal_lags = 1

        # Ajustar modelo VAR
        self.model = model.fit(optimal_lags)
        self.fitted = True

        return {
            "variables": self.var_names,
            "optimal_lags": optimal_lags,
            "n_obs": len(clean_data),
            "aic": self.model.aic,
            "bic": self.model.bic,
        }

    def impulse_response(
        self,
        shock_variable: str,
        response_variable: str,
        periods: int = 10,
    ) -> Optional[List[float]]:
        """Calcula la función de impulso respuesta (IRF).

        Args:
            shock_variable: Variable que recibe el shock.
            response_variable: Variable que responde.
            periods: Número de períodos a proyectar.

        Returns:
            Lista de respuestas en cada período, o None si falla.
        """
        if not self.fitted:
            return None

        try:
            irf = self.model.irf(periods)

            # Obtener índice de las variables
            shock_idx = self.var_names.index(shock_variable)
            response_idx = self.var_names.index(response_variable)

            # IRF: efecto de shock en variable shock_idx sobre variable response_idx
            irf_values = irf.irfs[:, response_idx, shock_idx]
            return [float(v) for v in irf_values]
        except Exception as exc:
            logger.warning("IRF falló: %s", exc)
            return None

    def forecast_error_variance_decomposition(
        self,
        variable: str,
        periods: int = 10,
    ) -> Optional[Dict[str, float]]:
        """Descomposición de varianza del error de predicción.

        Muestra qué porcentaje de la varianza de cada variable
        es explicada por shocks de cada una de las variables del sistema.

        Args:
            variable: Variable a analizar.
            periods: Horizonte de predicción.

        Returns:
            Dict variable → % de varianza explicada.
        """
        if not self.fitted:
            return None

        try:
            fevd = self.model.fevd(periods)

            # Obtener índice de la variable
            var_idx = self.var_names.index(variable)

            # FEVD: último período
            decomp = fevd.decomp[var_idx][-1]

            result = {}
            for i, name in enumerate(self.var_names):
                result[name] = round(float(decomp[i]) * 100, 2)

            return result
        except Exception as exc:
            logger.warning("FEVD falló: %s", exc)
            return None

    def analyze_shock(
        self,
        shock_variable: str,
        response_variable: str,
        periods: int = 10,
    ) -> Optional[ShockResult]:
        """Análisis completo de un shock estructural.

        Args:
            shock_variable: Variable que recibe el shock.
            response_variable: Variable que responde.
            periods: Horizonte de análisis.

        Returns:
            ShockResult con IRF y FEVD.
        """
        irf = self.impulse_response(shock_variable, response_variable, periods)
        if irf is None:
            return None

        fevd = self.forecast_error_variance_decomposition(response_variable, periods)
        if fevd is None:
            fevd = {}

        cumulative = sum(irf[1:])  # Efecto acumulado (excluyendo período 0)

        return ShockResult(
            variable=response_variable,
            shock_source=shock_variable,
            impulse_responses=irf,
            variance_decomposition=fevd,
            periods=periods,
            cumulative_effect=round(cumulative, 4),
        )

    def summary(self) -> Optional[dict]:
        """Resumen del modelo ajustado."""
        if not self.fitted:
            return None

        return {
            "variables": self.var_names,
            "lags": self.model.k_ar,
            "n_obs": self.model.nobs,
            "aic": round(self.model.aic, 4),
            "bic": round(self.model.bic, 4),
        }
