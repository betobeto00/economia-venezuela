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
    feature_importance: Dict[str, float] = None
    interpretation: str = ""

    def __post_init__(self):
        if self.feature_importance is None:
            self.feature_importance = {}


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

        # ── Nuevas features de series temporales ──
        if "parallel_rate" in df.columns:
            pr = df["parallel_rate"]
            # Momentum: cambio relativo a 7 días
            features["momentum_7d"] = pr.pct_change(7) * 100
            # Volatilidad: desviación estándar rolling de 7 días
            features["volatility_7d"] = pr.pct_change().rolling(7).std() * 100
            # Aceleración: cambio del cambio
            delta = pr.pct_change() * 100
            features["acceleration"] = delta.diff()
            # Nivel normalizado (z-score rolling 14 días)
            roll_mean = pr.rolling(14).mean()
            roll_std = pr.rolling(14).std()
            features["zscore_14d"] = (pr - roll_mean) / roll_std.clip(lower=1)
            # Tasa de cambio logarítmica
            features["log_return"] = np.log(pr / pr.shift(1)).clip(-1, 1)

        if "official_rate" in df.columns:
            ofr = df["official_rate"]
            features["delta_official"] = ofr.pct_change() * 100
            features["volatility_official_7d"] = ofr.pct_change().rolling(7).std() * 100

        # Sentimiento rolling
        if "sentiment_score" in df.columns:
            features["sentiment_ma7"] = df["sentiment_score"].rolling(7).mean()
            features["sentiment_momentum"] = df["sentiment_score"].diff()

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

        # Importancia de features
        importances = dict(zip(
            self.feature_names,
            [round(float(x), 4) for x in self.model.feature_importances_],
        ))
        # Top 5 features más importantes
        top_features = sorted(importances.items(), key=lambda x: -x[1])[:5]
        top_str = ", ".join(f"{k}={v:.2%}" for k, v in top_features)

        interpretation = (
            f"Modelo RandomForest. "
            f"Predicción: {prediction:.2f}% (IC 95%: [{prediction-1.96*std:.2f}, {prediction+1.96*std:.2f}]). "
            f"Variables más relevantes: {top_str}."
        )

        return NowcastResult(
            indicator="inflacion_mensual",
            predicted_value=round(prediction, 2),
            confidence_lower=round(prediction - 1.96 * std, 2),
            confidence_upper=round(prediction + 1.96 * std, 2),
            model="RandomForest",
            features_used=self.feature_names,
            feature_importance=importances,
            interpretation=interpretation,
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

        # Estimar incertidumbre con staging (GradientBoosting)
        staged_preds = np.array([
            est.predict(X_clean.iloc[[-1]])[0]
            for est in self.model.estimators_.ravel()
        ])
        std = float(np.std(staged_preds))

        # Importancia de features
        importances = dict(zip(
            self.feature_names,
            [round(float(x), 4) for x in self.model.feature_importances_],
        ))
        top_features = sorted(importances.items(), key=lambda x: -x[1])[:5]
        top_str = ", ".join(f"{k}={v:.2%}" for k, v in top_features)

        interpretation = (
            f"Modelo GradientBoosting. "
            f"Predicción PIB: {prediction:.2f}% (IC 95%: [{prediction-1.96*std:.2f}, {prediction+1.96*std:.2f}]). "
            f"Variables más relevantes: {top_str}."
        )

        return NowcastResult(
            indicator="pib_trimestral",
            predicted_value=round(prediction, 2),
            confidence_lower=round(prediction - 1.96 * std, 2),
            confidence_upper=round(prediction + 1.96 * std, 2),
            model="GradientBoosting",
            features_used=self.feature_names,
            feature_importance=importances,
            interpretation=interpretation,
        )
