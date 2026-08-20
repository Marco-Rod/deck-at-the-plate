from sqlalchemy import Column, String, Integer, JSON, Boolean
from app.database import Base

class PlayerCard(Base):
    __tablename__ = "player_cards"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    year = Column(Integer, default=2024)
    attributes = Column(JSON, nullable=False)
    extra_metadata = Column(JSON, nullable=True)

class TacticCard(Base):
    __tablename__ = "tactic_cards"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    target_role = Column(String, nullable=False)
    effects = Column(JSON, nullable=False)
    description = Column(String, nullable=True)

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