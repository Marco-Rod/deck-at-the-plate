"""Discovery de 10_STRIKEOUT_GAME desde MLB Schedule/Game Feed."""

import copy
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    CardEdition,
    CardRatingProfile,
    MomentContext,
    MomentEvaluation,
    MomentType,
)
from etl.cli import _build_parser
from etl.dto import PlayerSourceRecord
from etl.services.ten_strikeout_game_detector import detect_ten_strikeout_games


GAME_DATE = dt.date(2026, 8, 30)


def _schedule():
    return {
        "dates": [
            {
                "date": GAME_DATE.isoformat(),
                "games": [
                    {
                        "gamePk": 900010,
                        "season": "2026",
                        "status": {"abstractGameState": "Final"},
                    }
                ],
            }
        ]
    }


def _pitcher_record(mlb_id, strikeouts):
    return {
        "person": {"id": mlb_id},
        "stats": {
            "pitching": {
                "inningsPitched": "7.0",
                "strikeOuts": strikeouts,
                "battersFaced": 27,
                "hits": 4,
                "baseOnBalls": 2,
                "earnedRuns": 1,
                "pitchesThrown": 101,
                "strikes": 69,
            }
        },
    }


def _strikeout_plays(pitcher, count, *, start_index, half):
    return [
        {
            "about": {
                "atBatIndex": start_index + index,
                "inning": index // 3 + 1,
                "halfInning": half,
                "isComplete": True,
                "endTime": f"2026-08-31T01:{index:02d}:00Z",
            },
            "matchup": {
                "pitcher": {"id": pitcher},
                "batter": {"id": 800000 + start_index + index},
            },
            "result": {"eventType": "strikeout"},
        }
        for index in range(count)
    ]


def _feed(*pitchers):
    away_players = {}
    home_players = {}
    plays = []
    for index, (pitcher, boxscore_k, play_k, side) in enumerate(pitchers):
        target = away_players if side == "away" else home_players
        target[f"ID{pitcher}"] = _pitcher_record(pitcher, boxscore_k)
        plays.extend(
            _strikeout_plays(
                pitcher,
                play_k,
                start_index=index * 100,
                half="Bottom" if side == "away" else "Top",
            )
        )
    return {
        "gameData": {
            "status": {"abstractGameState": "Final", "detailedState": "Final"}
        },
        "liveData": {
            "plays": {"allPlays": plays},
            "linescore": {
                "currentInning": 9,
                "teams": {"away": {"runs": 4}, "home": {"runs": 2}},
            },
            "boxscore": {
                "teams": {
                    "away": {"players": away_players},
                    "home": {"players": home_players},
                }
            },
        },
    }


class FakeMLBClient:
    def __init__(self, feed):
        self.feed = feed

    def get_schedule(self, _date_from, _date_to):
        return copy.deepcopy(_schedule())

    def get_game_feed(self, game_pk):
        assert game_pk == 900010
        return copy.deepcopy(self.feed)

    def get_person(self, mlb_id):
        return PlayerSourceRecord(mlb_id=mlb_id, full_name=f"Pitcher {mlb_id}")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _detect(db, feed):
    return detect_ten_strikeout_games(
        db,
        FakeMLBClient(feed),
        date_from=GAME_DATE,
        date_to=GAME_DATE,
    )


def test_descubre_exactamente_diez_k_y_persiste_solo_hechos(db):
    result = _detect(db, _feed((111, 10, 10, "away")))

    assert (result.selected, result.confirmed, result.created, result.failed) == (
        1,
        1,
        1,
        0,
    )
    context = db.query(MomentContext).one()
    assert context.role == "PITCHER"
    assert context.facts["game"]["game_date"] == GAME_DATE.isoformat()
    assert context.facts["pitching"] == {
        "innings_pitched": "7.0",
        "strikeouts": 10,
        "batters_faced": 27,
        "hits": 4,
        "walks": 2,
        "earned_runs": 1,
        "pitches": 101,
        "strikes": 69,
        "team_side": "AWAY",
        "game_result": "WON",
    }
    assert len(context.facts["strikeouts"]) == 10
    assert "significance" not in context.facts
    assert db.query(MomentEvaluation).count() == 0
    assert db.query(CardRatingProfile).count() == 0
    assert MomentType.TEN_STRIKEOUT_GAME.value == "10_STRIKEOUT_GAME"


def test_nueve_k_no_califica(db):
    result = _detect(db, _feed((111, 9, 9, "away")))

    assert (result.confirmed, result.unconfirmed) == (0, 1)
    assert db.query(MomentContext).count() == 0


def test_once_k_si_califica(db):
    result = _detect(db, _feed((111, 11, 11, "away")))

    assert (result.confirmed, result.created) == (1, 1)
    assert db.query(MomentContext).one().facts["pitching"]["strikeouts"] == 11


def test_un_juego_puede_producir_dos_pitcher_moments(db):
    result = _detect(
        db,
        _feed((111, 10, 10, "away"), (222, 12, 12, "home")),
    )

    assert (result.selected, result.confirmed, result.created) == (1, 2, 2)
    assert db.query(MomentContext).count() == 2
    assert db.query(CardEdition).count() == 2


def test_boxscore_y_all_plays_inconsistentes_no_confirman(db):
    result = _detect(db, _feed((111, 10, 9, "away")))

    assert (result.confirmed, result.unconfirmed) == (0, 1)
    assert db.query(MomentContext).count() == 0


def test_rerun_es_idempotente(db):
    feed = _feed((111, 10, 10, "away"))
    first = _detect(db, feed)
    second = _detect(db, feed)

    assert first.created == 1
    assert second.unchanged == 1
    assert first.moment_context_ids == second.moment_context_ids
    assert db.query(MomentContext).count() == 1


def test_fallo_de_un_pitcher_no_revierte_ni_impide_al_otro(db, monkeypatch):
    from etl.services import ten_strikeout_game_detector as service

    real_ensure_player = service._ensure_player

    def ensure_player(db, client, mlb_id):
        if mlb_id == 222:
            raise RuntimeError("broken pitcher")
        return real_ensure_player(db, client, mlb_id)

    monkeypatch.setattr(service, "_ensure_player", ensure_player)
    result = _detect(
        db,
        _feed((111, 10, 10, "away"), (222, 12, 12, "home")),
    )

    assert (result.confirmed, result.created, result.failed) == (1, 1, 1)
    assert result.failures[0].pitcher_mlb_id == 222
    assert db.query(MomentContext).count() == 1
    assert db.query(CardEdition).count() == 1


def test_cli_expone_discovery_sin_evaluacion_ni_ratings():
    args = _build_parser().parse_args(
        [
            "detect-ten-strikeout-games",
            "--from",
            "2026-08-25",
            "--to",
            "2026-09-02",
        ]
    )
    assert args.date_from == dt.date(2026, 8, 25)
    assert args.date_to == dt.date(2026, 9, 2)
