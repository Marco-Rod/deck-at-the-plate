#!/usr/bin/env python3
"""
Script simple para probar el endpoint de asignación de pack a través de la API.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_pack_assignment():
    print("\n" + "="*80)
    print("Testing Pack Assignment via API")
    print("="*80)
    
    # 1. Registrar usuario
    print("\n1. Registering test user...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={
        "username": f"test_user_{int(__import__('time').time())}",
        "password": "test_password_123"
    })
    
    if response.status_code not in [200, 201]:
        print(f"✗ Registration failed: {response.status_code} {response.text}")
        return False
    
    user_data = response.json()
    user_id = user_data["user_id"]
    print(f"✓ User created: {user_id}")
    
    # Login para obtener token
    print("\n1b. Logging in...")
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", data={
        "username": user_data["username"],
        "password": "test_password_123"
    })
    
    if response.status_code != 200:
        print(f"✗ Login failed: {response.text}")
        return False
    
    auth_data = response.json()
    token = auth_data["access_token"]
    print(f"✓ Login successful")
    
    # 2. Crear equipo personalizado
    print("\n2. Creating personal team...")
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
        print(f"✗ Team creation failed: {response.text}")
        return False
    
    print(f"✓ Team created")
    
    # 3. Obtener equipos disponibles
    print("\n3. Getting available teams...")
    response = requests.get(
        f"{BASE_URL}/api/v1/teams/cpu",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code != 200:
        print(f"✗ Failed to get teams: {response.text}")
        return False
    
    teams = response.json()
    print(f"✓ Found {len(teams)} teams")
    
    if len(teams) < 2:
        print("✗ Need at least 2 teams for testing")
        return False
    
    # 4. Probar con diferentes equipos
    test_teams = [teams[0]["id"], teams[1]["id"]]
    if len(teams) > 2:
        test_teams.append(teams[2]["id"])
    
    all_passed = True
    
    for team_id in test_teams:
        print(f"\n4.{test_teams.index(team_id)+1}. Testing pack assignment for team {team_id}...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/shop/claim-starter-pack",
            json={"team_id": team_id},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code != 200:
            print(f"✗ Pack assignment failed: {response.text}")
            all_passed = False
            continue
        
        pack_data = response.json()
        cards = pack_data.get("cards", [])
        
        print(f"  Cards assigned: {len(cards)}")
        
        # Verificar composición
        team_cards = [c for c in cards if c["team_id"] == team_id]
        other_cards = [c for c in cards if c["team_id"] != team_id]
        
        fielders = [c for c in cards if c["position"] not in ["SP", "RP", "CP"]]
        pitchers = [c for c in cards if c["position"] in ["SP", "RP", "CP"]]
        
        team_fielders = [c for c in team_cards if c["position"] not in ["SP", "RP", "CP"]]
        team_pitchers = [c for c in team_cards if c["position"] in ["SP", "RP", "CP"]]
        
        print(f"  - Total: {len(cards)} (expected 13)")
        print(f"  - From {team_id}: {len(team_cards)} (expected 7)")
        print(f"  - From others: {len(other_cards)} (expected 6)")
        print(f"  - Team fielders: {len(team_fielders)} (expected 5)")
        print(f"  - Team pitchers: {len(team_pitchers)} (expected 2)")
        print(f"  - Total fielders: {len(fielders)} (expected 9)")
        print(f"  - Total pitchers: {len(pitchers)} (expected 4)")
        
        # Verificar posiciones
        pos_count = {}
        for card in cards:
            pos = card["position"]
            pos_count[pos] = pos_count.get(pos, 0) + 1
        
        print(f"\n  Position distribution:")
        max_pos = 0
        for pos in sorted(pos_count.keys()):
            count = pos_count[pos]
            max_pos = max(max_pos, count)
            status = "✓" if count <= 2 else "✗"
            print(f"    {pos}: {count} {status}")
        
        # Verificar raridades
        rarity_count = {}
        for card in cards:
            rarity = card.get("rarity", "UNKNOWN")
            rarity_count[rarity] = rarity_count.get(rarity, 0) + 1
        
        print(f"\n  Rarity distribution:")
        for rarity in sorted(rarity_count.keys()):
            count = rarity_count[rarity]
            print(f"    {rarity}: {count}")
        
        # Validaciones
        errors = []
        if len(cards) != 13:
            errors.append(f"Expected 13 cards, got {len(cards)}")
        if len(team_fielders) != 5:
            errors.append(f"Expected 5 team fielders, got {len(team_fielders)}")
        if len(team_pitchers) != 2:
            errors.append(f"Expected 2 team pitchers, got {len(team_pitchers)}")
        if len(other_cards) != 6:
            errors.append(f"Expected 6 cards from others, got {len(other_cards)}")
        if max_pos > 2:
            errors.append(f"Position duplicated more than 2 times (max: {max_pos})")
        
        if errors:
            print(f"\n✗ Errors:")
            for error in errors:
                print(f"  - {error}")
            all_passed = False
        else:
            print(f"\n✓ All checks passed for {team_id}")
    
    return all_passed

if __name__ == "__main__":
    try:
        if test_pack_assignment():
            print("\n" + "="*80)
            print("✓ All tests passed!")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("✗ Some tests failed")
            print("="*80)
    except Exception as e:
        print(f"\n✗ Exception: {e}")
        import traceback
        traceback.print_exc()
