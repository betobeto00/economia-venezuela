"""
Índice de Riesgo Soberano (v2 - Expandido)
============================================

Índice compuesto de riesgo económico para Venezuela, calculado
a partir de múltiples indicadores:

1. Brecha cambiaria (proxy de presión cambiaria)
2. Volatilidad del tipo de cambio (GARCH)
3. Nivel de inflación (estabilidad de precios) - con saturación logarítmica
4. Cobertura de reservas (solvencia externa)
5. Deuda/PIB (sostenibilidad fiscal)
6. Producción petrolera (ingresos)
7. Riesgo político
8. Índice de incertidumbre
9. Capitalización del mercado bursátil BVC (nuevo)

Funcionalidades adicionales:
- Ponderaciones dinámicas vía PCA
- Tracking de momentum (cambio vs mes anterior)
- Análisis de tendencia
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RiskResult:
    """Resultado del cálculo de riesgo soberano."""
    score: float  # 0-100
    level: str  # "bajo", "medio", "alto", "extremo"
    components: Dict[str, float]  # Desglose por factor
    weights: Dict[str, float]  # Ponderaciones usadas
    interpretation: str
    momentum: Optional[float] = None  # Cambio vs período anterior
    dominant_factor: Optional[str] = None


class SovereignRiskIndex:
    """Índice de Riesgo Soberano de Venezuela."""

    def __init__(self):
        # Ponderaciones por defecto (se pueden hacer dinámicas)
        self.default_weights = {
            "spread": 0.18,
            "volatility": 0.10,
            "inflation": 0.18,
            "reserves": 0.10,
            "debt": 0.10,
            "oil": 0.07,
            "political": 0.08,
            "uncertainty": 0.07,
            "market_cap": 0.12,
        }
        self.weights = dict(self.default_weights)
        self._previous_score: Optional[float] = None

    def update_weights_pca(
        self,
        historical_components: List[Dict[str, float]],
    ) -> Dict[str, float]:
        """Actualiza ponderaciones usando análisis de componentes principales.

        Args:
            historical_components: Lista de dicts con valores de componentes históricos.

        Returns:
            Nuevas ponderaciones calculadas.
        """
        if len(historical_components) < 5:
            return self.weights

        try:
            import pandas as pd
            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler

            df = pd.DataFrame(historical_components)
            required_cols = set(self.default_weights.keys())
            available_cols = [c for c in df.columns if c in required_cols]

            if len(available_cols) < 3:
                return self.weights

            scaler = StandardScaler()
            X = scaler.fit_transform(df[available_cols])

            pca = PCA(n_components=min(3, len(available_cols)))
            pca.fit(X)

            # Ponderaciones = varianza explicada por componente × loadings
            loadings = np.abs(pca.components_)  # shape: (n_components, n_features)
            variance_weights = pca.explained_variance_ratio_

            # Combinar: cada variable recibe la suma de loadings ponderados
            combined = np.zeros(len(available_cols))
            for i, var_w in enumerate(variance_weights):
                combined += var_w * loadings[i]

            # Normalizar a que sumen 1
            total = combined.sum()
            if total > 0:
                combined = combined / total

            # Asignar
            new_weights = {}
            for i, col in enumerate(available_cols):
                new_weights[col] = float(combined[i])

            # Mantener pesos de variables no disponibles
            for col in required_cols:
                if col not in new_weights:
                    new_weights[col] = self.default_weights.get(col, 0.1)

            # Renormalizar
            w_sum = sum(new_weights.values())
            if w_sum > 0:
                new_weights = {k: v / w_sum for k, v in new_weights.items()}

            self.weights = new_weights
            logger.info("Ponderaciones PCA actualizadas: %s", new_weights)
            return new_weights

        except Exception as exc:
            logger.warning("PCA falló, usando ponderaciones por defecto: %s", exc)
            return self.weights

    def _score_spread(self, spread_pct: float) -> float:
        """Score de riesgo por brecha cambiaria (0-100)."""
        return min(100, spread_pct)

    def _score_volatility(self, volatility: float) -> float:
        """Score de riesgo por volatilidad (0-100)."""
        return min(100, volatility * 100)

    def _score_inflation(self, annual_inflation: float) -> float:
        """Score de riesgo por inflación (0-100) con saturación logarítmica.

        En hiperinflación (>= 1,000% anual), la función se satura suavemente.
        """
        if annual_inflation is None:
            annual_inflation = 0
        if annual_inflation < 0:
            return 0
        elif annual_inflation < 10:
            return annual_inflation
        elif annual_inflation < 100:
            return 30 + (annual_inflation - 10) * 0.7
        elif annual_inflation < 1000:
            return 80 + np.log(annual_inflation / 100) * 10
        else:
            # Saturación suave en hiperinflación
            return min(100, 90 + np.log10(annual_inflation / 1000) * 5)

    def _score_reserves(self, months_coverage: float) -> float:
        """Score de riesgo por cobertura de reservas (0-100)."""
        if months_coverage >= 12:
            return 10
        elif months_coverage >= 6:
            return 30
        elif months_coverage >= 3:
            return 60
        else:
            return min(100, 70 + (3 - months_coverage) * 10)

    def _score_debt(self, debt_gdp_pct: float) -> float:
        """Score de riesgo por deuda/PIB (0-100)."""
        if debt_gdp_pct < 50:
            return debt_gdp_pct * 0.4
        elif debt_gdp_pct < 100:
            return 20 + (debt_gdp_pct - 50) * 0.6
        elif debt_gdp_pct < 300:
            return 50 + (debt_gdp_pct - 100) * 0.15
        else:
            return min(100, 80 + (debt_gdp_pct - 300) * 0.05)

    def _score_oil(self, production_mbd: float, baseline: float = 1.5) -> float:
        """Score de riesgo por producción petrolera (0-100)."""
        if production_mbd >= baseline:
            return 10
        ratio = production_mbd / baseline
        return min(100, (1 - ratio) * 100)

    def _score_market_cap(
        self,
        market_cap_bs: float = 0.0,
        market_cap_change_pct: float = 0.0,
        months_available: int = 0,
    ) -> float:
        """Score de riesgo por capitalización del mercado bursátil (0-100).

        Una capitalización baja y en declive indica desconfianza del mercado.
        Una capitalización creciente indica estabilidad y confianza.

        Args:
            market_cap_bs: Capitalización total en Bs. (o equivalente).
            market_cap_change_pct: Cambio mensual de capitalización (%).
            months_available: Meses de datos disponibles (para confianza).

        Returns:
            Score de riesgo (0=bajo, 100=extremo).
        """
        if market_cap_bs <= 0 or months_available < 2:
            # Sin datos suficientes → riesgo neutro
            return 50.0

        # Base: capitalización baja = mayor riesgo
        # Normalizar contra un umbral (ej. 100B Bs. como "sano")
        cap_score = max(0, 100 - (market_cap_bs / 1e9) * 2)  # Ajustar escala
        cap_score = min(100, max(0, cap_score))

        # Tendencia: caída fuerte = mayor riesgo
        trend_score = 50.0  # Neutro
        if market_cap_change_pct < -20:
            trend_score = 90  # Caída fuerte
        elif market_cap_change_pct < -10:
            trend_score = 75
        elif market_cap_change_pct < -5:
            trend_score = 60
        elif market_cap_change_pct > 10:
            trend_score = 20  # Subida fuerte = bajo riesgo
        elif market_cap_change_pct > 5:
            trend_score = 30
        elif market_cap_change_pct > 0:
            trend_score = 40

        # Combinar: 60% tendencia, 40% nivel
        return trend_score * 0.6 + cap_score * 0.4

    def _score_political(
        self,
        sanctions_level: int = 0,
        social_unrest: int = 0,
        governance_score: int = 50,
    ) -> float:
        """Score de riesgo político (0-100).

        Args:
            sanctions_level: Nivel de sanciones (0-100, 0=ninguna, 100=máximas).
            social_unrest: Tensión social (0-100, 0=estable, 100=conflicto).
            governance_score: Calidad de gobernanza (0-100, 0=peor, 100=mejor).

        Returns:
            Score de riesgo político (0-100).
        """
        # Invertir governance: mejor gobernanza = menor riesgo
        governance_risk = 100 - governance_score
        return min(100, sanctions_level * 0.4 + social_unrest * 0.3 + governance_risk * 0.3)

    def _score_uncertainty(
        self,
        sentiment_volatility: float = 0.0,
        survey_dispersion: float = 0.0,
        forecast_error: float = 0.0,
    ) -> float:
        """Score de incertidumbre (0-100).

        Basado en volatilidad del sentimiento, dispersión de encuestas,
        y error de pronóstico de modelos.

        Args:
            sentiment_volatility: Volatilidad del sentimiento (0-1).
            survey_dispersion: Dispersión de respuestas de encuestas (0-100).
            forecast_error: Error de pronóstico promedio (%).

        Returns:
            Score de incertidumbre (0-100).
        """
        sent_score = min(100, sentiment_volatility * 200)
        survey_score = min(100, survey_dispersion)
        forecast_score = min(100, forecast_error * 2)
        return (sent_score * 0.3 + survey_score * 0.3 + forecast_score * 0.4)

    def calculate(
        self,
        spread_pct: float = 0,
        volatility: float = 0,
        annual_inflation: float = 0,
        reserves_months: float = 12,
        debt_gdp_pct: float = 0,
        oil_production_mbd: float = 1.5,
        sanctions_level: int = 0,
        social_unrest: int = 0,
        governance_score: int = 50,
        sentiment_volatility: float = 0.0,
        survey_dispersion: float = 0.0,
        forecast_error: float = 0.0,
        market_cap_bs: float = 0.0,
        market_cap_change_pct: float = 0.0,
        market_cap_months: int = 0,
    ) -> RiskResult:
        """Calcula el índice de riesgo soberano.

        Args:
            spread_pct: Brecha cambiaria (%).
            volatility: Volatilidad anualizada del tipo de cambio.
            annual_inflation: Inflación anual (%).
            reserves_months: Meses de cobertura de reservas.
            debt_gdp_pct: Deuda como % del PIB.
            oil_production_mbd: Producción petrolera (mbd).
            sanctions_level: Nivel de sanciones (0-100).
            social_unrest: Tensión social (0-100).
            governance_score: Calidad de gobernanza (0-100).
            sentiment_volatility: Volatilidad del sentimiento (0-1).
            survey_dispersion: Dispersión de encuestas (0-100).
            forecast_error: Error de pronóstico (%).
            market_cap_bs: Capitalización total del mercado BVC en Bs.
            market_cap_change_pct: Cambio mensual de capitalización (%).
            market_cap_months: Meses de datos de capitalización disponibles.

        Returns:
            RiskResult con el índice y desglose.
        """
        components = {
            "spread": self._score_spread(spread_pct),
            "volatility": self._score_volatility(volatility),
            "inflation": self._score_inflation(annual_inflation),
            "reserves": self._score_reserves(reserves_months),
            "debt": self._score_debt(debt_gdp_pct),
            "oil": self._score_oil(oil_production_mbd),
            "political": self._score_political(sanctions_level, social_unrest, governance_score),
            "uncertainty": self._score_uncertainty(sentiment_volatility, survey_dispersion, forecast_error),
            "market_cap": self._score_market_cap(market_cap_bs, market_cap_change_pct, market_cap_months),
        }

        # Score compuesto (promedio ponderado)
        score = sum(
            components[k] * self.weights.get(k, 0.1)
            for k in components
        )
        score = round(min(100, max(0, score)), 1)

        # Nivel de riesgo
        if score < 25:
            level = "bajo"
        elif score < 50:
            level = "medio"
        elif score < 75:
            level = "alto"
        else:
            level = "extremo"

        # Momentum
        momentum = None
        if self._previous_score is not None:
            momentum = round(score - self._previous_score, 1)
        self._previous_score = score

        # Factor dominante
        sorted_components = sorted(components.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_components[0][0] if sorted_components else None

        # Interpretación
        interpretation = f"Riesgo soberano: {level.upper()} ({score}/100). "

        risk_labels = {
            "spread": "brecha cambiaria",
            "volatility": "volatilidad cambiaria",
            "inflation": "inflación",
            "reserves": "bajas reservas",
            "debt": "deuda elevada",
            "oil": "baja producción petrolera",
            "political": "riesgo político",
            "uncertainty": "incertidumbre macroeconómica",
            "market_cap": "debilidad del mercado bursátil",
        }

        top_risks = [k for k, v in sorted_components if v > 50]
        if top_risks:
            risks_text = ", ".join(risk_labels.get(k, k) for k in top_risks[:3])
            interpretation += f"Principales factores de riesgo: {risks_text}."

        if momentum is not None:
            if momentum > 5:
                interpretation += f" El riesgo AUMENTÓ {momentum:.1f} puntos vs período anterior."
            elif momentum < -5:
                interpretation += f" El riesgo DISMINUYÓ {abs(momentum):.1f} puntos vs período anterior."
            else:
                interpretation += f" El riesgo se mantuvo estable ({momentum:+.1f} puntos)."

        return RiskResult(
            score=score,
            level=level,
            components=components,
            weights=dict(self.weights),
            interpretation=interpretation,
            momentum=momentum,
            dominant_factor=dominant,
        )
