"""
Capa de base de datos (SQLAlchemy)
==================================

- session: motor, sesiones, init_db y session_scope.
- models: ORM de encuestas (surveys, survey_responses).
- repositories: SurveyRepository (CRUD idempotente).
- migrations: SQL crudo para aplicar el esquema en PostgreSQL/TimescaleDB.

Uso rápido:
    from src.db import init_db, session_scope
    from src.db.repositories import SurveyRepository

    init_db()
    with session_scope() as session:
        repo = SurveyRepository(session)
        repo.save_responses(responses)
"""

from src.db.session import (
    Base,
    get_engine,
    get_session,
    init_db,
    session_scope,
)

__all__ = [
    "Base",
    "get_engine",
    "get_session",
    "init_db",
    "session_scope",
]