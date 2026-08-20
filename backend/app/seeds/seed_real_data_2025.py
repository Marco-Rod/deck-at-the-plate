from app.database import engine, Base, SessionLocal
from app.models import PlayerCard, TacticCard, GameSession

def seed_real_data():
    print(f"Tablas registradas en Base: {list(Base.metadata.tables.keys())}")
    print("Recreando tablas en la base de datos...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Insertando cartas base...")
        cards = [
            PlayerCard(
                id="card_nyy_cole_2025",
                name="Gerrit Cole",
                role="Pitcher",
                year=2025,
                attributes={
                    "velocidad": 96,
                    "movimiento": 88,
                    "control": 92,
                    "estamina": 85,
                    "clutch": 80
                },
                extra_metadata={
                    "real_team": "New York Yankees",
                    "team_code": "NYY",
                    "pitch_types": ["FF", "SL", "CH", "CU"]
                }
            ),
            PlayerCard(
                id="card_nyy_soto_2025",
                name="Juan Soto",
                role="Batter",
                year=2025,
                attributes={
                    "contacto": 89,
                    "poder": 94,
                    "vision": 98,
                    "velocidad": 68,
                    "clutch": 90
                },
                extra_metadata={
                    "real_team": "New York Yankees",
                    "team_code": "NYY",
                    "bats": "L"
                }
            ),
            PlayerCard(
                id="card_lad_ohtani_2025",
                name="Shohei Ohtani",
                role="Batter",
                year=2025,
                attributes={
                    "contacto": 88,
                    "poder": 99,
                    "vision": 82,
                    "velocidad": 92,
                    "clutch": 95
                },
                extra_metadata={
                    "real_team": "Los Angeles Dodgers",
                    "team_code": "LAD",
                    "bats": "L"
                }
            )
        ]

        tactics = [
            TacticCard(
                id="tac_vision_boost",
                name="Paciencia en el Plato",
                category="BUFF",
                target_role="BATTER",
                effects=[{"attribute": "vision", "modifier_type": "PERCENTAGE", "value": 20}],
                description="Aumenta la Visión un +20% en este enfrentamiento."
            ),
            TacticCard(
                id="tac_slider_break",
                name="Trampa de Efecto",
                category="BUFF",
                target_role="PITCHER",
                effects=[{"attribute": "movimiento", "modifier_type": "PERCENTAGE", "value": 15}],
                description="Aumenta el Movimiento del lanzamiento un +15%."
            )
        ]

        db.add_all(cards + tactics)
        db.commit()
        print("¡Cartas iniciales cargadas exitosamente!")

    except Exception as e:
        print(f"Error al poblar BD: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_real_data()