"""
Balanza de Pagos y Dinámica de Reservas (v2 - Expandido)
==========================================================

Análisis completo de la balanza de pagos de Venezuela:
- Cuenta corriente: petróleo, no petróleo, servicios, remesas, transferencias
- Cuenta de capital y financiera: IED, préstamos, amortizaciones
- Reservas internacionales: desglose por oro, DEG, divisas
- Ciclo del petróleo: ingresos brutos vs flujo de caja efectivo
- Sostenibilidad externa

Fuentes:
- BCV: reservas internacionales, balanza de pagos
- OPEP: ingresos petroleros
- Seniat: recaudación fiscal
- BCV: remesas, servicios
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CurrentAccountResult:
    """Desglose de la cuenta corriente."""
    oil_revenues: float = 0.0
    non_oil_exports: float = 0.0
    gold_exports: float = 0.0
    agricultural_exports: float = 0.0
    imports: float = 0.0
    services_net: float = 0.0  # exportaciones - importaciones de servicios
    remittances: float = 0.0
    investment_income: float = 0.0  # intereses, dividendos
    unilateral_transfers: float = 0.0
    balance: float = 0.0  # saldo total

    def to_dict(self) -> dict:
        return {
            "oil_revenues": self.oil_revenues,
            "non_oil_exports": self.non_oil_exports,
            "gold_exports": self.gold_exports,
            "agricultural_exports": self.agricultural_exports,
            "imports": self.imports,
            "services_net": self.services_net,
            "remittances": self.remittances,
            "investment_income": self.investment_income,
            "unilateral_transfers": self.unilateral_transfers,
            "balance": self.balance,
        }


@dataclass
class CapitalAccountResult:
    """Desglose de la cuenta de capital y financiera."""
    fdi_inflow: float = 0.0  # inversión extranjera directa
    fdi_outflow: float = 0.0
    portfolio_investment: float = 0.0
    other_investment: float = 0.0  # préstamos, créditos comerciales
    debt_amortization: float = 0.0  # amortizaciones de deuda
    reserve_changes: float = 0.0  # cambio en reservas
    balance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "fdi_inflow": self.fdi_inflow,
            "fdi_outflow": self.fdi_outflow,
            "portfolio_investment": self.portfolio_investment,
            "other_investment": self.other_investment,
            "debt_amortization": self.debt_amortization,
            "reserve_changes": self.reserve_changes,
            "balance": self.balance,
        }


@dataclass
class ReservesBreakdown:
    """Desglose de reservas internacionales."""
    total_usd: float = 0.0
    foreign_currencies: float = 0.0
    gold_usd: float = 0.0
    sdr: float = 0.0  # Derechos Especiales de Giro (DEG)
    imf_position: float = 0.0
    other_assets: float = 0.0
    months_coverage: float = 0.0
    months_debt_service: float = 0.0  # cobertura de servicio de deuda

    def to_dict(self) -> dict:
        return {
            "total_usd": self.total_usd,
            "foreign_currencies": self.foreign_currencies,
            "gold_usd": self.gold_usd,
            "sdr": self.sdr,
            "imf_position": self.imf_position,
            "other_assets": self.other_assets,
            "months_coverage": self.months_coverage,
            "months_debt_service": self.months_debt_service,
        }


@dataclass
class OilCycleResult:
    """Análisis del ciclo petrolero."""
    gross_revenues: float = 0.0  # ingresos brutos
    extraction_cost: float = 0.0  # costo de extracción
    pdvsa_share: float = 0.0  # regalías e impuestos a PDVSA
    net_revenues: float = 0.0  # ingresos netos para el fisco
    effective_cash_flow: float = 0.0  # flujo de caja efectivo (neto de compromisos)
    breakeven_price: float = 0.0  # precio de equilibrio
    interpretation: str = ""

    def to_dict(self) -> dict:
        return {
            "gross_revenues": self.gross_revenues,
            "extraction_cost": self.extraction_cost,
            "pdvsa_share": self.pdvsa_share,
            "net_revenues": self.net_revenues,
            "effective_cash_flow": self.effective_cash_flow,
            "breakeven_price": self.breakeven_price,
            "interpretation": self.interpretation,
        }


@dataclass
class BalanceResult:
    """Resultado completo del análisis de balanza de pagos."""
    current_account: CurrentAccountResult
    capital_account: CapitalAccountResult
    reserves: ReservesBreakdown
    oil_cycle: OilCycleResult
    external_sustainability_score: float  # 0-100
    interpretation: str


class BalanceOfPaymentsAnalyzer:
    """Analizador completo de Balanza de Pagos de Venezuela."""

    def __init__(self):
        pass

    # --- Cuenta Corriente ---

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
        return production_mbd * oil_price_usd * 365 * 1e6  # mbd → barriles/día, resultado en USD

    def estimate_non_oil_exports(
        self,
        gold_exports: float = 0.0,
        agricultural_exports: float = 0.0,
        mineral_exports: float = 0.0,
        industrial_exports: float = 0.0,
    ) -> float:
        """Estima exportaciones no petroleras.

        Args:
            gold_exports: Exportaciones de oro (USD).
            agricultural_exports: Exportaciones agrícolas (USD).
            mineral_exports: Exportaciones minerales no petroleras (USD).
            industrial_exports: Exportaciones industriales (USD).

        Returns:
            Total de exportaciones no petroleras (USD).
        """
        return gold_exports + agricultural_exports + mineral_exports + industrial_exports

    def current_account(
        self,
        oil_revenues: float = 0.0,
        non_oil_exports: float = 0.0,
        imports: float = 0.0,
        services_net: float = 0.0,
        remittances: float = 0.0,
        investment_income: float = 0.0,
        unilateral_transfers: float = 0.0,
    ) -> CurrentAccountResult:
        """Calcula la cuenta corriente completa.

        Args:
            oil_revenues: Ingresos petroleros (USD).
            non_oil_exports: Exportaciones no petroleras (USD).
            imports: Importaciones totales (USD).
            services_net: Balanza de servicios (export - import, USD).
            remittances: Remesas recibidas (USD).
            investment_income: Ingresos por inversiones (intereses, dividendos).
            unilateral_transfers: Transferencias unilaterales netas (USD).

        Returns:
            CurrentAccountResult con el desglose.
        """
        balance = (
            oil_revenues
            + non_oil_exports
            - imports
            + services_net
            + remittances
            + investment_income
            + unilateral_transfers
        )

        return CurrentAccountResult(
            oil_revenues=oil_revenues,
            non_oil_exports=non_oil_exports,
            imports=imports,
            services_net=services_net,
            remittances=remittances,
            investment_income=investment_income,
            unilateral_transfers=unilateral_transfers,
            balance=round(balance, 2),
        )

    # --- Cuenta de Capital y Financiera ---

    def capital_account(
        self,
        fdi_inflow: float = 0.0,
        fdi_outflow: float = 0.0,
        portfolio_investment: float = 0.0,
        other_investment: float = 0.0,
        debt_amortization: float = 0.0,
        previous_reserves: float = 0.0,
        current_reserves: float = 0.0,
    ) -> CapitalAccountResult:
        """Calcula la cuenta de capital y financiera.

        Args:
            fdi_inflow: Inversión extranjera directa recibida (USD).
            fdi_outflow: IED enviada al exterior (USD).
            portfolio_investment: Inversión de portafolio neta (USD).
            other_investment: Otros flujos (préstamos, créditos, USD).
            debt_amortization: Amortizaciones de deuda (USD, positivo = pago).
            previous_reserves: Reservas del período anterior (USD).
            current_reserves: Reservas actuales (USD).

        Returns:
            CapitalAccountResult con el desglose.
        """
        reserve_changes = current_reserves - previous_reserves

        balance = (
            (fdi_inflow - fdi_outflow)
            + portfolio_investment
            + other_investment
            - debt_amortization
        )

        return CapitalAccountResult(
            fdi_inflow=fdi_inflow,
            fdi_outflow=fdi_outflow,
            portfolio_investment=portfolio_investment,
            other_investment=other_investment,
            debt_amortization=debt_amortization,
            reserve_changes=round(reserve_changes, 2),
            balance=round(balance, 2),
        )

    # --- Reservas ---

    def reserves_breakdown(
        self,
        total_reserves: float = 0.0,
        foreign_currencies: float = 0.0,
        gold_usd: float = 0.0,
        sdr: float = 0.0,
        imf_position: float = 0.0,
        other_assets: float = 0.0,
        monthly_imports: float = 0.0,
        annual_debt_service: float = 0.0,
    ) -> ReservesBreakdown:
        """Desglose de reservas internacionales.

        Args:
            total_reserves: Reservas totales (USD).
            foreign_currencies: Divisas (USD).
            gold_usd: Oro en USD.
            sdr: Derechos Especiales de Giro (USD).
            imf_position: Posición en el FMI (USD).
            other_assets: Otros activos líquidos (USD).
            monthly_imports: Importaciones mensuales (USD).
            annual_debt_service: Servicio de deuda anual (USD).

        Returns:
            ReservesBreakdown con el desglose.
        """
        months_coverage = 0.0
        if monthly_imports > 0:
            months_coverage = total_reserves / monthly_imports

        months_debt_service = 0.0
        if annual_debt_service > 0:
            months_debt_service = total_reserves / (annual_debt_service / 12)

        return ReservesBreakdown(
            total_usd=total_reserves,
            foreign_currencies=foreign_currencies,
            gold_usd=gold_usd,
            sdr=sdr,
            imf_position=imf_position,
            other_assets=other_assets,
            months_coverage=round(months_coverage, 1),
            months_debt_service=round(months_debt_service, 1),
        )

    # --- Ciclo del Petróleo ---

    def oil_cycle(
        self,
        production_mbd: float,
        oil_price_usd: float,
        extraction_cost_per_barrel: float = 15.0,
        pdvsa_royalty_pct: float = 33.0,
        pdvsa_corporate_tax_pct: float = 50.0,
        pdvsa_operating_cost_mbd: float = 0.3,
        debt_service_commitments: float = 0.0,
    ) -> OilCycleResult:
        """Análisis del ciclo petrolero completo.

        Args:
            production_mbd: Producción (mbd).
            oil_price_usd: Precio del petróleo (USD/barril).
            extraction_cost_per_barrel: Costo de extracción por barril (USD).
            pdvsa_royalty_pct: Regalías PDVSA (%).
            pdvsa_corporate_tax_pct: Impuesto corporativo PDVSA (%).
            pdvsa_operating_cost_mbd: Costo operativo PDVSA (mbd).
            debt_service_commitments: Compromisos de servicio de deuda (USD/año).

        Returns:
            OilCycleResult con el análisis del ciclo.
        """
        gross = self.estimate_oil_revenues(production_mbd, oil_price_usd)
        extraction = production_mbd * 1e6 * extraction_cost_per_barrel * 365  # mbd → barriles
        pdvsa_ops = pdvsa_operating_cost_mbd * 1e6 * oil_price_usd * 365

        # Regalías e impuestos
        royalty = gross * pdvsa_royalty_pct / 100
        taxable = gross - royalty - extraction - pdvsa_ops
        tax = max(0, taxable * pdvsa_corporate_tax_pct / 100)

        net_revenues = gross - royalty - tax - extraction - pdvsa_ops
        effective_cf = net_revenues - debt_service_commitments

        # Precio de equilibrio: costo total / producción (en barriles)
        total_cost = extraction + pdvsa_ops + (royalty + tax)
        breakeven = total_cost / (production_mbd * 1e6 * 365) if production_mbd > 0 else 0

        interpretation = ""
        if effective_cf < 0:
            interpretation = (
                f"FLUJO NEGATIVO: El fisco recibe ${net_revenues/1e6:.0f}M netos, "
                f"pero los compromisos de deuda (${debt_service_commitments/1e6:.0f}M) "
                f"superan los ingresos. La sostenibilidad fiscal es precaria."
            )
        elif net_revenues > 0:
            interpretation = (
                f"Ingresos netos del fisco: ${net_revenues/1e6:.0f}M. "
                f"Flujo efectivo después de deuda: ${effective_cf/1e6:.0f}M. "
            )
            if breakeven > oil_price_usd:
                interpretation += (
                    f"Precio de equilibrio (${breakeven:.0f}) supera el precio actual "
                    f"(${oil_price_usd:.0f}). Se requiere disciplina fiscal."
                )
            else:
                interpretation += f"Margen de seguridad: ${oil_price_usd - breakeven:.0f}/barril."
        else:
            interpretation = (
                f"Pérdida neta del fisco petrolero: ${abs(net_revenues)/1e6:.0f}M. "
                f"Los costos de extracción y regalías superan los ingresos."
            )

        return OilCycleResult(
            gross_revenues=round(gross, 2),
            extraction_cost=round(extraction, 2),
            pdvsa_share=round(royalty + tax, 2),
            net_revenues=round(net_revenues, 2),
            effective_cash_flow=round(effective_cf, 2),
            breakeven_price=round(breakeven, 2),
            interpretation=interpretation,
        )

    # --- Reservas Coverage ---

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

    # --- Análisis Completo ---

    def analyze(
        self,
        reserves: Optional[float] = None,
        gold_reserves: Optional[float] = None,
        oil_production_mbd: Optional[float] = None,
        oil_price_usd: Optional[float] = None,
        imports_monthly: Optional[float] = None,
        previous_reserves: Optional[float] = None,
        services_net: Optional[float] = None,
        remittances: Optional[float] = None,
        investment_income: Optional[float] = None,
        gold_exports: Optional[float] = None,
        agric_exports: Optional[float] = None,
        extraction_cost_per_barrel: Optional[float] = None,
        debt_service: Optional[float] = None,
        fdi_inflow: Optional[float] = None,
        fdi_outflow: Optional[float] = None,
    ) -> BalanceResult:
        """Análisis completo de balanza de pagos.

        Args:
            reserves: Reservas internacionales (USD).
            gold_reserves: Oro en reservas (USD).
            oil_production_mbd: Producción petrolera (mbd).
            oil_price_usd: Precio del petróleo (USD/barril).
            imports_monthly: Importaciones mensuales (USD).
            previous_reserves: Reservas del período anterior (USD).
            services_net: Balanza de servicios (USD).
            remittances: Remesas recibidas (USD).
            investment_income: Ingresos por inversiones (USD).
            gold_exports: Exportaciones de oro (USD).
            agric_exports: Exportaciones agrícolas (USD).
            extraction_cost_per_barrel: Costo extracción por barril (USD).
            debt_service: Servicio de deuda anual (USD).
            fdi_inflow: IED recibida (USD).
            fdi_outflow: IED enviada (USD).

        Returns:
            BalanceResult con análisis completo.
        """
        # 1. Cuenta corriente
        oil_rev = 0.0
        if oil_production_mbd and oil_price_usd:
            oil_rev = self.estimate_oil_revenues(oil_production_mbd, oil_price_usd)

        non_oil = 0.0
        if gold_exports or agric_exports:
            non_oil = self.estimate_non_oil_exports(
                gold_exports=gold_exports or 0,
                agric_exports=agric_exports or 0,
            )

        annual_imports = (imports_monthly or 0) * 12
        ca = self.current_account(
            oil_revenues=oil_rev,
            non_oil_exports=non_oil,
            imports=annual_imports,
            services_net=services_net or 0,
            remittances=remittances or 0,
            investment_income=investment_income or 0,
        )

        # 2. Cuenta de capital
        prev = previous_reserves or 0
        curr = reserves or 0
        cap = self.capital_account(
            fdi_inflow=fdi_inflow or 0,
            fdi_outflow=fdi_outflow or 0,
            previous_reserves=prev,
            current_reserves=curr,
        )

        # 3. Reservas
        res = self.reserves_breakdown(
            total_reserves=reserves or 0,
            gold_usd=gold_reserves or 0,
            monthly_imports=imports_monthly or 0,
            annual_debt_service=debt_service or 0,
        )

        # 4. Ciclo petrolero
        oil_cyc = self.oil_cycle(
            production_mbd=oil_production_mbd or 0,
            oil_price_usd=oil_price_usd or 0,
            extraction_cost_per_barrel=extraction_cost_per_barrel or 15.0,
            debt_service_commitments=debt_service or 0,
        )

        # 5. Score de sostenibilidad externa (0-100, menor = mejor)
        score_components = []
        if res.months_coverage > 0:
            if res.months_coverage < 3:
                score_components.append(90)
            elif res.months_coverage < 6:
                score_components.append(60)
            else:
                score_components.append(max(10, 100 - res.months_coverage * 5))

        if ca.balance < 0:
            deficit_ratio = abs(ca.balance) / (oil_rev if oil_rev > 0 else 1)
            score_components.append(min(100, deficit_ratio * 50))
        else:
            score_components.append(max(5, 30 - ca.balance / (oil_rev if oil_rev > 0 else 1) * 20))

        if oil_cyc.effective_cash_flow < 0:
            score_components.append(85)
        else:
            score_components.append(max(10, 50))

        sustainability_score = round(
            np.mean(score_components) if score_components else 50, 1
        )

        # 6. Interpretación general
        interpretation_parts = []

        if res.months_coverage > 0:
            if res.months_coverage < 3:
                interpretation_parts.append(
                    f"CRÍTICO: Las reservas cubren solo {res.months_coverage:.1f} meses de importaciones."
                )
            elif res.months_coverage < 6:
                interpretation_parts.append(
                    f"ADVERTENCIA: Reservas para {res.months_coverage:.1f} meses."
                )
            else:
                interpretation_parts.append(
                    f"Reservas cubren {res.months_coverage:.1f} meses de importaciones."
                )

        if ca.balance < 0:
            interpretation_parts.append(
                f"Déficit de cuenta corriente: ${abs(ca.balance)/1e6:.0f}M."
            )
        elif ca.balance > 0:
            interpretation_parts.append(
                f"Superávit de cuenta corriente: ${ca.balance/1e6:.0f}M."
            )

        if remittances and remittances > 0:
            interpretation_parts.append(
                f"Remesas: ${remittances/1e6:.0f}M (fuente importante de divisas)."
            )

        if oil_cyc.interpretation:
            interpretation_parts.append(oil_cyc.interpretation)

        if previous_reserves and reserves:
            change = (reserves - previous_reserves) / previous_reserves * 100
            if change < -10:
                interpretation_parts.append(
                    f"Las reservas cayeron {abs(change):.1f}% respecto al período anterior."
                )
            elif change > 10:
                interpretation_parts.append(
                    f"Las reservas subieron {change:.1f}% respecto al período anterior."
                )

        interpretation = " ".join(interpretation_parts) or "Datos insuficientes para análisis completo."

        return BalanceResult(
            current_account=ca,
            capital_account=cap,
            reserves=res,
            oil_cycle=oil_cyc,
            external_sustainability_score=sustainability_score,
            interpretation=interpretation,
        )
