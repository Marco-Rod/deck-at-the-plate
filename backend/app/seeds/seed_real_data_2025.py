"""
Seed: Datos reales MLB 2025 (versión actualizada)
===================================================
Pobla la base de datos con un conjunto inicial de cartas de jugadores reales
y cartas tácticas de ejemplo.

Cambios respecto a la versión legacy:
    - Usa PlayerCardModel (columnas individuales: power, contact, velocity, control, movement)
      en lugar del modelo legacy PlayerCard con campo 'attributes' JSON.
    - Incluye el campo 'movement' requerido por el engine.
    - Agrega equipos (Team) antes de insertar cartas para respetar la FK team_id.
    - Compatible con la estructura actual de modelos (models/card.py, models/team.py).

Uso (dentro del contenedor Docker):
    docker compose exec backend python -m app.seeds.seed_real_data_2025
"""

from app.database import SessionLocal, engine
from app.models import PlayerCardModel, TacticCard, CardRarity
from app.models.team import Team
from app.core.identities import game_team_id_for
from app.services.card_editions import ensure_system_base_edition


# Franquicias públicas del seed (id = UUID determinístico V2).
TEAM_DEFS = [
    ("NYY", "New York Yankees", "New York", "#003087", "#C4CED4"),
    ("LAD", "Los Angeles Dodgers", "Los Angeles", "#005A9C", "#FFFFFF"),
    ("HOU", "Houston Astros", "Houston", "#002D62", "#EB6E1F"),
    ("ATL", "Atlanta Braves", "Atlanta", "#CE1141", "#13274F"),
]
TEAM_IDS = {abbr: game_team_id_for(abbr) for abbr, *_ in TEAM_DEFS}


def seed_real_data():
    print("=== Seed: Datos reales MLB 2025 ===")
    print("Reconstruyendo esquema con Alembic (DROP SCHEMA + upgrade head)...")

    import subprocess, sys
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)

    db = SessionLocal()
    try:
        # ------------------------------------------------------------------
        # 1. Equipos
        # ------------------------------------------------------------------
        print("Insertando equipos...")
        teams = [
            Team(id=TEAM_IDS[abbr], abbreviation=abbr, name=name, city=city, primary_color=pc, secondary_color=sc)
            for abbr, name, city, pc, sc in TEAM_DEFS
        ]
        db.add_all(teams)
        db.flush()
        base_edition = ensure_system_base_edition(db, season=2025)

        # ------------------------------------------------------------------
        # 2. Cartas de jugadores (PlayerCardModel con columnas individuales)
        #
        # Atributos:
        #   velocity / control / movement  → Pitcheo (0-99)
        #   power    / contact             → Bateo   (0-99)
        #   overall                        → Rating global (58-99)
        # ------------------------------------------------------------------
        print("Insertando cartas de jugadores...")
        cards = [
            # --- Lanzadores (SP) ---
            PlayerCardModel(
                id="card_nyy_cole_2025",
                team_id=TEAM_IDS["NYY"],
                name="Gerrit Cole",
                number="45",
                position="SP",
                overall=94,
                rarity=CardRarity.GOLD,
                is_two_way=False,
                # Bateo (SP, valores bajos)
                power=20,
                contact=20,
                # Pitcheo
                velocity=96,
                control=92,
                movement=88,
            ),
            PlayerCardModel(
                id="card_lad_yamamoto_2025",
                team_id=TEAM_IDS["LAD"],
                name="Yoshinobu Yamamoto",
                number="18",
                position="SP",
                overall=92,
                rarity=CardRarity.GOLD,
                is_two_way=False,
                power=18,
                contact=22,
                velocity=96,
                control=94,
                movement=91,
            ),
            PlayerCardModel(
                id="card_hou_verlander_2025",
                team_id=TEAM_IDS["HOU"],
                name="Justin Verlander",
                number="35",
                position="SP",
                overall=88,
                rarity=CardRarity.SILVER,
                is_two_way=False,
                power=15,
                contact=20,
                velocity=91,
                control=93,
                movement=85,
            ),
            # --- Relevistas (RP) ---
            PlayerCardModel(
                id="card_nyy_holmes_2025",
                team_id=TEAM_IDS["NYY"],
                name="Clay Holmes",
                number="34",
                position="RP",
                overall=84,
                rarity=CardRarity.SILVER,
                is_two_way=False,
                power=15,
                contact=18,
                velocity=94,
                control=84,
                movement=92,
            ),
            # --- Bateadores ---
            PlayerCardModel(
                id="card_nyy_judge_2025",
                team_id=TEAM_IDS["NYY"],
                name="Aaron Judge",
                number="99",
                position="CF",
                overall=97,
                rarity=CardRarity.DIAMOND,
                is_two_way=False,
                power=99,
                contact=86,
                velocity=50,
                control=50,
                movement=50,
            ),
            PlayerCardModel(
                id="card_nyy_soto_2025",
                team_id=TEAM_IDS["NYY"],
                name="Juan Soto",
                number="22",
                position="DH",
                overall=94,
                rarity=CardRarity.DIAMOND,
                is_two_way=False,
                power=94,
                contact=89,
                velocity=50,
                control=50,
                movement=50,
            ),
            PlayerCardModel(
                id="card_lad_freeman_2025",
                team_id=TEAM_IDS["LAD"],
                name="Freddie Freeman",
                number="5",
                position="1B",
                overall=91,
                rarity=CardRarity.GOLD,
                is_two_way=False,
                power=88,
                contact=93,
                velocity=50,
                control=50,
                movement=50,
            ),
            PlayerCardModel(
                id="card_lad_betts_2025",
                team_id=TEAM_IDS["LAD"],
                name="Mookie Betts",
                number="50",
                position="RF",
                overall=93,
                rarity=CardRarity.GOLD,
                is_two_way=False,
                power=86,
                contact=91,
                velocity=50,
                control=50,
                movement=50,
            ),
            PlayerCardModel(
                id="card_atl_acuna_2025",
                team_id=TEAM_IDS["ATL"],
                name="Ronald Acuña Jr.",
                number="13",
                position="RF",
                overall=96,
                rarity=CardRarity.DIAMOND,
                is_two_way=False,
                power=92,
                contact=87,
                velocity=50,
                control=50,
                movement=50,
            ),
            # --- Jugador de dos vías (TWP) ---
            PlayerCardModel(
                id="card_lad_ohtani_2025",
                team_id=TEAM_IDS["LAD"],
                name="Shohei Ohtani",
                number="17",
                position="TWP",
                overall=99,
                rarity=CardRarity.DIAMOND,
                is_two_way=True,
                # Ohtani tiene atributos reales en ambas categorías
                power=99,
                contact=88,
                velocity=99,
                control=88,
                movement=92,
            ),
        ]
        for card in cards:
            card.card_edition_id = base_edition.id
            card.season = 2025
        db.add_all(cards)
        db.flush()

        # ------------------------------------------------------------------
        # 3. Cartas Tácticas
        # ------------------------------------------------------------------
        print("Insertando cartas tácticas...")
        tactics = [
            TacticCard(
                id="tac_vision_boost",
                name="Paciencia en el Plato",
                category="BUFF",
                target_role="BATTER",
                effects=[{"attribute": "vision", "modifier_type": "PERCENTAGE", "value": 20}],
                description="Aumenta la Visión un +20% en este enfrentamiento. Ideal para conteos 2-0 o 3-1."
            ),
            TacticCard(
                id="tac_power_boost",
                name="Swing de Barril",
                category="BUFF",
                target_role="BATTER",
                effects=[{"attribute": "poder", "modifier_type": "PERCENTAGE", "value": 25}],
                description="Aumenta el Poder un +25%. Incrementa el riesgo de swing abanicado."
            ),
            TacticCard(
                id="tac_contact_boost",
                name="Batazo de Contacto",
                category="BUFF",
                target_role="BATTER",
                effects=[{"attribute": "contacto", "modifier_type": "PERCENTAGE", "value": 15}],
                description="Aumenta el Contacto un +15%. Reduce la tasa de whiff."
            ),
            TacticCard(
                id="tac_slider_break",
                name="Trampa de Efecto",
                category="BUFF",
                target_role="PITCHER",
                effects=[{"attribute": "movimiento", "modifier_type": "PERCENTAGE", "value": 15}],
                description="Aumenta el Movimiento del lanzamiento un +15%. Ideal para sliders y curves."
            ),
            TacticCard(
                id="tac_velocity_boost",
                name="Recta de Fuego",
                category="BUFF",
                target_role="PITCHER",
                effects=[{"attribute": "velocidad", "modifier_type": "PERCENTAGE", "value": 10}],
                description="Aumenta la Velocidad del lanzamiento un +10%. Máximo impacto en zona alta."
            ),
            TacticCard(
                id="tac_debuff_vision",
                name="Lanzamiento Engañoso",
                category="DEBUFF",
                target_role="BATTER",
                effects=[{"attribute": "vision", "modifier_type": "PERCENTAGE", "value": -15}],
                description="Reduce la Visión del bateador un -15% en este enfrentamiento."
            ),
        ]
        db.add_all(tactics)
        db.commit()
        print("✓ Datos de MLB 2025 cargados exitosamente.")
        print(f"  → {len(cards)} cartas de jugadores")
        print(f"  → {len(tactics)} cartas tácticas")
        print(f"  → {len(teams)} equipos")

    except Exception as e:
        print(f"✗ Error al poblar la base de datos: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_real_data()
