# backend/app/seeds/seed_cpu_teams.py

"""
Script de Seed: Creación de Equipos y Cartas CPU para Rival
===========================================================
Ejecutar en Docker:
    docker compose exec baseball_backend python app/seeds/seed_cpu_teams.py
"""
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "../../"))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, "../")))

from sqlalchemy.orm import Session
try:
    from app.database import SessionLocal
    from app.models import PlayerCardModel, CardRarity, Team
except ModuleNotFoundError:
    from database import SessionLocal
    from models import PlayerCardModel, CardRarity, Team

CPU_TEAMS = [
    {"id": "JAL", "name": "Charros", "city": "Jalisco", "primary_color": "#002B66", "secondary_color": "#C5A059", "is_cpu": True},
    {"id": "CUL", "name": "Tomateros", "city": "Culiacán", "primary_color": "#7A003C", "secondary_color": "#FFFFFF", "is_cpu": True},
    {"id": "MTY", "name": "Sultanes", "city": "Monterrey", "primary_color": "#0B162C", "secondary_color": "#D3122A", "is_cpu": True},
    {"id": "MXL", "name": "Águilas", "city": "Mexicali", "primary_color": "#D3122A", "secondary_color": "#002B66", "is_cpu": True},
]

CPU_CARDS = [
    # ==================== CHARROS DE JALISCO (JAL) ====================
    {"id": "card_jal_p1", "team_id": "JAL", "name": "Manny Barreda", "number": "38", "position": "SP", "overall": 88, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 94, "control": 88, "movement": 86, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 94, "control": 88, "movement": 86}, {"pitch_type": "SLIDER", "velocity": 84, "control": 85, "movement": 89}]},
    {"id": "card_jal_p2", "team_id": "JAL", "name": "Alemao Hernández", "number": "81", "position": "RP", "overall": 82, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 92, "control": 83, "movement": 84, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "CHANGE", "velocity": 82, "control": 85, "movement": 88}]},
    {"id": "card_jal_p3", "team_id": "JAL", "name": "Josh Green", "number": "55", "position": "CP", "overall": 85, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 96, "control": 86, "movement": 90, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "SINKER", "velocity": 96, "control": 86, "movement": 90}]},
    {"id": "card_jal_p4", "team_id": "JAL", "name": "Jared Wilson", "number": "44", "position": "RP", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 93, "control": 79, "movement": 82, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 93, "control": 79, "movement": 82}]},
    {"id": "card_jal_b1", "team_id": "JAL", "name": "Japhet Amador", "number": "44", "position": "DH", "overall": 87, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 80, "power": 92, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b2", "team_id": "JAL", "name": "Christian Villanueva", "number": "19", "position": "3B", "overall": 85, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 82, "power": 86, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b3", "team_id": "JAL", "name": "Mateo Gil", "number": "12", "position": "SS", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 78, "power": 79, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b4", "team_id": "JAL", "name": "Manny Rodríguez", "number": "13", "position": "2B", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 84, "power": 76, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b5", "team_id": "JAL", "name": "Reynaldo Rodríguez", "number": "25", "position": "1B", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 81, "power": 85, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b6", "team_id": "JAL", "name": "Sebastian Valle", "number": "59", "position": "C", "overall": 82, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 76, "power": 83, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b7", "team_id": "JAL", "name": "Julian Ornelas", "number": "53", "position": "CF", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 83, "power": 81, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b8", "team_id": "JAL", "name": "José Aguilar", "number": "14", "position": "RF", "overall": 79, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 77, "power": 72, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_jal_b9", "team_id": "JAL", "name": "Fernando Villegas", "number": "22", "position": "LF", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 85, "power": 78, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},

    # ==================== TOMATEROS DE CULIACÁN (CUL) ====================
    {"id": "card_cul_p1", "team_id": "CUL", "name": "Manny Bañuelos", "number": "49", "position": "SP", "overall": 87, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 93, "control": 87, "movement": 88, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 93, "control": 87, "movement": 88}, {"pitch_type": "CURVE", "velocity": 78, "control": 84, "movement": 90}]},
    {"id": "card_cul_p2", "team_id": "CUL", "name": "David Gutiérrez", "number": "62", "position": "RP", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 94, "control": 80, "movement": 82, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 94, "control": 80, "movement": 82}]},
    {"id": "card_cul_p3", "team_id": "CUL", "name": "Spencer Bivens", "number": "51", "position": "CP", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 95, "control": 85, "movement": 87, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "SLIDER", "velocity": 86, "control": 88, "movement": 91}]},
    {"id": "card_cul_p4", "team_id": "CUL", "name": "Sasagi Sánchez", "number": "31", "position": "RP", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 92, "control": 82, "movement": 80, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "CHANGE", "velocity": 83, "control": 82, "movement": 84}]},
    {"id": "card_cul_b1", "team_id": "CUL", "name": "Joey Meneses", "number": "32", "position": "1B", "overall": 89, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 88, "power": 89, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b2", "team_id": "CUL", "name": "Ramiro Peña", "number": "19", "position": "2B", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 84, "power": 74, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b3", "team_id": "CUL", "name": "Sebastián Elizalde", "number": "8", "position": "RF", "overall": 85, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 86, "power": 82, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b4", "team_id": "CUL", "name": "Ali Solís", "number": "44", "position": "C", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 73, "power": 76, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b5", "team_id": "CUL", "name": "Efrén Navarro", "number": "20", "position": "DH", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 82, "power": 75, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b6", "team_id": "CUL", "name": "Emmanuel Ávila", "number": "3", "position": "3B", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 78, "power": 73, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b7", "team_id": "CUL", "name": "José Guadalupe Chávez", "number": "13", "position": "SS", "overall": 78, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 75, "power": 69, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b8", "team_id": "CUL", "name": "Jesus Fabela", "number": "29", "position": "CF", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 81, "power": 71, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_cul_b9", "team_id": "CUL", "name": "Edgar Robles", "number": "15", "position": "LF", "overall": 79, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 77, "power": 70, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},

    # ==================== SULTANES DE MONTERREY (MTY) ====================
    {"id": "card_mty_p1", "team_id": "MTY", "name": "César Vargas", "number": "46", "position": "SP", "overall": 86, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 93, "control": 86, "movement": 85, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 93, "control": 86, "movement": 85}]},
    {"id": "card_mty_p2", "team_id": "MTY", "name": "Norman Elenes", "number": "52", "position": "RP", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 92, "control": 81, "movement": 82, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "SLIDER", "velocity": 84, "control": 81, "movement": 85}]},
    {"id": "card_mty_p3", "team_id": "MTY", "name": "Joe Riley", "number": "39", "position": "CP", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "velocity": 96, "control": 83, "movement": 89, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 96, "control": 83, "movement": 89}]},
    {"id": "card_mty_b1", "team_id": "MTY", "name": "Roberto Valenzuela", "number": "27", "position": "SS", "overall": 88, "rarity": CardRarity.GOLD, "is_two_way": False, "contact": 90, "power": 82, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b2", "team_id": "MTY", "name": "Zoilo Almonte", "number": "57", "position": "DH", "overall": 86, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 80, "power": 90, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b3", "team_id": "MTY", "name": "Ramiro Peña", "number": "14", "position": "2B", "overall": 82, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 83, "power": 73, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b4", "team_id": "MTY", "name": "Victor Mendoza", "number": "35", "position": "1B", "overall": 85, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 84, "power": 85, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b5", "team_id": "MTY", "name": "Asael Sánchez", "number": "18", "position": "RF", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 78, "power": 76, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b6", "team_id": "MTY", "name": "José Cardona", "number": "10", "position": "CF", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 82, "power": 72, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b7", "team_id": "MTY", "name": "Javier Salazar", "number": "7", "position": "3B", "overall": 79, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 76, "power": 71, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b8", "team_id": "MTY", "name": "Omar Rentería", "number": "21", "position": "C", "overall": 78, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 74, "power": 73, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mty_b9", "team_id": "MTY", "name": "Sebastián Elizalde", "number": "25", "position": "LF", "overall": 84, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 83, "power": 80, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},

    # ==================== ÁGUILAS DEL MEXICALI (MXL) ====================
    {"id": "card_mxl_p1", "team_id": "MXL", "name": "David Reyes", "number": "33", "position": "SP", "overall": 87, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 92, "control": 90, "movement": 87, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 92, "control": 90, "movement": 87}]},
    {"id": "card_mxl_p2", "team_id": "MXL", "name": "Jake Sánchez", "number": "28", "position": "CP", "overall": 88, "rarity": CardRarity.GOLD, "is_two_way": False, "velocity": 97, "control": 91, "movement": 90, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "4-SEAM", "velocity": 97, "control": 91, "movement": 90}, {"pitch_type": "SLIDER", "velocity": 87, "control": 89, "movement": 93}]},
    {"id": "card_mxl_p3", "team_id": "MXL", "name": "Thomas Melgarejo", "number": "38", "position": "RP", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "velocity": 91, "control": 82, "movement": 83, "power": 20, "contact": 20, "repertoire": [{"pitch_type": "CHANGE", "velocity": 81, "control": 82, "movement": 85}]},
    {"id": "card_mxl_b1", "team_id": "MXL", "name": "Leo Heras", "number": "9", "position": "LF", "overall": 83, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 84, "power": 77, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b2", "team_id": "MXL", "name": "Xorge Carrillo", "number": "34", "position": "C", "overall": 82, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 78, "power": 80, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b3", "team_id": "MXL", "name": "Reynaldo Rodríguez", "number": "17", "position": "1B", "overall": 86, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 82, "power": 87, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b4", "team_id": "MXL", "name": "Moises Gutiérrez", "number": "22", "position": "2B", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 79, "power": 78, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b5", "team_id": "MXL", "name": "Luis Santos", "number": "5", "position": "3B", "overall": 79, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 76, "power": 74, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b6", "team_id": "MXL", "name": "Javier Salazar", "number": "2", "position": "SS", "overall": 80, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 78, "power": 72, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b7", "team_id": "MXL", "name": "Wynton Bernard", "number": "12", "position": "CF", "overall": 85, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 86, "power": 79, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b8", "team_id": "MXL", "name": "Norberto Obeso", "number": "15", "position": "RF", "overall": 81, "rarity": CardRarity.BRONZE, "is_two_way": False, "contact": 82, "power": 71, "velocity": 30, "control": 30, "movement": 30, "repertoire": []},
    {"id": "card_mxl_b9", "team_id": "MXL", "name": "Kennys Vargas", "number": "24", "position": "DH", "overall": 86, "rarity": CardRarity.SILVER, "is_two_way": False, "contact": 76, "power": 92, "velocity": 30, "control": 30, "movement": 30, "repertoire": []}
]


def seed_cpu_teams():
    db: Session = SessionLocal()
    try:
        teams_added = 0
        teams_updated = 0
        
        for team_data in CPU_TEAMS:
            existing = db.query(Team).filter(Team.id == team_data["id"]).first()
            if not existing:
                team = Team(**team_data)
                db.add(team)
                teams_added += 1
            else:
                # Actualizar el equipo existente con is_cpu=True
                existing.is_cpu = team_data.get("is_cpu", False)
                teams_updated += 1

        db.flush()

        cards_added = 0
        for card_data in CPU_CARDS:
            existing = db.query(PlayerCardModel).filter(PlayerCardModel.id == card_data["id"]).first()
            if not existing:
                card = PlayerCardModel(**card_data)
                db.add(card)
                cards_added += 1

        db.commit()
        print(f"✅ Equipos CPU sembrados exitosamente: {teams_added} equipos creados, {teams_updated} equipos actualizados, {cards_added} cartas nuevas.")
    except Exception as e:
        db.rollback()
        print(f"❌ Error al sembrar equipos CPU: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_cpu_teams()