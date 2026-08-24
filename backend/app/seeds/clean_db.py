# backend/app/seeds/clean_db.py

import sys
import os

# Añadir el directorio raíz de la aplicación (/app) al PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

from sqlalchemy import text
try:
    from app.database import SessionLocal
except ModuleNotFoundError:
    from database import SessionLocal

def clean_database():
    """
    Script de limpieza integral para resetear usuarios, inventarios,
    lineups y equipos manteniendo las cartas maestras cargadas.
    """
    db = SessionLocal()
    try:
        print("⚡ Iniciando limpieza de la base de datos...")

        truncate_query = text("""
            TRUNCATE TABLE 
                user_card_inventories,
                user_lineups,
                user_teams,
                user_wallets,
                users
            RESTART IDENTITY CASCADE;
        """)
        
        db.execute(truncate_query)
        db.commit()

        print("✅ Base de datos limpiada con éxito.")
        print("   - Tabla 'users' vaciada.")
        print("   - Tabla 'user_wallets' vaciada.")
        print("   - Tabla 'user_teams' vaciada (si existe).")
        print("   - Tabla 'user_lineups' vaciada.")
        print("   - Tabla 'user_card_inventories' vaciada.")
        print("🚀 Entorno listo para la creación de clubes y el nuevo flujo de onboarding.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error durante la limpieza: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    confirm = input("⚠️  ¿Deseas eliminar TODOS los usuarios y sus clubes/lineups? (s/n): ")
    if confirm.lower() == 's':
        clean_database()
    else:
        print("Operación cancelada.")