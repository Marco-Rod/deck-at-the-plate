"""Pruebas del adaptador Statcast: query builder, chunking, CSV y headers."""

import datetime as dt
import pathlib

import httpx
import pytest

from etl.http.client import ExternalHttpClient
from etl.sources.statcast import (
    REQUIRED_COLUMNS,
    StatcastCSVParser,
    StatcastQueryBuilder,
    StatcastSourceAdapter,
    split_date_ranges,
    validate_headers,
)

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def test_split_date_ranges_trocitos_de_5_dias():
    windows = split_date_ranges(dt.date(2026, 4, 1), dt.date(2026, 4, 15), chunk_days=5)
    assert windows == [
        (dt.date(2026, 4, 1), dt.date(2026, 4, 5)),
        (dt.date(2026, 4, 6), dt.date(2026, 4, 10)),
        (dt.date(2026, 4, 11), dt.date(2026, 4, 15)),
    ]


def test_split_date_ranges_ventana_invertida_vacia():
    assert split_date_ranges(dt.date(2026, 4, 5), dt.date(2026, 4, 1)) == []


class TestQueryBuilder:
    def test_date_range_params(self):
        qb = StatcastQueryBuilder()
        params = qb.build_date_range(dt.date(2026, 4, 1), dt.date(2026, 4, 5))
        assert params["all"] == "true"
        assert params["type"] == "details"
        assert params["game_date_gt"] == "2026-04-01"
        assert params["game_date_lt"] == "2026-04-05"

    def test_batter_lookup(self):
        params = StatcastQueryBuilder().build_batter(660271, dt.date(2026, 4, 1), dt.date(2026, 4, 5))
        assert params["batters_lookup[]"] == "660271"

    def test_pitcher_lookup(self):
        params = StatcastQueryBuilder().build_pitcher(669373, dt.date(2026, 4, 1), dt.date(2026, 4, 5))
        assert params["pitchers_lookup[]"] == "669373"


class TestCSVParser:
    def test_parse_fixture_con_landas_y_tipos(self):
        parser = StatcastCSVParser()
        records = parser.parse((FIXTURES / "statcast_small.csv").read_text())
        assert len(records) == 7
        first = records[0]
        assert first.game_pk == 716180
        assert first.game_date == dt.date(2026, 4, 1)
        assert first.batter_mlb_id == 660271
        assert first.pitcher_mlb_id == 669373
        assert first.stand == "L"
        assert first.description == "swinging_strike"
        assert first.release_speed is not None
        assert first.zone == 4

    def test_blank_optionals_son_none(self):
        parser = StatcastCSVParser()
        records = parser.parse((FIXTURES / "statcast_small.csv").read_text())
        third = records[2]
        assert third.bb_type == "line_drive"
        r4 = records[3]
        assert r4.zone is None
        assert r4.launch_speed is not None

    def test_natural_key_y_season(self):
        parser = StatcastCSVParser()
        records = parser.parse((FIXTURES / "statcast_small.csv").read_text())
        assert records[0].natural_key == (716180, 1, 1)
        assert records[0].season == 2026


class TestHeaderValidation:
    def test_falta_columna_requerida_falla(self):
        headers = ["game_pk", "game_date"]
        with pytest.raises(ValueError):
            validate_headers(headers)

    def test_columna_nueva_se_ignora(self):
        headers = list(REQUIRED_COLUMNS) + ["columna_rara_2026"]
        result = validate_headers(headers)
        assert "columna_rara_2026" in result


class TestStatcastAdapter:
    def _adapter(self, csv_text: str, *, extra_params_check=None):
        def handler(request):
            if extra_params_check:
                extra_params_check(dict(request.url.params))
            return httpx.Response(200, text=csv_text, request=request)

        http = ExternalHttpClient(transport=httpx.MockTransport(handler))
        return StatcastSourceAdapter(http=http, base_url="https://savant.test")

    def test_fetch_date_range_y_usa_query_builder(self):
        captured = {}

        def check(params):
            captured.update(params)

        adapter = self._adapter((FIXTURES / "statcast_small.csv").read_text(), extra_params_check=check)
        records = adapter.fetch_date_range(dt.date(2026, 4, 1), dt.date(2026, 4, 5))
        assert len(records) == 7
        assert captured["game_date_gt"] == "2026-04-01"
        assert captured["player_type"] == "pitcher"

    def test_fetch_batter(self):
        captured = {}

        def check(params):
            captured.update(params)

        adapter = self._adapter((FIXTURES / "statcast_small.csv").read_text(), extra_params_check=check)
        adapter.fetch_batter(660271, dt.date(2026, 4, 1), dt.date(2026, 4, 5))
        assert captured["batters_lookup[]"] == "660271"

    def test_error_en_http_se_propaga(self):
        def handler(request):
            return httpx.Response(404, request=request)

        adapter = StatcastSourceAdapter(
            http=ExternalHttpClient(transport=httpx.MockTransport(handler)),
            base_url="https://savant.test",
        )
        with pytest.raises(httpx.HTTPStatusError):
            adapter.fetch_date_range(dt.date(2026, 4, 1), dt.date(2026, 4, 5))