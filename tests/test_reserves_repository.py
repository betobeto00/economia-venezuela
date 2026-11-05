"""
Tests del histórico de reservas del BCV (``reserves_history``)
==============================================================

Usa SQLite (mismo esquema que PostgreSQL) para comprobar que la serie es
idempotente por fecha y que se puede leer ordenada.
"""

import pytest
from sqlalchemy.orm import sessionmaker

from src.db import get_engine, init_db
from src.db.repositories import ReservesRepository


@pytest.fixture
def session(tmp_path):
    url = f"sqlite:///{tmp_path / 'test_reserves.db'}"
    init_db(url)
    factory = sessionmaker(bind=get_engine(url), future=True)
    s = factory()
    yield s
    s.close()


def test_guarda_y_lee_ordenado(session):
    repo = ReservesRepository(session)

    inserted = repo.save_history([
        {"date": "2026-11-04", "total_usd": 13191e6, "bcv_usd": 13188e6, "fem_usd": 3e6},
        {"date": "2026-11-03", "total_usd": 12967e6, "bcv_usd": 12964e6, "fem_usd": 3e6},
    ])

    assert inserted == 2
    history = repo.get_history()
    assert [d["date"] for d in history] == ["2026-11-03", "2026-11-04"]
    assert history[-1]["total_usd"] == pytest.approx(13191e6)
    assert history[-1]["bcv_usd"] == pytest.approx(13188e6)
    assert repo.count() == 2


def test_repetir_fecha_actualiza_sin_duplicar(session):
    repo = ReservesRepository(session)
    repo.save_history([{"date": "2026-11-04", "total_usd": 13191e6}])

    inserted = repo.save_history([{"date": "2026-11-04", "total_usd": 13200e6}])

    assert inserted == 0
    assert repo.count() == 1
    assert repo.get_history()[-1]["total_usd"] == pytest.approx(13200e6)


def test_get_history_filtra_por_fecha(session):
    repo = ReservesRepository(session)
    repo.save_history([
        {"date": "2024-01-02", "total_usd": 1e9},
        {"date": "2026-11-04", "total_usd": 13191e6},
    ])

    history = repo.get_history(since="2026-01-01")

    assert [d["date"] for d in history] == ["2026-11-04"]
