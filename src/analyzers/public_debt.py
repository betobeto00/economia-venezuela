"""
Análisis de Deuda Pública
==========================

Análisis de la deuda pública de Venezuela:
- Deuda externa vs interna
- Sostenibilidad de la deuda
- Proyecciones bajo diferentes escenarios
- Relación deuda/PIB

Fuentes:
- BCV: deuda pública
- FMI: proyecciones
- Banco Mundial: indicadores de deuda
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DebtResult:
    """Resultado del análisis de deuda."""
    total_debt_usd: Optional[float]
    debt_gdp_ratio: Optional[float]
    external_debt: Optional[float]
    internal_debt: Optional[float]
    external_ratio: Optional[float]  # % de deuda externa
    sustainability: str  # "sostenible", "en_riesgo", "insostenible"
    years_to_crisis: Optional[float]  # Años estimados hasta crisis
    interpretation: str


class PublicDebtAnalyzer:
    """Analizador de Deuda Pública de Venezuela."""

    def __init__(self):
        pass

    def analyze(
        self,
        total_debt_usd: Optional[float] = None,
        gdp_usd: Optional[float] = None,
        external_debt_usd: Optional[float] = None,
        fiscal_deficit_pct: Optional[float] = None,
        oil_revenues_usd: Optional[float] = None,
        inflation_rate: Optional[float] = None,
    ) -> DebtResult:
        """Análisis de sostenibilidad de deuda.

        Args:
            total_debt_usd: Deuda total en USD.
            gdp_usd: PIB en USD.
            external_debt_usd: Deuda externa en USD.
            fiscal_deficit_pct: Déficit fiscal como % del PIB.
            oil_revenues_usd: Ingresos petroleros anuales en USD.
            inflation_rate: Inflación anual (%).

        Returns:
            DebtResult con el análisis.
        """
        internal_debt = None
        external_ratio = None
        if total_debt_usd and external_debt_usd:
            internal_debt = total_debt_usd - external_debt_usd
            external_ratio = external_debt_usd / total_debt_usd * 100

        debt_gdp = None
        if total_debt_usd and gdp_usd and gdp_usd > 0:
            debt_gdp = total_debt_usd / gdp_usd * 100

        # Análisis de sostenibilidad
        sustainability = "desconocido"
        years_to_crisis = None
        interpretation = ""

        if debt_gdp is not None:
            if debt_gdp > 300:
                sustainability = "insostenible"
                interpretation = (
                    f"Deuda/PIB de {debt_gdp:.0f}% es extremadamente alta. "
                    f"La deuda supera 3 veces el PIB. "
                )
            elif debt_gdp > 100:
                sustainability = "en_riesgo"
                interpretation = (
                    f"Deuda/PIB de {debt_gdp:.0f}% está por encima del umbral crítico. "
                )
            else:
                sustainability = "sostenible"
                interpretation = f"Deuda/PIB de {debt_gdp:.0f}% dentro de rangos manejables. "

            # Estimar años hasta crisis (simplificado)
            if fiscal_deficit_pct and gdp_usd and gdp_usd > 0:
                annual_deficit_usd = gdp_usd * fiscal_deficit_pct / 100
                if annual_deficit_usd > 0 and total_debt_usd:
                    # Asumiendo que el déficit se financia con deuda
                    years_to_crisis = total_debt_usd / annual_deficit_usd if annual_deficit_usd > 0 else None
                    if years_to_crisis and years_to_crisis < 5:
                        interpretation += (
                            f"Al ritmo actual de déficit ({fiscal_deficit_pct:.1f}% del PIB), "
                            f"la deuda crecería significativamente en {years_to_crisis:.1f} años."
                        )

        # Estructura de deuda
        if external_ratio is not None:
            interpretation += (
                f"Deuda externa: {external_ratio:.0f}% del total. "
            )
            if external_ratio > 70:
                interpretation += "Alta exposición a riesgo cambiario. "
            else:
                interpretation += "Exposición moderada al tipo de cambio. "

        # Capacidad de pago
        if oil_revenues_usd and total_debt_usd:
            years_of_revenues = total_debt_usd / oil_revenues_usd if oil_revenues_usd > 0 else None
            if years_of_revenues:
                interpretation += (
                    f"La deuda total equivale a {years_of_revenues:.1f} años de ingresos petroleros. "
                )

        return DebtResult(
            total_debt_usd=total_debt_usd,
            debt_gdp_ratio=round(debt_gdp, 1) if debt_gdp else None,
            external_debt=external_debt_usd,
            internal_debt=internal_debt,
            external_ratio=round(external_ratio, 1) if external_ratio else None,
            sustainability=sustainability,
            years_to_crisis=round(years_to_crisis, 1) if years_to_crisis else None,
            interpretation=interpretation or "Datos insuficientes para análisis de deuda.",
        )

    def project_debt(
        self,
        current_debt: float,
        annual_deficit: float,
        interest_rate: float = 0.05,
        gdp_growth: float = 0.0,
        years: int = 5,
    ) -> list:
        """Proyecta la trayectoria de deuda bajo diferentes escenarios.

        Args:
            current_debt: Deuda actual (USD).
            annual_deficit: Déficit anual (USD).
            interest_rate: Tasa de interés de la deuda.
            gdp_growth: Crecimiento del PIB (proxy para crecimiento de deuda).
            years: Años a proyectar.

        Returns:
            Lista de dicts con proyección por año.
        """
        projections = []
        debt = current_debt

        for year in range(1, years + 1):
            interest = debt * interest_rate
            new_debt = debt + annual_deficit + interest
            projections.append({
                "year": year,
                "debt": round(new_debt, 0),
                "interest": round(interest, 0),
                "new_borrowing": round(annual_deficit + interest, 0),
            })
            debt = new_debt

        return projections
