"""Pruebas del client MLB y los loaders core (spec §48: mocked HTTP)."""

import datetime as dt

import pytest
import httpx
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Player, PlayerSeason, PlayerTeamStint, SourceTeam, Team
from etl.dto import PlayerSourceRecord, TeamSourceRecord
from etl.loaders.core import upsert_player, upsert_player_season, upsert_player_team_stint, upsert_source_team, upsert_team
from etl.sources.mlb import MLBStatsApiClient, PlayerMetadataCache


TEAMS_PAYLOAD = {
    "teams": [
        {"id": 119, "name": "Los Angeles Dodgers", "abbreviation": "LAD", "locationName": "Los Angeles", "active": True},
        {"id": 1191, "name": "Philadelphia Phillies", "abbreviation": "PHI", "locationName": "Philadelphia", "active": True},
    ]
}

ROSTER_PAYLOAD = {
    "roster": [
        {
            "person": {"id": 660271, "fullName": "Shohei Ohtani"},
            "jerseyNumber": "17",
            "position": {"code": "P", "abbreviation": "SP"},
            "status": {"code": "ACTIVE"},
        }
    ]
}

PERSON_PAYLOAD = {
    "people": [
        {
            "id": 660271,
            "fullName": "Shohei Ohtani",
            "firstName": "Shohei",
            "lastName": "Ohtani",
            "birthDate": "1994-07-05",
            "primaryPosition": {"abbreviation": "SP"},
            "batSide": {"code": "L"},
            "pitchHand": {"code": "L"},
            "active": True,
        }
    ]
}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


def _mlb_client(routes: dict):
    def handler(request):
        for prefix, payload in routes.items():
            if request.url.path.endswith(prefix):
                return httpx.Response(200, json=payload, request=request)
        return httpx.Response(404, request=request)

    from etl.http.client import ExternalHttpClient

    return MLBStatsApiClient(
        http=ExternalHttpClient(
            transport=httpx.MockTransport(handler), max_retries=0
        ),
        base_url="https://mlb.test/api/v1",
    )


def _game_feed_client(statuses):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        status, payload = statuses[request.url.path]
        return httpx.Response(status, json=payload, request=request)

    from etl.http.client import ExternalHttpClient

    client = MLBStatsApiClient(
        http=ExternalHttpClient(
            transport=httpx.MockTransport(handler), max_retries=0
        ),
        base_url="https://mlb.test/api/v1",
    )
    return client, calls


class TestMLBStatsApiClient:
    def test_get_game_feed_usa_v1_si_responde_200(self):
        payload = {"source": "v1"}
        client, calls = _game_feed_client(
            {"/api/v1/game/824230/feed/live": (200, payload)}
        )
        assert client.get_game_feed(824230) == payload
        assert calls == ["/api/v1/game/824230/feed/live"]

    def test_get_game_feed_usa_v11_solo_si_v1_responde_404(self):
        payload = {"source": "v1.1"}
        client, calls = _game_feed_client(
            {
                "/api/v1/game/824230/feed/live": (404, {}),
                "/api/v1.1/game/824230/feed/live": (200, payload),
            }
        )
        assert client.get_game_feed(824230) == payload
        assert calls == [
            "/api/v1/game/824230/feed/live",
            "/api/v1.1/game/824230/feed/live",
        ]

    def test_get_game_feed_propaga_500_sin_fallback(self):
        client, calls = _game_feed_client(
            {"/api/v1/game/824230/feed/live": (500, {})}
        )
        with pytest.raises(httpx.HTTPStatusError) as error:
            client.get_game_feed(824230)
        assert error.value.response.status_code == 500
        assert calls == ["/api/v1/game/824230/feed/live"]

    def test_get_game_feed_propaga_404_de_v11(self):
        client, calls = _game_feed_client(
            {
                "/api/v1/game/824230/feed/live": (404, {}),
                "/api/v1.1/game/824230/feed/live": (404, {}),
            }
        )
        with pytest.raises(httpx.HTTPStatusError) as error:
            client.get_game_feed(824230)
        assert error.value.response.status_code == 404
        assert calls == [
            "/api/v1/game/824230/feed/live",
            "/api/v1.1/game/824230/feed/live",
        ]

    def test_get_teams_mapping(self):
        client = _mlb_client({"/teams": TEAMS_PAYLOAD})
        teams = client.get_teams(2026)
        assert [t.abbreviation for t in teams] == ["LAD", "PHI"]
        assert teams[0].location_name == "Los Angeles"

    def test_get_roster(self):
        client = _mlb_client({"/teams/119/roster": ROSTER_PAYLOAD})
        roster = client.get_roster(119, 2026)
        assert len(roster) == 1
        assert roster[0].mlb_id == 660271
        assert roster[0].team_abbreviation == ""

    def test_get_person_mapping(self):
        client = _mlb_client({"/people/660271": PERSON_PAYLOAD})
        person = client.get_person(660271)
        assert person is not None
        assert person.mlb_id == 660271
        assert person.bats == "L"
        assert person.throws == "L"
        assert person.primary_position == "SP"
        assert person.birth_date == dt.date(1994, 7, 5)

    def test_player_metadata_cache_resuelve_una_vez(self):
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            return httpx.Response(200, json=PERSON_PAYLOAD, request=request)

        from etl.http.client import ExternalHttpClient

        client = MLBStatsApiClient(
            http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
            base_url="https://mlb.test/api/v1",
        )
        cache = PlayerMetadataCache(client)
        first = cache.get_player(660271)
        second = cache.get_player(660271)
        assert first.mlb_id == second.mlb_id == 660271
        assert calls["n"] == 1


class TestLoadersCore:
    def test_upsert_team_por_abbreviation(self, db):
        team = upsert_team(db, TeamSourceRecord(mlb_team_id=119, name="Los Angeles Dodgers", abbreviation="LAD", location_name="Los Angeles", active=True))
        db.commit()
        assert len(team.id) == 36  # UUID determinístico
        assert team.abbreviation == "LAD"
        assert db.get(Team, team.id).city == "Los Angeles"

    def test_upsert_player_por_mlb_id(self, db):
        player = upsert_player(db, PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani", bats="L", throws="L", primary_position="SP"))
        db.commit()
        assert db.query(Player).count() == 1
        assert player.mlb_id == 660271
        stored = db.execute(
            text("SELECT bats, throws FROM players WHERE mlb_id = :mlb_id"),
            {"mlb_id": 660271},
        ).one()
        assert stored == ("L", "L")

    def test_upsert_player_reutiliza_misma_fila(self, db):
        record = PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani")
        upsert_player(db, record)
        db.flush()
        upsert_player(db, record)
        db.commit()
        assert db.query(Player).count() == 1

    def test_upsert_player_season_por_ventana(self, db):
        player = upsert_player(db, PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani"))
        upsert_player_season(db, player=player, season=2026, data_start_date=dt.date(2026, 3, 20), data_end_date=dt.date(2026, 8, 31))
        db.flush()
        upsert_player_season(db, player=player, season=2026, data_start_date=dt.date(2026, 3, 20), data_end_date=dt.date(2026, 8, 31))
        db.commit()
        assert db.query(PlayerSeason).count() == 1

    def test_upsert_player_team_stint_por_clave_unica(self, db):
        player = upsert_player(db, PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani"))
        source_team = upsert_source_team(db, TeamSourceRecord(mlb_team_id=119, name="Dodgers", abbreviation="LAD", location_name="LA", active=True))
        for _ in range(2):
            upsert_player_team_stint(db, player=player, season=2026, source_team_id=source_team.id, start_date=dt.date(2026, 3, 20))
        db.commit()
        assert db.query(PlayerTeamStint).count() == 1
