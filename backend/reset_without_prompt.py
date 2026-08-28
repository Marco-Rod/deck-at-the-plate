#!/usr/bin/env python
"""
Script de reset sin interactividad - ideal para ejecutar en Docker.
Limpia BD completamente y recarga datos MLB 2026.
"""

import sys
import os
import logging

# Configurar PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../"))
sys.path.insert(0, current_dir)
sys.path.insert(0, parent_dir)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from sqlalchemy import text
from app.database import SessionLocal

def clean_database():
    """Limpia completamente la BD sin pedir confirmación"""
    db = SessionLocal()
    try:
        print("\n" + "="*80)
        print("🧹 PASO 1: Limpiando base de datos...")
        print("="*80 + "\n")

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
        print("   ✓ Tabla 'users' vaciada")
        print("   ✓ Tabla 'user_wallets' vaciada")
        print("   ✓ Tabla 'user_teams' vaciada")
        print("   ✓ Tabla 'user_lineups' vaciada")
        print("   ✓ Tabla 'user_card_inventories' vaciada")
        print("   ✓ Tabla 'teams' vaciada\n")

        return True

    except Exception as e:
        db.rollback()
        print(f"❌ Error durante la limpieza: {e}")
        return False
    finally:
        db.close()

def seed_mlb_data():
    """Carga datos MLB 2026 sin pedir confirmación"""
    try:
        print("="*80)
        print("📥 PASO 2: Cargando datos MLB 2026...")
        print("="*80 + "\n")
        
        from app.seeds.seed_mlb_2026 import seed_mlb_2026_data
        from app.database import SessionLocal
        
        db = SessionLocal()
        seed_mlb_2026_data(db)
        db.close()
        
        print("\n✅ Seed completado exitosamente\n")
        return True
        
    except Exception as e:
        print(f"\n❌ Error al hacer seed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*80)
    print("🏟️  RESET & SEED - Base de Datos MLB 2026 (No-Interactive)")
    print("="*80)
    print("\n⏳ Iniciando reset automático...\n")
    
    # Paso 1: Limpiar
    if not clean_database():
        print("❌ Error en limpieza. Abortando.")
        return False
    
    # Paso 2: Seed
    if not seed_mlb_data():
        print("❌ Error en seed. Abortando.")
        return False
    
    # Resumen
    print("="*80)
    print("✅ COMPLETADO - Base de datos lista")
    print("="*80)
    print("\n📋 Cambios aplicados:")
    print("   ✓ Todos los usuarios eliminados")
    print("   ✓ Todos los equipos recreados de 0")
    print("   ✓ ~1200 cartas cargadas con fixes:")
    print("     • overall: 70-95 (basado en jerseyNumber)")
    print("     • rarity: DIAMOND(90+) GOLD(85+) SILVER(80+) BRONZE(75+) COMMON")
    print("\n🎮 Próximas acciones:")
    print("   1. El backend está corriendo en el contenedor")
    print("   2. Abre http://localhost:5173 en tu browser")
    print("   3. Crea un usuario nuevo")
    print("   4. Selecciona un equipo (SF, NYY, etc - NO LAD)")
    print("   5. Abre el sobre inicial y verifica los logs:")
    print("      - Distribución: 2 SILVER + 4 BRONZE + 7 COMMON")
    print("      - Equipo favorito respetado")
    print("="*80 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
