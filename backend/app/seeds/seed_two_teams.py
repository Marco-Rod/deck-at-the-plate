import json
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Team, PlayerCardModel, CardRarity

def seed_teams_and_players():
    db: Session = SessionLocal()
    try:
        json_path = os.path.join(os.path.dirname(__file__), "data/teams_and_players.json")
        
        with open(json_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        # 1. Poblar Equipos
        for team_data in data.get("teams", []):
            existing_team = db.query(Team).filter(Team.id == team_data["id"]).first()
            if not existing_team:
                db.add(Team(**team_data))
                print(f"Equipo agregado: {team_data['name']}")

        db.commit()

        # 2. Poblar Jugadores
        for player_data in data.get("players", []):
            existing_card = db.query(PlayerCardModel).filter(PlayerCardModel.id == player_data["id"]).first()
            if not existing_card:
                # Convertir el string de rareza al Enum
                player_data["rarity"] = CardRarity[player_data["rarity"]]
                db.add(PlayerCardModel(**player_data))
                print(f"Carta agregada: {player_data['name']} ({player_data['position']})")

        db.commit()
        print("\n ¡Poblado exitoso de equipos y jugadores!")

    except Exception as e:
        db.rollback()
        print(f"\n Error al poblar la base de datos: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_teams_and_players()