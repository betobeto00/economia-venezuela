"""
Modelos de datos de mercado y macro (Fase A)
============================================

Entidades normalizadas que producen los collectors oficiales e
internacionales. Diseño:
- ``source``: identifica el emisor de los datos (bcv, ovf, world_bank, onapre).
- Fechas como ``datetime`` y períodos como ``YYYY-MM`` para facilitar series.
"""

from datetime import date as _date
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ExchangeRate(BaseModel):
    """Tasa de cambio de una moneda a USD/VES en una fecha.

    Atributos:
        source: Emisor/mercado (bcv, ovf, paralelo, binance, ...).
        currency: Código de moneda (usd, eur, ...).
        rate: Valor de la tasa (bolívares por unidad de currency).
        date: Fecha de la tasa.
        variation_pct: Variación porcentual vs. día anterior (opcional).
    """

    source: str
    currency: str
    rate: float
    date: datetime
    variation_pct: Optional[float] = None

    @property
    def iso_date(self) -> str:
        return self.date.strftime("%Y-%m-%d")


class InflationPoint(BaseModel):
    """Punto de inflación mensual para un período.

    Atributos:
        source: Emisor (bcv, ovf, ine, world_bank).
        period: Período en formato ``YYYY-MM``.
        monthly_rate: Variación porcentual mensual del IPC.
        annual_rate: Variación porcentual interanual del IPC.
        index: Índice de precios (nivel, opcional).
    """

    source: str
    period: str
    monthly_rate: Optional[float] = None
    annual_rate: Optional[float] = None
    index: Optional[float] = None


class GDPPoint(BaseModel):
    """Dato de PIB de un país/año.

    Atributos:
        indicator: Código del indicador (p.ej. ``NY.GDP.MKTP.CD``).
        value: Valor del indicador.
        year: Año del dato.
        country: Código ISO del país (``VE`` por defecto).
        source: Emisor (``world_bank`` por defecto).
    """

    indicator: str
    value: float
    year: int
    country: str = "VE"
    source: str = "world_bank"


class BudgetExecution(BaseModel):
    """Registro de ejecución presupuestaria (ONAPRE).

    Atributos:
        year: Año del presupuesto.
        entity: Ente/partida presupuestaria.
        amount_bs: Monto en bolívares (opcional).
        amount_usd: Monto en dólares (opcional).
        source: Emisor (``onapre`` por defecto).
    """

    year: int
    entity: str
    amount_bs: Optional[float] = None
    amount_usd: Optional[float] = None
    source: str = "onapre"
    url: Optional[str] = Field(default=None, description="Fuente del dato")


class IndexPoint(BaseModel):
    """Cierre de un índice bursátil en una fecha (p.ej. IBC de Caracas).

    Atributos:
        source: Emisor (``bvc`` por defecto).
        symbol: Símbolo del índice/acción.
        value: Valor de cierre.
        date: Fecha del cierre.
    """

    source: str = "bvc"
    symbol: str
    value: float
    date: datetime


class IndicatorPoint(BaseModel):
    """Punto de un indicador socioeconómico (pobreza, empleo, producción).

    Atributos:
        source: Emisor (``ine``, ``opec``, ...).
        indicator: Nombre/etiqueta del indicador.
        value: Valor numérico.
        period: Período del dato (``2025``, ``2026-12``, ...).
        unit: Unidad opcional (``%``, ``mbd``, ``USD``, ...).
    """

    source: str
    indicator: str
    value: float
    period: str
    unit: Optional[str] = None


class FiscalDocument(BaseModel):
    """Documento/informe fiscal localizado (CGR, AN, MPPEF, gaceta).

    Atributos:
        source: Emisor (``cgr``, ``an``, ``mppef``, ``gaceta``, ...).
        title: Título del documento.
        url: URL del documento.
        year: Año del documento (opcional).
        date: Fecha del documento (opcional).
        description: Resumen/contenido de impacto del documento (opcional).
    """

    source: str
    title: str
    url: str
    year: Optional[int] = None
    date: Optional[_date] = None
    description: Optional[str] = None