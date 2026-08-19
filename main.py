"""
Economía Venezuela - Punto de Entrada Principal
"""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings
from src import __version__


def setup_logging():
    """Configura el sistema de logging"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("economia_ve.log", encoding="utf-8")
        ]
    )
    return logging.getLogger(__name__)


def main():
    """Función principal de la aplicación"""
    logger = setup_logging()
    
    logger.info(f"Iniciando {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Entorno: {settings.ENVIRONMENT}")
    logger.info(f"Modo debug: {settings.DEBUG}")
    
    # TODO: Implementar lógica principal aquí
    # 1. Conectar a base de datos
    # 2. Iniciar collectors
    # 3. Iniciar scheduler
    # 4. Iniciar dashboard (opcional)
    
    logger.info("Sistema inicializado correctamente")
    logger.info("Presiona Ctrl+C para detener")
    
    try:
        # Mantener el sistema ejecutándose
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Deteniendo sistema...")


if __name__ == "__main__":
    main()
