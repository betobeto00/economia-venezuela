"""
Balanza de Pagos y Dinámica de Reservas
=========================================

Análisis de la balanza de pagos de Venezuela:
- Cuenta corriente (exportaciones petroleras vs importaciones)
- Reservas internacionales
- Emisión monetaria vs tipo de cambio
- Sostenibilidad fiscal

Fuentes:
- BCV: reservas internacionales, balanza de pagos
- OPEP: ingresos petroleros
- Seniat: recaudación fiscal
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class BalanceResult:
    """Resultado del análisis de balanza de pagos."""
    current_account: Optional[float]  # Cuenta corriente (USD)
    oil_revenues: Optional[float]  # Ingresos petroleros (USD)
    imports: Optional[float]  # Importaciones (USD)
    reserves: Optional[float]  # Reservas internacionales (USD)
    reserves_months: Optional[float]  # Meses de cobertura de importaciones
    deficit: Optional[float]  # Déficit de cuenta corriente
    interpretation: str


class BalanceOfPaymentsAnalyzer:
    """Analizador de Balanza de Pagos de Venezuela."""

    def __init__(self):
        pass

    def estimate_oil_revenues(
        self,
        production_mbd: float,
        oil_price_usd: float,
    ) -> float:
        """Estima ingresos petroleros anuales.

        Args:
            production_mbd: Producción en millones de barriles diarios.
            oil_price_usd: Precio del petróleo en USD/barril.

        Returns:
            Ingresos anuales estimados en USD.
        """
        return production_mbd * oil_price_usd * 365

    def reserves_coverage(
        self,
        reserves_usd: float,
        monthly_imports_usd: float,
    ) -> float:
        """Calcula meses de cobertura de importaciones.

        Args:
            reserves_usd: Reservas internacionales en USD.
            monthly_imports_usd: Importaciones mensuales en USD.

        Returns:
            Meses de cobertura.
        """
        if monthly_imports_usd <= 0:
            return 0
        return reserves_usd / monthly_imports_usd

    def analyze(
        self,
        reserves: Optional[float] = None,
        oil_production_mbd: Optional[float] = None,
        oil_price_usd: Optional[float] = None,
        imports_monthly: Optional[float] = None,
        previous_reserves: Optional[float] = None,
    ) -> BalanceResult:
        """Análisis completo de balanza de pagos.

        Args:
            reserves: Reservas internacionales (USD).
            oil_production_mbd: Producción petrolera (mbd).
            oil_price_usd: Precio del petróleo (USD/barril).
            imports_monthly: Importaciones mensuales (USD).
            previous_reserves: Reservas del período anterior (USD).

        Returns:
            BalanceResult con el análisis.
        """
        oil_revenues = None
        if oil_production_mbd and oil_price_usd:
            oil_revenues = self.estimate_oil_revenues(oil_production_mbd, oil_price_usd)

        reserves_months = None
        if reserves and imports_monthly:
            reserves_months = self.reserves_coverage(reserves, imports_monthly)

        deficit = None
        if oil_revenues and imports_monthly:
            annual_imports = imports_monthly * 12
            deficit = oil_revenues - annual_imports

        # Interpretación
        interpretation = ""

        if reserves_months is not None:
            if reserves_months < 3:
                interpretation += (
                    f"CRÍTICO: Las reservas cubren solo {reserves_months:.1f} meses de importaciones. "
                    "Riesgo de crisis de balanza de pagos. "
                )
            elif reserves_months < 6:
                interpretation += (
                    f"ADVERTENCIA: Reservas para {reserves_months:.1f} meses. "
                    "Cobertura insuficiente. "
                )
            else:
                interpretation += (
                    f"Reservas cubren {reserves_months:.1f} meses. "
                    "Cobertura aceptable. "
                )

        if deficit is not None:
            if deficit < 0:
                interpretation += (
                    f"Déficit de cuenta corriente: ${abs(deficit)/1e6:.0f}M. "
                    "El petróleo no cubre las importaciones. "
                )
            else:
                interpretation += (
                    f"Superávit de cuenta corriente: ${deficit/1e6:.0f}M. "
                )

        if previous_reserves and reserves:
            change = (reserves - previous_reserves) / previous_reserves * 100
            if change < -10:
                interpretation += (
                    f"Las reservas cayeron {abs(change):.1f}% respecto al período anterior."
                )
            elif change > 10:
                interpretation += (
                    f"Las reservas subieron {change:.1f}% respecto al período anterior."
                )

        return BalanceResult(
            current_account=deficit,
            oil_revenues=oil_revenues,
            imports=imports_monthly * 12 if imports_monthly else None,
            reserves=reserves,
            reserves_months=round(reserves_months, 1) if reserves_months else None,
            deficit=deficit,
            interpretation=interpretation or "Datos insuficientes para análisis completo.",
        )
