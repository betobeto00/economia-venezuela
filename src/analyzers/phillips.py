"""
Curva de Phillips
==================

Relación entre inflación y brecha del producto (o desempleo).
Permite analizar:
- ¿La inflación está impulsada por demanda o por costos?
- ¿Hay inercia inflacionaria?
- ¿Qué tan sensible es la inflación a cambios en la actividad económica?

Modelos implementados:
1. Phillips Curve básico: π = α + β·u + γ·πᵉ + ε
2. Phillips Curve con expectativas adaptativas
3. NAIRU estimado (tasa de desempleo natural)
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PhillipsResult:
    """Resultado del análisis de Phillips Curve."""
    slope: float  # Pendiente de la curva (negativa = trade-off)
    intercept: float
    r_squared: float
    nairu: Optional[float]  # NAIRU estimado
    inflation_gap: float  # Diferencia inflación actual vs NAIRU
    interpretation: str


class PhillipsCurveAnalyzer:
    """Analizador de Curva de Phillips para Venezuela."""

    def __init__(self):
        self.model = None

    def fit_basic(
        self,
        inflation: pd.Series,
        unemployment: pd.Series,
    ) -> Optional[PhillipsResult]:
        """Ajusta una Phillips Curve básica.

        π = α + β·u + ε

        Args:
            inflation: Serie de inflación mensual (%).
            unemployment: Serie de desempleo (%).

        Returns:
            PhillipsResult o None si no hay datos suficientes.
        """
        from sklearn.linear_model import LinearRegression

        # Combinar y limpiar
        df = pd.DataFrame({
            "inflation": inflation,
            "unemployment": unemployment,
        }).dropna()

        if len(df) < 10:
            logger.warning("Datos insuficientes para Phillips Curve: %d", len(df))
            return None

        X = df[["unemployment"]].values
        y = df["inflation"].values

        model = LinearRegression()
        model.fit(X, y)

        slope = float(model.coef_[0])
        intercept = float(model.intercept_)
        r_squared = float(model.score(X, y))

        # NAIRU: desempleo donde la inflación es estable (π = πᵉ)
        # En el modelo simplificado: NAIRU = -intercept / slope (si slope != 0)
        nairu = None
        if slope != 0:
            # NAIRU cuando la inflación es igual a su promedio histórico
            avg_inflation = float(df["inflation"].mean())
            nairu = (avg_inflation - intercept) / slope

        inflation_gap = None
        if nairu is not None:
            current_unemployment = float(df["unemployment"].iloc[-1])
            inflation_gap = current_unemployment - nairu

        # Interpretación
        interpretation = ""
        if slope < 0:
            interpretation = (
                f"Trade-off clásico: cada punto extra de desempleo reduce "
                f"la inflación en {abs(slope):.2f} puntos. "
            )
        else:
            interpretation = (
                f"Relación positiva inusual: el desempleo y la inflación "
                f"se mueven en la misma dirección (posible estanflación). "
            )

        if nairu is not None:
            interpretation += f"NAIRU estimado: {nairu:.1f}%."
            if inflation_gap > 2:
                interpretation += " La economía opera por debajo del pleno empleo."
            elif inflation_gap < -2:
                interpretation += " La economía opera sobre el pleno empleo (sobrecalentamiento)."

        return PhillipsResult(
            slope=round(slope, 4),
            intercept=round(intercept, 4),
            r_squared=round(r_squared, 4),
            nairu=round(nairu, 1) if nairu is not None else None,
            inflation_gap=round(inflation_gap, 1) if inflation_gap is not None else 0,
            interpretation=interpretation,
        )

    def fit_with_expectations(
        self,
        inflation: pd.Series,
        unemployment: pd.Series,
        expected_inflation: Optional[pd.Series] = None,
    ) -> Optional[PhillipsResult]:
        """Phillips Curve con expectativas de inflación.

        π = α + β·u + γ·πᵉ + ε

        Si no se prove πᵉ, se usa inflación rezagada como proxy.
        """
        from sklearn.linear_model import LinearRegression

        if expected_inflation is None:
            expected_inflation = inflation.shift(1)  # Expectativas adaptativas

        df = pd.DataFrame({
            "inflation": inflation,
            "unemployment": unemployment,
            "expected_inflation": expected_inflation,
        }).dropna()

        if len(df) < 10:
            return None

        X = df[["unemployment", "expected_inflation"]].values
        y = df["inflation"].values

        model = LinearRegression()
        model.fit(X, y)

        slope = float(model.coef_[0])
        intercept = float(model.intercept_)
        r_squared = float(model.score(X, y))

        interpretation = (
            f"Phillips Curve con expectativas: pendiente={slope:.4f}, "
            f"inercia={model.coef_[1]:.4f}, R²={r_squared:.4f}. "
        )

        if abs(model.coef_[1]) > 0.5:
            interpretation += "Alta inercia inflacionaria: las expectativas pasadas dominan."
        else:
            interpretation += "Baja inercia: la inflación responde rápido a cambios de actividad."

        return PhillipsResult(
            slope=round(slope, 4),
            intercept=round(intercept, 4),
            r_squared=round(r_squared, 4),
            nairu=None,
            inflation_gap=0,
            interpretation=interpretation,
        )
