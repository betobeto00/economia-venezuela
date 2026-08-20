"""
Índice de Actividad Económica (IAE)
=====================================

Proxy en tiempo real del PIB usando variables de alta frecuencia.
El PIB se publica con rezago trimestral; este índice estima la
actividad económica actual usando:

1. Tipo de cambio paralelo (proxy de actividad comercial)
2. Producción petrolera (sector petrolero)
3. Sentimiento público (anticipación)
4. Noticias económicas (frecuencia de menciones)

El IAE se calcula como un índice compuesto (0-100) donde:
- 100 = actividad normal de referencia
- >100 = expansión
- <100 = contracción
"""

import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class IAEResult:
    """Resultado del cálculo del IAE."""
    value: float  # Índice compuesto (0-100+)
    components: dict  # Desglose por componente
    trend: str  # "expansion", "contraction", "stable"
    period: str


class IAEIndex:
    """Índice de Actividad Económica en tiempo real."""

    def __init__(self):
        # Pesos para el índice compuesto
        self.weights = {
            "exchange_rate": 0.30,  # Tipo de cambio
            "oil_production": 0.25,  # Producción petrolera
            "sentiment": 0.20,  # Sentimiento
            "news_frequency": 0.15,  # Frecuencia de noticias
            "inflation": 0.10,  # Inflación (inverso)
        }

    def normalize(self, value: float, min_val: float, max_val: float) -> float:
        """Normaliza un valor al rango 0-100."""
        if max_val == min_val:
            return 50.0
        return max(0, min(100, ((value - min_val) / (max_val - min_val)) * 100))

    def calculate_exchange_rate_component(
        self,
        current_rate: float,
        avg_rate_30d: float,
    ) -> float:
        """Componente del tipo de cambio: estabilidad = buena actividad."""
        if avg_rate_30d == 0:
            return 50.0
        # Si el dólar está estable o baja → actividad positiva
        change = (current_rate / avg_rate_30d - 1) * 100
        # Cambio positivo (dólar sube) = actividad negativa
        return self.normalize(-change, -50, 50)

    def calculate_oil_component(
        self,
        current_production: float,
        baseline_production: float = 1.0,
    ) -> float:
        """Componente petrolero: más producción = más actividad."""
        return self.normalize(current_production, 0, baseline_production * 1.5)

    def calculate_sentiment_component(
        self,
        mean_sentiment: float,
    ) -> float:
        """Componente de sentimiento: positivo = buena actividad."""
        return self.normalize(mean_sentiment, -1, 1)

    def calculate_news_component(
        self,
        news_count_7d: int,
        baseline_count: int = 50,
    ) -> float:
        """Componente de noticias: más noticias económicas = más actividad."""
        return self.normalize(news_count_7d, 0, baseline_count * 2)

    def calculate_inflation_component(
        self,
        monthly_inflation: float,
    ) -> float:
        """Componente de inflación: menos inflación = mejor actividad."""
        return self.normalize(-monthly_inflation, -100, 0)

    def calculate(
        self,
        parallel_rate: float = 0,
        avg_rate_30d: float = 0,
        oil_production: float = 0,
        sentiment_score: float = 0,
        news_count_7d: int = 0,
        monthly_inflation: float = 0,
    ) -> IAEResult:
        """Calcula el IAE compuesto.

        Args:
            parallel_rate: Tipo de cambio paralelo actual.
            avg_rate_30d: Promedio del paralelo en 30 días.
            oil_production: Producción petrolera (mbd).
            sentiment_score: Sentimiento promedio (-1 a 1).
            news_count_7d: Cantidad de noticias económicas en 7 días.
            monthly_inflation: Inflación mensual (%).

        Returns:
            IAEResult con el índice y desglose.
        """
        components = {}

        if parallel_rate > 0 and avg_rate_30d > 0:
            components["exchange_rate"] = self.calculate_exchange_rate_component(
                parallel_rate, avg_rate_30d
            )

        if oil_production > 0:
            components["oil_production"] = self.calculate_oil_component(oil_production)

        if sentiment_score != 0:
            components["sentiment"] = self.calculate_sentiment_component(sentiment_score)

        if news_count_7d > 0:
            components["news_frequency"] = self.calculate_news_component(news_count_7d)

        if monthly_inflation > 0:
            components["inflation"] = self.calculate_inflation_component(monthly_inflation)

        # Calcular índice compuesto (promedio ponderado)
        if components:
            total_weight = sum(
                self.weights[k] for k in components if k in self.weights
            )
            if total_weight > 0:
                value = sum(
                    components[k] * self.weights[k]
                    for k in components if k in self.weights
                ) / total_weight
            else:
                value = 50.0
        else:
            value = 50.0

        # Determinar tendencia
        if value > 55:
            trend = "expansion"
        elif value < 45:
            trend = "contraction"
        else:
            trend = "stable"

        return IAEResult(
            value=round(value, 1),
            components=components,
            trend=trend,
            period="actual",
        )
