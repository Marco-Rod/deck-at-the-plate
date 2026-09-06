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

# Tamaño de lote del bulk UPSERT de raw_pitch_events (corrección §4).
BULK_UPSERT_BATCH_SIZE = int(os.getenv("BULK_UPSERT_BATCH_SIZE", "1000"))

# Rating model que usan los perfiles de carta generados por el ETL.
RATING_MODEL_VERSION = os.getenv("ETL_RATING_MODEL_VERSION", "ratings-1.0")

# Generador de identidades GAME (§63-§93): versión determinista de pools.
NAMES_GENERATOR_VERSION = os.getenv("ETL_NAMES_GENERATOR_VERSION", "names-1.0")
# Confianza mínima para aceptar la clasificación lingüística (§87).
NAME_CLASSIFIER_THRESHOLD = float(os.getenv("ETL_NAME_CLASSIFIER_THRESHOLD", "0.62"))
# Intentos máximos del generador por jugador (colisión/bloqueado) (§70).
NAMES_MAX_ATTEMPTS = int(os.getenv("ETL_NAMES_MAX_ATTEMPTS", "20"))
# Probabilidad de conservar la inicial del nombre fuente (§73).
NAMES_PRESERVE_INITIALS = float(os.getenv("ETL_NAMES_PRESERVE_INITIALS", "0.20"))