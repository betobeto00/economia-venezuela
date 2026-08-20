"""Fixtures compartidos para todos los tests."""

import pytest


@pytest.fixture(autouse=True)
def _clear_llm_cache():
    """Limpia el cache de LLM antes de cada test para evitar interferencias."""
    from src.analyzers.llm import clear_cache
    clear_cache()
    yield
    clear_cache()
