"""Configuración compartida para pruebas sin servicios externos."""

import os


# Debe definirse antes de que cualquier módulo importe app.database. Las pruebas
# unitarias no requieren PostgreSQL ni su driver nativo.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-secret-not-for-production"
