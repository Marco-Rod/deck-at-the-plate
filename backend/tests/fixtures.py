"""Dataset canónico de pruebas — Fase 0 del plan maestro de validación.

Congela el "dataset de prueba": los escenarios F01..F08 definidos en la
sección 15 del plan (Deck_at_the_Plate_Plan_Validacion_Gameplay_Telemetria_
Analitica_v2) como estados de partida reproducibles. Todos los builders son
funciones puras (sin pytest, sin BD) para que puedan reutilizarse desde
cualquier test, la suite de invariantes (Fase 4) o el runner headless (Fase
11).

Contrato del estado (state_data):
    - ``game`` es un ``SimpleNamespace`` con los campos de GameSession que el
      engine consume: outs, balls, strikes, is_top_inning, current_inning,
      score_home, score_away, home_user_id, away_user_id.
    - ``state`` es el dict mutable con: runners, current_pitch, active_pitcher,
      home_pitcher_id, away_pitcher_id, active_batter, away_batter_index,
      away_lineup, home_batter_index, home_lineup, total_innings,
      just_switched_half, active_tactics, tactics, pitch_counts,
      score_history, last_runs_scored, is_game_over, winner_message.

La determinismo es una precondición: construir dos veces un mismo escenario
sin tocar el estado global debe producir diccionarios idénticos.
"""

from __future__ import annotations

import datetime as dt
import hashlib
from types import SimpleNamespace

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

# Importar los modelos deja registrado todo el metadata en ``app.database.Base``
# antes de cualquier ``create_all`` (requisito del patrón canónico de tests).
import app.models  # noqa: F401

# Identidad del baseline congelado (Fase 0).
BASELINE_COMMIT = "4ee14a8"
SCHEMA_HEAD = "0041"

START = dt.date(2026, 8, 25)
END = dt.date(2026, 9, 2)

_HOME_USER = "player-home"
_AWAY_USER = "CPU_BOT"

DEFAULT_LINEUPS = {
    "home_lineup": [f"H{i}" for i in range(9)],
    "away_lineup": [f"A{i}" for i in range(9)],
}


def make_game(**overrides):
    """Stub de GameSession con los campos que consume el engine (puro)."""
    base = dict(
        home_user_id=_HOME_USER,
        away_user_id=_AWAY_USER,
        outs=0,
        balls=0,
        strikes=0,
        is_top_inning=True,
        current_inning=1,
        score_home=0,
        score_away=0,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def make_state(**overrides):
    """Estado state_data canónico de una partida recién creada (puro)."""
    state = {
        "runners": {"1b": None, "2b": None, "3b": None},
        "current_pitch": None,
        "active_pitcher": "H-P1",
        "home_pitcher_id": "H-P1",
        "away_pitcher_id": "A-P1",
        "active_batter": "A0",
        "away_batter_index": 0,
        "away_lineup": list(DEFAULT_LINEUPS["away_lineup"]),
        "home_batter_index": 1,
        "home_lineup": list(DEFAULT_LINEUPS["home_lineup"]),
        "total_innings": 9,
        "just_switched_half": False,
        "active_tactics": {"home": None, "away": None},
        "tactics": make_tactics_state(),
        "pitch_counts": {"H-P1": 0, "A-P1": 0},
        "score_history": {},
        "last_runs_scored": 0,
        "is_game_over": False,
        "winner_message": None,
    }
    state.update(overrides)
    return state


def make_tactics_state(home_deck=(), away_deck=(), home_hand=None, away_hand=None):
    """Mazo táctico determinista (sin random.shuffle global)."""
    return {
        "home": {
            "deck": list(home_deck),
            "hand": list(home_hand) if home_hand is not None else [],
            "discard": [],
        },
        "away": {
            "deck": list(away_deck),
            "hand": list(away_hand) if away_hand is not None else [],
            "discard": [],
        },
    }


def make_card(**overrides):
    """Carta/attributos de bateador o lanzador (stub de PlayerCardModel)."""
    base = dict(
        id="card-1",
        team_id="team-1",
        position="1B",
        overall=75,
        rarity="SILVER",
        power=75,
        contact=75,
        velocity=75,
        control=75,
        movement=75,
        vision=75,
        clutch=75,
        name="Player One",
        number="10",
        is_two_way=False,
        repertoire=["4-SEAM", "SLIDER", "CHANGEUP", "CURVEBALL"],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def make_pitcher_card(**overrides):
    return make_card(
        id="card-pitcher",
        position="SP",
        velocity=85,
        control=80,
        movement=82,
        repertoire=["4-SEAM", "SLIDER", "CHANGEUP", "CURVEBALL"],
        **overrides,
    )


def make_batter_card(**overrides):
    return make_card(
        id="card-batter",
        position="DH",
        contact=80,
        power=82,
        vision=78,
        clutch=75,
        repertoire=[],
        **overrides,
    )


# ---------------------------------------------------------------------------
# Escenarios canónicos (plan §15) -> (SimpleNamespace, dict)
# ---------------------------------------------------------------------------

def scenario_f01(**overrides):
    """Pitcher y batter medios; bases vacías; 0-0; inning 1 (smoke at-bat)."""
    game = make_game()
    state = make_state()
    if overrides.get("state"):
        state.update(overrides.pop("state"))
    game = make_game(**overrides.pop("game", {}))
    return game, state


def scenario_f02(**overrides):
    """2 outs, bases llenas, count 3-2 (transición y scoring bajo presión)."""
    game = make_game(outs=2, balls=3, strikes=2)
    state = make_state(
        runners={"1b": "A1", "2b": "A2", "3b": "A3"},
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f03(**overrides):
    """Pitcher con fatiga alta + bullpen disponible (CPU/human pitcher change)."""
    game = make_game()
    state = make_state(
        pitch_counts={"H-P1": 95, "A-P1": 12},
        bullpen={"home": ["H-P2", "H-P3"], "away": ["A-P2"]},
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f04(**overrides):
    """Pitcher con fatiga alta + bullpen vacío (fallback sin bloqueo)."""
    game = make_game()
    state = make_state(
        pitch_counts={"H-P1": 101, "A-P1": 12},
        bullpen={"home": [], "away": ["A-P2"]},
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f05(**overrides):
    """Runner en 1B/2B (steal éxito/out y tercer out)."""
    game = make_game()
    state = make_state(
        runners={"1b": "A1", "2b": "A2", "3b": None},
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f06(**overrides):
    """Tácticas activas de ambos lados (modifiers y descarte una sola vez)."""
    game = make_game()
    state = make_state(
        active_tactics={"home": "tac_vision_boost", "away": "tac_velocity_boost"},
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f07(**overrides):
    """Bottom 9, home abajo/empatado (walk-off / game over)."""
    game = make_game(is_top_inning=False, current_inning=9, score_home=3, score_away=4)
    state = make_state(
        active_batter="H0",
        home_batter_index=1,
        **overrides.get("state", {}),
    )
    return game, state


def scenario_f08(**overrides):
    """Extra innings (reglas y tácticas EXTRA_INNINGS, ghost runner en 2B)."""
    game = make_game(is_top_inning=True, current_inning=10, outs=2, score_home=3, score_away=3)
    state = make_state(
        runners={"1b": None, "2b": "last-out-away", "3b": None},
        active_batter="A0",
        away_batter_index=0,
        home_batter_index=1,
        **overrides.get("state", {}),
    )
    return game, state


SCENARIOS = {
    "F01": (scenario_f01, "Pitcher/batter medios, bases vacías, 0-0, inning 1"),
    "F02": (scenario_f02, "2 outs, bases llenas, count 3-2"),
    "F03": (scenario_f03, "Pitcher con fatiga alta + bullpen disponible"),
    "F04": (scenario_f04, "Pitcher con fatiga alta + bullpen vacío"),
    "F05": (scenario_f05, "Runner en 1B/2B"),
    "F06": (scenario_f06, "Tácticas activas de ambos lados"),
    "F07": (scenario_f07, "Bottom 9, home abajo/empatado (walk-off)"),
    "F08": (scenario_f08, "Extra innings con ghost runner en 2B"),
}


def all_scenarios():
    """[(codigo, descripcion, builder)] en orden del plan §15."""
    return [(code, desc, fn) for code, (fn, desc) in SCENARIOS.items()]


def scenario(code: str, **overrides):
    """Resuelve un escenario canónico por código (F01..F08)."""
    if code not in SCENARIOS:
        raise ValueError(f"escenario canónico desconocido: {code}")
    builder, _ = SCENARIOS[code]
    return builder(**overrides)


# ---------------------------------------------------------------------------
# Infraestructura de BD de prueba (SQLite en memoria) y catálogo publicable.
# ---------------------------------------------------------------------------

def new_db():
    """Nueva BD SQLite en memoria con claves externas habilitadas.

    Retorna (engine, Session) con el esquema completo (Base.metadata). Es el
    patrón canónico reutilizado por la mayoría de los tests del proyecto.
    """
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    from app.database import Base

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session()


def ensure_edition(db: Session, *, season: int = 2026):
    """Edición BASE del flujo normal (find-or-create idempotente)."""
    from app.services.card_editions import ensure_system_base_edition

    return ensure_system_base_edition(db, season=season)


def make_base_edition(
    db: Session,
    *,
    code: str,
    season: int = 2026,
):
    """Crea una CardEdition BASE independiente para tests multiversión."""
    from app.models import CardEdition, CardEditionSourceType, CardEditionType
    from etl.services.base_eligibility_policy import BASE_ELIGIBILITY_POLICY_VERSION
    from etl.services.card_rating_policies import BASE_RATING_POLICY_VERSION

    edition = CardEdition(
        code=code,
        name=f"Base {code}",
        edition_type=CardEditionType.BASE,
        season=season,
        version="edition-1.0",
        source_type=CardEditionSourceType.SYSTEM,
        rating_policy_version=BASE_RATING_POLICY_VERSION,
        eligibility_policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
        metadata_payload={},
    )
    db.add(edition)
    db.flush()
    return edition


def _fixed_hash(*parts) -> str:
    """Hash determinista de 64 chars (CHECK ck_*_input_hash exige length=64)."""
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


def publishable_player(
    db: Session,
    edition,
    *,
    index: int,
    rarity,
    role: str = "BATTER",
    rating_model_version: str = "ratings-2.0",
    team=None,
    position=None,
):
    """Jugador publicable: perfiles de generación + rating con eligibility.

    Réplica 1:1 del fixture de `tests/etl/test_card_catalog_lifecycle.py`:
    crea Team, SourceTeam, mapping, roster, identidad pública, PlayerRatings,
    CardGenerationProfile y CardRatingProfile (eligibility auto-materializada)
    para la edición dada. Retorna el Player.

    ``team`` reutiliza un Team existente (p. ej. para rosters CPU con varias
    cartas por equipo). ``position`` anula la posición por defecto (SP/DH).
    """
    from app.models import (
        CardGenerationProfile,
        GamePlayerIdentity,
        Player,
        PlayerRatings,
        PlayerSeason,
        SourceTeam,
        SourceTeamGameTeamMapping,
        SourceTeamRosterMember,
        SourceTeamRosterSnapshot,
        Team,
    )
    from etl.services.card_rating_profiles import generate_card_rating_profile

    index = int(index)
    position = position or ("SP" if role == "PITCHER" else "DH")
    if team is None:
        team = Team(
            id=f"team-{index}",
            abbreviation=f"T{index}",
            name=f"Test Team {index}",
            city="Test City",
        )
    _PITCHER_REPERTOIRE = [
        {
            "pitch_type": "FF",
            "pitch_name": "4-Seam Fastball",
            "velocity": 93,
            "control": 88,
            "movement": 42,
        },
        {
            "pitch_type": "SL",
            "pitch_name": "Slider",
            "velocity": 84,
            "control": 79,
            "movement": 48,
        },
        {
            "pitch_type": "CH",
            "pitch_name": "Changeup",
            "velocity": 82,
            "control": 84,
            "movement": 45,
        },
        {
            "pitch_type": "CU",
            "pitch_name": "Curveball",
            "velocity": 78,
            "control": 81,
            "movement": 55,
        },
    ]
    source_team = SourceTeam(
        source="MLB",
        external_id=100 + index,
        source_name=f"Source Team {index}",
        source_abbreviation=f"SRC{index}",
    )
    player = Player(
        mlb_id=600000 + index,
        full_name=f"Player {index}",
        primary_position=position,
    )
    db.add_all([team, source_team, player])
    db.flush()
    db.add(SourceTeamGameTeamMapping(
        source_team_id=source_team.id,
        team_id=team.id,
        valid_from=START,
    ))
    snapshot = SourceTeamRosterSnapshot(
        source_team_id=source_team.id,
        season=2026,
        as_of_date=END,
    )
    db.add(snapshot)
    db.flush()
    db.add(SourceTeamRosterMember(
        roster_snapshot_id=snapshot.id,
        player_id=player.id,
        status="ACTIVE",
        position=position,
    ))
    db.add(GamePlayerIdentity(
        player_id=player.id,
        display_first_name="First",
        display_last_name=f"Player {index}",
        display_name=f"Player {index}",
    ))
    player_season = PlayerSeason(
        player_id=player.id,
        season=2026,
        data_start_date=START,
        data_end_date=END,
    )
    db.add(player_season)
    db.flush()
    ratings = PlayerRatings(
        player_id=player.id,
        season=2026,
        role=role,
        rating_model_version=rating_model_version,
        distribution_version="dist-1.0",
        data_start_date=START,
        data_end_date=END,
        contact_rating=(65 if role == "BATTER" else None),
        power_rating=(65 if role == "BATTER" else None),
        vision_rating=(65 if role == "BATTER" else None),
        clutch_rating=(65 if role == "BATTER" else None),
        velocity_rating=(85 if role == "PITCHER" else None),
        control_rating=(80 if role == "PITCHER" else None),
        movement_rating=(82 if role == "PITCHER" else None),
        stuff_rating=(78 if role == "PITCHER" else None),
        overall_rating=75,
        input_hash=_fixed_hash("ratings", index),
    )
    db.add(ratings)
    db.flush()
    is_pitcher = role == "PITCHER"
    generation = CardGenerationProfile(
        player_season_id=player_season.id,
        rating_model_version=rating_model_version,
        role=role,
        player_ratings_id=ratings.id,
        input_hash=_fixed_hash("generation", player_season.id),
        contact_rating=None if is_pitcher else 65,
        power_rating=None if is_pitcher else 65,
        vision_rating=None if is_pitcher else 65,
        clutch_rating=None if is_pitcher else 65,
        velocity_rating=85 if is_pitcher else None,
        control_rating=80 if is_pitcher else None,
        movement_rating=82 if is_pitcher else None,
        stuff_rating=78 if is_pitcher else None,
        overall_rating=75,
        calculated_rarity=rarity,
        primary_batter_trait=None,
        primary_pitcher_trait="FASTBALL_COMMAND" if is_pitcher else None,
        repertoire_payload=_PITCHER_REPERTOIRE if is_pitcher else None,
        calculation_metadata={"adapter_version": "fixture"},
    )
    db.add(generation)
    db.flush()
    generate_card_rating_profile(
        db,
        source_player_ratings_id=ratings.id,
        card_edition_id=edition.id,
        commit=False,
    )
    # El fixture es un jugador "de catálogo normal": sin evidencia estadística
    # real la policy materializa INELIGIBLE; el dataset canónico lo declara
    # PROVISIONAL (publicable) como el fixture de test_card_catalog_lifecycle.
    from app.models import CardRatingProfile

    rating = (
        db.query(CardRatingProfile)
        .filter_by(
            player_id=player.id,
            card_edition_id=edition.id,
            role=role,
        )
        .one()
    )
    metadata = dict(rating.metadata_payload or {})
    eligibility = dict(metadata.get("eligibility") or {})
    eligibility["status"] = "PROVISIONAL"
    metadata["eligibility"] = eligibility
    rating.metadata_payload = metadata
    db.flush()
    return player


def seed_catalog(
    db: Session,
    *,
    edition=None,
    rarities=("COMMON", "BRONZE", "SILVER", "GOLD", "DIAMOND"),
    start: int = 1,
):
    """Catálogo ACTIVE reproducible: un jugador publicable por rareza.

    Publica una edición con 5 jugadores (uno por tier) y promueve a ACTIVE.
    Retorna (CardCatalog, CardEdition, [Player, ...]).
    """
    from app.models.card import CardRarity
    from app.models import CardCatalog
    from etl.services.card_catalog import publish_card_catalog

    edition = edition or ensure_edition(db)
    players = []
    rarities = [CardRarity(r) if isinstance(r, str) else r for r in rarities]
    for idx, rarity in enumerate(rarities):
        players.append(
            publishable_player(db, edition, index=start + idx, rarity=rarity)
        )
    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    if result.status != "ACTIVE":
        raise AssertionError(f"catalog seed falló: {result.status} {result.issues}")
    catalog = (
        db.query(CardCatalog)
        .filter(CardCatalog.season == 2026, CardCatalog.edition_type == "BASE")
        .order_by(CardCatalog.version.desc())
        .first()
    )
    return catalog, edition, players


ROSTER_TEAM_ID = "3f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e5f"


def seed_roster(
    db: Session,
    edition,
    *,
    team_id: str = ROSTER_TEAM_ID,
    batters: int = 9,
    pitchers: int = 2,
    start: int = 100,
):
    """Roster CPU jugable: un equipo con N bateadores y M pitchers publicados.

    Publica todos los jugadores sobre UN MISMO ``Team`` (id UUID de 36 chars
    compatible con las rutas públicas) y promueve el catálogo a ACTIVE.

    Retorna un dict con:
        catalog, edition, team, lineup (ids de bateadores, hasta 9+),
        pitchers (ids de pitchers).
    """
    from app.models import Team

    edition = edition or ensure_edition(db)
    team = Team(
        id=team_id,
        abbreviation="ROSTER",
        name="Test Roster Team",
        city="Test City",
    )
    db.add(team)
    db.flush()

    signed: list[tuple[object, str]] = []
    for i in range(batters):
        signed.append(
            (
                publishable_player(
                    db,
                    edition,
                    index=start + i,
                    rarity="COMMON",
                    role="BATTER",
                    team=team,
                ),
                "BATTER",
            )
        )
    for j in range(pitchers):
        signed.append(
            (
                publishable_player(
                    db,
                    edition,
                    index=start + batters + j,
                    rarity="SILVER",
                    role="PITCHER",
                    team=team,
                ),
                "PITCHER",
            )
        )

    from etl.services.card_catalog import publish_card_catalog

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    if result.status != "ACTIVE":
        raise AssertionError(f"roster seed falló: {result.status} {result.issues}")

    from app.models import CardCatalog, PlayerCardModel

    catalog = (
        db.query(CardCatalog)
        .filter(CardCatalog.season == 2026, CardCatalog.edition_type == "BASE")
        .order_by(CardCatalog.version.desc())
        .first()
    )
    player_to_role = {p.id: role for p, role in signed}
    lineup = []
    pitchers_ids = []
    for card in db.query(PlayerCardModel).filter(PlayerCardModel.team_id == team.id):
        (pitchers_ids if player_to_role.get(card.player_id) == "PITCHER" else lineup).append(card.id)
    db.commit()
    return {
        "catalog": catalog,
        "edition": edition,
        "team": team,
        "lineup": sorted(lineup),
        "pitchers": sorted(pitchers_ids),
    }


def seed_versioned_cpu_roster(
    db: Session,
    *,
    team_id: str = "4f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e6f",
):
    """Dos generaciones completas del mismo equipo: v1 RETIRED y v2 ACTIVE."""
    from app.models import CardCatalog, PlayerCardModel, Team
    from app.models.card import CardRarity
    from etl.services.card_catalog import promote_card_catalog, publish_card_catalog

    team = Team(
        id=team_id,
        abbreviation="VERSIONED",
        name="Versioned CPU Team",
        city="Test City",
    )
    db.add(team)
    db.flush()
    ed1 = make_base_edition(db, code="2026_GAMEPLAY_CPU_V1")
    ed2 = make_base_edition(db, code="2026_GAMEPLAY_CPU_V2")
    batter_rarities = (
        CardRarity.COMMON,
        CardRarity.BRONZE,
        CardRarity.SILVER,
        CardRarity.GOLD,
        CardRarity.DIAMOND,
        CardRarity.COMMON,
        CardRarity.COMMON,
        CardRarity.COMMON,
        CardRarity.COMMON,
    )

    for index, rarity in enumerate(batter_rarities):
        publishable_player(
            db,
            ed1,
            index=1000 + index,
            rarity=rarity,
            role="BATTER",
            rating_model_version="ratings-1.0",
            team=team,
        )
    for index in range(2):
        publishable_player(
            db,
            ed1,
            index=1100 + index,
            rarity=CardRarity.SILVER,
            role="PITCHER",
            rating_model_version="ratings-1.0",
            team=team,
        )
    db.commit()

    first = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=ed1.id,
        rating_model_version="ratings-1.0",
        data_end_date=END,
    )
    v1 = db.get(CardCatalog, first.catalog_id)
    if first.status != "ACTIVE":
        raise AssertionError(f"v1 seed falló: {first.status} {first.issues}")

    for index, rarity in enumerate(batter_rarities):
        publishable_player(
            db,
            ed2,
            index=2000 + index,
            rarity=rarity,
            role="BATTER",
            rating_model_version="ratings-2.0",
            team=team,
        )
    for index in range(2):
        publishable_player(
            db,
            ed2,
            index=2100 + index,
            rarity=CardRarity.SILVER,
            role="PITCHER",
            rating_model_version="ratings-2.0",
            team=team,
        )
    db.commit()

    second = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=ed2.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    if second.status != "VALIDATING":
        raise AssertionError(f"v2 seed falló: {second.status} {second.issues}")
    v2 = db.get(CardCatalog, second.catalog_id)
    promoted = promote_card_catalog(db, catalog_id=v2.id)
    if promoted.status != "ACTIVE":
        raise AssertionError(f"v2 promote falló: {promoted.status} {promoted.issues}")

    db.refresh(v1)
    db.refresh(v2)
    retired_cards = (
        db.query(PlayerCardModel)
        .filter(PlayerCardModel.catalog_id == v1.id)
        .all()
    )
    active_cards = (
        db.query(PlayerCardModel)
        .filter(PlayerCardModel.catalog_id == v2.id)
        .all()
    )
    if v1.status != "RETIRED" or v2.status != "ACTIVE":
        raise AssertionError("lifecycle v1/v2 no quedó en RETIRED/ACTIVE")
    if v2.supersedes_catalog_id != v1.id:
        raise AssertionError("v2 no conserva el predecesor v1")
    if len(retired_cards) != 11 or len(active_cards) != 11:
        raise AssertionError("cada generación debe contener 9 bateadores + 2 pitchers")
    return {
        "team": team,
        "retired_catalog": v1,
        "active_catalog": v2,
        "retired_cards": retired_cards,
        "active_cards": active_cards,
    }


def seed_incomplete_cpu_roster(
    db: Session,
    *,
    human_team_id: str = "6f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e8f",
    cpu_team_id: str = "7f0c1133-6f5f-4a2a-9d2f-0a1b2c3d4e9f",
    human_batters: int = 9,
    human_pitchers: int = 1,
    cpu_batters: int = 8,
    cpu_pitchers: int = 2,
):
    """Catálogo ACTIVE con humano válido y CPU con solo ocho bateadores."""
    from app.models import CardCatalog, PlayerCardModel, Team
    from etl.services.card_catalog import publish_card_catalog

    edition = make_base_edition(db, code="2026_GAMEPLAY_CPU_INCOMPLETE")
    human_team = Team(
        id=human_team_id,
        abbreviation="HUMAN",
        name="Human Test Team",
        city="Test City",
    )
    cpu_team = Team(
        id=cpu_team_id,
        abbreviation="CPU8",
        name="Incomplete CPU Team",
        city="Test City",
    )
    db.add_all([human_team, cpu_team])
    db.flush()

    for index in range(human_batters):
        publishable_player(
            db,
            edition,
            index=3000 + index,
            rarity="COMMON",
            role="BATTER",
            team=human_team,
        )
    for index in range(human_pitchers):
        publishable_player(
            db,
            edition,
            index=3100 + index,
            rarity="SILVER",
            role="PITCHER",
            team=human_team,
        )
    for index in range(cpu_batters):
        publishable_player(
            db,
            edition,
            index=4000 + index,
            rarity="COMMON",
            role="BATTER",
            team=cpu_team,
        )
    for index in range(cpu_pitchers):
        publishable_player(
            db,
            edition,
            index=4100 + index,
            rarity="SILVER",
            role="PITCHER",
            team=cpu_team,
        )
    db.commit()

    result = publish_card_catalog(
        db,
        season=2026,
        card_edition_id=edition.id,
        rating_model_version="ratings-2.0",
        data_end_date=END,
    )
    if result.status != "ACTIVE":
        raise AssertionError(
            f"incomplete CPU seed falló: {result.status} {result.issues}"
        )
    catalog = db.get(CardCatalog, result.catalog_id)
    human_cards = (
        db.query(PlayerCardModel)
        .filter(
            PlayerCardModel.team_id == human_team.id,
            PlayerCardModel.catalog_id == catalog.id,
        )
        .all()
    )
    cpu_cards = (
        db.query(PlayerCardModel)
        .filter(
            PlayerCardModel.team_id == cpu_team.id,
            PlayerCardModel.catalog_id == catalog.id,
        )
        .all()
    )
    return {
        "catalog": catalog,
        "edition": edition,
        "human_team": human_team,
        "cpu_team": cpu_team,
        "human_cards": human_cards,
        "cpu_cards": cpu_cards,
    }
