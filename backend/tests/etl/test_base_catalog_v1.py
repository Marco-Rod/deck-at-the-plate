"""Contrato del orquestador BASE V1: orden, promoción y fallo temprano."""

from datetime import date
from types import SimpleNamespace

import pytest

from etl.pipelines.base_catalog_v1 import BaseCatalogV1Pipeline


AS_OF = date(2026, 6, 15)
START = date(2026, 3, 26)


class FakeQuery:
    def filter(self, *_args):
        return self

    def order_by(self, *_args):
        return self

    def all(self):
        return []


class FakeDb:
    def query(self, _model):
        return FakeQuery()


def _metadata(events):
    class Metadata:
        def __init__(self, *_args):
            pass

        def run_source_teams(self, **_kwargs):
            events.append("source_teams")
            return "source"

        def run_game_team_mappings(self, **_kwargs):
            events.append("mappings")
            return "mappings"

        def run_rosters(self, **_kwargs):
            events.append("rosters")
            return "rosters"

        def run_game_identities(self, **_kwargs):
            events.append("identities")
            return "identities"

    return Metadata


def _configure(monkeypatch, events, *, gate_ok=True, catalog_status="VALIDATING"):
    monkeypatch.setattr("etl.pipelines.base_catalog_v1.resolve_regular_season_start", lambda *_args, **_kwargs: START)
    monkeypatch.setattr("etl.pipelines.base_catalog_v1.MetadataPipeline", _metadata(events))
    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.validate_game_identities",
        lambda *_args, **_kwargs: SimpleNamespace(ok=gate_ok, detail=["identity error"]),
    )

    class Statcast:
        def __init__(self, *_args):
            pass

        def run(self, **_kwargs):
            events.append("statcast")
            return "statcast"

    monkeypatch.setattr("etl.pipelines.base_catalog_v1.StatcastRawPipeline", Statcast)

    def ratings(_db, *, role, **_kwargs):
        events.append(f"ratings:{role}")
        return SimpleNamespace(ratings=SimpleNamespace(created=1, updated=0, unchanged=0))

    monkeypatch.setattr("etl.pipelines.base_catalog_v1.generate_player_ratings_as_of", ratings)
    def distributions(_db, *, role, **_kwargs):
        events.append(f"distribution:{role}")
        return SimpleNamespace(status="CREATED", population_size=1)

    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.build_overall_rating_distribution",
        distributions,
    )
    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.ensure_system_base_edition",
        lambda *_args, **_kwargs: SimpleNamespace(id="edition"),
    )
    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.publish_card_catalog",
        lambda *_args, **kwargs: (
            events.append(f"publish:{kwargs['activate_if_first']}")
            or SimpleNamespace(catalog_id="catalog", status=catalog_status, catalog_version=1, created=3, issues=[])
        ),
    )
    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.sync_candidate_repertoires",
        lambda *_args, **_kwargs: SimpleNamespace(
            inspected=0, updated=0, missing=0, profiles_refreshed=0
        ),
    )
    monkeypatch.setattr(
        "etl.pipelines.base_catalog_v1.promote_card_catalog",
        lambda *_args, **kwargs: (
            events.append(f"promote:{kwargs['enforce_gameplay_gates']}")
            or SimpleNamespace(catalog_id="catalog", status="ACTIVE", catalog_version=1, created=3, issues=[])
        ),
    )


def test_run_creates_candidate_without_activation(monkeypatch):
    events = []
    _configure(monkeypatch, events)

    result = BaseCatalogV1Pipeline(FakeDb()).run(season=2026, as_of_date=AS_OF)

    assert result.catalog_status == "VALIDATING"
    assert result.activate_requested is False
    assert events == [
        "source_teams", "mappings", "rosters", "identities", "statcast",
        "ratings:BATTER", "ratings:PITCHER",
        "distribution:BATTER", "distribution:PITCHER", "publish:False",
    ]


def test_run_promotes_only_with_explicit_activation(monkeypatch):
    events = []
    _configure(monkeypatch, events)

    result = BaseCatalogV1Pipeline(FakeDb()).run(
        season=2026, as_of_date=AS_OF, activate=True
    )

    assert result.catalog_status == "ACTIVE"
    assert events[-1] == "promote:True"


def test_rerun_of_an_active_edition_does_not_promote_again(monkeypatch):
    events = []
    _configure(monkeypatch, events, catalog_status="ACTIVE")

    result = BaseCatalogV1Pipeline(FakeDb()).run(
        season=2026, as_of_date=AS_OF, activate=True
    )

    assert result.catalog_status == "ACTIVE"
    assert not any(event.startswith("promote:") for event in events)


def test_run_stops_before_statcast_when_identity_gate_fails(monkeypatch):
    events = []
    _configure(monkeypatch, events, gate_ok=False)

    with pytest.raises(ValueError, match="identidades GAME inválidas"):
        BaseCatalogV1Pipeline(FakeDb()).run(season=2026, as_of_date=AS_OF)

    assert events == ["source_teams", "mappings", "rosters", "identities"]


def test_run_rejects_cutoff_from_another_season():
    with pytest.raises(ValueError, match="pertenecer a season"):
        BaseCatalogV1Pipeline(FakeDb()).run(
            season=2026, as_of_date=date(2025, 12, 31)
        )
