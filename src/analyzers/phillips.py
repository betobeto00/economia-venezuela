"""
Curva de Phillips (v2 - Expandido)
====================================

Relación entre inflación y brecha del producto (o desempleo).
Permite analizar:
- ¿La inflación está impulsada por demanda o por costos?
- ¿Hay inercia inflacionaria?
- ¿Qué tan sensible es la inflación a cambios en la actividad económica?

Modelos implementados:
1. Phillips Curve básico: π = α + β·u + γ·πᵉ + ε
2. Phillips Curve con expectativas adaptativas
3. Phillips Curve híbrido (adaptativas + racionales + variables exógenas)
4. Phillips Curve no lineal (splines)
5. NAIRU estimado (tasa de desempleo natural)
6. Análisis de estanflación
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
    model_type: str = "basic"
    coefficients: Optional[dict] = None  # Coeficientes del modelo


@dataclass
class PhillipsHybridResult:
    """Resultado del Phillips Curve híbrido."""
    slope: float
    intercept: float
    r_squared: float
    persistence: float  # Inercia inflacionaria (γ)
    oil_sensitivity: float  # Sensibilidad al petróleo
    exchange_sensitivity: float  # Sensibilidad al tipo de cambio
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
        nairu = None
        if slope != 0:
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
            model_type="basic",
            coefficients={"unemployment": slope},
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
        persistence = float(model.coef_[1])

        interpretation = (
            f"Phillips Curve con expectativas: pendiente={slope:.4f}, "
            f"inercia={persistence:.4f}, R²={r_squared:.4f}. "
        )

        if abs(persistence) > 0.5:
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
            model_type="expectations",
            coefficients={"unemployment": slope, "expected_inflation": persistence},
        )

    def fit_hybrid(
        self,
        inflation: pd.Series,
        unemployment: pd.Series,
        oil_price_change: Optional[pd.Series] = None,
        exchange_rate_change: Optional[pd.Series] = None,
        expected_future: Optional[pd.Series] = None,
    ) -> Optional[PhillipsHybridResult]:
        """Phillips Curve híbrido con variables exógenas.

        Combina expectativas adaptativas y racionales (Nuevo Keynesiano).
        Incluye shocks de precios (petróleo, tipo de cambio) como variables exógenas.

        π = α + β·u + γ·πᵉ + δ·Δpetróleo + ζ·ΔTC + ε

        Args:
            inflation: Serie de inflación mensual (%).
            unemployment: Serie de desempleo (%).
            oil_price_change: Cambio mensual en precio del petróleo (%).
            exchange_rate_change: Cambio mensual en tipo de cambio (%).
            expected_future: Inflación esperada futura (si se dispone).

        Returns:
            PhillipsHybridResult o None.
        """
        from sklearn.linear_model import LinearRegression

        expected = expected_future if expected_future is not None else inflation.shift(1)
        oil = oil_price_change if oil_price_change is not None else pd.Series(0, index=inflation.index)
        exch = exchange_rate_change if exchange_rate_change is not None else pd.Series(0, index=inflation.index)

        df = pd.DataFrame({
            "inflation": inflation,
            "unemployment": unemployment,
            "expected": expected,
            "oil": oil,
            "exchange": exch,
        }).dropna()

        if len(df) < 15:
            return None

        X = df[["unemployment", "expected", "oil", "exchange"]].values
        y = df["inflation"].values

        model = LinearRegression()
        model.fit(X, y)

        slope = float(model.coef_[0])
        intercept = float(model.intercept_)
        r_squared = float(model.score(X, y))
        persistence = float(model.coef_[1])
        oil_sens = float(model.coef_[2])
        exch_sens = float(model.coef_[3])

        interpretation = (
            f"Phillips híbrido (R²={r_squared:.3f}): "
            f"desempleo={slope:.3f}, inercia={persistence:.3f}, "
            f"petróleo={oil_sens:.3f}, TC={exch_sens:.3f}. "
        )

        if abs(persistence) > 0.5:
            interpretation += "Alta persistencia inflacionaria. "
        if abs(oil_sens) > 0.1:
            interpretation += f"El petróleo tiene efecto significativo sobre la inflación. "
        if abs(exch_sens) > 0.1:
            interpretation += f"La depreciación cambiaria transmite directamente a precios. "

        return PhillipsHybridResult(
            slope=round(slope, 4),
            intercept=round(intercept, 4),
            r_squared=round(r_squared, 4),
            persistence=round(persistence, 4),
            oil_sensitivity=round(oil_sens, 4),
            exchange_sensitivity=round(exch_sens, 4),
            interpretation=interpretation,
        )

    def fit_nonlinear(
        self,
        inflation: pd.Series,
        unemployment: pd.Series,
        n_knots: int = 3,
    ) -> Optional[PhillipsResult]:
        """Phillips Curve no lineal usando splines.

        La relación puede ser convexa (Phillips no lineal).

        Args:
            inflation: Serie de inflación mensual (%).
            unemployment: Serie de desempleo (%).
            n_knots: Número de nudos del spline.

        Returns:
            PhillipsResult con R² del spline.
        """
        from sklearn.preprocessing import SplineTransformer
        from sklearn.linear_model import LinearRegression

        df = pd.DataFrame({
            "inflation": inflation,
            "unemployment": unemployment,
        }).dropna()

        if len(df) < 20:
            return None

        X = df[["unemployment"]].values
        y = df["inflation"].values

        spline = SplineTransformer(n_knots=n_knots, degree=3)
        X_spline = spline.fit_transform(X)

        model = LinearRegression()
        model.fit(X_spline, y)
        r_squared = float(model.score(X_spline, y))

        interpretation = (
            f"Phillips no lineal (splines, R²={r_squared:.3f}): "
            f"La relación entre desempleo e inflación no es constante. "
        )

        # Evaluar si la pendiente media es negativa
        X_test = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
        X_test_spline = spline.transform(X_test)
        y_pred = model.predict(X_test_spline)
        avg_slope = np.mean(np.diff(y_pred) / np.diff(X_test.flatten()))

        if avg_slope < 0:
            interpretation += f"Pendiente media negativa ({avg_slope:.3f}): trade-off existe pero es no lineal."
        else:
            interpretation += f"Pendiente media positiva: posible estanflación no lineal."

        return PhillipsResult(
            slope=round(float(avg_slope), 4),
            intercept=0.0,
            r_squared=round(r_squared, 4),
            nairu=None,
            inflation_gap=0,
            interpretation=interpretation,
            model_type="nonlinear",
        )

    def detect_stagflation(
        self,
        inflation: pd.Series,
        unemployment: pd.Series,
        inflation_threshold: float = 20.0,
        unemployment_threshold: float = 10.0,
    ) -> dict:
        """Detecta episodios de estanflación.

        Args:
            inflation: Serie de inflación mensual (%).
            unemployment: Serie de desempleo (%).
            inflation_threshold: Umbral de inflación alta (%).
            unemployment_threshold: Umbral de desempleo alto (%).

        Returns:
            Dict con análisis de estanflación.
        """
        df = pd.DataFrame({
            "inflation": inflation,
            "unemployment": unemployment,
        }).dropna()

        if len(df) == 0:
            return {"stagflation_episodes": 0, "current": False}

        high_inflation = df["inflation"] > inflation_threshold
        high_unemployment = df["unemployment"] > unemployment_threshold
        stagflation = high_inflation & high_unemployment

        episodes = int(stagflation.sum())
        current = bool(stagflation.iloc[-1]) if len(stagflation) > 0 else False

        interpretation = ""
        if current:
            interpretation = (
                f"ESTANFLACIÓN ACTUAL: Inflación ({df['inflation'].iloc[-1]:.1f}%) "
                f"y desempleo ({df['unemployment'].iloc[-1]:.1f}%) ambos elevados."
            )
        elif episodes > 0:
            interpretation = (
                f"Se detectaron {episodes} períodos de estanflación en la serie. "
                f"Actualmente no hay estanflación."
            )
        else:
            interpretation = "No se detectaron episodios de estanflación en la serie analizada."

        return {
            "stagflation_episodes": episodes,
            "current": current,
            "interpretation": interpretation,
        }
