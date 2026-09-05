"""Configuración del pipeline ETL (spec sección 36).

Se lee de variables de entorno con defaults razonables; el contenedor hereda
las variables del entorno/servicio sin cambios de código.
"""

import os

ETL_PIPELINE_VERSION = os.getenv("ETL_PIPELINE_VERSION", "1.0.0")

MLB_STATS_API_BASE_URL = os.getenv(
    "MLB_STATS_API_BASE_URL", "https://statsapi.mlb.com/api/v1"
)
BASEBALL_SAVANT_BASE_URL = os.getenv(
    "BASEBALL_SAVANT_BASE_URL", "https://baseballsavant.mlb.com"
)

ETL_HTTP_USER_AGENT = os.getenv("ETL_HTTP_USER_AGENT", "DeckAtThePlate-ETL/1.0")
ETL_CONNECT_TIMEOUT_SECONDS = float(os.getenv("ETL_CONNECT_TIMEOUT_SECONDS", "5"))
ETL_READ_TIMEOUT_SECONDS = float(os.getenv("ETL_READ_TIMEOUT_SECONDS", "45"))
ETL_MAX_RETRIES = int(os.getenv("ETL_MAX_RETRIES", "3"))

STATCAST_CHUNK_DAYS = int(os.getenv("STATCAST_CHUNK_DAYS", "5"))
STATCAST_SAFE_ROW_THRESHOLD = int(os.getenv("STATCAST_SAFE_ROW_THRESHOLD", "25000"))

# Rating model que usan los perfiles de carta generados por el ETL.
RATING_MODEL_VERSION = os.getenv("ETL_RATING_MODEL_VERSION", "ratings-1.0")