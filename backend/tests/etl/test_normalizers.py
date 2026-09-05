"""Pruebas de normalizadores (spec secciones 14-19): familias, zonas, resultado, hash, mapper."""

import datetime as dt
import pathlib

from app.core.enums import Handedness, PitchFamily, ThrowHand
from etl.dto import PitchSourceRecord
from etl.normalizers.hash import canonical_hash, record_to_hash_payload
from etl.normalizers.pitch_families import map_pitch_family
from etl.normalizers.pitch_result import PitchResult, is_swing, is_whiff, normalize_pitch_result
from etl.normalizers.raw_mapper import normalize_row
from etl.normalizers.values import normalize_inning_topbot
from etl.normalizers.zones import game_zone_from_statcast

FIXTURES = pathlib.Path(__file__).parent / "fixtures"


class TestPitchFamily:
    def test_fastball(self):
        assert map_pitch_family("FF") == PitchFamily.FASTBALL
        assert map_pitch_family("SI") == PitchFamily.FASTBALL
        assert map_pitch_family("FC") == PitchFamily.FASTBALL

    def test_breaking(self):
        assert map_pitch_family("SL") == PitchFamily.BREAKING
        assert map_pitch_family("CU") == PitchFamily.BREAKING

    def test_offspeed(self):
        assert map_pitch_family("CH") == PitchFamily.OFFSPEED
        assert map_pitch_family("FS") == PitchFamily.OFFSPEED

    def test_otras_politica_explicita_other(self):
        assert map_pitch_family("KN") == PitchFamily.OTHER
        assert map_pitch_family("EP") == PitchFamily.OTHER
        assert map_pitch_family("IN") == PitchFamily.OTHER
        assert map_pitch_family("PO") == PitchFamily.OTHER

    def test_desconocido_devuelve_none(self):
        assert map_pitch_family("XYZ") is None
        assert map_pitch_family(None) is None
        assert map_pitch_family("") is None

    def test_case_insensitive(self):
        assert map_pitch_family("ff") == PitchFamily.FASTBALL


class TestGameZone:
    def test_en_reticula_1_9(self):
        assert game_zone_from_statcast(1) == 1
        assert game_zone_from_statcast(9) == 9

    def test_fuera_de_reticula_none(self):
        assert game_zone_from_statcast(13) is None
        assert game_zone_from_statcast(0) is None
        assert game_zone_from_statcast(None) is None


class TestPitchResult:
    def test_normalize(self):
        assert normalize_pitch_result("ball") == PitchResult.BALL
        assert normalize_pitch_result("called_strike") == PitchResult.CALLED_STRIKE
        assert normalize_pitch_result("swinging_strike_blocked") == PitchResult.SWINGING_STRIKE
        assert normalize_pitch_result("foul_tip") == PitchResult.FOUL
        assert normalize_pitch_result("hit_into_play_no_out") == PitchResult.IN_PLAY
        assert normalize_pitch_result("hit_by_pitch") == PitchResult.HBP
        assert normalize_pitch_result("cosa_rara") == PitchResult.OTHER

    def test_is_swing_conciencia_de_called_strike(self):
        assert is_swing("swinging_strike") is True
        assert is_swing("called_strike") is False
        assert is_swing("hit_into_play") is True
        assert is_swing("ball") is False

    def test_is_whiff(self):
        assert is_whiff("swinging_strike") is True
        assert is_whiff("swinging_strike_blocked") is True
        assert is_whiff("foul") is False
        assert is_whiff("called_strike") is False


class TestInningTopBot:
    def test_normalize(self):
        assert normalize_inning_topbot("Top") == "Top"
        assert normalize_inning_topbot("bottom") == "Bottom"
        assert normalize_inning_topbot(None) is None


class TestHash:
    def test_canonical_stable(self):
        payload = {"b": 2, "a": 1, "c": None}
        assert canonical_hash(payload) == canonical_hash({"a": 1, "c": None, "b": 2})

    def test_cambio_de_valor_cambia_hash(self):
        assert canonical_hash({"a": 1}) != canonical_hash({"a": 2})

    def test_record_to_hash_payload_primitivas(self):
        from etl.dto import PitchSourceRecord

        record = PitchSourceRecord(
            game_pk=716180, game_date=dt.date(2026, 4, 1), at_bat_number=1, pitch_number=1,
            batter_mlb_id=660271, pitcher_mlb_id=669373,
        )
        payload = record_to_hash_payload(record)
        assert payload["game_date"] == "2026-04-01"


class TestRawMapper:
    def _record(self):
        return PitchSourceRecord(
            game_pk=716180,
            game_date=dt.date(2026, 4, 1),
            at_bat_number=1,
            pitch_number=1,
            batter_mlb_id=660271,
            pitcher_mlb_id=669373,
            balls=0,
            strikes=0,
            outs_when_up=0,
            inning=1,
            inning_topbot="Top",
            stand="L",
            p_throws="L",
            pitch_type="FF",
            release_speed=98.2,
            zone=4,
            description="swinging_strike",
            events=None,
            home_team="LAD",
            away_team="PHI",
        )

    def test_derivados(self):
        row = normalize_row(self._record())
        assert row["season"] == 2026
        assert row["pitch_family"] == PitchFamily.FASTBALL
        assert row["game_zone"] == 4
        assert row["statcast_zone"] == 4
        assert row["stand"] == Handedness.LEFT
        assert row["p_throws"] == ThrowHand.LEFT
        assert row["inning_topbot"] == "Top"
        assert row["event"] is None
        assert len(row["raw_payload_hash"]) == 64

    def test_descripcion_y_evento_originales(self):
        record = self._record()
        row = normalize_row(record)
        assert row["description"] == "swinging_strike"

    def test_pitch_type_limpiado(self):
        record = self._record()
        import dataclasses

        record = dataclasses.replace(record, pitch_type="ff")
        row = normalize_row(record)
        assert row["pitch_type"] == "FF"

    def test_familia_desconocida_none_y_zona_fuera(self):
        import dataclasses

        record = dataclasses.replace(self._record(), pitch_type="XYZ", zone=13)
        row = normalize_row(record)
        assert row["pitch_family"] is None
        assert row["game_zone"] is None
        assert row["statcast_zone"] == 13

    def test_hash_desde_fixture_es_reproducible(self):
        from etl.sources.statcast import StatcastCSVParser

        records = StatcastCSVParser().parse((FIXTURES / "statcast_small.csv").read_text())
        h1 = normalize_row(records[0])["raw_payload_hash"]
        h2 = normalize_row(records[0])["raw_payload_hash"]
        assert h1 == h2
        assert len(h1) == 64