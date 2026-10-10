"""Fase 0 — Baseline reproducible: el entorno congelado no cambia.

Gate de cierre: "un entorno donde una misma seed/fixture produzca el mismo
escenario base" y "no cambiar reglas durante la auditoría". Este módulo
verifica que:

    1. El esquema sigue siendo alembic head (``0043``).
    2. El ancla histórica de CALIBRATED-BASELINE-v1 sigue congelada, y el
       build/rules del runtime se gestionan por separado.
    3. Cada escenario canónico F01..F08 es reproducible (dos builds idénticos).
    4. Cada escenario canónico es estructuralmente válido para el engine.
    5. El seed del catálogo publicable es reproducible entre sesiones BD.

Qué se movió en 003B-6A y por qué
---------------------------------
``SCHEMA_HEAD`` pasó de ``0041`` a ``0042`` porque 003B-6A instala la columna
``player_cards.stuff``. Eso es un cambio de ESQUEMA, y el esquema es el
contenedor: no altera ningún mecanismo del motor, y por eso se mueve.

``ENGINE_BUILD``, ``GAMEPLAY_RULES_VERSION`` y ``BASELINE_COMMIT`` NO se mueven.
Siguen siendo el ancla de auditoría de CALIBRATED-BASELINE-v1 (003A), que es
contra lo que el bloque C de 003B-6C compara para demostrar que los mecanismos
que Stuff no debía alterar siguen byte a byte idénticos. Es además la convención
que el propio repo aplicó en la promoción de Fatigue v2 (d8c8804) y a lo largo
de 003B-1..5C: el rótulo de reglas se deja quieto y el cambio de gameplay se
registra en el commit y en el ADR, no reetiquetando el baseline.

Bump de esquema (0041 → 0042) y bump de reglas son cosas distintas, y confundir
las dos es exactamente el error que haría que " Stuff no cambió nada" quedara
sin poder verificarse.

Qué movió GAMEPLAY-PROVENANCE-001
---------------------------------
Este módulo separó las tres cosas que antes estaban accidentalmente unidas en
un solo rótulo:

*   ``CALIBRATED_BASELINE_V1_ENGINE_BUILD`` = ``4ee14a8``. No se mueve. Es la
    revisión histórica contra la que 003A compara, y no pretende describir el
    runtime.
*   ``ENGINE_BUILD`` pasa a ``engine-20261001-datap4``. El fix de
    ``Position.PITCHER`` (DATA-AUDIT-001) cambió el comportamiento observable
    de 403 cartas del catálogo activo sin tocar ``calculator.py``. Mantener el
    rótulo viejo para que este test siguiera apuntando al mismo valor habría
    hecho que la provenance afirmara un runtime que ya no existe.
*   ``GAMEPLAY_RULES_VERSION`` pasa de ``rules-1.0-lab`` a ``rules-1.0``, una
    promoción explícita: Fatigue v2, Plate Discipline y Stuff ya pasaron
    acceptance productivo. No es un efecto colateral del fix, que fue
    corrección de clasificación de dominio y por eso NO bumpea reglas.
*   ``ENGINE_VERSION`` nace como ``engine-1.0``.
"""

import re
from pathlib import Path

from app.engine.build import (
    CALIBRATED_BASELINE_V1_ENGINE_BUILD,
    ENGINE_BUILD,
    ENGINE_VERSION,
    GAMEPLAY_RULES_VERSION,
)
from app.models import PlayerCardModel
from tests import fixtures

_SCENARIO_CODES = ("F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08")

_REVISION_RE = re.compile(r"^revision\b.*?['\"]([^'\"]+)['\"]", re.MULTILINE)
_DOWN_REVISION_RE = re.compile(
    r"^down_revision\b.*?['\"]([^'\",\)]+)['\"]", re.MULTILINE
)


def _alembic_heads(versions_dir: Path) -> set[str]:
    """Heads del grafo de migraciones, derivadas sin ejecutar alembic.

    En el grafo ``down_revision``, la head es la revisión que nadie referencia
    como padre (no es el *down* de ninguna otra); es la última aplicada.
    """
    revisions: dict[str, set[str]] = {}
    parents: set[str] = set()
    for path in versions_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        match = _REVISION_RE.search(text)
        if not match:
            continue
        rev = match.group(1)
        revisions.setdefault(rev, set())
        down = _DOWN_REVISION_RE.search(text)
        parent = down.group(1) if down else None
        if parent and parent != rev:
            revisions[parent].add(rev)
            parents.add(parent)
    return {rev for rev in revisions if rev not in parents}


def test_schema_head_congelado_es_0044():
    # 0044 = 0044_game_event_sequence (RUNTIME TELEMETRY P5-A, sequence_no en
    # game_event_logs). Único head: la cadena de down_revision sigue lineal.
    versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    heads = _alembic_heads(versions_dir)
    assert heads == {"0044"}, f"heads inesperados: {heads}"


def test_ancla_historica_de_calibrated_baseline_v1_no_se_mueve():
    # El build de CALIBRATED-BASELINE-v1 es una referencia histórica congelada
    # (003A), NO el runtime actual. GAMEPLAY-PROVENANCE-001 separó ambas cosas:
    # el fix de Position.PITCHER bumpeó ENGINE_BUILD, y mantener el rótulo viejo
    # "para que este test siguiera apuntando al mismo valor" habría convertido la
    # provenance en una mentira.
    assert CALIBRATED_BASELINE_V1_ENGINE_BUILD == "4ee14a8"
    assert fixtures.BASELINE_COMMIT == "4ee14a8"


def test_engine_build_refleja_el_runtime_productivo_actual():
    # Bump por DATA-AUDIT-001: el fix de Position.PITCHER cambió el
    # comportamiento observable de 403 cartas aunque no tocara calculator.py.
    assert ENGINE_BUILD == "engine-20261001-datap4"
    # El ancla congelada y el runtime son valores distintos por construcción.
    assert ENGINE_BUILD != CALIBRATED_BASELINE_V1_ENGINE_BUILD


def test_rules_version_no_cambio_por_un_fix_de_implementacion():
    # El fix de Position.PITCHER fue corrección de clasificación de dominio,
    # no una regla semántica nueva. Sólo bumpea el build.
    assert GAMEPLAY_RULES_VERSION == "rules-1.0"
    # rules-1.0-lab → rules-1.0 es una promoción explícita, hecha en P4 y no
    # un efecto colateral del fix.
    assert GAMEPLAY_RULES_VERSION != "rules-1.0-lab"
    assert ENGINE_VERSION == "engine-1.0"


def test_escenarios_canonicos_reproducibles():
    for code in _SCENARIO_CODES:
        game_a, state_a = fixtures.scenario(code)
        game_b, state_b = fixtures.scenario(code)
        assert vars(game_a) == vars(game_b), f"{code}: game no determinista"
        assert state_a == state_b, f"{code}: state no determinista"


def test_escenarios_canonicos_validos():
    for code in _SCENARIO_CODES:
        game, state = fixtures.scenario(code)
        assert len(state["home_lineup"]) == 9, f"{code}: lineup home != 9"
        assert len(state["away_lineup"]) == 9, f"{code}: lineup away != 9"
        assert set(state["runners"]) == {"1b", "2b", "3b"}, f"{code}: runners"
        assert 0 <= game.outs <= 2, f"{code}: outs fuera de rango"
        assert 0 <= game.balls <= 3, f"{code}: balls fuera de rango"
        assert 0 <= game.strikes <= 2, f"{code}: strikes fuera de rango"
        assert 1 <= game.current_inning <= 20, f"{code}: inning fuera de rango"
        assert state["active_pitcher"]
        assert state["active_batter"]


def test_seed_catalogo_reproducible_entre_sesiones():
    def _seed_once():
        engine, db = fixtures.new_db()
        catalog, edition, players = fixtures.seed_catalog(db)
        rows = sorted(
            (c.rarity.name, c.team_id, c.position)
            for c in db.query(PlayerCardModel).all()
        )
        db.close()
        engine.dispose()
        return catalog.status, len(rows), rows, len(players)

    assert _seed_once() == _seed_once()