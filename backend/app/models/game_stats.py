"""
Modelo: GameEventLog
====================
Registra cada evento de una partida con información del jugador y estadísticas.
Se usa para:
  - Guardar histórico de eventos durante el juego
  - Calcular estadísticas finales (hits, homeruns, strikeouts, etc.)
  - Mostrar en tiempo real en el frontend (box score)
"""

from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean
from datetime import datetime
from app.database import Base


class GameEventLog(Base):
    """
    Registra cada evento individual del juego.
    
    Ejemplos:
    - HIT_1B por bateador X en inning Y
    - STRIKEOUT contra pitcher X en inning Y
    - HOME_RUN por bateador X con 2 corredores en base
    """
    __tablename__ = "game_event_logs"

    id = Column(String, primary_key=True, index=True)
    game_id = Column(String, index=True, nullable=False)
    
    # Identificación del evento
    event_type = Column(String, nullable=False)  # HIT_1B, HIT_2B, HIT_3B, HOME_RUN, STRIKEOUT, WALK, OUT_FLY, OUT_GROUND, BUNT, SACRIFICE_FLY, DOUBLE_PLAY
    inning = Column(Integer, nullable=False)
    is_top_inning = Column(Boolean, nullable=False)  # True=Alta (visita), False=Baja (local)
    
    # Jugadores involucrados
    batter_id = Column(String, nullable=False)  # ID de la tarjeta del bateador
    pitcher_id = Column(String, nullable=False)  # ID de la tarjeta del pitcher
    batter_name = Column(String, nullable=True)  # Nombre del bateador (denormalizado para facilitar queries)
    pitcher_name = Column(String, nullable=True)  # Nombre del pitcher
    
    # Contexto del evento
    balls = Column(Integer, default=0)  # Conteo de bolas
    strikes = Column(Integer, default=0)  # Conteo de strikes
    outs = Column(Integer, default=0)  # Outs en la entrada
    runners_on_base = Column(JSON, nullable=True)  # {"1b": player_id, "2b": player_id, "3b": player_id}
    
    # Resultados
    runs_scored = Column(Integer, default=0)  # Carreras anotadas como resultado
    rbi = Column(Integer, default=0)  # RBI generadas por este evento

    # --- Campos aditivos (telemetría pitch-by-pitch; backward-compatible) ---
    # Agrupa los PitchEventLog que desembocan en este evento final.
    plate_appearance_id = Column(String(36), nullable=True, index=True)
    # Versión del motor que resolvió la jugada; útil para análisis histórico.
    engine_version = Column(String(30), nullable=True, index=True)

    # Metadatos
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<GameEventLog game={self.game_id} inning={self.inning} event={self.event_type} batter={self.batter_name}>"
