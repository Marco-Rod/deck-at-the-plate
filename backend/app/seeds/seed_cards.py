"""
Script de Seed: Poblamiento de Datos Iniciales (28 Cartas Únicas)
==================================================================
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/seed_cards.py
"""
import sys
import os

# Solución al ModuleNotFoundError: agregar la raíz del proyecto al sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

from sqlalchemy.orm import Session
try:
    from app.database import SessionLocal, engine, Base
    from app.models import PlayerCardModel, CardRarity, Team
except ModuleNotFoundError:
    from database import SessionLocal, engine, Base
    from models import PlayerCardModel, CardRarity, Team

Base.metadata.create_all(bind=engine)

INITIAL_TEAMS = [
    {"id": "LAD", "name": "Dodgers", "city": "Los Angeles", "primary_color": "#005A9C", "secondary_color": "#FFFFFF"},
    {"id": "NYY", "name": "Yankees", "city": "New York", "primary_color": "#0C2340", "secondary_color": "#E3D4AD"},
]

INITIAL_CARDS = [
    # ==================== DODGERS (LAD) - 14 PLAYERS ====================
    {
        "id": "card_yamamoto_18", "team_id": "LAD", "name": "Y. Yamamoto", "number": "18", "position": "SP",
        "overall": 91, "rarity": CardRarity.DIAMOND, "is_two_way": False, "velocity": 96, "control": 92, "movement": 88,
        "power": 30, "contact": 25,
        "repertoire": [
            {"pitch_type": "4-SEAM", "velocity": 96, "control": 92, "movement": 88},
            {"pitch_type": "SLIDER", "velocity": 85, "control": 88, "movement": 94},
            {"pitch_type": "CURVE", "velocity": 78, "control": 82, "movement": 91},
            {"pitch_type": "CHANGE", "velocity": 87, "control": 85, "movement": 89}
        ]
    },
    {
        "id": "card_graterol_48", "team_id": "LAD", "name": "Brusdar Graterol", "number": "48", "position": "RP",
        "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 100, "control": 80, "movement": 82,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "SINKER", "velocity": 100, "control": 80, "movement": 82},
            {"pitch_type": "SLIDER", "velocity": 89, "control": 78, "movement": 88}
        ]
    },
    {
        "id": "card_phillips_59", "team_id": "LAD", "name": "Evan Phillips", "number": "59", "position": "CP",
        "overall": 86, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 95, "control": 90, "movement": 91,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "SLIDER", "velocity": 86, "control": 92, "movement": 94},
            {"pitch_type": "4-SEAM", "velocity": 95, "control": 88, "movement": 85},
            {"pitch_type": "CUTTER", "velocity": 90, "control": 86, "movement": 88}
        ]
    },
    {
        "id": "card_vesia_51", "team_id": "LAD", "name": "Alex Vesia", "number": "51", "position": "RP",
        "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 94, "control": 78, "movement": 89,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "4-SEAM", "velocity": 94, "control": 78, "movement": 89},
            {"pitch_type": "SLIDER", "velocity": 84, "control": 75, "movement": 92}
        ]
    },
    {"id": "card_betts_50", "team_id": "LAD", "name": "Mookie Betts", "number": "50", "position": "SS", "overall": 90, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 88, "power": 85, "velocity": 40, "control": 40, "movement": 40, "repertoire": []},
    {
        "id": "card_ohtani_17", "team_id": "LAD", "name": "Shohei Ohtani", "number": "17", "position": "TWP", "overall": 99, "rarity": CardRarity.DIAMOND, "is_two_way": True, "contact": 92, "power": 98, "velocity": 98, "control": 88, "movement": 92,
        "repertoire": [
            {"pitch_type": "4-SEAM", "velocity": 98, "control": 88, "movement": 92},
            {"pitch_type": "SWEOPER", "velocity": 85, "control": 86, "movement": 96},
            {"pitch_type": "SPLITTER", "velocity": 89, "control": 84, "movement": 95}
        ]
    },
    {"id": "card_freeman_5", "team_id": "LAD", "name": "Freddie Freeman", "number": "5", "position": "1B", "overall": 91, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 92, "power": 84, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_smith_16", "team_id": "LAD", "name": "Will Smith", "number": "16", "position": "C", "overall": 86, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 82, "power": 80, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_muncy_13", "team_id": "LAD", "name": "Max Muncy", "number": "13", "position": "3B", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 74, "power": 88, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_lux_9", "team_id": "LAD", "name": "Gavin Lux", "number": "9", "position": "2B", "overall": 78, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 76, "power": 70, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_outman_33", "team_id": "LAD", "name": "James Outman", "number": "33", "position": "CF", "overall": 77, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 72, "power": 76, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_taylor_3", "team_id": "LAD", "name": "Chris Taylor", "number": "3", "position": "LF", "overall": 76, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 73, "power": 73, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_heyward_23", "team_id": "LAD", "name": "Jason Heyward", "number": "23", "position": "RF", "overall": 75, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 74, "power": 71, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_hernandez_37", "team_id": "LAD", "name": "Teoscar Hernández", "number": "37", "position": "DH", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 78, "power": 87, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},

    # ==================== YANKEES (NYY) - 14 PLAYERS ====================
    {
        "id": "card_cole_45", "team_id": "NYY", "name": "Gerrit Cole", "number": "45", "position": "SP",
        "overall": 92, "rarity": CardRarity.DIAMOND, "is_two_way": False, "velocity": 98, "control": 90, "movement": 86,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "4-SEAM", "velocity": 98, "control": 90, "movement": 86},
            {"pitch_type": "SLIDER", "velocity": 89, "control": 85, "movement": 90},
            {"pitch_type": "CURVE", "velocity": 82, "control": 84, "movement": 88}
        ]
    },
    {
        "id": "card_holmes_35", "team_id": "NYY", "name": "Clay Holmes", "number": "35", "position": "CP",
        "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 97, "control": 81, "movement": 93,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "SINKER", "velocity": 97, "control": 81, "movement": 93},
            {"pitch_type": "SLIDER", "velocity": 86, "control": 82, "movement": 89}
        ]
    },
    {
        "id": "card_kahnle_41", "team_id": "NYY", "name": "Tommy Kahnle", "number": "41", "position": "RP",
        "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 95, "control": 79, "movement": 92,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "CHANGE", "velocity": 88, "control": 85, "movement": 94},
            {"pitch_type": "4-SEAM", "velocity": 95, "control": 79, "movement": 80}
        ]
    },
    {
        "id": "card_weaver_30", "team_id": "NYY", "name": "Luke Weaver", "number": "30", "position": "RP",
        "overall": 82, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 96, "control": 83, "movement": 85,
        "power": 20, "contact": 20,
        "repertoire": [
            {"pitch_type": "4-SEAM", "velocity": 96, "control": 83, "movement": 85},
            {"pitch_type": "CHANGE", "velocity": 86, "control": 84, "movement": 88}
        ]
    },
    {"id": "card_judge_99", "team_id": "NYY", "name": "Aaron Judge", "number": "99", "position": "CF", "overall": 96, "rarity": CardRarity.DIAMOND, "is_two_way": False, "contact": 86, "power": 99, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_soto_22", "team_id": "NYY", "name": "Juan Soto", "number": "22", "position": "RF", "overall": 93, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 90, "power": 91, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_stanton_27", "team_id": "NYY", "name": "Giancarlo Stanton", "number": "27", "position": "DH", "overall": 85, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 70, "power": 94, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_torres_25", "team_id": "NYY", "name": "Gleyber Torres", "number": "25", "position": "2B", "overall": 81, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 78, "power": 77, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_volpe_11", "team_id": "NYY", "name": "Anthony Volpe", "number": "11", "position": "SS", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 75, "power": 74, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_verdugo_24", "team_id": "NYY", "name": "Alex Verdugo", "number": "24", "position": "LF", "overall": 79, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 80, "power": 71, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_rizzo_48", "team_id": "NYY", "name": "Anthony Rizzo", "number": "48", "position": "1B", "overall": 78, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 73, "power": 78, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_wells_28", "team_id": "NYY", "name": "Austin Wells", "number": "28", "position": "C", "overall": 77, "rarity": CardRarity.COMMON, "is_two_way": False, "contact": 72, "power": 75, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_chisholm_13", "team_id": "NYY", "name": "Jazz Chisholm Jr.", "number": "13", "position": "3B", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 76, "power": 82, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_dominguez_89", "team_id": "NYY", "name": "Jasson Domínguez", "number": "89", "position": "LF", "overall": 78, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 74, "power": 79, "velocity": 30, "control": 30, "movement": 30, "repertoire": []}
]


def seed_database():
    db: Session = SessionLocal()
    try:
        teams_added = 0
        for team_data in INITIAL_TEAMS:
            existing = db.query(Team).filter(Team.id == team_data["id"]).first()
            if not existing:
                team = Team(**team_data)
                db.add(team)
                teams_added += 1

        db.flush()

        cards_added = 0
        for card_data in INITIAL_CARDS:
            existing = db.query(PlayerCardModel).filter(PlayerCardModel.id == card_data["id"]).first()
            if not existing:
                card = PlayerCardModel(**card_data)
                db.add(card)
                cards_added += 1

        db.commit()
        print(f"✅ Sembrado completado exitosamente: {teams_added} equipos y {cards_added} cartas únicas creadas.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al poblar la base de datos: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()