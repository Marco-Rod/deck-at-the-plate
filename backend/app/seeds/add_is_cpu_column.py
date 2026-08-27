"""
Script para agregar la columna is_cpu a la tabla teams
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/add_is_cpu_column.py
"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

try:
    from app.database import SessionLocal, engine
except ModuleNotFoundError:
    from database import SessionLocal, engine

from sqlalchemy import text


def add_is_cpu_column():
    """Agrega la columna is_cpu a la tabla teams si no existe"""
    db = SessionLocal()
    try:
        # Verificar si la columna ya existe
        result = db.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='teams' AND column_name='is_cpu'
        """))
        
        if result.fetchone():
            print("✓ Columna is_cpu ya existe en la tabla teams")
            return
        
        # Agregar la columna
        db.execute(text("""
            ALTER TABLE teams ADD COLUMN is_cpu BOOLEAN NOT NULL DEFAULT false;
        """))
        
        # Crear índice
        db.execute(text("""
            CREATE INDEX idx_teams_is_cpu ON teams(is_cpu);
        """))
        
        db.commit()
        print("✅ Columna is_cpu agregada exitosamente a la tabla teams")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error al agregar columna: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    add_is_cpu_column()
