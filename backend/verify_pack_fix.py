#!/usr/bin/env python3
"""
Script para verificar que el starter pack ahora asigna solo 13 cartas.

Uso:
  1. Asegurar que Docker está corriendo: docker compose up -d
  2. Ejecutar: docker exec baseball_backend python verify_pack_fix.py
  
O desde local (con dependencias instaladas):
  python verify_pack_fix.py
"""

import sys
import requests

BASE_URL = "http://localhost:8000"

def test_starter_pack():
    print("\n" + "="*80)
    print("Verificando asignación de Starter Pack (debe ser 13 cartas)")
    print("="*80)
    
    try:
        # 1. Registrar usuario
        import time
        username = f"test_pack_{int(time.time())}"
        
        print(f"\n1. Registrando usuario: {username}")
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
            "username": username,
            "password": "test_password_123"
        })
        
        if response.status_code not in [200, 201]:
            print(f"✗ Error en registro: {response.status_code}")
            print(response.text)
            return False
        
        user_data = response.json()
        user_id = user_data["user_id"]
        print(f"✓ Usuario creado: {user_id}")
        
        # 2. Login
        print("\n2. Iniciando sesión")
        response = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
            "username": username,
            "password": "test_password_123"
        })
        
        if response.status_code != 200:
            print(f"✗ Error en login: {response.status_code}")
            return False
        
        auth_data = response.json()
        token = auth_data["access_token"]
        print("✓ Sesión iniciada")
        
        # 3. Crear equipo
        print("\n3. Creando equipo personal")
        response = requests.post(
            f"{BASE_URL}/api/v1/user/{user_id}/team",
            json={
                "name": "Test Team",
                "short_name": "TST",
                "city": "Test City"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code not in [200, 201]:
            print(f"✗ Error al crear equipo: {response.status_code}")
            print(response.text)
            return False
        
        print("✓ Equipo creado")
        
        # 4. Obtener equipos disponibles
        print("\n4. Obteniendo equipos disponibles")
        response = requests.get(
            f"{BASE_URL}/api/v1/teams/cpu",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"✗ Error al obtener equipos: {response.status_code}")
            return False
        
        teams = response.json()
        if not teams:
            print("✗ No hay equipos disponibles")
            return False
        
        test_team = teams[0]["id"]
        print(f"✓ Equipos disponibles: {len(teams)}")
        print(f"  Probando con equipo: {test_team}")
        
        # 5. Reclamar starter pack
        print(f"\n5. Reclamando starter pack para equipo {test_team}")
        response = requests.post(
            f"{BASE_URL}/api/v1/shop/starter-pack",
            params={"user_id": user_id, "team_id": test_team},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"✗ Error al reclamar pack: {response.status_code}")
            print(response.text)
            return False
        
        pack_data = response.json()
        cards = pack_data.get("cards", [])
        cards_claimed = pack_data.get("cards_claimed", 0)
        
        print(f"✓ Pack reclamado")
        print(f"  Cartas asignadas: {cards_claimed}")
        
        # 6. Verificar
        print(f"\n6. Verificando asignación")
        
        if cards_claimed != 13:
            print(f"✗ ERROR: Se esperaban 13 cartas, se asignaron {cards_claimed}")
            return False
        
        if len(cards) != 13:
            print(f"✗ ERROR: Se esperaban 13 cartas en response, se recibieron {len(cards)}")
            return False
        
        # Analizar composición
        team_cards = [c for c in cards if c.get("team_id") == test_team]
        other_cards = [c for c in cards if c.get("team_id") != test_team]
        
        fielders = [c for c in cards if c.get("position") not in ["SP", "RP", "CP"]]
        pitchers = [c for c in cards if c.get("position") in ["SP", "RP", "CP"]]
        
        team_fielders = [c for c in team_cards if c.get("position") not in ["SP", "RP", "CP"]]
        team_pitchers = [c for c in team_cards if c.get("position") in ["SP", "RP", "CP"]]
        
        print(f"\n  Composición:")
        print(f"    Total: {len(cards)} cartas ✓")
        print(f"    Del equipo {test_team}: {len(team_cards)} (5 fielders + 2 pitchers)")
        print(f"      - Fielders: {len(team_fielders)} {'✓' if len(team_fielders) == 5 else '✗'}")
        print(f"      - Pitchers: {len(team_pitchers)} {'✓' if len(team_pitchers) == 2 else '✗'}")
        print(f"    De otros equipos: {len(other_cards)} cartas {'✓' if len(other_cards) == 6 else '✗'}")
        print(f"    Fielders totales: {len(fielders)} {'✓' if len(fielders) == 9 else '✗'}")
        print(f"    Pitchers totales: {len(pitchers)} {'✓' if len(pitchers) == 4 else '✗'}")
        
        # Verificar posiciones
        pos_count = {}
        for card in cards:
            pos = card.get("position")
            if pos:
                pos_count[pos] = pos_count.get(pos, 0) + 1
        
        print(f"\n  Distribución por posición:")
        has_error = False
        for pos in sorted(pos_count.keys()):
            count = pos_count[pos]
            status = "✓" if count <= 2 else "✗ DUPLICADA"
            if count > 2:
                has_error = True
            print(f"    {pos}: {count} {status}")
        
        if has_error:
            print(f"\n✗ ERROR: Posición duplicada más de 2 veces")
            return False
        
        # Verificar raridades
        rarity_count = {}
        for card in cards:
            rarity = card.get("rarity", "UNKNOWN")
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        print(f"\n  Distribución por raridad:")
        for rarity in sorted(rarity_count.keys()):
            count = rarity_count[rarity]
            print(f"    {rarity}: {count}")
        
        print(f"\n✓ ¡VERIFICACIÓN EXITOSA!")
        print(f"  El starter pack se asigna correctamente con 13 cartas.")
        return True
        
    except Exception as e:
        print(f"\n✗ Excepción: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_starter_pack()
    print("\n" + "="*80)
    if success:
        print("✓ Test passed - Pack assignment is working correctly")
        sys.exit(0)
    else:
        print("✗ Test failed - Check the issues above")
        sys.exit(1)
