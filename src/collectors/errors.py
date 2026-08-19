"""
Errores de la capa de recolección
=================================

Excepción única para fallos de collectors, distinguible de errores de
aplicación (el scheduler y el dashboard la capturan para degradar con gracia).
"""


class CollectorError(Exception):
    """Fallo de un collector (red, parseo o fuente no disponible)."""


class CollectorSourceError(CollectorError):
    """La fuente respondió pero el contenido no era el esperado."""