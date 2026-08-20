"""
Análisis de Deuda Pública (v2 - Expandido)
============================================

Análisis completo de la deuda pública de Venezuela:
- Deuda externa vs interna (desglose por moneda)
- Sostenibilidad de la deuda con escenarios de estrés
- Proyecciones bajo diferentes escenarios
- Análisis de vencimientos (rollover risk)
- Deuda contingente (PDVSA, empresas públicas, pensiones)
- Relación deuda/PIB y costo promedio de la deuda

Fuentes:
- BCV: deuda pública
- FMI: proyecciones
- Banco Mundial: indicadores de deuda
- PDVSA: deuda corporativa
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DebtStructure:
    """Estructura detallada de la deuda."""
    total_usd: float = 0.0
    external_usd: float = 0.0
    internal_usd: float = 0.0
    external_local_currency: float = 0.0  # deuda externa en Bs.
    bond_debt: float = 0.0  # bonos soberanos
    bilateral_debt: float = 0.0  # deuda bilateral (China, Rusia, etc.)
    multilateral_debt: float = 0.0  # bancos multilaterales
    commercial_debt: float = 0.0  # deuda comercial
    weighted_interest_rate: float = 0.0  # tasa de interés ponderada
    external_ratio: float = 0.0  # % de deuda externa
    local_ratio: float = 0.0  # % de deuda interna

    def to_dict(self) -> dict:
        return {
            "total_usd": self.total_usd,
            "external_usd": self.external_usd,
            "internal_usd": self.internal_usd,
            "external_local_currency": self.external_local_currency,
            "bond_debt": self.bond_debt,
            "bilateral_debt": self.bilateral_debt,
            "multilateral_debt": self.multilateral_debt,
            "commercial_debt": self.commercial_debt,
            "weighted_interest_rate": self.weighted_interest_rate,
            "external_ratio": self.external_ratio,
            "local_ratio": self.local_ratio,
        }


@dataclass
class MaturityProfile:
    """Perfil de vencimientos de deuda."""
    short_term: float = 0.0  # < 1 año
    medium_term: float = 0.0  # 1-5 años
    long_term: float = 0.0  # > 5 años
    next_12m: float = 0.0  # vencimiento en próximos 12 meses
    next_3y: float = 0.0  # vencimiento en próximos 3 años
    next_5y: float = 0.0  # vencimiento en próximos 5 años
    rollover_risk: str = ""  # "bajo", "medio", "alto", "crítico"

    def to_dict(self) -> dict:
        return {
            "short_term": self.short_term,
            "medium_term": self.medium_term,
            "long_term": self.long_term,
            "next_12m": self.next_12m,
            "next_3y": self.next_3y,
            "next_5y": self.next_5y,
            "rollover_risk": self.rollover_risk,
        }


@dataclass
class StressScenario:
    """Resultado de un escenario de estrés."""
    name: str
    oil_price: float
    gdp_growth: float
    interest_rate: float
    deficit_pct: float
    projected_debt_gdp: float
    sustainability: str
    interpretation: str


@dataclass
class DebtResult:
    """Resultado completo del análisis de deuda."""
    structure: DebtStructure
    maturity: MaturityProfile
    debt_gdp_ratio: Optional[float]
    sustainability: str  # "sostenible", "en_riesgo", "insostenible"
    stress_scenarios: List[StressScenario]
    years_to_crisis: Optional[float]
    interpretation: str


@dataclass
class ContingentLiabilities:
    """Pasivos contingentes."""
    pdvsa_debt: float = 0.0
    state_enterprise_debt: float = 0.0
    unfunded_pensions: float = 0.0
    guarantees: float = 0.0
    total: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pdvsa_debt": self.pdvsa_debt,
            "state_enterprise_debt": self.state_enterprise_debt,
            "unfunded_pensions": self.unfunded_pensions,
            "guarantees": self.guarantees,
            "total": self.total,
        }


class PublicDebtAnalyzer:
    """Analizador completo de Deuda Pública de Venezuela."""

    def __init__(self):
        pass

    def analyze_structure(
        self,
        total_debt_usd: float,
        external_debt_usd: float = 0.0,
        bond_debt: float = 0.0,
        bilateral_debt: float = 0.0,
        multilateral_debt: float = 0.0,
        commercial_debt: float = 0.0,
        interest_rates: Optional[Dict[str, float]] = None,
        debt_amounts: Optional[Dict[str, float]] = None,
    ) -> DebtStructure:
        """Analiza la estructura de la deuda.

        Args:
            total_debt_usd: Deuda total en USD.
            external_debt_usd: Deuda externa en USD.
            bond_debt: Deuda en bonos soberanos (USD).
            bilateral_debt: Deuda bilateral (USD).
            multilateral_debt: Deuda multilateral (USD).
            commercial_debt: Deuda comercial (USD).
            interest_rates: Dict de tasa de interés por componente.
            debt_amounts: Dict de monto por componente (para calcular tasa ponderada).

        Returns:
            DebtStructure con el desglose.
        """
        internal = total_debt_usd - external_debt_usd

        external_ratio = (external_debt_usd / total_debt_usd * 100) if total_debt_usd > 0 else 0
        local_ratio = 100 - external_ratio

        # Tasa ponderada
        weighted_rate = 0.0
        if interest_rates and debt_amounts:
            total_weighted = 0
            total_amount = 0
            for comp, rate in interest_rates.items():
                amount = debt_amounts.get(comp, 0)
                total_weighted += rate * amount
                total_amount += amount
            if total_amount > 0:
                weighted_rate = total_weighted / total_amount

        return DebtStructure(
            total_usd=total_debt_usd,
            external_usd=external_debt_usd,
            internal_usd=internal,
            bond_debt=bond_debt,
            bilateral_debt=bilateral_debt,
            multilateral_debt=multilateral_debt,
            commercial_debt=commercial_debt,
            weighted_interest_rate=round(weighted_rate, 2),
            external_ratio=round(external_ratio, 1),
            local_ratio=round(local_ratio, 1),
        )

    def analyze_maturities(
        self,
        short_term: float = 0.0,
        medium_term: float = 0.0,
        long_term: float = 0.0,
    ) -> MaturityProfile:
        """Analiza el perfil de vencimientos.

        Args:
            short_term: Deuda de corto plazo (< 1 año, USD).
            medium_term: Deuda de mediano plazo (1-5 años, USD).
            long_term: Deuda de largo plazo (> 5 años, USD).

        Returns:
            MaturityProfile con el análisis.
        """
        total = short_term + medium_term + long_term

        next_12m = short_term
        next_3y = short_term + medium_term * 0.6  # Aproximación
        next_5y = short_term + medium_term + long_term * 0.3

        # Riesgo de refinanciamiento
        if total <= 0:
            rollover_risk = "bajo"
        else:
            st_ratio = short_term / total * 100
            if st_ratio > 50:
                rollover_risk = "crítico"
            elif st_ratio > 30:
                rollover_risk = "alto"
            elif st_ratio > 15:
                rollover_risk = "medio"
            else:
                rollover_risk = "bajo"

        return MaturityProfile(
            short_term=short_term,
            medium_term=medium_term,
            long_term=long_term,
            next_12m=round(next_12m, 0),
            next_3y=round(next_3y, 0),
            next_5y=round(next_5y, 0),
            rollover_risk=rollover_risk,
        )

    def stress_test(
        self,
        current_debt: float,
        gdp_usd: float,
        scenarios: List[Dict],
    ) -> List[StressScenario]:
        """Ejecuta escenarios de estrés sobre la deuda.

        Args:
            current_debt: Deuda actual (USD).
            gdp_usd: PIB actual (USD).
            scenarios: Lista de dicts con keys:
                - name: nombre del escenario
                - oil_price: precio del petróleo (USD/barril)
                - gdp_growth: crecimiento del PIB (%)
                - interest_rate: tasa de interés de la deuda (%)
                - deficit_pct: déficit fiscal (% del PIB)
                - years: años a proyectar

        Returns:
            Lista de StressScenario con resultados.
        """
        results = []

        for sc in scenarios:
            name = sc.get("name", "Sin nombre")
            oil_price = sc.get("oil_price", 60)
            gdp_growth = sc.get("gdp_growth", 0)
            interest_rate = sc.get("interest_rate", 0.05)
            deficit_pct = sc.get("deficit_pct", 5)
            years = sc.get("years", 5)

            # Proyectar deuda
            debt = current_debt
            gdp = gdp_usd
            for y in range(years):
                deficit_usd = gdp * deficit_pct / 100
                interest = debt * interest_rate
                debt = debt + deficit_usd + interest
                gdp = gdp * (1 + gdp_growth / 100)

            debt_gdp = (debt / gdp * 100) if gdp > 0 else 999

            if debt_gdp > 300:
                sustainability = "insostenible"
            elif debt_gdp > 100:
                sustainability = "en_riesgo"
            else:
                sustainability = "sostenible"

            interpretation = (
                f"En {years} años, deuda/PIB = {debt_gdp:.0f}% "
                f"(petróleo=${oil_price:.0f}, crecimiento={gdp_growth:.1f}%, "
                f"déficit={deficit_pct:.1f}%, interés={interest_rate*100:.1f}%)."
            )

            results.append(StressScenario(
                name=name,
                oil_price=oil_price,
                gdp_growth=gdp_growth,
                interest_rate=interest_rate,
                deficit_pct=deficit_pct,
                projected_debt_gdp=round(debt_gdp, 1),
                sustainability=sustainability,
                interpretation=interpretation,
            ))

        return results

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

    def load_ocr_data(self) -> dict:
        """Carga datos de deuda desde archivos OCR (BVC).

        Returns:
            Dict con datos parseados de DPN, Letras del Tesoro, etc.
        """
        try:
            from src.analyzers.debt_parser import load_all_debt_data, get_debt_totals
            all_data = load_all_debt_data()
            totals = get_debt_totals()

            # Extract useful info from DPN
            dpn_data = all_data.get("dpn")
            bills_data = all_data.get("bills")

            result = {
                "source": "BVC/OCR",
                "total_emissions": totals["total_emissions"],
                "total_amount_bs": totals["total_amount_bs"],
                "fixed_rate_count": totals["fixed_rate_count"],
                "floating_rate_count": totals["floating_rate_count"],
                "documents": totals["documents"],
                "dpn_emissions": [],
                "bills_count": bills_data.total_emissions if bills_data else 0,
            }

            # Parse DPN emissions for display
            if dpn_data:
                for e in dpn_data.emissions[:20]:  # Top 20
                    result["dpn_emissions"].append({
                        "code": e.code,
                        "isin": e.isin,
                        "sibe": e.sibe,
                        "rate_type": e.rate_type,
                        "amount_bs": e.amount_bs,
                        "decree_date": e.decree_date,
                        "maturity_date": e.maturity_date,
                    })

            return result

        except Exception as exc:
            logger.debug("OCR data not available: %s", exc)
            return {}

    def analyze_contingent_liabilities(
        self,
        pdvsa_debt: float = 0.0,
        state_enterprise_debt: float = 0.0,
        unfunded_pensions: float = 0.0,
        guarantees: float = 0.0,
    ) -> ContingentLiabilities:
        """Analiza pasivos contingentes.

        Args:
            pdvsa_debt: Deuda de PDVSA (USD).
            state_enterprise_debt: Deuda de empresas estatales (USD).
            unfunded_pensions: Pasivo acumulado de pensiones (USD).
            guarantees: Garantías gubernamentales (USD).

        Returns:
            ContingentLiabilities con el desglose.
        """
        total = pdvsa_debt + state_enterprise_debt + unfunded_pensions + guarantees

        return ContingentLiabilities(
            pdvsa_debt=pdvsa_debt,
            state_enterprise_debt=state_enterprise_debt,
            unfunded_pensions=unfunded_pensions,
            guarantees=guarantees,
            total=total,
        )

    def analyze(
        self,
        total_debt_usd: Optional[float] = None,
        gdp_usd: Optional[float] = None,
        external_debt_usd: Optional[float] = None,
        fiscal_deficit_pct: Optional[float] = None,
        oil_revenues_usd: Optional[float] = None,
        inflation_rate: Optional[float] = None,
        bond_debt: float = 0.0,
        bilateral_debt: float = 0.0,
        multilateral_debt: float = 0.0,
        commercial_debt: float = 0.0,
        short_term_debt: float = 0.0,
        medium_term_debt: float = 0.0,
        long_term_debt: float = 0.0,
        pdvsa_debt: float = 0.0,
        oil_price: float = 60.0,
    ) -> DebtResult:
        """Análisis completo de deuda pública.

        Args:
            total_debt_usd: Deuda total en USD.
            gdp_usd: PIB en USD.
            external_debt_usd: Deuda externa en USD.
            fiscal_deficit_pct: Déficit fiscal como % del PIB.
            oil_revenues_usd: Ingresos petroleros anuales en USD.
            inflation_rate: Inflación anual (%).
            bond_debt: Deuda en bonos (USD).
            bilateral_debt: Deuda bilateral (USD).
            multilateral_debt: Deuda multilateral (USD).
            commercial_debt: Deuda comercial (USD).
            short_term_debt: Deuda corto plazo (USD).
            medium_term_debt: Deuda mediano plazo (USD).
            long_term_debt: Deuda largo plazo (USD).
            pdvsa_debt: Deuda de PDVSA (USD).
            oil_price: Precio del petróleo (USD/barril).

        Returns:
            DebtResult con análisis completo.
        """
        total = total_debt_usd or 0
        ext = external_debt_usd or 0

        # 1. Estructura
        structure = self.analyze_structure(
            total_debt_usd=total,
            external_debt_usd=ext,
            bond_debt=bond_debt,
            bilateral_debt=bilateral_debt,
            multilateral_debt=multilateral_debt,
            commercial_debt=commercial_debt,
        )

        # 2. Vencimientos
        maturity = self.analyze_maturities(
            short_term=short_term_debt,
            medium_term=medium_term_debt,
            long_term=long_term_debt,
        )

        # 3. Deuda/PIB
        debt_gdp = None
        if gdp_usd and gdp_usd > 0:
            debt_gdp = total / gdp_usd * 100

        # 4. Sostenibilidad
        sustainability = "desconocido"
        if debt_gdp is not None:
            if debt_gdp > 300:
                sustainability = "insostenible"
            elif debt_gdp > 100:
                sustainability = "en_riesgo"
            else:
                sustainability = "sostenible"

        # 5. Años hasta crisis
        years_to_crisis = None
        if fiscal_deficit_pct and gdp_usd and gdp_usd > 0:
            annual_deficit_usd = gdp_usd * fiscal_deficit_pct / 100
            if annual_deficit_usd > 0 and total > 0:
                years_to_crisis = total / annual_deficit_usd

        # 6. Escenarios de estrés
        scenarios = []
        if total > 0 and gdp_usd and gdp_usd > 0:
            scenarios = self.stress_test(
                current_debt=total,
                gdp_usd=gdp_usd,
                scenarios=[
                    {
                        "name": "Base",
                        "oil_price": oil_price,
                        "gdp_growth": 3.0,
                        "interest_rate": 0.05,
                        "deficit_pct": fiscal_deficit_pct or 5,
                        "years": 5,
                    },
                    {
                        "name": "Optimista",
                        "oil_price": oil_price * 1.3,
                        "gdp_growth": 8.0,
                        "interest_rate": 0.04,
                        "deficit_pct": max(0, (fiscal_deficit_pct or 5) - 3),
                        "years": 5,
                    },
                    {
                        "name": "Pesimista",
                        "oil_price": oil_price * 0.6,
                        "gdp_growth": -2.0,
                        "interest_rate": 0.08,
                        "deficit_pct": (fiscal_deficit_pct or 5) + 4,
                        "years": 5,
                    },
                    {
                        "name": "Crisis petrolera",
                        "oil_price": 30,
                        "gdp_growth": -5.0,
                        "interest_rate": 0.10,
                        "deficit_pct": 15,
                        "years": 5,
                    },
                ],
            )

        # 7. Pasivos contingentes
        contingent = self.analyze_contingent_liabilities(pdvsa_debt=pdvsa_debt)

        # 8. Interpretación
        interpretation_parts = []

        if debt_gdp is not None:
            if debt_gdp > 300:
                interpretation_parts.append(
                    f"Deuda/PIB de {debt_gdp:.0f}% es extremadamente alta. La deuda supera 3 veces el PIB."
                )
            elif debt_gdp > 100:
                interpretation_parts.append(
                    f"Deuda/PIB de {debt_gdp:.0f}% está por encima del umbral crítico."
                )
            else:
                interpretation_parts.append(
                    f"Deuda/PIB de {debt_gdp:.0f}% dentro de rangos manejables."
                )

        if structure.external_ratio > 70:
            interpretation_parts.append(
                f"Alta exposición a riesgo cambiario: {structure.external_ratio:.0f}% de deuda externa."
            )

        if maturity.rollover_risk in ("alto", "crítico"):
            interpretation_parts.append(
                f"Riesgo de refinanciamiento {maturity.rollover_risk}: "
                f"${maturity.short_term/1e9:.1f}B vencen en <1 año."
            )

        if oil_revenues_usd and total > 0:
            years_of_revenues = total / oil_revenues_usd if oil_revenues_usd > 0 else None
            if years_of_revenues:
                interpretation_parts.append(
                    f"La deuda total equivale a {years_of_revenues:.1f} años de ingresos petroleros."
                )

        if years_to_crisis and years_to_crisis < 5:
            interpretation_parts.append(
                f"Al ritmo actual de déficit ({fiscal_deficit_pct:.1f}% del PIB), "
                f"la deuda crecería significativamente en {years_to_crisis:.1f} años."
            )

        if contingent.total > 0:
            interpretation_parts.append(
                f"Pasivos contingentes (PDVSA, pensiones): ${contingent.total/1e9:.1f}B "
                f"que podrían materializarse."
            )

        interpretation = " ".join(interpretation_parts) or "Datos insuficientes para análisis de deuda."

        # 9. Load OCR data for additional context
        ocr_data = self.load_ocr_data()
        if ocr_data:
            total_emissions = ocr_data.get("total_emissions", 0)
            if total_emissions > 0:
                interpretation_parts.append(
                    f"Base de conocimiento BVC: {total_emissions} emisiones de deuda documentadas "
                    f"(DPN, Letras del Tesoro, Bonos BCV/PDVSA)."
                )
                interpretation = " ".join(interpretation_parts)

        return DebtResult(
            structure=structure,
            maturity=maturity,
            debt_gdp_ratio=round(debt_gdp, 1) if debt_gdp else None,
            sustainability=sustainability,
            stress_scenarios=scenarios,
            years_to_crisis=round(years_to_crisis, 1) if years_to_crisis else None,
            interpretation=interpretation,
        )
