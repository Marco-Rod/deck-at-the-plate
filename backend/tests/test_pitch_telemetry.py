"""Pruebas del builder puro de telemetría (PitchEventLog) y su repo.

El builder no toca la base de datos: se prueba contra dicts.
El repo se prueba contra sqlite en-memory con el esquema completo.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.core.enums import BatterApproach, PitchFamily, SwingType
from app.services.pitch_telemetry import (
    approach_match_for_runtime,
    batter_approach_for_runtime,
    build_pitch_event_log_payload,
    pitch_family_for_runtime,
)
from app.repositories.pitch_telemetry_repository import (
    record_pitch_event,
    get_pitch_logs_by_game,
)
from app.models import PlayerCardModel, PitchEventLog
from app.services.card_editions import ensure_system_base_edition


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.info["card_edition_id"] = ensure_system_base_edition(
        session, season=2026
    ).id
    yield session
    session.close()
    engine.dispose()


def _base_kwargs(**overrides):
    kwargs = {
        "game_id": str(uuid.uuid4()),
        "plate_appearance_id": str(uuid.uuid4()),
        "pitch_number": 1,
        "batter_card_id": "bat-1",
        "pitcher_card_id": "pit-1",
        "batter_approach": BatterApproach.FASTBALL,
        "pitcher_zone_choice": 5,
        "pitch_type": "FF",
        "pitch_family": PitchFamily.FASTBALL,
        "probability_distribution": {"hit": 0.35, "strike": 0.30, "ball": 0.35},
        "result": "STRIKE",
        "engine_version": "matchup-engine-v1-dev",
    }
    kwargs.update(overrides)
    return kwargs


class TestBuilder:
    def test_payload_correcto(self):
        payload = build_pitch_event_log_payload(**_base_kwargs())
        assert payload["pitch_number"] == 1
        assert payload["batter_approach"] == BatterApproach.FASTBALL
        assert payload["rng_value"] is None
        assert payload["tactical_modifiers"] is None

    def test_pitch_number_debe_ser_positivo(self):
        with pytest.raises(ValueError, match="pitch_number"):
            build_pitch_event_log_payload(**_base_kwargs(pitch_number=0))

    def test_zona_fuera_de_rango(self):
        with pytest.raises(ValueError, match="pitcher_zone_choice"):
            build_pitch_event_log_payload(**_base_kwargs(pitcher_zone_choice=10))

    def test_zona_bateador_fuera_de_rango(self):
        with pytest.raises(ValueError, match="batter_zone_choice"):
            build_pitch_event_log_payload(**_base_kwargs(batter_zone_choice=-1))

    def test_distribucion_no_suma_uno(self):
        with pytest.raises(ValueError, match="sumar"):
            build_pitch_event_log_payload(**{
                **_base_kwargs(),
                "probability_distribution": {"hit": 0.1, "strike": 0.1, "ball": 0.1},
            })

    def test_taque_con_zona_es_contradiccion(self):
        with pytest.raises(ValueError, match="TAKE"):
            build_pitch_event_log_payload(**{
                **_base_kwargs(batter_approach=BatterApproach.TAKE),
                "batter_zone_choice": 5,
            })

    def test_taque_sin_zona_es_valido(self):
        payload = build_pitch_event_log_payload(**{
            **_base_kwargs(batter_approach=BatterApproach.TAKE),
            "batter_zone_choice": None,
            "approach_match": True,
        })
        assert payload["batter_approach"] == BatterApproach.TAKE

    def test_engine_version_obligatoria(self):
        with pytest.raises(ValueError, match="engine_version"):
            build_pitch_event_log_payload(**_base_kwargs(engine_version=""))


class TestRepository:
    def test_record_y_consulta_por_juego(self, db):
        # Necesario por la FK de PitchEventLog -> player_cards
        batter = PlayerCardModel(id="bat-1", name="Batter", team_id="LAD",
                                 position="CF", overall=85, contact=70, power=75, velocity=90, control=85, movement=80,
                                 card_edition_id=db.info["card_edition_id"])
        pitcher = PlayerCardModel(id="pit-1", name="Pitcher", team_id="SFG",
                                  position="SP", overall=90, contact=40, power=30, velocity=97, control=90, movement=88,
                                  card_edition_id=db.info["card_edition_id"])
        db.add_all([batter, pitcher])
        db.flush()

        log = record_pitch_event(db, build_pitch_event_log_payload(**{
            **_base_kwargs(),
            "batter_zone_choice": 5,
            "zone_match": True,
            "approach_match": True,
            "rng_value": 0.42,
            "pitcher_fatigue": 1.0,
        }))
        assert isinstance(log, PitchEventLog)
        assert log.id is not None

        logs = get_pitch_logs_by_game(db, log.game_id)
        assert len(logs) == 1
        assert logs[0].zone_match is True
        assert logs[0].approach_match is True


# ---------------------------------------------------------------------------
# Mapping runtime pitch_type → pitch_family (P5-A)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("pitch_type", "expected"),
    [
        ("4-SEAM", PitchFamily.FASTBALL),
        ("SINKER", PitchFamily.FASTBALL),
        ("CUTTER", PitchFamily.FASTBALL),
        ("SLIDER", PitchFamily.BREAKING),
        ("CURVE", PitchFamily.BREAKING),
        ("CHANGE", PitchFamily.OFFSPEED),
        ("IBB", PitchFamily.OTHER),
    ],
)
def test_pitch_family_for_runtime_clasifica_el_repertorio(pitch_type, expected):
    assert pitch_family_for_runtime(pitch_type) == expected


def test_pitch_family_for_runtime_desconocido_no_inventa():
    # Una carta legacy con un código fuera del repertorio V1 cae en OTHER:
    # nunca se inventa una familia (misma regla que el ETL).
    assert pitch_family_for_runtime("ZX") == PitchFamily.OTHER
    assert pitch_family_for_runtime("") == PitchFamily.OTHER


# ---------------------------------------------------------------------------
# Dominio BatterApproach del runtime (P5-B / TELEMETRY-DOMAIN-001)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("guessed_pitch", "expected"),
    [
        ("4-SEAM", BatterApproach.FASTBALL),
        ("SINKER", BatterApproach.FASTBALL),
        ("CUTTER", BatterApproach.FASTBALL),
        ("SLIDER", BatterApproach.BREAKING),
        ("CURVE", BatterApproach.BREAKING),
        # OFFSPEED no es un approach seleccionable en V1 → REACT.
        ("CHANGE", BatterApproach.REACT),
        # Sin apuesta / código desconocido → REACT.
        (None, BatterApproach.REACT),
        ("ZX", BatterApproach.REACT),
    ],
)
def test_batter_approach_for_runtime(guessed_pitch, expected):
    assert batter_approach_for_runtime(SwingType.NORMAL, guessed_pitch) == expected


def test_batter_approach_for_runtime_take_gana_siempre():
    # TAKE nunca es un approach de swing, aunque traiga un guess de la CPU.
    assert batter_approach_for_runtime(SwingType.TAKE, "4-SEAM") == BatterApproach.TAKE
    assert batter_approach_for_runtime(SwingType.TAKE, None) == BatterApproach.TAKE


@pytest.mark.parametrize(
    ("approach", "actual_pitch", "expected"),
    [
        (BatterApproach.FASTBALL, "SINKER", True),
        (BatterApproach.FASTBALL, "SLIDER", False),
        (BatterApproach.BREAKING, "CURVE", True),
        (BatterApproach.BREAKING, "4-SEAM", False),
        # REACT/TAKE no tienen acierto binario.
        (BatterApproach.REACT, "SLIDER", None),
        (BatterApproach.TAKE, "SLIDER", None),
    ],
)
def test_approach_match_for_runtime(approach, actual_pitch, expected):
    assert approach_match_for_runtime(approach, actual_pitch) is expected


def test_approach_match_compara_familias_no_tipos():
    # El approach V1 es por familia: acertar CURVE habiendo apostado BREAKING
    # cuenta como acierto, aunque el tipo exacto difiera (reward del motor).
    assert approach_match_for_runtime(BatterApproach.BREAKING, "SLIDER") is True

