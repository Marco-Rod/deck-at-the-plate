#!/usr/bin/env python
"""
Script de utilidad para limpiar completamente la BD y cargar datos frescos.
Ejecuta en orden:
1. clean_db.py - elimina todos los usuarios y equipos
2. seed_mlb_2026.py - carga 30 equipos MLB con ~40 jugadores cada uno
"""

import sys
import os
import subprocess

# Añadir el directorio raíz al PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def run_script(script_name):
    """Ejecuta un script de seed"""
    print(f"\n{'='*80}")
    print(f"🚀 Ejecutando: {script_name}")
    print(f"{'='*80}\n")
    
    script_path = os.path.join(current_dir, "app/seeds", script_name)
    result = subprocess.run([sys.executable, script_path], cwd=current_dir)
    
    if result.returncode != 0:
        print(f"\n❌ Error al ejecutar {script_name}")
        return False
    return True

def main():
    print(f"\n{'='*80}")
    print("🏟️  RESET & SEED - Base de Datos MLB 2026")
    print(f"{'='*80}\n")
    
    confirm = input("⚠️  ¿Deseas limpiar TODA la BD y recargar desde 0? (s/n): ")
    if confirm.lower() != 's':
        print("Operación cancelada.")
        return
    
    # Paso 1: Limpiar BD
    print("\n[PASO 1] Limpiando base de datos...")
    if not run_script("clean_db.py"):
        return
    
    # Paso 2: Cargar datos MLB 2026
    print("\n[PASO 2] Cargando datos MLB 2026...")
    if not run_script("seed_mlb_2026.py"):
        return
    
    print(f"\n{'='*80}")
    print("✅ COMPLETADO - Base de datos lista para testing")
    print(f"{'='*80}\n")
    print("📋 Resumen:")
    print("   ✓ Todos los usuarios eliminados")
    print("   ✓ Todos los equipos MLB recreados desde 0")
    print("   ✓ ~1200 cartas de jugadores cargadas con fixes:")
    print("     - overall correcto: 70-95 (basado en jerseyNumber)")
    print("     - rarity distribution: DIAMOND/GOLD/SILVER/BRONZE/COMMON")
    print("\n🎮 Próximo paso: crea un usuario nuevo en el frontend")
    print("   1. Funda tu club")
    print("   2. Selecciona franquicia favorita (no debería ser LAD)")
    print("   3. Abre sobre inicial")
    print("   4. Verifica: distribución 2-4-7 y equipo correcto")
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()
