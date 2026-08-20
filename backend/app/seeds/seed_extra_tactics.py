import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models import TacticCard

def seed_extra_tactics():
    db = SessionLocal()
    try:
        extra_tactics = [
            TacticCard(
                id="tac_iron_closer",
                name="Cerrador de Hierro",
                category="EXTRA_INNINGS",
                target_role="PITCHER",
                effects=[
                    {"attribute": "control", "modifier_type": "PERCENTAGE", "value": 20},
                    {"attribute": "movimiento", "modifier_type": "PERCENTAGE", "value": 15}
                ],
                description="Incrementa Control (+20%) y Movimiento (+15%) a partir del inning 10."
            ),
            TacticCard(
                id="tac_walkoff_power",
                name="Batazo de Oro",
                category="EXTRA_INNINGS",
                target_role="BATTER",
                effects=[
                    {"attribute": "vision", "modifier_type": "PERCENTAGE", "value": 25},
                    {"attribute": "poder", "modifier_type": "PERCENTAGE", "value": 20}
                ],
                description="Aumenta Visión (+25%) y Poder (+20%) para buscar dejar al rival en el campo."
            ),
            TacticCard(
                id="tac_emergency_contact",
                name="Contacto de Emergencia",
                category="EXTRA_INNINGS",
                target_role="BATTER",
                effects=[
                    {"attribute": "contacto", "modifier_type": "PERCENTAGE", "value": 30}
                ],
                description="Otorga +30% de Contacto para asegurar poner la pelota en juego."
            ),
            TacticCard(
                id="tac_home_plate_lock",
                name="Cerrojo en Home",
                category="EXTRA_INNINGS",
                target_role="PITCHER",
                effects=[
                    {"attribute": "velocidad", "modifier_type": "PERCENTAGE", "value": 15},
                    {"attribute": "control", "modifier_type": "PERCENTAGE", "value": 15}
                ],
                description="Neutraliza el avance del corredor automático en extra innings."
            )
        ]

        print("Insertando cartas tácticas de extra innings...")
        for tactic in extra_tactics:
            db.merge(tactic)  # Inserta o actualiza por ID si ya existe

        db.commit()
        print("¡Cartas de extra innings guardadas exitosamente en PostgreSQL!")

    except Exception as e:
        print(f"Error al poblar BD: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_extra_tactics()