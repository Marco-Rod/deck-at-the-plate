import subprocess
import sys
from sqlalchemy import text

from app.database import engine


def reset_db():
    """
    Reconstruye por completo el esquema de la BD usando Alembic.

    Usa DROP SCHEMA public CASCADE (que en PostgreSQL elimina también los
    tipos ENUM, cosa que drop_table no hace) y luego alembic upgrade head.
    """
    print("Reconstruyendo esquema con Alembic (DROP SCHEMA + upgrade head)...")
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    print("¡Base de datos lista!")

if __name__ == "__main__":
    reset_db()