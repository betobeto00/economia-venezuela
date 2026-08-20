"""
Sistema de Alertas Económicas
===============================

Monitorea indicadores clave y genera alertas cuando superan umbrales
críticos. Las alertas se pueden configurar por indicador y se muestran
en el dashboard.

Tipos de alerta:
- Cambio significativo en tipo de cambio
- Inflación fuera de rango esperado
- Brecha cambiaria crítica
- Volatilidad extrema (GARCH)
- Indicador macro desactualizado
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveles de severidad de alerta."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(Enum):
    """Tipos de alerta económica."""
    EXCHANGE_RATE = "exchange_rate"
    INFLATION = "inflation"
    SPREAD = "spread"
    VOLATILITY = "volatility"
    MACRO_STALE = "macro_stale"
    IBC = "ibc"


@dataclass
class Alert:
    """Una alerta generada por el sistema."""
    type: AlertType
    level: AlertLevel
    title: str
    message: str
    indicator: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "level": self.level.value,
            "title": self.title,
            "message": self.message,
            "indicator": self.indicator,
            "current_value": self.current_value,
            "threshold": self.threshold,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AlertRule:
    """Regla de alerta para un indicador."""
    type: AlertType
    indicator: str
    warning_threshold: float
    critical_threshold: float
    description: str
    check_fn: Optional[Callable] = None


# Reglas por defecto
DEFAULT_RULES = [
    AlertRule(
        type=AlertType.EXCHANGE_RATE,
        indicator="parallel_rate",
        warning_threshold=20.0,  # 20% variación diaria
        critical_threshold=50.0,  # 50% variación diaria
        description="Variación del tipo de cambio paralelo",
    ),
    AlertRule(
        type=AlertType.SPREAD,
        indicator="brecha_porcentaje",
        warning_threshold=30.0,  # 30% de brecha
        critical_threshold=50.0,  # 50% de brecha
        description="Brecha cambiaria oficial vs paralelo",
    ),
    AlertRule(
        type=AlertType.INFLATION,
        indicator="monthly_inflation",
        warning_threshold=20.0,  # 20% mensual
        critical_threshold=50.0,  # 50% mensual (hiperinflación)
        description="Inflación mensual",
    ),
    AlertRule(
        type=AlertType.IBC,
        indicator="ibc_change_pct",
        warning_threshold=5.0,  # 5% variación
        critical_threshold=10.0,  # 10% variación
        description="Variación del IBC",
    ),
]


class AlertManager:
    """Gestor de alertas del sistema."""

    def __init__(self, rules: Optional[List[AlertRule]] = None):
        self.rules = rules or DEFAULT_RULES
        self.alerts: List[Alert] = []
        self._alert_history: List[Alert] = []

    def check_exchange_rate(
        self,
        parallel_rate: float,
        official_rate: float,
        prev_parallel: Optional[float] = None,
    ) -> List[Alert]:
        """Verifica alertas de tipo de cambio."""
        alerts = []

        # Brecha cambiaria
        if official_rate > 0:
            spread = (parallel_rate / official_rate - 1) * 100
            for rule in self.rules:
                if rule.type == AlertType.SPREAD and rule.indicator == "brecha_porcentaje":
                    if spread >= rule.critical_threshold:
                        alerts.append(Alert(
                            type=AlertType.SPREAD,
                            level=AlertLevel.CRITICAL,
                            title="Brecha cambiaria crítica",
                            message=f"La brecha cambiaria alcanzó {spread:.1f}%",
                            indicator="brecha_porcentaje",
                            current_value=spread,
                            threshold=rule.critical_threshold,
                        ))
                    elif spread >= rule.warning_threshold:
                        alerts.append(Alert(
                            type=AlertType.SPREAD,
                            level=AlertLevel.WARNING,
                            title="Brecha cambiaria elevada",
                            message=f"La brecha cambiaria es {spread:.1f}%",
                            indicator="brecha_porcentaje",
                            current_value=spread,
                            threshold=rule.warning_threshold,
                        ))

        # Variación del paralelo
        if prev_parallel and prev_parallel > 0:
            change_pct = abs((parallel_rate / prev_parallel - 1) * 100)
            for rule in self.rules:
                if rule.type == AlertType.EXCHANGE_RATE:
                    if change_pct >= rule.critical_threshold:
                        alerts.append(Alert(
                            type=AlertType.EXCHANGE_RATE,
                            level=AlertLevel.CRITICAL,
                            title="Tasa de cambio volátil",
                            message=f"El dólar paralelo varió {change_pct:.1f}%",
                            indicator="parallel_rate",
                            current_value=parallel_rate,
                            threshold=rule.critical_threshold,
                        ))

        self.alerts.extend(alerts)
        return alerts

    def check_inflation(self, monthly_rate: float) -> List[Alert]:
        """Verifica alertas de inflación."""
        alerts = []
        for rule in self.rules:
            if rule.type == AlertType.INFLATION:
                if monthly_rate >= rule.critical_threshold:
                    alerts.append(Alert(
                        type=AlertType.INFLATION,
                        level=AlertLevel.CRITICAL,
                        title="Inflación extrema",
                        message=f"Inflación mensual de {monthly_rate:.1f}%",
                        indicator="monthly_inflation",
                        current_value=monthly_rate,
                        threshold=rule.critical_threshold,
                    ))
                elif monthly_rate >= rule.warning_threshold:
                    alerts.append(Alert(
                        type=AlertType.INFLATION,
                        level=AlertLevel.WARNING,
                        title="Inflación elevada",
                        message=f"Inflación mensual de {monthly_rate:.1f}%",
                        indicator="monthly_inflation",
                        current_value=monthly_rate,
                        threshold=rule.warning_threshold,
                    ))
        self.alerts.extend(alerts)
        return alerts

    def check_ibc(self, change_pct: float) -> List[Alert]:
        """Verifica alertas del IBC."""
        alerts = []
        for rule in self.rules:
            if rule.type == AlertType.IBC:
                if abs(change_pct) >= rule.critical_threshold:
                    alerts.append(Alert(
                        type=AlertType.IBC,
                        level=AlertLevel.CRITICAL,
                        title="IBC con variación extrema",
                        message=f"El IBC varió {change_pct:+.1f}%",
                        indicator="ibc_change_pct",
                        current_value=change_pct,
                        threshold=rule.critical_threshold,
                    ))
        self.alerts.extend(alerts)
        return alerts

    def get_active_alerts(self, limit: int = 20) -> List[Alert]:
        """Retorna las alertas más recientes."""
        return sorted(self.alerts, key=lambda a: a.timestamp, reverse=True)[:limit]

    def get_alerts_by_level(self, level: AlertLevel) -> List[Alert]:
        """Retorna alertas filtradas por nivel."""
        return [a for a in self.alerts if a.level == level]

    def clear_old_alerts(self, hours: int = 24) -> int:
        """Limpia alertas más antiguas que X horas."""
        cutoff = datetime.now(timezone.utc).timestamp() - hours * 3600
        before = len(self.alerts)
        self.alerts = [
            a for a in self.alerts
            if a.timestamp.timestamp() > cutoff
        ]
        return before - len(self.alerts)
