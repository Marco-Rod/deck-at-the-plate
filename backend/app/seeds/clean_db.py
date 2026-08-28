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
    Script de limpieza integral para resetear completamente la BD.
    Elimina:
    - Usuarios y sus datos (wallets, inventarios, lineups)
    - Equipos del usuario (user_teams)
    - Equipos MLB (teams) - para permitir crear de 0 en seed_mlb_2026
    
    Mantiene:
    - Cartas maestras (player_cards) - se recargan en seed_mlb_2026
    """
    db = SessionLocal()
    try:
        print("⚡ Iniciando limpieza completa de la base de datos...")

        truncate_query = text("""
            TRUNCATE TABLE 
                user_card_inventories,
                user_lineups,
                user_teams,
                user_wallets,
                users,
                teams
            RESTART IDENTITY CASCADE;
        """)
        
        db.execute(truncate_query)
        db.commit()

        print("✅ Base de datos limpiada con éxito.")
        print("   - Tabla 'users' vaciada.")
        print("   - Tabla 'user_wallets' vaciada.")
        print("   - Tabla 'user_teams' vaciada.")
        print("   - Tabla 'user_lineups' vaciada.")
        print("   - Tabla 'user_card_inventories' vaciada.")
        print("   - Tabla 'teams' vaciada (equipos MLB listos para crear de 0).")
        print()
        print("🚀 Próximo paso: ejecuta seed_mlb_2026.py para recargar datos.")

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