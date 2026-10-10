from sqlalchemy import Column, String, Integer, Boolean, JSON, ForeignKey
from app.database import Base


class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(String, primary_key=True, index=True)
    home_user_id = Column(String, nullable=False)
    away_user_id = Column(String, nullable=False)
    current_inning = Column(Integer, default=1)
    is_top_inning = Column(Boolean, default=True)
    outs = Column(Integer, default=0)
    balls = Column(Integer, default=0)
    strikes = Column(Integer, default=0)
    score_home = Column(Integer, default=0)
    score_away = Column(Integer, default=0)
    state_data = Column(JSON, nullable=True)

    # --- Provenance (GAMEPLAY-PROVENANCE-001) --------------------------
    # Snapshot inmutable tomado UNA vez en create(). Nunca se relee el
    # catálogo ACTIVE para reinterpretar una partida existente: si el
    # catálogo se promueve después, la partida vieja debe seguir diciendo
    # con qué cartas se jugó.
    #
    # rating_model_version es denormalización deliberada: también vive en
    # card_catalogs, pero persistinglo aquí permite responder directamente
    # qué modelo de ratings usó la partida y detectar sesiones incoherentes
    # sin reconstruir el dato por join.
    catalog_id = Column(
        String(36),
        ForeignKey("card_catalogs.id", ondelete="RESTRICT"),
        index=True,
    )
    rating_model_version = Column(String(30), index=True)
    rules_version = Column(String(30))
    engine_version = Column(String(30))
    engine_build = Column(String(30), index=True)