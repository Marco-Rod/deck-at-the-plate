#!/usr/bin/env python3
"""
Script de prueba para verificar la lógica de assign_starter_pack con diferentes equipos.

Uso:
  python test_pack_assignment.py
"""

import sys
sys.path.insert(0, '/workspace/backend')

from app.database import SessionLocal
from app.services.pack_service import PackService
from app.models import User, UserTeam, PlayerCardModel, CardRarity
from sqlalchemy import func

def print_header(text):
    print("\n" + "="*80)
    print(f"  {text}")
    print("="*80)

def print_section(text):
    print(f"\n▶ {text}")
    print("-" * 80)

def test_pack_assignment_for_team(db, user_id, team_id):
    """Prueba assign_starter_pack para un equipo específico."""
    
    print_section(f"Testing pack assignment for team: {team_id}")
    
    try:
        # Obtener cartas del equipo
        team_cards = db.query(PlayerCardModel).filter(
            PlayerCardModel.team_id == team_id
        ).all()
        
        print(f"Total cards in team {team_id}: {len(team_cards)}")
        
        # Contar por posición
        by_position = {}
        by_rarity = {}
        for card in team_cards:
            by_position[card.position] = by_position.get(card.position, 0) + 1
            rarity_name = card.rarity.value if card.rarity else "UNKNOWN"
            by_rarity[rarity_name] = by_rarity.get(rarity_name, 0) + 1
        
        print(f"  By position: {by_position}")
        print(f"  By rarity: {by_rarity}")
        
        # Asignar pack
        assigned_cards = PackService.assign_starter_pack(db, user_id, team_id)
        
        print(f"\n✓ Assigned {len(assigned_cards)} cards")
        
        # Análisis de las cartas asignadas
        team_cards_in_pack = [c for c in assigned_cards if c.team_id == team_id]
        other_cards_in_pack = [c for c in assigned_cards if c.team_id != team_id]
        
        fielders = [c for c in assigned_cards if c.position not in ["SP", "RP", "CP"]]
        pitchers = [c for c in assigned_cards if c.position in ["SP", "RP", "CP"]]
        
        print(f"\n  Total: {len(assigned_cards)}")
        print(f"  From {team_id}: {len(team_cards_in_pack)}")
        print(f"  From others: {len(other_cards_in_pack)}")
        print(f"  Fielders: {len(fielders)}")
        print(f"  Pitchers: {len(pitchers)}")
        
        # Verificar composición esperada
        team_fielders_in_pack = [c for c in team_cards_in_pack if c.position not in ["SP", "RP", "CP"]]
        team_pitchers_in_pack = [c for c in team_cards_in_pack if c.position in ["SP", "RP", "CP"]]
        
        print(f"\n  Team fielders: {len(team_fielders_in_pack)} (expected: 5)")
        print(f"  Team pitchers: {len(team_pitchers_in_pack)} (expected: 2)")
        print(f"  Other teams: {len(other_cards_in_pack)} (expected: 6)")
        
        # Mostrar detalles de las cartas asignadas
        print(f"\n  Cards assigned:")
        position_count = {}
        rarity_count = {}
        for i, card in enumerate(assigned_cards, 1):
            pos = card.position
            team_label = f"[{card.team_id}]" if card.team_id == team_id else f"[{card.team_id}*]"
            rarity_name = card.rarity.value if card.rarity else "UNKNOWN"
            print(f"    {i:2d}. {card.name:30s} {pos:3s} {rarity_name:8s} OVR:{card.overall:2d} {team_label}")
            
            position_count[pos] = position_count.get(pos, 0) + 1
            rarity_count[rarity_name] = rarity_count.get(rarity_name, 0) + 1
        
        # Verificar duplicación de posiciones
        print(f"\n  Position distribution:")
        max_pos_count = max(position_count.values()) if position_count else 0
        for pos in sorted(position_count.keys()):
            count = position_count[pos]
            status = "✓" if count <= 2 else "✗ DUPLICATED"
            print(f"    {pos}: {count} {status}")
        
        print(f"\n  Rarity distribution:")
        for rarity in sorted(rarity_count.keys()):
            count = rarity_count[rarity]
            print(f"    {rarity}: {count}")
        
        # Validaciones
        errors = []
        
        if len(assigned_cards) != 13:
            errors.append(f"Expected 13 cards, got {len(assigned_cards)}")
        
        if len(team_fielders_in_pack) != 5:
            errors.append(f"Expected 5 fielders from {team_id}, got {len(team_fielders_in_pack)}")
        
        if len(team_pitchers_in_pack) != 2:
            errors.append(f"Expected 2 pitchers from {team_id}, got {len(team_pitchers_in_pack)}")
        
        if len(other_cards_in_pack) != 6:
            errors.append(f"Expected 6 cards from other teams, got {len(other_cards_in_pack)}")
        
        if max_pos_count > 2:
            errors.append(f"Position duplicated more than 2 times (max: {max_pos_count})")
        
        if errors:
            print(f"\n✗ ERRORS:")
            for error in errors:
                print(f"    - {error}")
            return False
        else:
            print(f"\n✓ All validations passed!")
            return True
        
    except Exception as e:
        print(f"\n✗ Exception: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print_header("Pack Assignment Testing")
    
    db = SessionLocal()
    
    try:
        # Crear usuario de prueba si no existe
        test_user_id = "test_pack_user_001"
        test_user = db.query(User).filter(User.id == test_user_id).first()
        if not test_user:
            test_user = User(id=test_user_id, username="test_pack_user", hashed_password="dummy")
            db.add(test_user)
            db.commit()
            print(f"✓ Created test user: {test_user_id}")
        
        # Obtener equipos únicos disponibles
        team_ids = db.query(PlayerCardModel.team_id).distinct().all()
        available_teams = sorted([t[0] for t in team_ids if t[0]])[:5]  # Primeros 5 equipos
        
        print(f"\nTesting with {len(available_teams)} teams: {available_teams}")
        
        passed = 0
        failed = 0
        
        for i, team_id in enumerate(available_teams, 1):
            print_header(f"Test {i}/{len(available_teams)}: Team {team_id}")
            
            if test_pack_assignment_for_team(db, test_user_id, team_id):
                passed += 1
            else:
                failed += 1
        
        # Resumen
        print_header("Test Summary")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Total:  {passed + failed}")
        
        if failed == 0:
            print("\n✓ All tests passed!")
            return 0
        else:
            print(f"\n✗ {failed} test(s) failed")
            return 1
        
    finally:
        db.close()

if __name__ == "__main__":
    sys.exit(main())
