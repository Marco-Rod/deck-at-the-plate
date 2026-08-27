"""
Script para revisar cuántas cartas tiene cada equipo
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/check_cards_by_team.py
"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

try:
    from app.database import SessionLocal
    from app.models import Team, PlayerCardModel
except ModuleNotFoundError:
    from database import SessionLocal
    from models import Team, PlayerCardModel


def check_cards():
    """Revisa cartas por equipo"""
    db = SessionLocal()
    try:
        print("=" * 70)
        print("CARTAS POR EQUIPO")
        print("=" * 70)
        
        all_teams = db.query(Team).all()
        print(f"\n📊 Total de equipos: {len(all_teams)}\n")
        
        teams_with_cards = 0
        teams_without_cards = 0
        total_cards = 0
        
        print("Equipo | Cartas | Lanzadores | Bateadores | is_cpu")
        print("-" * 70)
        
        for team in sorted(all_teams, key=lambda t: t.id):
            cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).all()
            card_count = len(cards)
            
            pitchers = len([c for c in cards if c.position in ["SP", "RP", "CP"]])
            batters = len([c for c in cards if c.position not in ["SP", "RP", "CP"]])
            
            cpu_flag = "✓" if team.is_cpu else " "
            
            if card_count > 0:
                teams_with_cards += 1
                total_cards += card_count
                status = "✓"
            else:
                teams_without_cards += 1
                status = "✗"
            
            print(f"{team.id:5} | {card_count:5} | {pitchers:10} | {batters:10} | {cpu_flag}")
        
        print("-" * 70)
        print(f"\n📈 Resumen:")
        print(f"   Equipos CON cartas: {teams_with_cards}")
        print(f"   Equipos SIN cartas: {teams_without_cards}")
        print(f"   Total de cartas: {total_cards}")
        print(f"\n🔗 El endpoint /api/v1/teams/cpu retornará: {teams_with_cards} equipos")
        
        if teams_without_cards > 0:
            print(f"\n⚠️  {teams_without_cards} equipos no tienen cartas")
            print("   Necesitas ejecutar: python app/seeds/seed_mlb_2026.py")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    check_cards()
