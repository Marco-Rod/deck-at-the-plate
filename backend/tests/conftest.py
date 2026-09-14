"""Configuración compartida para pruebas sin servicios externos.

La fase 0 del plan maestro congela el dataset de prueba en ``tests.fixtures``
y expone aquí una BD SQLite canónica reutilizable. Los tests que definen su
propio fixture ``db`` local lo sobreescriben (pytest resuelve el más cercano);
los demás comparten esta sesión por defecto.
"""

import os

# Debe definirse antes de que cualquier módulo importe app.database. Las pruebas
# unitarias no requieren PostgreSQL ni su driver nativo.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production"

import pytest  # noqa: E402

from tests import fixtures  # noqa: E402


@pytest.fixture
def db():
    """BD SQLite en memoria con el esquema completo (patrón canónico)."""
    engine, session = fixtures.new_db()
    yield session
    session.close()
    engine.dispose()