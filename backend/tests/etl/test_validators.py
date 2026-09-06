"""Pruebas de validators de raw y analytics (spec secciones 6 y 48)."""

import datetime as dt

from etl.dto import PitchSourceRecord
from etl.validators.analytics import validate_profile
from etl.validators.raw import validate_raw_row


def _record(**overrides):
    base = dict(
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
        stand="L",
        p_throws="L",
        zone=4,
    )
    base.update(overrides)
    return PitchSourceRecord(**base)


class TestRawValidator:
    def test_fila_valida(self):
        assert validate_raw_row(_record()) == []

    def test_falta_clave_natural(self):
        errors = validate_raw_row(_record(at_bat_number=None, pitch_number=0))
        assert any("at_bat_number" in e for e in errors)
        assert any("pitch_number" in e for e in errors)

    def test_counts_fuera_de_rango(self):
        errors = validate_raw_row(_record(balls=5, strikes=-1, outs_when_up=3))
        assert any("balls" in e for e in errors)
        assert any("strikes" in e for e in errors)
        assert any("outs_when_up" in e for e in errors)

    def test_inning_cero(self):
        errors = validate_raw_row(_record(inning=0))
        assert any("inning" in e for e in errors)

    def test_stands_invalidos(self):
        errors = validate_raw_row(_record(stand="U", p_throws="Z"))
        assert any("stand" in e for e in errors)
        assert any("p_throws" in e for e in errors)

    def test_stand_switch_valido(self):
        assert validate_raw_row(_record(stand="S")) == []

    def test_zonas_statcast_exteriores_son_validas(self):
        for zone in range(11, 15):
            assert validate_raw_row(_record(zone=zone)) == []

    def test_zone_desconocida_rechaza(self):
        errors = validate_raw_row(_record(zone=42))
        assert any("zone" in e for e in errors)

    def test_estrella_de_pitches_sin_zona_es_valida(self):
        assert validate_raw_row(_record(zone=None, balls=None, strikes=None)) == []


class TestAnalyticsValidator:
    def test_perfil_valido(self):
        errors = validate_profile(
            {
                "sample_size": 30,
                "pitches_seen": 30,
                "swings": 15,
                "whiff_rate": 0.5,
                "hard_hit_rate": 0.1,
            },
            rate_fields=("whiff_rate", "hard_hit_rate"),
            non_negative_fields=("swings", "pitches_seen", "sample_size"),
            sample_field="sample_size",
            denominator_field="pitches_seen",
        )
        assert errors == []

    def test_rate_fuera_de_rango(self):
        errors = validate_profile(
            {"whiff_rate": 1.5},
            rate_fields=("whiff_rate",),
            non_negative_fields=(),
        )
        assert any("whiff_rate" in e and "0..1" in e for e in errors)

    def test_rate_none_permitido(self):
        errors = validate_profile(
            {"whiff_rate": None},
            rate_fields=("whiff_rate",),
            non_negative_fields=(),
        )
        assert errors == []

    def test_conteo_negativo(self):
        errors = validate_profile(
            {"swings": -1},
            rate_fields=(),
            non_negative_fields=("swings",),
        )
        assert any("swings" in e and "negativo" in e for e in errors)

    def test_sample_size_no_coincide_con_denominador(self):
        errors = validate_profile(
            {"sample_size": 10, "pitches_seen": 12},
            rate_fields=(),
            non_negative_fields=(),
            sample_field="sample_size",
            denominator_field="pitches_seen",
        )
        assert any("sample_size" in e for e in errors)
