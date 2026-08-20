"""
Índice de Riesgo Soberano
==========================

Índice compuesto de riesgo económico para Venezuela, calculado
a partir de múltiples indicadores:

1. Brecha cambiaria (proxy de presión cambiaria)
2. Volatilidad del tipo de cambio (GARCH)
3. Nivel de inflación (estabilidad de precios)
4. Cobertura de reservas (solvencia externa)
5. Deuda/PIB (sostenibilidad fiscal)
6. Producción petrolera (ingresos)

El índice va de 0 (riesgo bajo) a 100 (riesgo extremo).
"""

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class RiskResult:
    """Resultado del cálculo de riesgo soberano."""
    score: float  # 0-100
    level: str  # "bajo", "medio", "alto", "extremo"
    components: dict  # Desglose por factor
    interpretation: str


class SovereignRiskIndex:
    """Índice de Riesgo Soberano de Venezuela."""

    def __init__(self):
        self.weights = {
            "spread": 0.25,
            "volatility": 0.15,
            "inflation": 0.25,
            "reserves": 0.15,
            "debt": 0.10,
            "oil": 0.10,
        }

    def _score_spread(self, spread_pct: float) -> float:
        """Score de riesgo por brecha cambiaria (0-100)."""
        # 0% = 0 riesgo, 100%+ = riesgo máximo
        return min(100, spread_pct)

    def _score_volatility(self, volatility: float) -> float:
        """Score de riesgo por volatilidad (0-100)."""
        # Volatilidad anualizada: 0% = 0, 100%+ = máximo
        return min(100, volatility * 100)

    def _score_inflation(self, annual_inflation: float) -> float:
        """Score de riesgo por inflación (0-100)."""
        if annual_inflation < 10:
            return annual_inflation
        elif annual_inflation < 100:
            return 30 + (annual_inflation - 10) * 0.7
        else:
            return min(100, 80 + (annual_inflation - 100) * 0.05)

    def _score_reserves(self, months_coverage: float) -> float:
        """Score de riesgo por cobertura de reservas (0-100)."""
        # Menos meses = más riesgo
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
        # Menos producción = más riesgo
        if production_mbd >= baseline:
            return 10
        ratio = production_mbd / baseline
        return min(100, (1 - ratio) * 100)

    def calculate(
        self,
        spread_pct: float = 0,
        volatility: float = 0,
        annual_inflation: float = 0,
        reserves_months: float = 12,
        debt_gdp_pct: float = 0,
        oil_production_mbd: float = 1.5,
    ) -> RiskResult:
        """Calcula el índice de riesgo soberano.

        Args:
            spread_pct: Brecha cambiaria (%).
            volatility: Volatilidad anualizada del tipo de cambio.
            annual_inflation: Inflación anual (%).
            reserves_months: Meses de cobertura de reservas.
            debt_gdp_pct: Deuda como % del PIB.
            oil_production_mbd: Producción petrolera (mbd).

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
        }

        # Score compuesto (promedio ponderado)
        score = sum(
            components[k] * self.weights[k]
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

        # Interpretación
        interpretation = f"Riesgo soberano: {level.upper()} ({score}/100). "

        # Factores dominantes
        sorted_components = sorted(components.items(), key=lambda x: x[1], reverse=True)
        top_risks = [k for k, v in sorted_components if v > 50]
        if top_risks:
            risk_labels = {
                "spread": "brecha cambiaria",
                "volatility": "volatilidad cambiaria",
                "inflation": "inflación",
                "reserves": "bajas reservas",
                "debt": "deuda elevada",
                "oil": "baja producción petrolera",
            }
            risks_text = ", ".join(risk_labels.get(k, k) for k in top_risks[:3])
            interpretation += f"Principales factores de riesgo: {risks_text}."

        return RiskResult(
            score=score,
            level=level,
            components=components,
            interpretation=interpretation,
        )
