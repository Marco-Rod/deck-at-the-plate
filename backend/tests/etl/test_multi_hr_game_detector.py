"""Discovery de MULTI_HR_GAME desde MLB Schedule/Game Feed."""

import copy
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardEdition, CardRatingProfile, MomentContext, MomentEvaluation
from etl.cli import _build_parser
from etl.dto import PlayerSourceRecord
from etl.services.multi_hr_game_detector import detect_multi_hr_games


GAME_DATE = dt.date(2026, 8, 30)


def _schedule():
    return {
        "dates": [
            {
                "date": GAME_DATE.isoformat(),
                "games": [
                    {
                        "gamePk": 900001,
                        "season": "2026",
                        "status": {"abstractGameState": "Final"},
                    }
                ],
            }
        ]
    }


def _play(index, inning, half, batter, *, event="home_run", home=0, away=0):
    return {
        "about": {
            "atBatIndex": index,
            "inning": inning,
            "halfInning": half,
            "isComplete": True,
            "endTime": f"2026-08-31T0{inning}:00:00Z",
        },
        "matchup": {"batter": {"id": batter}},
        "result": {
            "eventType": event,
            "rbi": 1 if event == "home_run" else 0,
            "homeScore": home,
            "awayScore": away,
        },
    }


def _player_record(mlb_id, *, home_runs):
    return {
        "person": {"id": mlb_id},
        "stats": {
            "batting": {
                "plateAppearances": 5,
                "atBats": 4,
                "hits": 3,
                "homeRuns": home_runs,
                "rbi": home_runs + 1,
            }
        },
    }


def _feed():
    return {
        "gameData": {
            "status": {"abstractGameState": "Final", "detailedState": "Final"}
        },
        "liveData": {
            "plays": {
                "allPlays": [
                    _play(10, 2, "top", 111, away=1),
                    _play(20, 3, "bottom", 222, home=1, away=1),
                    _play(52, 7, "top", 111, home=1, away=2),
                    _play(60, 8, "bottom", 222, home=2, away=2),
                ]
            },
            "linescore": {"currentInning": 9},
            "boxscore": {
                "teams": {
                    "away": {"players": {"ID111": _player_record(111, home_runs=2)}},
                    "home": {"players": {"ID222": _player_record(222, home_runs=2)}},
                }
            },
        },
    }


class FakeMLBClient:
    def __init__(self, feed=None):
        self.feed = feed or _feed()
        self.person_calls = []

    def get_schedule(self, _date_from, _date_to):
        return copy.deepcopy(_schedule())

    def get_game_feed(self, game_pk):
        assert game_pk == 900001
        return copy.deepcopy(self.feed)

    def get_person(self, mlb_id):
        self.person_calls.append(mlb_id)
        return PlayerSourceRecord(mlb_id=mlb_id, full_name=f"Player {mlb_id}")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_un_juego_puede_crear_multiples_moments(db):
    client = FakeMLBClient()
    result = detect_multi_hr_games(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )

    assert (result.selected, result.confirmed, result.created, result.failed) == (
        1,
        2,
        2,
        0,
    )
    assert db.query(MomentContext).count() == 2
    assert db.query(CardEdition).count() == 2
    assert db.query(MomentEvaluation).count() == 0
    assert db.query(CardRatingProfile).count() == 0
    assert client.person_calls == [111, 222]

    contexts = db.query(MomentContext).order_by(MomentContext.player_id).all()
    by_mlb_id = {context.player.mlb_id: context for context in contexts}
    away = by_mlb_id[111]
    assert away.facts["batting"]["home_runs"] == 2
    assert [item["at_bat_index"] for item in away.facts["home_runs"]] == [10, 52]
    assert away.facts["game"]["inning_count"] == 9
    assert "significance" not in away.facts


def test_boxscore_no_basta_sin_dos_hr_confirmados_en_all_plays(db):
    feed = _feed()
    feed["liveData"]["plays"]["allPlays"][2]["result"]["eventType"] = "double"
    result = detect_multi_hr_games(
        db, FakeMLBClient(feed), date_from=GAME_DATE, date_to=GAME_DATE
    )

    assert (result.confirmed, result.created) == (1, 1)
    assert db.query(MomentContext).count() == 1
    assert db.query(MomentContext).one().player.mlb_id == 222


def test_rerun_es_idempotente(db):
    client = FakeMLBClient()
    first = detect_multi_hr_games(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )
    second = detect_multi_hr_games(
        db, client, date_from=GAME_DATE, date_to=GAME_DATE
    )

    assert first.created == 2
    assert second.unchanged == 2
    assert first.moment_context_ids == second.moment_context_ids
    assert db.query(MomentContext).count() == 2


def test_cli_expone_discovery_sin_evaluacion_ni_ratings():
    args = _build_parser().parse_args(
        [
            "detect-multi-hr-games",
            "--from",
            "2026-08-25",
            "--to",
            "2026-09-02",
        ]
    )
    assert args.date_from == dt.date(2026, 8, 25)
    assert args.date_to == dt.date(2026, 9, 2)
