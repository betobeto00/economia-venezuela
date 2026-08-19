"""
Capa de acceso a datos (SQLAlchemy)
==================================

Configuración del motor, sesiones y base declarativa. El motor se construye
de forma perezosa (get_engine) para que importar los módulos no exija tener
el driver de PostgreSQL instalado ni un servidor corriendo (los tests usan
SQLite).

Para desarrollo local sin PostgreSQL, fija en .env:
    DATABASE_URL=sqlite:///data/economia_ve.db
"""

import logging
from contextlib import contextmanager
from functools import lru_cache
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base declarativa de SQLAlchemy 2.0 para los modelos ORM."""


@lru_cache(maxsize=1)
def get_engine(url: Optional[str] = None) -> Engine:
    """Construye (y cachea) el motor de base de datos.

    Args:
        url: Cadena de conexión; si es None usa ``settings.DATABASE_URL``.

    Returns:
        Motor SQLAlchemy. La conexión es perezosa (no se abre aquí).
    """
    database_url = url or settings.DATABASE_URL
    logger.debug("Creando motor para %s", database_url.split("@")[-1])
    return create_engine(database_url, future=True)


def build_session_maker(url: Optional[str] = None) -> sessionmaker:
    """Fábrica de sesiones ligada a un motor (para tests o CLI)."""
    return sessionmaker(
        bind=get_engine(url),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )


_session_factory = None


def get_session_factory() -> sessionmaker:
    """Fábrica de sesiones por defecto (usa settings.DATABASE_URL)."""
    global _session_factory
    if _session_factory is None:
        _session_factory = build_session_maker()
    return _session_factory


def init_db(url: Optional[str] = None) -> None:
    """Crea las tablas si no existen (idempotente).

    Args:
        url: Cadena de conexión opcional (por defecto usa settings).
    """
    from src.db import models  # noqa: F401 - registra los modelos en Base

    engine = get_engine(url)
    Base.metadata.create_all(engine)
    logger.info("Esquema de base de datos verificado (tablas: %s)",
                len(Base.metadata.tables))


def get_session(url: Optional[str] = None) -> Session:
    """Abre una sesión nueva (ciérrala con contextlib.closing o en finally)."""
    factory = build_session_maker(url)
    return factory()


@contextmanager
def session_scope(url: Optional[str] = None):
    """Context manager de sesión: confirma al salir o revierte en excepción.

    Uso:
        with session_scope() as session:
            repo = SurveyRepository(session)
            ...
    """
    session = get_session(url)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()