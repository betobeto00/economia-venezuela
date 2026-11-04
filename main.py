"""
Economía Venezuela - Punto de Entrada Principal
================================================

Desde el corte a n8n este módulo **no programa tareas**: solo prepara el
esquema y verifica la configuración. El calendario de jobs vive en los
workflows de ``n8n/workflows/``, que invocan al runner HTTP
(``src/api/runner.py``).

Uso:
    python main.py           # bootstrap: logging + esquema + resumen de estado
    python main.py --check   # solo comprueba DB y sale con 0/1 (para CI/Docker)
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config import settings


def setup_logging():
    """Configura el sistema de logging con rotación de archivos."""
    log_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(log_formatter)

    # Rotating file handler: max 5 MB por archivo, máximo 5 backups
    file_handler = RotatingFileHandler(
        "economia_ve.log",
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(log_formatter)

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        handlers=[console_handler, file_handler],
    )
    return logging.getLogger(__name__)


def init_database():
    """Crea el esquema de base de datos si no existe."""
    from src.db.session import init_db

    init_db()


def database_ok() -> bool:
    """Devuelve ``True`` si la base de datos configurada responde."""
    try:
        from sqlalchemy import text

        from src.db.session import get_engine

        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as exc:  # noqa: BLE001 - el bootstrap debe explicar el fallo
        logging.getLogger(__name__).error("Base de datos no disponible: %s", exc)
        return False


def main(argv=None) -> int:
    """Bootstrap del sistema (sin scheduler).

    Returns:
        Código de salida: 0 si la base responde, 1 si no.
    """
    argv = sys.argv[1:] if argv is None else argv
    logger = setup_logging()

    logger.info("Iniciando %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Entorno: %s | Zona horaria: %s", settings.ENVIRONMENT, settings.TIMEZONE)

    try:
        init_database()
        logger.info("Base de datos lista")
    except Exception as exc:  # noqa: BLE001 - se reporta abajo como fallo
        logger.error("No se pudo inicializar la base de datos: %s", exc)

    ok = database_ok()
    logger.info(
        "Scheduler: desactivado (los jobs los programa n8n; ver n8n/README.md)"
    )
    logger.info("Runner HTTP: %s:%s", "127.0.0.1", settings.RUNNER_PORT)
    logger.info("Estado de la base de datos: %s", "ok" if ok else "fallo")

    if "--check" in argv:
        return 0 if ok else 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
