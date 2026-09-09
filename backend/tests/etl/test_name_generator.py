"""Tests del generador determinista + validador (plan V2.1 §70-§75, §84)."""

import pytest

from etl.services.names import (
    DEFAULT_POOLS,
    CollisionValidator,
    FictionalNameGenerator,
    contains_blocked,
)
from etl.services.names.generator import seed_for


@pytest.fixture
def generated() -> FictionalNameGenerator:
    return FictionalNameGenerator(DEFAULT_POOLS)


def test_misma_entrada_mismo_resultado(generated):
    kwargs = dict(
        player_id="p1",
        generator_version="names-1.0",
        first="Jose",
        last="Ramirez",
        profile="SPANISH",
        used=set(),
        source_names=set(),
    )
    first = generated.generate(**kwargs)
    second = generated.generate(**kwargs)
    assert first.display == second.display
    assert first.first == second.first
    assert first.last == second.last


def test_seed_estable_por_identificador():
    assert seed_for("p1", "names-1.0", 1) == seed_for("p1", "names-1.0", 1)
    assert seed_for("p1", "names-1.0", 2) != seed_for("p1", "names-1.0", 1)
    assert seed_for("p1", "names-2.0", 1) != seed_for("p1", "names-1.0", 1)
    assert seed_for("p2", "names-1.0", 1) != seed_for("p1", "names-1.0", 1)


def test_candidato_pertenece_a_pool_korean(generated):
    name = generated.generate(
        player_id="pk",
        generator_version="names-1.0",
        first="Minjae",
        last="Kim",
        profile="KOREAN",
        used=set(),
        source_names=set(),
    )
    given_pool = set(DEFAULT_POOLS.given_for("KOREAN"))
    family_pool = set(DEFAULT_POOLS.family_for("KOREAN"))
    assert name.first.lower() in given_pool
    assert name.last.lower() in family_pool


def test_retry_determinista_ante_colision(generated):
    kwargs = dict(
        player_id="p2",
        generator_version="names-1.0",
        first="John",
        last="Smith",
        profile="ENGLISH",
        source_names=set(),
    )
    first = generated.generate(**kwargs, used=set())
    second = generated.generate(**kwargs, used={first.display})
    third = generated.generate(**kwargs, used={first.display})
    assert second.display != first.display
    assert third.display == second.display  # el retry es determinista


def test_colision_usa_la_misma_normalizacion_que_el_gate():
    validator = CollisionValidator()
    assert not validator.is_acceptable(
        "Jose Foo", used={"José Foo"}, source_names=set()
    )


def test_busqueda_exhaustiva_evade_colisiones_tras_retries_rapidos():
    generator = FictionalNameGenerator(DEFAULT_POOLS, max_attempts=0)
    name = generator.generate(
        player_id="exhaustive-player",
        generator_version="names-1.0",
        first="Jose",
        last="Example",
        profile="UNKNOWN",
        used=set(),
        source_names=set(),
    )

    assert not name.display.startswith("Player ")
    assert name.first.lower() in DEFAULT_POOLS.given_for("UNKNOWN")
    assert name.last.lower() in DEFAULT_POOLS.family_for("UNKNOWN")


def test_evita_repeticion_de_nombres_fuente(generated):
    source = {"Jose Ramirez"}
    name = generated.generate(
        player_id="ps",
        generator_version="names-1.0",
        first="Jose",
        last="Ramirez",
        profile="SPANISH",
        used=set(),
        source_names=source,
    )
    assert name.display != "Jose Ramirez"


def test_blocklist_rechaza_candidato():
    validator = CollisionValidator(blocked={"slut"})
    assert not validator.is_acceptable("Slut Rocker", used=set(), source_names=set())
    assert validator.is_acceptable("Jose Rubio", used=set(), source_names=set())


def test_contains_blocked_sin_importar_caso_acentos():
    assert contains_blocked("Jose Culo Miguel", DEFAULT_POOLS.blocked)
    assert contains_blocked("Jose-Culo", DEFAULT_POOLS.blocked)
    assert not contains_blocked("Jose Rubio", DEFAULT_POOLS.blocked)


def test_fallback_tras_max_attempts():
    blocked = set()
    for pool in DEFAULT_POOLS.pools.values():
        blocked.update(pool.given)
        blocked.update(pool.family)
    forgiving_generator = FictionalNameGenerator(
        DEFAULT_POOLS,
        validator=CollisionValidator(blocked=blocked),
        max_attempts=3,
    )
    name = forgiving_generator.generate(
        player_id="pf",
        generator_version="names-1.0",
        first="Jose",
        last="Ramirez",
        profile="SPANISH",
        used=set(),
        source_names=set(),
    )
    assert name.display.startswith("Player")


def test_preservacion_inicial_opcional(generated):
    # Con prob. alta de preservar, la inicial del primer nombre se mantiene.
    strict = FictionalNameGenerator(DEFAULT_POOLS, preserve_initials=1.0)
    name = strict.generate(
        player_id="pv",
        generator_version="names-1.0",
        first="Jonas",
        last="Schmidt",
        profile="GERMANIC",
        used=set(),
        source_names=set(),
    )
    assert name.first.startswith("J")
