"""Detector WALK_OFF_HR exige confirmación terminal del feed oficial MLB."""

import copy
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.enums import ImportStatus
from app.database import Base
from app.models import (
    CardEdition,
    CardRatingProfile,
    DataImportRun,
    MomentContext,
    MomentEvaluation,
    Player,
    RawPitchEvent,
)
from etl.services.walk_off_hr_detector import detect_walk_off_home_runs


GAME_DATE = dt.date(2026, 9, 5)


def _feed():
    return {
        "gameData": {
            "status": {
                "abstractGameState": "Final",
                "detailedState": "Final",
            }
        },
        "liveData": {
            "plays": {
                "allPlays": [
                    {
                        "about": {
                            "atBatIndex": 40,
                            "inning": 9,
                            "halfInning": "bottom",
                            "isComplete": True,
                            "endTime": "2026-09-06T01:30:00Z",
                        },
                        "matchup": {"batter": {"id": 111111}},
                        "result": {
                            "eventType": "single",
                            "homeScore": 3,
                            "awayScore": 4,
                        },
                    },
                    {
                        "about": {
                            "atBatIndex": 41,
                            "inning": 9,
                            "halfInning": "bottom",
                            "isComplete": True,
                            "endTime": "2026-09-06T01:35:12Z",
                        },
                        "matchup": {"batter": {"id": 660271}},
                        "result": {
                            "event": "Home Run",
                            "eventType": "home_run",
                            "description": "Two-run walk-off home run",
                            "homeScore": 5,
                            "awayScore": 4,
                        },
                    },
                ]
            },
            "linescore": {
                "teams": {"home": {"runs": 5}, "away": {"runs": 4}}
            },
            "boxscore": {
                "teams": {
                    "home": {
                        "players": {
                            "ID660271": {
                                "person": {"id": 660271},
                                "stats": {
                                    "batting": {
                                        "plateAppearances": 5,
                                        "atBats": 5,
                                        "hits": 4,
                                        "homeRuns": 2,
                                        "rbi": 5,
                                    }
                                },
                            }
                        }
                    }
                }
            },
        },
    }


class FakeMLBClient:
    def __init__(self, feeds):
        self.feeds = feeds
        self.calls = []

    def get_game_feed(self, game_pk):
        self.calls.append(game_pk)
        return copy.deepcopy(self.feeds[game_pk])


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _seed_candidate(db, *, at_bat=41, batter_mlb_id=660271):
    run = db.query(DataImportRun).first()
    if run is None:
        run = DataImportRun(
            source="STATCAST",
            pipeline_version="1.0.0",
            season=2026,
            date_from=GAME_DATE,
            date_to=GAME_DATE,
            status=ImportStatus.SUCCESS,
        )
        db.add(run)
        db.flush()
    if db.query(Player).filter_by(mlb_id=batter_mlb_id).one_or_none() is None:
        db.add(Player(mlb_id=batter_mlb_id, full_name=f"Player {batter_mlb_id}"))
        db.flush()
    row = RawPitchEvent(
        import_run_id=run.id,
        game_pk=824230,
        game_date=GAME_DATE,
        season=2026,
        at_bat_number=at_bat,
        pitch_number=4,
        batter_mlb_id=batter_mlb_id,
        pitcher_mlb_id=999999,
        inning=9,
        inning_topbot="Bottom",
        event="home_run",
        description="hit_into_play",
        home_team="LAD",
        away_team="PHI",
        raw_payload_hash=(str(at_bat)[-1] * 64),
    )
    db.add(row)
    db.commit()
    return row


def test_confirma_walk_off_y_crea_solo_edition_y_context(db):
    raw = _seed_candidate(db)
    client = FakeMLBClient({824230: _feed()})

    result = detect_walk_off_home_runs(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )
    context = db.get(MomentContext, result.moment_context_ids[0])
    edition = db.get(CardEdition, context.card_edition_id)

    assert (result.selected, result.confirmed, result.created) == (1, 1, 1)
    assert (result.unconfirmed, result.failed) == (0, 0)
    assert context.player.mlb_id == 660271
    assert context.facts["batting"] == {
        "plate_appearances": 5,
        "at_bats": 5,
        "hits": 4,
        "home_runs": 2,
        "runs_batted_in": 5,
        "walk_off": True,
    }
    assert context.facts["game"]["pre_home_score"] == 3
    assert context.facts["game"]["pre_away_score"] == 4
    assert context.facts["game"]["final_home_score"] == 5
    assert context.facts["statcast_candidate"]["raw_pitch_event_id"] == raw.id
    assert edition.code == "2026_WALK_OFF_HR_824230_660271_41"
    assert edition.is_active is False
    assert db.query(MomentEvaluation).count() == 0
    assert db.query(CardRatingProfile).count() == 0


def test_repeticion_es_idempotente(db):
    _seed_candidate(db)
    client = FakeMLBClient({824230: _feed()})
    created = detect_walk_off_home_runs(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )
    unchanged = detect_walk_off_home_runs(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )

    assert created.created == 1
    assert unchanged.unchanged == 1
    assert unchanged.moment_context_ids == created.moment_context_ids
    assert db.query(CardEdition).count() == 1
    assert db.query(MomentContext).count() == 1


def test_acepta_indice_mlb_base_cero_frente_a_at_bat_statcast_base_uno(db):
    _seed_candidate(db, at_bat=41)
    feed = _feed()
    feed["liveData"]["plays"]["allPlays"][0]["about"]["atBatIndex"] = 39
    feed["liveData"]["plays"]["allPlays"][1]["about"]["atBatIndex"] = 40
    result = detect_walk_off_home_runs(
        db,
        FakeMLBClient({824230: feed}),
        date_from=GAME_DATE,
        date_to=GAME_DATE,
    )
    assert result.confirmed == 1


def test_hr_en_novena_no_basta_si_juego_no_es_final(db):
    _seed_candidate(db)
    feed = _feed()
    feed["gameData"]["status"]["abstractGameState"] = "Live"
    result = detect_walk_off_home_runs(
        db,
        FakeMLBClient({824230: feed}),
        date_from=GAME_DATE,
        date_to=GAME_DATE,
    )
    assert (result.confirmed, result.unconfirmed, result.failed) == (0, 1, 0)
    assert db.query(MomentContext).count() == 0


def test_rechaza_hr_que_no_produce_la_ventaja_ganadora(db):
    _seed_candidate(db)
    feed = _feed()
    previous = feed["liveData"]["plays"]["allPlays"][0]["result"]
    previous.update(homeScore=5, awayScore=4)
    result = detect_walk_off_home_runs(
        db,
        FakeMLBClient({824230: feed}),
        date_from=GAME_DATE,
        date_to=GAME_DATE,
    )
    assert result.unconfirmed == 1
    assert db.query(MomentContext).count() == 0


def test_rechaza_hr_que_no_es_el_pa_terminal(db):
    _seed_candidate(db)
    feed = _feed()
    feed["liveData"]["plays"]["allPlays"].append(
        {
            "about": {"atBatIndex": 42, "isComplete": True},
            "matchup": {"batter": {"id": 222222}},
            "result": {"eventType": "field_out", "homeScore": 5, "awayScore": 4},
        }
    )
    result = detect_walk_off_home_runs(
        db,
        FakeMLBClient({824230: feed}),
        date_from=GAME_DATE,
        date_to=GAME_DATE,
    )
    assert result.unconfirmed == 1


def test_un_feed_se_consulta_una_vez_para_varios_candidatos_del_juego(db):
    _seed_candidate(db)
    _seed_candidate(db, at_bat=20, batter_mlb_id=111111)
    client = FakeMLBClient({824230: _feed()})
    result = detect_walk_off_home_runs(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )
    assert result.selected == 2
    assert result.confirmed == 1
    assert result.unconfirmed == 1
    assert client.calls == [824230]
