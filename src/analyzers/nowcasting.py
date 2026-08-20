"""
Nowcasting (Predicción en Tiempo Real)
========================================

Modelos de Machine Learning para predecir PIB e inflación en tiempo real
usando variables de alta frecuencia (tipo de cambio, precio del petróleo,
datos de sentimiento, etc.).

Enfoques:
1. Random Forest para nowcasting de inflación mensual
2. XGBoost para nowcasting de PIB trimestral
3. Regresión dinámica con variables proxy

El PIB se publica con rezago trimestral; este módulo usa variables de
alta frecuencia para estimar el valor actual antes de la publicación oficial.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class NowcastResult:
    """Resultado de un nowcast."""
    indicator: str
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    model: str
    features_used: List[str]
    r_squared: float = 0.0


class InflationNowcaster:
    """Nowcasting de inflación mensual usando variables de alta frecuencia.

    Variables proxy:
    - Tipo de cambio paralelo (proxy de expectativas)
    - Precio del petróleo (impacto en ingresos)
    - Sentimiento público (anticipación)
    - Inflación rezagada (inercia)
    """

    def __init__(self):
        self.model = None
        self.feature_names = []

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara features para el nowcasting de inflación.

        Args:
            df: DataFrame con columnas:
                - official_rate, parallel_rate (tipos de cambio)
                - oil_price (precio petróleo)
                - sentiment_score (sentimiento)
                - inflation_lag1, inflation_lag2 (inflación rezagada)

        Returns:
            DataFrame con features preparadas.
        """
        features = pd.DataFrame()

        # Log-transform de tipos de cambio
        if "parallel_rate" in df.columns:
            features["log_parallel"] = np.log(df["parallel_rate"].clip(lower=1))
        if "official_rate" in df.columns:
            features["log_official"] = np.log(df["official_rate"].clip(lower=1))

        # Brecha cambiaria
        if "parallel_rate" in df.columns and "official_rate" in df.columns:
            features["brecha"] = (df["parallel_rate"] / df["official_rate"] - 1) * 100

        # Petróleo
        if "oil_price" in df.columns:
            features["log_oil"] = np.log(df["oil_price"].clip(lower=1))

        # Sentimiento
        if "sentiment_score" in df.columns:
            features["sentiment"] = df["sentiment_score"]

        # Inercia (inflación rezagada)
        if "inflation_lag1" in df.columns:
            features["inflation_lag1"] = df["inflation_lag1"]
        if "inflation_lag2" in df.columns:
            features["inflation_lag2"] = df["inflation_lag2"]

        # Variación del tipo de cambio
        if "parallel_rate" in df.columns:
            features["delta_parallel"] = df["parallel_rate"].pct_change() * 100

        self.feature_names = list(features.columns)
        return features

    def train(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Entrena el modelo de nowcasting.

        Args:
            X: Features preparadas.
            y: Target (inflación mensual real).

        Returns:
            R² del modelo en entrenamiento.
        """
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import cross_val_score

        # Limpiar NaN
        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask]
        y_clean = y[mask]

        if len(X_clean) < 10:
            logger.warning("Datos insuficientes para nowcasting: %d filas", len(X_clean))
            return 0.0

        self.model = RandomForestRegressor(
            n_estimators=100, max_depth=5, random_state=42
        )
        self.model.fit(X_clean, y_clean)

        # Evaluar con cross-validation
        scores = cross_val_score(self.model, X_clean, y_clean, cv=min(5, len(X_clean)), scoring="r2")
        r_squared = float(np.mean(scores))
        logger.info("Nowcasting inflación: R² = %.3f", r_squared)
        return r_squared

    def predict(self, X: pd.DataFrame) -> NowcastResult:
        """Predice la inflación del período actual.

        Args:
            X: Features del período actual.

        Returns:
            NowcastResult con predicción e intervalos.
        """
        if self.model is None:
            raise RuntimeError("Modelo no entrenado. Ejecuta train() primero.")

        X_clean = X[self.feature_names].fillna(0)
        prediction = float(self.model.predict(X_clean.iloc[[-1]])[0])

        # Estimar intervalo de confianza usando std de los árboles
        tree_predictions = np.array([
            tree.predict(X_clean.iloc[[-1]])[0]
            for tree in self.model.estimators_
        ])
        std = float(np.std(tree_predictions))

        return NowcastResult(
            indicator="inflacion_mensual",
            predicted_value=round(prediction, 2),
            confidence_lower=round(prediction - 1.96 * std, 2),
            confidence_upper=round(prediction + 1.96 * std, 2),
            model="RandomForest",
            features_used=self.feature_names,
        )


class GDPNowcaster:
    """Nowcasting de PIB trimestral usando variables de alta frecuencia.

    Variables proxy:
    - Producción petrolera (proxy del sector petrolero)
    - Tipo de cambio (actividad económica)
    - Consumo de electricidad (si disponible)
    - Sentimiento empresarial
    """

    def __init__(self):
        self.model = None
        self.feature_names = []

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepara features para el nowcasting de PIB."""
        features = pd.DataFrame()

        if "oil_production" in df.columns:
            features["oil_prod"] = df["oil_production"]

        if "parallel_rate" in df.columns:
            features["log_parallel"] = np.log(df["parallel_rate"].clip(lower=1))

        if "official_rate" in df.columns:
            features["log_official"] = np.log(df["official_rate"].clip(lower=1))

        if "sentiment_score" in df.columns:
            features["sentiment"] = df["sentiment_score"]

        if "gdp_lag1" in df.columns:
            features["gdp_lag1"] = df["gdp_lag1"]

        self.feature_names = list(features.columns)
        return features

    def train(self, X: pd.DataFrame, y: pd.Series) -> float:
        """Entrena el modelo de nowcasting de PIB."""
        from sklearn.ensemble import GradientBoostingRegressor
        from sklearn.model_selection import cross_val_score

        mask = ~(X.isna().any(axis=1) | y.isna())
        X_clean = X[mask]
        y_clean = y[mask]

        if len(X_clean) < 8:
            logger.warning("Datos insuficientes para nowcasting PIB: %d filas", len(X_clean))
            return 0.0

        self.model = GradientBoostingRegressor(
            n_estimators=50, max_depth=3, random_state=42
        )
        self.model.fit(X_clean, y_clean)

        scores = cross_val_score(self.model, X_clean, y_clean, cv=min(3, len(X_clean)), scoring="r2")
        r_squared = float(np.mean(scores))
        logger.info("Nowcasting PIB: R² = %.3f", r_squared)
        return r_squared

    def predict(self, X: pd.DataFrame) -> NowcastResult:
        """Predice el PIB del trimestre actual."""
        if self.model is None:
            raise RuntimeError("Modelo no entrenado. Ejecuta train() primero.")

        X_clean = X[self.feature_names].fillna(0)
        prediction = float(self.model.predict(X_clean.iloc[[-1]])[0])

        tree_predictions = np.array([
            tree.predict(X_clean.iloc[[-1]])[0]
            for tree in self.model.estimators_
        ])
        std = float(np.std(tree_predictions))

        return NowcastResult(
            indicator="pib_trimestral",
            predicted_value=round(prediction, 2),
            confidence_lower=round(prediction - 1.96 * std, 2),
            confidence_upper=round(prediction + 1.96 * std, 2),
            model="GradientBoosting",
            features_used=self.feature_names,
        )
