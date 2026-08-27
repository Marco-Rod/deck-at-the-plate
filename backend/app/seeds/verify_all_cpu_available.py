"""
Script para verificar que todos los 34 equipos están disponibles como rivales CPU
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/verify_all_cpu_available.py
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


def verify():
    """Verifica que todos los equipos están disponibles como CPU"""
    db = SessionLocal()
    try:
        print("=" * 70)
        print("VERIFICACIÓN: TODOS LOS EQUIPOS COMO RIVALES CPU")
        print("=" * 70)
        
        all_teams = db.query(Team).all()
        total = len(all_teams)
        
        print(f"\n📊 Total de equipos en BD: {total}")
        print("\n🎮 Equipos disponibles como rivales CPU:")
        print("-" * 70)
        
        teams_with_cards = 0
        total_cards = 0
        
        for idx, team in enumerate(all_teams, 1):
            cards_count = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).count()
            if cards_count > 0:
                teams_with_cards += 1
                total_cards += cards_count
                
                # Calcular overall
                cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).all()
                batters = [c for c in cards if c.position not in ["SP", "RP", "CP"]]
                pitchers = [c for c in cards if c.position in ["SP", "RP", "CP"]]
                
                bat_ovr = round(sum(c.overall for c in batters) / len(batters)) if batters else 80
                pit_ovr = round(sum(c.overall for c in pitchers) / len(pitchers)) if pitchers else 80
                overall = round((bat_ovr + pit_ovr) / 2)
                
                cpu_flag = " [CPU]" if team.is_cpu else ""
                print(f"{idx:2}. {team.id}: {team.name:30} OVR:{overall:2} ({cards_count:2} cartas){cpu_flag}")
        
        print("-" * 70)
        print(f"\n✅ Equipos disponibles: {teams_with_cards}")
        print(f"📦 Total de cartas: {total_cards}")
        print(f"\n🔗 Endpoint /api/v1/teams/cpu retornará: {teams_with_cards} equipos")
        
        if teams_with_cards == total:
            print("\n✅ ÉXITO: Todos los equipos están disponibles como rivales CPU")
        else:
            print(f"\n⚠️  ADVERTENCIA: Solo {teams_with_cards}/{total} equipos tienen cartas")
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verify()
