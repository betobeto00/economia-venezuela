"""
Recolección de datos de mercado (Fase A)
========================================

Collectors de tasas de cambio e inflación de fuentes de mercado:
- BCV (dólar oficial, IPC oficial)
- OVF (Observatorio Venezolano de Finanzas: IPC alternativo)

Cada collector normaliza a los modelos de ``src.models.market`` y usa
``src.collectors.http`` para la red (parcheable en tests).
"""