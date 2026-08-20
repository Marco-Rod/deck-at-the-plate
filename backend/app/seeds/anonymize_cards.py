import os
import sys
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models import PlayerCard

# Mapeo de franquicias ficticias estilo arcade
TEAM_MAPPINGS = {
    "New York Yankees": "New York Empire",
    "Los Angeles Dodgers": "Los Angeles Stars",
    "Seattle Mariners": "Emerald City Captains",
    "Chicago Cubs": "Windy City Bears"
}

FIRST_NAMES = ["Gary", "John", "David", "Carlos", "Leo", "Sho", "Marcus", "Tyler"]
LAST_NAMES = ["Coal", "South", "O'Toole", "Stone", "Vance", "Rios", "Miller"]

def anonymize_database():
    db = SessionLocal()
    try:
        players = db.query(PlayerCard).all()
        print(f"Anonimizando {len(players)} cartas de jugadores...")

        for player in players:
            metadata = dict(player.extra_metadata or {})
            real_team = metadata.get("real_team", "Free Agent")
            
            # 1. Asignar franquicia ficticia
            fictional_team = TEAM_MAPPINGS.get(real_team, f"{real_team} Renegades")
            
            # 2. Generar nombre ficticio manteniendo el valor estadístico intacto
            fictional_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
            
            print(f"Transformando: {player.name} ({real_team}) -> {fictional_name} ({fictional_team})")
            
            # Guardar cambios
            player.name = fictional_name
            metadata["fictional_team"] = fictional_team
            metadata["original_ref_id"] = player.id
            player.extra_metadata = metadata

        db.commit()
        print("¡Anonimización completada! Los atributos estadísticos se mantuvieron intactos.")

    except Exception as e:
        print(f"Error durante la anonimización: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    anonymize_database()