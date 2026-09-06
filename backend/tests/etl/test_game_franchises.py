"""Tests del config de franquicias GAME e identidad pública (plan V2 §37).

Asegura que el universo GAME es 100% ficticio: 30 franquicias, abreviaturas
únicas y sin colisión con la liga real, slugs/nombres únicos, y paletas de
colores suficientemente diferenciadas (distancia mínima garantizada).
"""

import pytest

from etl.config.franchises import (
    EXPECTED_FRANCHISE_COUNT,
    MIN_PALETTE_DISTANCE,
    REAL_LEAGUE_ABBREVIATIONS,
    GameTeamConfig,
    _color_distance,
    _hex_rgb,
    franchise_config_issues,
    load_game_franchises,
    validate_game_franchises,
)


@pytest.fixture
def configs():
    return load_game_franchises()


def test_cantidad_y_ids_fuente_unicos(configs):
    assert len(configs) == EXPECTED_FRANCHISE_COUNT
    source_ids = [c.source_team_external_id for c in configs]
    assert len(source_ids) == len(set(source_ids))


def test_abreviaturas_unicas_y_sin_colision_con_liga_real(configs):
    abbrs = [c.public_abbreviation.upper() for c in configs]
    assert len(abbrs) == len(set(abbrs))
    for abbr in abbrs:
        assert abbr.isalnum()
        assert 2 <= len(abbr) <= 3
        assert abbr not in REAL_LEAGUE_ABBREVIATIONS


def test_slugs_y_nombres_unicos(configs):
    slugs = [c.slug.strip().lower() for c in configs]
    assert len(slugs) == len(set(slugs))
    for slug in slugs:
        assert slug and all(ch.isalnum() or ch == "-" for ch in slug)
    names = [c.name.strip().lower() for c in configs]
    assert len(names) == len(set(names))
    assert all(n for n in names)


def test_todas_cpu_y_colores_bien_formados(configs):
    for cfg in configs:
        assert cfg.is_cpu is True
        for color in (cfg.primary_color, cfg.secondary_color):
            assert len(color) == 7 and color[0] == "#"
            _hex_rgb(color)


def test_paleta_suficientemente_diferenciada(configs):
    palette = []
    for cfg in configs:
        palette.extend([_hex_rgb(cfg.primary_color), _hex_rgb(cfg.secondary_color)])
    assert len(palette) == len(set(palette))
    for i, first in enumerate(palette):
        for second in palette[i + 1 :]:
            assert _color_distance(first, second) >= MIN_PALETTE_DISTANCE


def test_validate_devuelve_configs_y_ojo_con_bugs(configs):
    returned = validate_game_franchises(configs)
    assert returned == configs

    broken = GameTeamConfig(
        source_team_external_id=configs[0].source_team_external_id,
        public_abbreviation="LAD",
        slug="cachorros",
        name="Cachorros de Chicago",
        city="Chicago",
        primary_color="C5A059",
        secondary_color="#C5A059",
        is_cpu=False,
    )
    issues = franchise_config_issues([broken, *configs[1:]] + [configs[0]])
    assert any("duplicado" in issue for issue in issues)
    assert any("liga real" in issue for issue in issues)
    assert any("is_cpu debe ser true" in issue for issue in issues)
    assert any("#RRGGBB" in issue for issue in issues)

    with pytest.raises(ValueError):
        validate_game_franchises([broken])