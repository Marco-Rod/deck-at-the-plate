"""
Modelos ANALYTICS: perfiles derivados del Matchup Engine V1
===========================================================
Estructura:
    Baseline       → BatterSeasonStats, PitcherSeasonStats
    Zona + familia → BatterZoneProfile, PitcherZoneProfile
    Familia        → BatterPitchFamilyProfile
    Arsenal        → PitcherPitchProfile
    Handedness     → BatterHandednessSplit, PitcherHandednessSplit
    Head-to-Head   → BatterPitcherMatchup

Reglas (ver referencias/nuevos_modelos.docx):
    - Los perfiles se derivan de raw; el engine NUNCA consulta RawPitchEvent.
    - Las tasas conservan SIEMPRE su denominador (pitches, swings, PA, BIP...).
    - Deben generarse niveles ALL además de los específicos para permitir
      fallback sin queries complejas.
    - Rates: Numeric(7,6) en rango 0..1. Métricas AVG/wOBA: Numeric(6,5).
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
)
from app.database import Base
from app.core.enums import PitchFamily, PitchFamilySplit, SplitHand, ThrowHand


def _new_id() -> str:
    return str(uuid.uuid4())


class BatterSeasonStats(Base):
    """Baseline ofensivo de un PlayerSeason. Una fila por snapshot (1:1)."""

    __tablename__ = "batter_season_stats"
    __table_args__ = (
        UniqueConstraint("player_season_id", name="uq_batter_season_stats_player_season"),
        CheckConstraint("pa >= 0 AND ab >= 0", name="ck_batter_season_stats_pa_ab"),
        CheckConstraint("hits >= 0", name="ck_batter_season_stats_hits"),
        CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_season_stats_hhr"),
        CheckConstraint("barrel_rate >= 0 AND barrel_rate <= 1", name="ck_batter_season_stats_barrel"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    pa = Column(Integer, nullable=False, default=0)
    ab = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    singles = Column(Integer, nullable=False, default=0)
    doubles = Column(Integer, nullable=False, default=0)
    triples = Column(Integer, nullable=False, default=0)
    home_runs = Column(Integer, nullable=False, default=0)
    walks = Column(Integer, nullable=False, default=0)
    strikeouts = Column(Integer, nullable=False, default=0)
    pitches_seen = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    balls_in_play = Column(Integer, nullable=False, default=0)
    avg = Column(Numeric(6, 5), nullable=True)
    obp = Column(Numeric(6, 5), nullable=True)
    slg = Column(Numeric(6, 5), nullable=True)
    ops = Column(Numeric(6, 5), nullable=True)
    woba = Column(Numeric(6, 5), nullable=True, index=True)
    xwoba = Column(Numeric(6, 5), nullable=True, index=True)
    avg_exit_velocity = Column(Numeric(6, 2), nullable=True)
    avg_launch_angle = Column(Numeric(6, 2), nullable=True)
    hard_hit_rate = Column(Numeric(7, 6), nullable=True)
    barrel_rate = Column(Numeric(7, 6), nullable=True)
    swing_rate = Column(Numeric(7, 6), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    contact_rate = Column(Numeric(7, 6), nullable=True)
    chase_rate = Column(Numeric(7, 6), nullable=True)
    zone_swing_rate = Column(Numeric(7, 6), nullable=True)
    zone_contact_rate = Column(Numeric(7, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PitcherSeasonStats(Base):
    """Baseline de pitcheo de un PlayerSeason. Una fila por snapshot (1:1)."""

    __tablename__ = "pitcher_season_stats"
    __table_args__ = (
        UniqueConstraint("player_season_id", name="uq_pitcher_season_stats_player_season"),
        CheckConstraint("hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1", name="ck_pitcher_season_stats_hhr"),
        CheckConstraint("barrel_rate_allowed >= 0 AND barrel_rate_allowed <= 1", name="ck_pitcher_season_stats_barrel"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    games = Column(Integer, nullable=False, default=0)
    starts = Column(Integer, nullable=False, default=0)
    batters_faced = Column(Integer, nullable=False, default=0)
    pitches = Column(Integer, nullable=False, default=0)
    outs_recorded = Column(Integer, nullable=False, default=0)
    hits_allowed = Column(Integer, nullable=False, default=0)
    home_runs_allowed = Column(Integer, nullable=False, default=0)
    walks = Column(Integer, nullable=False, default=0)
    strikeouts = Column(Integer, nullable=False, default=0)
    era = Column(Numeric(7, 4), nullable=True)
    whip = Column(Numeric(7, 4), nullable=True)
    woba_allowed = Column(Numeric(6, 5), nullable=True, index=True)
    xwoba_allowed = Column(Numeric(6, 5), nullable=True, index=True)
    avg_velocity = Column(Numeric(5, 2), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    chase_rate = Column(Numeric(7, 6), nullable=True)
    called_strike_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate_allowed = Column(Numeric(7, 6), nullable=True)
    barrel_rate_allowed = Column(Numeric(7, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class BatterZoneProfile(Base):
    """Perfil del bateador por zona 1-9, condicionado por mano y familia de pitch."""

    __tablename__ = "batter_zone_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id",
            "zone",
            "pitcher_hand",
            "pitch_family",
            name="uq_batter_zone_profiles_dimensions",
        ),
        CheckConstraint("zone >= 1 AND zone <= 9", name="ck_batter_zone_profiles_zone_range"),
        CheckConstraint("sample_size >= 0", name="ck_batter_zone_profiles_sample_size"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    zone = Column(SmallInteger, nullable=False, index=True)
    pitcher_hand = Column(
        Enum(SplitHand, name="sorthand", create_type=False), nullable=False, default=SplitHand.ALL, index=True
    )
    pitch_family = Column(
        Enum(PitchFamilySplit, name="pitchfamilysplit", create_type=False), nullable=False, default=PitchFamilySplit.ALL, index=True
    )
    pitches_seen = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    takes = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    contacts = Column(Integer, nullable=False, default=0)
    balls_in_play = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    home_runs = Column(Integer, nullable=False, default=0)
    avg = Column(Numeric(6, 5), nullable=True)
    slg = Column(Numeric(6, 5), nullable=True)
    woba = Column(Numeric(6, 5), nullable=True)
    xwoba = Column(Numeric(6, 5), nullable=True)
    contact_rate = Column(Numeric(7, 6), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate = Column(Numeric(7, 6), nullable=True)
    barrel_rate = Column(Numeric(7, 6), nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)  # alias V1: pitches_seen
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PitcherZoneProfile(Base):
    """Efectividad del pitcher por zona, mano del bateador y familia de pitch."""

    __tablename__ = "pitcher_zone_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id",
            "zone",
            "batter_side",
            "pitch_family",
            name="uq_pitcher_zone_profiles_dimensions",
        ),
        CheckConstraint("zone >= 1 AND zone <= 9", name="ck_pitcher_zone_profiles_zone_range"),
        CheckConstraint("sample_size >= 0", name="ck_pitcher_zone_profiles_sample_size"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    zone = Column(SmallInteger, nullable=False, index=True)
    batter_side = Column(
        Enum(SplitHand, name="sorthand", create_type=False), nullable=False, default=SplitHand.ALL, index=True
    )
    pitch_family = Column(
        Enum(PitchFamilySplit, name="pitchfamilysplit", create_type=False), nullable=False, default=PitchFamilySplit.ALL, index=True
    )
    pitches = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    takes = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    called_strikes = Column(Integer, nullable=False, default=0)
    balls_in_play = Column(Integer, nullable=False, default=0)
    hits_allowed = Column(Integer, nullable=False, default=0)
    home_runs_allowed = Column(Integer, nullable=False, default=0)
    woba_allowed = Column(Numeric(6, 5), nullable=True)
    xwoba_allowed = Column(Numeric(6, 5), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    called_strike_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate_allowed = Column(Numeric(7, 6), nullable=True)
    barrel_rate_allowed = Column(Numeric(7, 6), nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)  # alias V1: pitches
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class BatterPitchFamilyProfile(Base):
    """Resumen del bateador contra cada familia. Fallback cuando zona+familia tiene poca muestra."""

    __tablename__ = "batter_pitch_family_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id", "pitch_family", "pitcher_hand",
            name="uq_batter_pitch_family_profiles_dimensions",
        ),
        CheckConstraint("sample_size >= 0", name="ck_batter_pitch_family_profiles_sample_size"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    pitch_family = Column(
        Enum(PitchFamily, name="pitchfamily", create_type=False), nullable=False, index=True
    )
    pitcher_hand = Column(
        Enum(SplitHand, name="sorthand", create_type=False), nullable=False, default=SplitHand.ALL, index=True
    )
    pitches_seen = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    balls_in_play = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    home_runs = Column(Integer, nullable=False, default=0)
    woba = Column(Numeric(6, 5), nullable=True)
    xwoba = Column(Numeric(6, 5), nullable=True)
    contact_rate = Column(Numeric(7, 6), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate = Column(Numeric(7, 6), nullable=True)
    barrel_rate = Column(Numeric(7, 6), nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)  # pitches_seen
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PitcherPitchProfile(Base):
    """Estadística real de cada lanzamiento del pitcher. Se transforma al repertoire jugable."""

    __tablename__ = "pitcher_pitch_profiles"
    __table_args__ = (
        UniqueConstraint(
            "player_season_id", "pitch_type", "batter_side",
            name="uq_pitcher_pitch_profiles_dimensions",
        ),
        CheckConstraint("pitch_count >= 0", name="ck_pitcher_pitch_profiles_pitch_count"),
        CheckConstraint("usage_rate >= 0 AND usage_rate <= 1", name="ck_pitcher_pitch_profiles_usage"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    pitch_type = Column(String(12), nullable=False, index=True)
    pitch_family = Column(
        Enum(PitchFamily, name="pitchfamily", create_type=False), nullable=False, index=True
    )
    batter_side = Column(
        Enum(SplitHand, name="sorthand", create_type=False), nullable=False, default=SplitHand.ALL, index=True
    )
    pitch_count = Column(Integer, nullable=False, default=0)
    usage_rate = Column(Numeric(7, 6), nullable=True)
    avg_velocity = Column(Numeric(5, 2), nullable=True)
    max_velocity = Column(Numeric(5, 2), nullable=True)
    avg_spin_rate = Column(Numeric(7, 2), nullable=True)
    avg_horizontal_break = Column(Numeric(7, 4), nullable=True)
    avg_vertical_break = Column(Numeric(7, 4), nullable=True)
    avg_extension = Column(Numeric(5, 2), nullable=True)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    called_strikes = Column(Integer, nullable=False, default=0)
    balls_in_play = Column(Integer, nullable=False, default=0)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    chase_rate = Column(Numeric(7, 6), nullable=True)
    called_strike_rate = Column(Numeric(7, 6), nullable=True)
    woba_allowed = Column(Numeric(6, 5), nullable=True)
    xwoba_allowed = Column(Numeric(6, 5), nullable=True)
    hard_hit_rate_allowed = Column(Numeric(7, 6), nullable=True)
    barrel_rate_allowed = Column(Numeric(7, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class BatterHandednessSplit(Base):
    """Resumen del bateador vs pitcher L/R."""

    __tablename__ = "batter_handedness_splits"
    __table_args__ = (
        UniqueConstraint("player_season_id", "pitcher_hand", name="uq_batter_handedness_splits_hand"),
        CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_handedness_splits_hhr"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    pitcher_hand = Column(
        Enum(ThrowHand, name="throwhand", create_type=False), nullable=False, index=True
    )
    pa = Column(Integer, nullable=False, default=0)
    pitches_seen = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    home_runs = Column(Integer, nullable=False, default=0)
    walks = Column(Integer, nullable=False, default=0)
    strikeouts = Column(Integer, nullable=False, default=0)
    avg = Column(Numeric(6, 5), nullable=True)
    slg = Column(Numeric(6, 5), nullable=True)
    woba = Column(Numeric(6, 5), nullable=True)
    xwoba = Column(Numeric(6, 5), nullable=True)
    contact_rate = Column(Numeric(7, 6), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate = Column(Numeric(7, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class PitcherHandednessSplit(Base):
    """Resumen del pitcher vs bateador L/R (side efectivo observado)."""

    __tablename__ = "pitcher_handedness_splits"
    __table_args__ = (
        UniqueConstraint("player_season_id", "batter_side", name="uq_pitcher_handedness_splits_side"),
        CheckConstraint("whiff_rate >= 0 AND whiff_rate <= 1", name="ck_pitcher_handedness_splits_whiff"),
        CheckConstraint("hard_hit_rate_allowed >= 0 AND hard_hit_rate_allowed <= 1", name="ck_pitcher_handedness_splits_hhr"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    player_season_id = Column(
        String(36), ForeignKey("player_seasons.id"), nullable=False, index=True
    )
    batter_side = Column(
        Enum(ThrowHand, name="throwhand", create_type=False), nullable=False, index=True
    )
    batters_faced = Column(Integer, nullable=False, default=0)
    pitches = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    hits_allowed = Column(Integer, nullable=False, default=0)
    home_runs_allowed = Column(Integer, nullable=False, default=0)
    walks = Column(Integer, nullable=False, default=0)
    strikeouts = Column(Integer, nullable=False, default=0)
    woba_allowed = Column(Numeric(6, 5), nullable=True)
    xwoba_allowed = Column(Numeric(6, 5), nullable=True)
    whiff_rate = Column(Numeric(7, 6), nullable=True)
    hard_hit_rate_allowed = Column(Numeric(7, 6), nullable=True)
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)


class BatterPitcherMatchup(Base):
    """Historial agregado entre dos jugadores reales.

    Señal contextual, NUNCA sustituto del perfil global: el engine pondera su
    importancia por sample_size. Puede faltar sin provocar error.
    """

    __tablename__ = "batter_pitcher_matchups"
    __table_args__ = (
        UniqueConstraint(
            "batter_id", "pitcher_id", "season_start", "season_end", "data_end_date",
            name="uq_batter_pitcher_matchups_window",
        ),
        CheckConstraint("hard_hit_rate >= 0 AND hard_hit_rate <= 1", name="ck_batter_pitcher_matchups_hhr"),
    )

    id = Column(String(36), primary_key=True, default=_new_id)
    batter_id = Column(String(36), ForeignKey("players.id"), nullable=False, index=True)
    pitcher_id = Column(String(36), ForeignKey("players.id"), nullable=False, index=True)
    season_start = Column(SmallInteger, nullable=False, index=True)
    season_end = Column(SmallInteger, nullable=False, index=True)
    data_end_date = Column(DateTime(timezone=True), nullable=False, index=True)
    plate_appearances = Column(Integer, nullable=False, default=0)
    at_bats = Column(Integer, nullable=False, default=0)
    pitches = Column(Integer, nullable=False, default=0)
    hits = Column(Integer, nullable=False, default=0)
    singles = Column(Integer, nullable=False, default=0)
    doubles = Column(Integer, nullable=False, default=0)
    triples = Column(Integer, nullable=False, default=0)
    home_runs = Column(Integer, nullable=False, default=0)
    walks = Column(Integer, nullable=False, default=0)
    strikeouts = Column(Integer, nullable=False, default=0)
    swings = Column(Integer, nullable=False, default=0)
    whiffs = Column(Integer, nullable=False, default=0)
    avg = Column(Numeric(6, 5), nullable=True)
    slg = Column(Numeric(6, 5), nullable=True)
    woba = Column(Numeric(6, 5), nullable=True)
    xwoba = Column(Numeric(6, 5), nullable=True)
    hard_hit_rate = Column(Numeric(7, 6), nullable=True)
    sample_size = Column(Integer, nullable=False, default=0)  # convención V1: plate_appearances
    calculated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)