"""Pruebas del pipeline metadata y de generate-profiles (spec §7-§9, §23-§24, §33)."""

import datetime as dt

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import (
    Player,
    PlayerSeason,
    PlayerTeamStint,
    Team,
    TeamRosterMember,
    TeamRosterSnapshot,
    CardGenerationProfile,
    BatterSeasonStats,
    PitcherSeasonStats,
)
from app.core.enums import ImportStatus, PitchFamily
from etl.dto import PlayerSourceRecord, TeamSourceRecord
from etl.http.client import ExternalHttpClient
from etl.loaders.core import upsert_player, upsert_player_season, upsert_team
from etl.pipelines.metadata import MetadataPipeline
from etl.sources.mlb import MLBStatsApiClient
from etl.services.card_profiles import generate_profiles

W_FROM = dt.date(2026, 3, 20)
W_TO = dt.date(2026, 8, 31)
SEASON = 2026


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


TEAMS = {"teams": [{"id": 119, "name": "Dodgers", "abbreviation": "LAD", "locationName": "Los Angeles", "active": True}]}
ROSTER = {"roster": [{"person": {"id": 660271, "fullName": "Shohei Ohtani"}, "position": {"code": "P"}, "status": {"code": "ACTIVE"}}]}
PERSON = {"people": [{"id": 660271, "fullName": "Shohei Ohtani", "firstName": "Shohei", "lastName": "Ohtani", "birthDate": "1994-07-05", "primaryPosition": {"abbreviation": "SP"}, "batSide": {"code": "L"}, "pitchHand": {"code": "L"}, "active": True}]}


def _client(routes):
    def handler(request):
        for prefix, payload in routes.items():
            if request.url.path.endswith(prefix):
                return httpx.Response(200, json=payload, request=request)
        return httpx.Response(404, request=request)

    return MLBStatsApiClient(http=ExternalHttpClient(transport=httpx.MockTransport(handler)), base_url="https://mlb.test")


class TestMetadataPipeline:
    def test_importa_equipos_rosters_y_player_season(self, db):
        client = _client({"/teams": TEAMS, "/people/660271": PERSON, "/roster": ROSTER})
        result = MetadataPipeline(db, client).run_teams_and_rosters(
            season=SEASON, data_start_date=W_FROM, data_end_date=W_TO
        )
        assert result.teams == 1
        assert db.query(Team).count() == 1
        assert db.query(Player).count() == 1
        assert db.query(PlayerSeason).count() == 1
        assert db.query(PlayerTeamStint).count() == 1
        player = db.query(Player).one()
        assert player.mlb_id == 660271
        assert player.bats.value == "L"

    def test_import_jugador_especifico(self, db):
        client = _client({"/people/660271": PERSON})
        result = MetadataPipeline(db, client).run_season_snapshot_for(
            660271, season=SEASON, data_start_date=W_FROM, data_end_date=W_TO
        )
        assert db.query(Player).count() == 1
        assert db.query(PlayerSeason).count() == 1

    def test_sync_teams_upserta_idempotente(self, db):
        client = _client({"/teams": TEAMS})
        pipeline = MetadataPipeline(db, client)
        first = pipeline.run_teams(season=SEASON)
        second = pipeline.run_teams(season=SEASON)
        assert first.teams == 1
        assert second.teams == 1
        assert db.query(Team).count() == 1

    def test_sync_rosters_crea_snapshot_y_miembros(self, db):
        client = _client({"/teams": TEAMS, "/people/660271": PERSON, "/roster": ROSTER})
        pipeline = MetadataPipeline(db, client)
        result = pipeline.run_rosters(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
        assert result.players == 1
        assert result.stints == 1
        assert result.roster_snapshots == 1
        assert result.roster_members == 1
        assert db.query(Team).count() == 0  # sync-rosters NO upserta equipos
        assert db.query(TeamRosterSnapshot).count() == 1
        assert db.query(TeamRosterMember).count() == 1
        snapshot = db.query(TeamRosterSnapshot).one()
        assert snapshot.team_id == "LAD"
        assert snapshot.season == SEASON
        assert snapshot.as_of_date == W_TO
        assert snapshot.roster_type == "ACTIVE"
        member = db.query(TeamRosterMember).one()
        assert member.status == "ACTIVE"
        assert member.position == "P"

    def test_sync_rosters_misma_fecha_es_idempotente(self, db):
        client = _client({"/teams": TEAMS, "/people/660271": PERSON, "/roster": ROSTER})
        pipeline = MetadataPipeline(db, client)
        pipeline.run_rosters(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
        pipeline.run_rosters(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
        assert db.query(TeamRosterSnapshot).count() == 1
        assert db.query(TeamRosterMember).count() == 1

    def test_sync_rosters_fecha_distinta_genera_historial(self, db):
        client = _client({"/teams": TEAMS, "/people/660271": PERSON, "/roster": ROSTER})
        pipeline = MetadataPipeline(db, client)
        pipeline.run_rosters(season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
        pipeline.run_rosters(season=SEASON, data_start_date=W_FROM, data_end_date=dt.date(2026, 9, 15))
        assert db.query(TeamRosterSnapshot).count() == 2


class TestGenerateProfiles:
    def _seed_analytics(self, db):
        ohtani = upsert_player(db, PlayerSourceRecord(mlb_id=660271, full_name="Shohei Ohtani"))
        ps = upsert_player_season(db, player=ohtani, season=SEASON, data_start_date=W_FROM, data_end_date=W_TO)
        db.add(BatterSeasonStats(
            player_season_id=ps.id, pa=100, ab=90, hits=30, singles=20, doubles=5, triples=1, home_runs=4,
            walks=8, strikeouts=15, pitches_seen=300, swings=200, whiffs=60, balls_in_play=80,
            swing_rate=0.6, whiff_rate=0.3, contact_rate=0.7, hard_hit_rate=0.2, barrel_rate=0.05,
        ))
        db.commit()
        return ohtani, ps

    def test_genera_perfil_y_es_idempotente(self, db):
        _, ps = self._seed_analytics(db)
        first = generate_profiles(db, season=SEASON)
        assert first.created == 1
        second = generate_profiles(db, season=SEASON)
        assert second.created == 0
        assert second.skipped == 1
        profile = db.query(CardGenerationProfile).one()
        assert profile.player_season_id == ps.id
        assert 0 <= profile.overall_rating <= 99
        assert profile.created_at is not None

    def test_requiere_player_card_model_static(self, db):
        from app.models import PlayerCardModel

        assert callable(getattr(PlayerCardModel, "get_rarity_by_overall", None))