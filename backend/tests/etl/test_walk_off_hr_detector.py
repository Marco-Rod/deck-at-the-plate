"""Discovery de WALK_OFF_HR desde MLB Schedule/Game Feed."""

import copy
import datetime as dt

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import CardEdition, CardRatingProfile, MomentContext, MomentEvaluation, Player, RawPitchEvent
from etl.dto import PlayerSourceRecord
from etl.services.walk_off_hr_detector import detect_walk_off_home_runs


GAME_DATE = dt.date(2026, 9, 2)


def _schedule(*, final=True):
    return {
        "dates": [{
            "date": GAME_DATE.isoformat(),
            "games": [{
                "gamePk": 825042,
                "season": "2026",
                "status": {"abstractGameState": "Final" if final else "Live"},
            }],
        }]
    }


def _feed():
    return {
        "gameData": {"status": {"abstractGameState": "Final", "detailedState": "Final"}},
        "liveData": {
            "plays": {"allPlays": [
                {
                    "about": {"atBatIndex": 69, "isComplete": True},
                    "result": {"eventType": "single", "homeScore": 3, "awayScore": 4},
                },
                {
                    "about": {
                        "atBatIndex": 70,
                        "inning": 9,
                        "halfInning": "bottom",
                        "isComplete": True,
                        "endTime": "2026-09-03T02:15:00Z",
                    },
                    "matchup": {"batter": {"id": 805811}},
                    "result": {"eventType": "home_run", "homeScore": 5, "awayScore": 4},
                },
            ]},
            "linescore": {"teams": {"home": {"runs": 5}, "away": {"runs": 4}}},
            "boxscore": {"teams": {"home": {"players": {
                "ID805811": {"stats": {"batting": {
                    "plateAppearances": 5, "atBats": 4, "hits": 2, "homeRuns": 1, "rbi": 2,
                }}}
            }}}},
        },
    }


class FakeMLBClient:
    def __init__(self, schedule=None, feed=None):
        self.schedule = schedule or _schedule()
        self.feed = feed or _feed()
        self.schedule_calls = []
        self.feed_calls = []
        self.person_calls = []

    def get_schedule(self, date_from, date_to):
        self.schedule_calls.append((date_from, date_to))
        return copy.deepcopy(self.schedule)

    def get_game_feed(self, game_pk):
        self.feed_calls.append(game_pk)
        return copy.deepcopy(self.feed)

    def get_person(self, mlb_id):
        self.person_calls.append(mlb_id)
        return PlayerSourceRecord(mlb_id=mlb_id, full_name="Eli Waldschmidt")


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def test_descubre_walk_off_sin_raw_y_crea_contexto(db):
    client = FakeMLBClient()
    result = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    context = db.get(MomentContext, result.moment_context_ids[0])

    assert db.query(RawPitchEvent).count() == 0
    assert (result.selected, result.confirmed, result.created, result.failed) == (1, 1, 1, 0)
    assert context.player.mlb_id == 805811
    assert context.facts["detector"]["discovery_source"] == "MLB_STATS_API_SCHEDULE"
    assert context.facts["game"]["terminal_at_bat_index"] == 70
    assert context.facts["batting"]["walk_off"] is True
    assert client.person_calls == [805811]
    assert db.query(CardEdition).count() == 1
    assert db.query(MomentEvaluation).count() == 0
    assert db.query(CardRatingProfile).count() == 0


def test_rerun_es_idempotente_y_reutiliza_player(db):
    client = FakeMLBClient()
    first = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    second = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    assert first.created == 1
    assert second.unchanged == 1
    assert first.moment_context_ids == second.moment_context_ids
    assert client.person_calls == [805811]
    assert db.query(Player).count() == 1
    assert db.query(MomentContext).count() == 1


def test_schedule_no_final_no_consulta_feed(db):
    client = FakeMLBClient(schedule=_schedule(final=False))
    result = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    assert result.selected == 0
    assert client.feed_calls == []


def test_ultimo_play_no_walk_off_queda_unconfirmed(db):
    feed = _feed()
    feed["liveData"]["plays"]["allPlays"][-1]["result"]["eventType"] = "field_out"
    client = FakeMLBClient(feed=feed)
    result = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    assert (result.selected, result.confirmed, result.unconfirmed, result.failed) == (1, 0, 1, 0)
    assert db.query(MomentContext).count() == 0


def test_hr_terminal_no_basta_si_home_ya_iba_ganando(db):
    feed = _feed()
    feed["liveData"]["plays"]["allPlays"][-2]["result"].update(homeScore=5, awayScore=4)
    result = detect_walk_off_home_runs(db, FakeMLBClient(feed=feed), date_from=GAME_DATE, date_to=GAME_DATE)
    assert result.unconfirmed == 1


def test_error_de_un_feed_no_aborta_otro_juego(db):
    schedule = _schedule()
    schedule["dates"][0]["games"].insert(0, {
        "gamePk": 825041, "season": 2026, "status": {"abstractGameState": "Final"}
    })
    client = FakeMLBClient(schedule=schedule)
    original = client.get_game_feed

    def get_game_feed(game_pk):
        if game_pk == 825041:
            raise RuntimeError("feed unavailable")
        return original(game_pk)

    client.get_game_feed = get_game_feed
    result = detect_walk_off_home_runs(db, client, date_from=GAME_DATE, date_to=GAME_DATE)
    assert (result.selected, result.confirmed, result.created, result.failed) == (2, 1, 1, 1)
