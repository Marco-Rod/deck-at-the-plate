"""
Script de debug para verificar si la API MLB retorna datos
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/debug_mlb_api.py
"""
import sys
import os
import requests

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

BASE_URL = "https://statsapi.mlb.com/api/v1"


def debug_api():
    """Verifica si la API MLB funciona"""
    print("=" * 70)
    print("DEBUG: MLB STATS API")
    print("=" * 70)
    
    try:
        # 1. Obtener equipos
        print("\n1️⃣ Obteniendo equipos de MLB...")
        url = f"{BASE_URL}/teams"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        teams = [t for t in data.get("teams", []) if t.get("active") and t.get("sport", {}).get("name") == "Major League Baseball"]
        print(f"   ✓ Se obtuvieron {len(teams)} equipos")
        
        # 2. Probar con el primer equipo
        if teams:
            test_team = teams[0]
            team_id = test_team.get("id")
            team_name = test_team.get("name")
            team_abbr = test_team.get("abbreviation")
            
            print(f"\n2️⃣ Probando con equipo: {team_abbr} ({team_name}, ID: {team_id})")
            
            # 3. Obtener roster
            print(f"   Pidiendo roster a: {BASE_URL}/teams/{team_id}/roster")
            url = f"{BASE_URL}/teams/{team_id}/roster"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            roster = data.get("roster", [])
            print(f"   ✓ Roster retorna {len(roster)} jugadores")
            
            # 4. Filtrar como hace el script
            filtered_roster = [p for p in roster if p.get("status", {}).get("code") in ["ACTIVE", "ROSTER_40"]][:40]
            print(f"   ✓ Después de filtrar (ACTIVE/ROSTER_40): {len(filtered_roster)} jugadores")
            
            # 5. Inspeccionar primeros 2 jugadores
            if filtered_roster:
                print(f"\n3️⃣ Inspección de jugadores:")
                for idx, player in enumerate(filtered_roster[:2], 1):
                    person = player.get("person", {})
                    player_id = person.get("id")
                    player_name = person.get("fullName", "N/A")
                    position = player.get("position", {}).get("abbreviation", "DH")
                    status_code = player.get("status", {}).get("code", "N/A")
                    
                    print(f"\n   Jugador {idx}:")
                    print(f"     - ID: {player_id}")
                    print(f"     - Nombre: {player_name}")
                    print(f"     - Posición: {position}")
                    print(f"     - Estado: {status_code}")
                    
                    # Intentar obtener stats del jugador
                    if player_id:
                        stats_url = f"{BASE_URL}/people/{player_id}"
                        stats_params = {"hydrate": "stats(type=season,season=2026)"}
                        try:
                            stats_response = requests.get(stats_url, params=stats_params, timeout=10)
                            stats_response.raise_for_status()
                            stats_data = stats_response.json()
                            stats = stats_data.get("stats", [])
                            print(f"     - Stats disponibles: {len(stats)}")
                            if stats:
                                stat_type = stats[0].get("type", {}).get("displayName", "N/A")
                                print(f"     - Tipo de stats: {stat_type}")
                        except Exception as e:
                            print(f"     - Error al obtener stats: {e}")
            else:
                print("   ❌ No hay jugadores después de filtrar")
        else:
            print("   ❌ No hay equipos")
        
        print("\n" + "=" * 70)
        print("✅ API FUNCIONA CORRECTAMENTE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    debug_api()
