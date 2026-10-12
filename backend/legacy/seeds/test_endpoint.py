"""
Script para testear directamente el endpoint /api/v1/teams/cpu
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/test_endpoint.py
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


def test_endpoint():
    """Simula la respuesta del endpoint GET /api/v1/teams/cpu"""
    db = SessionLocal()
    try:
        print("=" * 70)
        print("TEST ENDPOINT: GET /api/v1/teams/cpu")
        print("=" * 70)
        
        # Obtener todos los equipos (como hace ahora)
        teams = db.query(Team).all()
        result = []
        
        print(f"\n📥 Total de equipos en BD: {len(teams)}")
        print(f"🔄 Procesando...\n")
        
        for team in teams:
            cards = db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id).all()
            if not cards:
                print(f"   ⚠️  {team.id}: {team.name} - SIN CARTAS (omitido)")
                continue
            
            # CÁLCULO DINÁMICO DE MEDIAS
            batters = [c for c in cards if c.position not in ["SP", "RP", "CP"]]
            pitchers = [c for c in cards if c.position in ["SP", "RP", "CP"]]
            
            bat_ovr = round(sum(c.overall for c in batters) / len(batters)) if batters else 80
            pit_ovr = round(sum(c.overall for c in pitchers) / len(pitchers)) if pitchers else 80
            overall = round((bat_ovr + pit_ovr) / 2)
            
            team_data = {
                "id": team.id,
                "name": team.name,
                "city": team.city,
                "color": team.primary_color,
                "secondary_color": team.secondary_color,
                "badge": team.id,
                "desc": f"Franquicia • {len(cards)} Jugadores",
                "ovr": overall,
                "batOvr": bat_ovr,
                "pitOvr": pit_ovr
            }
            result.append(team_data)
            print(f"   ✓ {team.id}: {team.name} (OVR:{overall}, {len(cards)} cartas)")
        
        print("\n" + "=" * 70)
        print(f"✅ RESULTADO: Endpoint retornará {len(result)} equipos")
        print("=" * 70)
        print()
        
        if len(result) <= 10:
            print("📋 Respuesta JSON:")
            import json
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"📋 Primeros 3 equipos:")
            import json
            print(json.dumps(result[:3], indent=2, ensure_ascii=False))
            print(f"   ... ({len(result) - 3} más)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    test_endpoint()
