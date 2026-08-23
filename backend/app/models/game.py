from sqlalchemy import Column, String, Integer, Boolean, JSON
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