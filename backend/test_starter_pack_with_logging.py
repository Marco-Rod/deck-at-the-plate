#!/usr/bin/env python3
"""
Script de prueba para validar la lógica de assign_starter_pack con logs detallados.
Ejecuta: python test_starter_pack_with_logging.py
"""

import sys
import logging
from pathlib import Path

# Configurar logging para ver los logs en consola
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('starter_pack_test.log')
    ]
)

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from app.database import SessionLocal
from app.models import User, UserTeam, PlayerCardModel
from app.services.pack_service import PackService, StarterPackConfig

def test_starter_pack():
    """Prueba la lógica de starter pack con una serie de usuarios."""
    db = SessionLocal()
    
    try:
        # Verificar que tenemos datos
        total_cards = db.query(PlayerCardModel).count()
        total_teams = db.query(UserTeam).count()
        
        print(f"\n{'='*80}")
        print(f"[TEST] Total de cartas en BD: {total_cards}")
        print(f"[TEST] Total de equipos de usuario en BD: {total_teams}")
        print(f"{'='*80}\n")
        
        if total_teams == 0:
            print("[ERROR] No hay equipos de usuario. Ejecuta primero el seed script.")
            return
        
        # Obtener el primer usuario con equipo
        user_team = db.query(UserTeam).first()
        if not user_team:
            print("[ERROR] No se encontró usuario con equipo")
            return
        
        user_id = user_team.user_id
        user = db.query(User).filter(User.id == user_id).first()
        
        print(f"[TEST] Usuario seleccionado: {user_id}")
        print(f"[TEST] Nombre del club: {user_team.name}")
        print(f"[TEST] favorite_team_id: {user.favorite_team_id}")
        
        # Obtener equipos disponibles
        teams = db.query(UserTeam).all()
        if not teams:
            print("[ERROR] No hay equipos disponibles")
            return
        
        # Seleccionar un equipo para el starter pack (diferente del club del usuario si es posible)
        selected_team = teams[0]
        team_id = selected_team.name.upper()[:3]  # Usar las siglas del equipo
        
        # Si no tenemos siglas válidas, usar el team_id
        if not team_id or len(team_id) < 2:
            # Intentar obtener un equipo de la tabla de cartas
            all_team_ids = db.query(PlayerCardModel.team_id).distinct().all()
            if all_team_ids:
                team_id = all_team_ids[0][0]
            else:
                print("[ERROR] No hay equipos en la tabla de cartas")
                return
        
        print(f"[TEST] Team ID seleccionado para starter pack: {team_id}")
        
        # Ejecutar assign_starter_pack
        print(f"\n[TEST] Ejecutando assign_starter_pack...")
        assigned_cards = PackService.assign_starter_pack(db, user_id=user_id, team_id=team_id)
        
        print(f"\n[TEST RESULT] ✓ Starter pack asignado exitosamente")
        print(f"[TEST RESULT] Total de cartas: {len(assigned_cards)}")
        
        # Validaciones
        print(f"\n{'='*80}")
        print(f"[VALIDACIONES]")
        print(f"{'='*80}")
        
        # 1. Verificar total de cartas
        expected_total = StarterPackConfig.TOTAL_CARDS
        actual_total = len(assigned_cards)
        status = "✓" if actual_total == expected_total else "✗"
        print(f"{status} Total de cartas: {actual_total} (esperadas {expected_total})")
        
        # 2. Verificar distribución por rareza
        print(f"\n[Distribución por Rareza]")
        rarity_counts = {}
        for card in assigned_cards:
            rarity = card.rarity.value if card.rarity else "COMMON"
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        for rarity in ["DIAMOND", "GOLD", "SILVER", "BRONZE", "COMMON"]:
            actual = rarity_counts.get(rarity, 0)
            expected = StarterPackConfig.RARITY_DISTRIBUTION.get(rarity, 0)
            status = "✓" if actual == expected else "✗"
            print(f"  {status} {rarity}: {actual} (esperadas {expected})")
        
        # 3. Verificar composición por equipo
        print(f"\n[Composición por Equipo]")
        team_counts = {}
        for card in assigned_cards:
            team = card.team_id
            team_counts[team] = team_counts.get(team, 0) + 1
        
        for team in sorted(team_counts.keys()):
            count = team_counts[team]
            is_selected_team = team == team_id.upper()
            marker = "(EQUIPO ELEGIDO)" if is_selected_team else ""
            print(f"  - {team}: {count} cartas {marker}")
        
        # 4. Verificar posiciones cubiertas
        print(f"\n[Posiciones Cubiertas]")
        positions = {}
        for card in assigned_cards:
            pos = card.position
            positions[pos] = positions.get(pos, 0) + 1
        
        all_positions = StarterPackConfig.REQUIRED_POSITIONS
        for pos in sorted(positions.keys()):
            count = positions[pos]
            print(f"  - {pos}: {count}")
        
        missing_positions = all_positions - set(positions.keys())
        if missing_positions:
            print(f"\n  ✗ POSICIONES FALTANTES: {missing_positions}")
        else:
            print(f"\n  ✓ Todas las posiciones requeridas cubiertas")
        
        # 5. Detalles de las cartas
        print(f"\n[Detalle de Cartas Asignadas]")
        for i, card in enumerate(assigned_cards, 1):
            print(f"  {i:2d}. {card.first_name} {card.last_name:15s} ({card.team_id}) - {card.position:2s} - OVR: {card.overall:2d} - {card.rarity}")
        
        print(f"\n{'='*80}")
        print(f"[TEST] Prueba completada exitosamente")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_starter_pack()
