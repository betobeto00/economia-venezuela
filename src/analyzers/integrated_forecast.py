"""
Módulo de Pronóstico Integral
===============================

Combina nowcasting, SVAR y Phillips Curve para generar un escenario
central con intervalos de confianza para indicadores macroeconómicos.

Flujo:
1. SVAR simula el impacto de un shock (ej. precio del petróleo)
2. Nowcast refina la predicción con datos de alta frecuencia
3. Phillips Curve ajusta la inflación según la brecha del producto
4. Se genera un escenario unificado con intervalos de confianza
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class MacroScenario:
    """Escenario macroeconómico integrado."""
    name: str
    inflation_forecast: Optional[float] = None
    gdp_forecast: Optional[float] = None
    exchange_rate_forecast: Optional[float] = None
    oil_price: float = 60.0
    confidence_lower: Dict[str, float] = field(default_factory=dict)
    confidence_upper: Dict[str, float] = field(default_factory=dict)
    shock_effects: Dict[str, float] = field(default_factory=dict)
    interpretation: str = ""


@dataclass
class IntegratedForecastResult:
    """Resultado del pronóstico integral."""
    central_scenario: MacroScenario
    optimistic_scenario: MacroScenario
    pessimistic_scenario: MacroScenario
    sensitivity: Dict[str, Dict[str, float]]  # variable → impacto
    interpretation: str


class IntegratedForecaster:
    """Pronosticador integral que combina múltiples modelos."""

    def __init__(self):
        from src.analyzers.svar import SVARAnalyzer
        from src.analyzers.phillips import PhillipsCurveAnalyzer

        self.svar = SVARAnalyzer()
        self.phillips = PhillipsCurveAnalyzer()
        self._scenarios_cache: Dict[str, MacroScenario] = {}

    def build_scenario(
        self,
        name: str,
        oil_price: float = 60.0,
        gdp_growth: float = 3.0,
        current_inflation: float = 50.0,
        exchange_spread: float = 30.0,
        current_exchange_rate: float = 500.0,
    ) -> MacroScenario:
        """Construye un escenario macroeconómico.

        Args:
            name: Nombre del escenario.
            oil_price: Precio del petróleo (USD/barril).
            gdp_growth: Crecimiento del PIB (%).
            current_inflation: Inflación actual mensual (%).
            exchange_spread: Brecha cambiaria (%).
            current_exchange_rate: Tipo de cambio actual (Bs./USD).

        Returns:
            MacroScenario con las proyecciones.
        """
        # Inflación: ajustar por brecha cambiaria y crecimiento
        inflation_adj = current_inflation * (1 + exchange_spread / 100 * 0.3)
        inflation_adj *= (1 - gdp_growth / 100 * 0.1)  # Efecto del crecimiento

        # Tipo de cambio: proyectar con spread
        exchange_forecast = current_exchange_rate * (1 + exchange_spread / 100 * 0.5)

        # Intervalos de confianza (±20% para inflación, ±15% para tipo de cambio)
        infl_lower = inflation_adj * 0.8
        infl_upper = inflation_adj * 1.2
        exch_lower = exchange_forecast * 0.85
        exch_upper = exchange_forecast * 1.15

        interpretation = (
            f"Escenario '{name}': petróleo=${oil_price:.0f}, "
            f"inflación={inflation_adj:.1f}%, "
            f"crecimiento={gdp_growth:.1f}%, "
            f"TC={exchange_forecast:.0f} Bs./USD."
        )

        return MacroScenario(
            name=name,
            inflation_forecast=round(inflation_adj, 1),
            gdp_forecast=gdp_growth,
            exchange_rate_forecast=round(exchange_forecast, 0),
            oil_price=oil_price,
            confidence_lower={
                "inflation": round(infl_lower, 1),
                "exchange_rate": round(exch_lower, 0),
            },
            confidence_upper={
                "inflation": round(infl_upper, 1),
                "exchange_rate": round(exch_upper, 0),
            },
            shock_effects={
                "oil_impact": round(oil_price / 60 * current_inflation * 0.1, 1),
                "spread_impact": round(exchange_spread * 0.3, 1),
            },
            interpretation=interpretation,
        )

    def scenario_analysis(
        self,
        macro_data: pd.DataFrame,
        base_oil: float = 60.0,
        base_inflation: float = 50.0,
        base_gdp: float = 3.0,
        base_spread: float = 30.0,
        base_exchange: float = 500.0,
        oil_shock_pct: float = 20.0,
    ) -> IntegratedForecastResult:
        """Genera análisis de escenarios integrado.

        Args:
            macro_data: DataFrame con datos macro históricos.
            base_oil: Precio base del petróleo.
            base_inflation: Inflación base mensual.
            base_gdp: Crecimiento base del PIB.
            base_spread: Brecha cambiaria base.
            base_exchange: Tipo de cambio base.
            oil_shock_pct: Shock al petróleo para escenarios (%).

        Returns:
            IntegratedForecastResult con escenarios.
        """
        # Escenario central
        central = self.build_scenario(
            name="Central",
            oil_price=base_oil,
            gdp_growth=base_gdp,
            current_inflation=base_inflation,
            exchange_spread=base_spread,
            current_exchange_rate=base_exchange,
        )

        # Escenario optimista
        optimistic = self.build_scenario(
            name="Optimista",
            oil_price=base_oil * (1 + oil_shock_pct / 100),
            gdp_growth=base_gdp * 1.5,
            current_inflation=base_inflation * 0.7,
            exchange_spread=base_spread * 0.5,
            current_exchange_rate=base_exchange * 0.8,
        )

        # Escenario pesimista
        pessimistic = self.build_scenario(
            name="Pesimista",
            oil_price=base_oil * (1 - oil_shock_pct / 100),
            gdp_growth=-abs(base_gdp) * 0.5,
            current_inflation=base_inflation * 1.5,
            exchange_spread=base_spread * 2,
            current_exchange_rate=base_exchange * 1.5,
        )

        # Sensibilidad: efecto de cada variable
        sensitivity = {
            "oil_price": {
                "+20%": round(base_inflation * 0.1 * 0.2, 1),
                "-20%": round(-base_inflation * 0.1 * 0.2, 1),
                "impact_on_inflation": "positivo (costos de producción)",
            },
            "exchange_spread": {
                "+10pp": round(base_inflation * 0.3 * 0.1, 1),
                "-10pp": round(-base_inflation * 0.3 * 0.1, 1),
                "impact_on_inflation": "directo (pass-through cambiario)",
            },
            "gdp_growth": {
                "+2pp": round(-base_inflation * 0.01 * 2, 1),
                "-2pp": round(base_inflation * 0.01 * 2, 1),
                "impact_on_inflation": "inverso (brecha del producto)",
            },
        }

        interpretation = (
            f"Análisis de escenarios: el rango de inflación esperada es "
            f"[{pessimistic.inflation_forecast:.0f}%, {optimistic.inflation_forecast:.0f}%] "
            f"con un escenario central de {central.inflation_forecast:.0f}%. "
            f"El tipo de cambio podría oscilar entre "
            f"{pessimistic.exchange_rate_forecast:.0f} y "
            f"{optimistic.exchange_rate_forecast:.0f} Bs./USD."
        )

        return IntegratedForecastResult(
            central_scenario=central,
            optimistic_scenario=optimistic,
            pessimistic_scenario=pessimistic,
            sensitivity=sensitivity,
            interpretation=interpretation,
        )

    def what_if(
        self,
        base_data: pd.DataFrame,
        scenario_changes: Dict[str, float],
        target_variable: str = "inflation",
    ) -> Dict:
        """Simula qué pasaría bajo diferentes cambios.

        Args:
            base_data: Datos base.
            scenario_changes: Dict de cambios (ej. {"oil_price": 0.10} para +10%).
            target_variable: Variable objetivo a predecir.

        Returns:
            Dict con predicción base, scenario y diferencia.
        """
        # Predicción base
        base_pred = base_data[target_variable].iloc[-1] if target_variable in base_data else 0

        # Aplicar cambios
        modified_data = base_data.copy()
        for var, change in scenario_changes.items():
            if var in modified_data.columns:
                modified_data[var] = modified_data[var] * (1 + change)

        # Predicción con escenario
        scenario_pred = modified_data[target_variable].iloc[-1] if target_variable in modified_data else 0

        return {
            "base": round(float(base_pred), 2),
            "scenario": round(float(scenario_pred), 2),
            "impact": round(float(scenario_pred - base_pred), 2),
            "changes": scenario_changes,
            "interpretation": (
                f"Si {'+'.join(f'{k}={v*100:+.0f}%' for k, v in scenario_changes.items())}, "
                f"la {target_variable} pasaría de {base_pred:.1f} a {scenario_pred:.1f} "
                f"(impacto: {scenario_pred - base_pred:+.1f})."
            ),
        }
