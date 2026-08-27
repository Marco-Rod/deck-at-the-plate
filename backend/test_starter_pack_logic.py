#!/usr/bin/env python3
"""
Script para verificar la lógica completa del starter pack.
Debe ejecutarse dentro del contenedor Docker.

Usage:
  docker exec baseball_backend python test_starter_pack_logic.py
"""

from app.database import SessionLocal
from app.models import User, UserTeam, PlayerCardModel, CardRarity
from app.services.pack_service import PackService, StarterPackConfig
from sqlalchemy import func

def print_header(text):
    print(f"\n{'='*80}")
    print(f"  {text}")
    print(f"{'='*80}\n")

def analyze_pack(cards, team_id):
    """Analiza un pack de cartas y verifica su composición."""
    print(f"✓ Pack total: {len(cards)} cartas")
    
    # Composición por equipo
    team_cards = [c for c in cards if c.team_id == team_id]
    other_cards = [c for c in cards if c.team_id != team_id]
    
    print(f"  - Del equipo {team_id}: {len(team_cards)}")
    print(f"  - De otros equipos: {len(other_cards)}")
    
    # Composición por tipo
    fielders = [c for c in cards if c.position not in StarterPackConfig.PITCHER_POSITIONS]
    pitchers = [c for c in cards if c.position in StarterPackConfig.PITCHER_POSITIONS]
    
    print(f"  - Fielders: {len(fielders)}")
    print(f"  - Pitchers: {len(pitchers)}")
    
    # Composición por rareza
    rarity_count = {}
    for card in cards:
        rarity = card.rarity.value if card.rarity else "UNKNOWN"
        rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
    
    print(f"\n  Rarities:")
    for rarity in sorted(rarity_count.keys()):
        count = rarity_count[rarity]
        expected = StarterPackConfig.RARITY_DISTRIBUTION.get(rarity, "N/A")
        status = "✓" if count == expected else "✗"
        print(f"    {status} {rarity}: {count} (expected: {expected})")
    
    # Posiciones
    position_count = {}
    for card in cards:
        pos = card.position
        position_count[pos] = position_count.get(pos, 0) + 1
    
    print(f"\n  Positions ({len(position_count)} unique):")
    for pos in sorted(position_count.keys()):
        count = position_count[pos]
        status = "✓" if count <= 2 else "✗"
        print(f"    {status} {pos}: {count}")
    
    # Validaciones
    errors = []
    
    if len(cards) != StarterPackConfig.TOTAL_CARDS:
        errors.append(f"Total cartas: esperadas {StarterPackConfig.TOTAL_CARDS}, obtenidas {len(cards)}")
    
    if len(team_cards) != 7:
        errors.append(f"Cartas del equipo: esperadas 7, obtenidas {len(team_cards)}")
    
    if len(other_cards) != 6:
        errors.append(f"Cartas de otros equipos: esperadas 6, obtenidas {len(other_cards)}")
    
    if len(fielders) != 9:
        errors.append(f"Fielders: esperados 9, obtenidos {len(fielders)}")
    
    if len(pitchers) != 4:
        errors.append(f"Pitchers: esperados 4, obtenidos {len(pitchers)}")
    
    # Verificar distribución de raridades
    for rarity, expected in StarterPackConfig.RARITY_DISTRIBUTION.items():
        actual = rarity_count.get(rarity, 0)
        if actual != expected:
            errors.append(f"Rareza {rarity}: esperadas {expected}, obtenidas {actual}")
    
    # Verificar duplicación de posiciones
    for pos, count in position_count.items():
        if count > 2:
            errors.append(f"Posición {pos} duplicada más de 2 veces: {count}")
    
    # Verificar cobertura de posiciones
    required_positions = StarterPackConfig.REQUIRED_POSITIONS - {"P"}  # P se cuenta implícitamente
    for pos in required_positions:
        if pos not in position_count:
            errors.append(f"Posición faltante: {pos}")
    
    if errors:
        print(f"\n  ✗ ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"    - {error}")
        return False
    else:
        print(f"\n  ✓ Todas las validaciones pasaron")
        return True

def main():
    db = SessionLocal()
    
    try:
        print_header("Starter Pack Logic Test")
        
        # Buscar un usuario de prueba o crear uno
        test_user = db.query(User).first()
        if not test_user:
            print("✗ No hay usuarios en la BD")
            return False
        
        test_user_id = test_user.id
        print(f"Usuario de prueba: {test_user_id}")
        
        # Verificar que el usuario tenga team
        user_team = db.query(UserTeam).filter(UserTeam.user_id == test_user_id).first()
        if not user_team:
            print("✗ El usuario no tiene un equipo personal")
            return False
        
        # Seleccionar un equipo para prueba
        available_teams = db.query(PlayerCardModel.team_id).distinct().limit(3).all()
        test_teams = [t[0] for t in available_teams if t[0]]
        
        if not test_teams:
            print("✗ No hay equipos disponibles en la BD")
            return False
        
        print(f"Equipos disponibles para prueba: {test_teams}\n")
        
        # Probar con cada equipo
        all_passed = True
        for i, team_id in enumerate(test_teams, 1):
            print_header(f"Test {i}/{len(test_teams)}: Equipo {team_id}")
            
            try:
                # Asignar pack
                cards = PackService.assign_starter_pack(db, test_user_id, team_id)
                
                # Analizar
                passed = analyze_pack(cards, team_id)
                
                if not passed:
                    all_passed = False
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                import traceback
                traceback.print_exc()
                all_passed = False
        
        print_header("Summary")
        if all_passed:
            print("✓ TODOS LOS TESTS PASARON")
            return True
        else:
            print("✗ ALGUNOS TESTS FALLARON")
            return False
        
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
