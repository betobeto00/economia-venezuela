"""
Comparaciones Regionales
=========================

Compara indicadores macroeconómicos de Venezuela con el resto de
Latinoamérica y economías similares (Argentina, Turquía).

Fuentes:
- CEPAL: datos regionales
- World Bank: indicadores por país
- IMF: World Economic Outlook

Permite identificar convergencia/divergencia macroeconómica.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

# Economías comparables
COMPARABLE_COUNTRIES = {
    "VEN": "Venezuela",
    "ARG": "Argentina",
    "TUR": "Turquía",
    "ECU": "Ecuador",
    "COL": "Colombia",
    "PER": "Perú",
    "CHL": "Chile",
    "BRA": "Brasil",
}

# Indicadores a comparar
INDICATORS = {
    "NY.GDP.MKTP.CD": "PIB (USD)",
    "NY.GDP.MKTP.KD.ZG": "Crecimiento PIB (%)",
    "FP.CPI.TOTL.ZG": "Inflación (%)",
    "BN.CAB.XOKA.CD": "Cuenta Corriente (USD)",
    "GC.DOD.TOTL.GD.ZS": "Deuda/PIB (%)",
}


@dataclass
class CountryIndicator:
    """Indicador de un país para comparación."""
    country_code: str
    country_name: str
    indicator: str
    indicator_name: str
    value: float
    period: str
    source: str = "World Bank"


@dataclass
class RegionalComparison:
    """Resultado de una comparación regional."""
    indicator: str
    indicator_name: str
    venezuela: Optional[CountryIndicator]
    latam_average: Optional[float]
    rankings: List[CountryIndicator]  # Ordenado por valor
    interpretation: str


class RegionalAnalyzer:
    """Analizador de comparaciones regionales."""

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}

    def fetch_indicator(
        self,
        indicator_code: str,
        countries: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        """Obtiene un indicador para múltiples países.

        Args:
            indicator_code: Código del indicador World Bank.
            countries: Lista de códigos ISO de países.

        Returns:
            DataFrame con columnas: country, year, value.
        """
        if indicator_code in self._cache:
            return self._cache[indicator_code]

        countries = countries or list(COMPARABLE_COUNTRIES.keys())

        try:
            import wbgapi as wb

            data = []
            for country in countries:
                try:
                    series = wb.data.DataFrame(
                        indicator_code, country, time=range(2020, 2027), labels=True
                    )
                    if not series.empty:
                        for year_col in series.columns:
                            if year_col.startswith("YR"):
                                year = int(year_col[2:])
                                value = series[year_col].iloc[0]
                                if pd.notna(value):
                                    data.append({
                                        "country": COMPARABLE_COUNTRIES.get(country, country),
                                        "country_code": country,
                                        "year": year,
                                        "value": float(value),
                                    })
                except Exception:
                    continue

            df = pd.DataFrame(data)
            self._cache[indicator_code] = df
            return df

        except ImportError:
            logger.warning("wbgapi no instalado para comparaciones regionales")
            return pd.DataFrame()
        except Exception as exc:
            logger.warning("Error fetching indicator %s: %s", indicator_code, exc)
            return pd.DataFrame()

    def compare(
        self,
        indicator_code: str,
        year: int = 2025,
    ) -> Optional[RegionalComparison]:
        """Compara un indicador de Venezuela con la región.

        Args:
            indicator_code: Código del indicador World Bank.
            year: Año a comparar.

        Returns:
            RegionalComparison o None si no hay datos.
        """
        df = self.fetch_indicator(indicator_code)
        if df.empty:
            return None

        # Filtrar por año
        year_data = df[df["year"] == year]
        if year_data.empty:
            # Tomar el año más reciente disponible
            latest_year = df["year"].max()
            year_data = df[df["year"] == latest_year]

        if year_data.empty:
            return None

        # Datos de Venezuela
        ven_data = year_data[year_data["country_code"] == "VEN"]
        venezuela = None
        if not ven_data.empty:
            row = ven_data.iloc[0]
            venezuela = CountryIndicator(
                country_code="VEN",
                country_name="Venezuela",
                indicator=indicator_code,
                indicator_name=INDICATORS.get(indicator_code, indicator_code),
                value=row["value"],
                period=str(int(row["year"])),
            )

        # Promedio regional (sin Venezuela)
        latam = year_data[year_data["country_code"] != "VEN"]
        latam_avg = float(latam["value"].mean()) if not latam.empty else None

        # Rankings
        rankings = []
        for _, row in year_data.sort_values("value", ascending=False).iterrows():
            rankings.append(CountryIndicator(
                country_code=row["country_code"],
                country_name=row["country"],
                indicator=indicator_code,
                indicator_name=INDICATORS.get(indicator_code, indicator_code),
                value=row["value"],
                period=str(int(row["year"])),
            ))

        # Interpretación
        interpretation = ""
        if venezuela and latam_avg is not None:
            diff = venezuela.value - latam_avg
            indicator_name = INDICATORS.get(indicator_code, indicator_code)

            if "PIB" in indicator_name and "USD" in indicator_name:
                # PIB: mostrar como ratio vs promedio
                ratio = venezuela.value / latam_avg if latam_avg > 0 else 0
                if ratio > 1:
                    interpretation = f"Venezuela tiene un PIB {ratio:.1f}x el promedio regional."
                else:
                    interpretation = f"Venezuela tiene un PIB {ratio:.0%} del promedio regional."
            elif "Crecimiento" in indicator_name:
                if diff > 0:
                    interpretation = f"Venezuela crece {abs(diff):.1f} puntos por encima del promedio regional."
                else:
                    interpretation = f"Venezuela crece {abs(diff):.1f} puntos por debajo del promedio regional."
            elif "Inflación" in indicator_name:
                if diff > 0:
                    interpretation = f"La inflación de Venezuela es {abs(diff):.1f} puntos mayor al promedio regional."
                else:
                    interpretation = f"La inflación de Venezuela es {abs(diff):.1f} puntos menor al promedio regional."
            else:
                if diff > 0:
                    interpretation = f"Venezuela está {abs(diff):.1f} puntos por encima del promedio."
                else:
                    interpretation = f"Venezuela está {abs(diff):.1f} puntos por debajo del promedio."

        return RegionalComparison(
            indicator=indicator_code,
            indicator_name=INDICATORS.get(indicator_code, indicator_code),
            venezuela=venezuela,
            latam_average=latam_avg,
            rankings=rankings,
            interpretation=interpretation,
        )

    def full_comparison(self, year: int = 2025) -> Dict[str, RegionalComparison]:
        """Comparación completa de todos los indicadores."""
        results = {}
        for code, name in INDICATORS.items():
            comparison = self.compare(code, year)
            if comparison:
                results[name] = comparison
        return results
