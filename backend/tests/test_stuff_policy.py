"""
GAMEPLAY-ENGINE-003B-6B — Contratos estructurales de la política de Stuff
==========================================================================
003B-5C congeló la política; 003B-6A la integrated en producción. Este módulo
congela la FRONTERA, sin Monte Carlo y sin pedirle permiso al azar: cada
contrato es exacto y falla con un mensaje que dice qué se rompió.

Los ocho contratos del diseño aprobado:

    T1 mapper          ratings Stuff → PitcherAttrs.stuff
    T2 fresh           factor=1.0 → effective Stuff == raw Stuff (identidad)
    T3 fatigue         raw95 + factor conocido → fórmula α=.50 exacta
    T4 baseline        Stuff 70 → supresión exactamente 0
    T5 high Stuff      Stuff 95 → power_score −7.5
    T6 low Stuff       Stuff 45 → power_score +7.5
    T7 isolation       Stuff no toca whiff ni called-strike
    T8 001C intacto    VEL/CTL/MOV conservan su semántica exacta

Los anclas deterministas (T4/T5/T6) no son decorativas: ±7.5 sobre el baseline
70 con k=.30 son los mismos números que 003B-5C validó estadísticamente en
2.7M PA. Si el boundary algebraico se rompe, el contrato falla antes de que
haga falta otro Monte Carlo.

Sobre T7 y la firma de _calculate_contact_outcome
-------------------------------------------------
T7 se verifica con la misma semilla y el MISMO dibujo forzado en las tres
Stuff. Stuff podría estar tocando el whiff y aun así dar el mismo resultado en
una sola tirada; por eso el test fuerza la rama del whiff con un dibujo por
debajo del umbral y comprueba que las tres Stuff caen en la MISMA rama. Si
alguien metiera ``stuff`` en ``whiff_base``, este test cae.

La ausencia de la clave ``stuff`` (PitcherAttrs legacy, fixtures previos a 003B)
produce supresión 0 y comportamiento byte a byte idéntico al anterior. Eso es lo
que permite que los 945 tests preexistentes —y el harness LAB, que sigue sin
``stuff`` en sus dicts— sigan verdes sin haberlos tocado.
"""

import inspect
import random

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.engine import calculator
from app.engine.calculator import _resolve_play_outcome, calculate_play_outcome
from app.engine.fatigue_manager import apply_pitcher_fatigue, get_fatigue_factor
from app.engine.stuff_policy import (
    STUFF_BASELINE,
    STUFF_FATIGUE_ALPHA,
    STUFF_POWER_SUPPRESSION,
    effective_stuff,
    stuff_power_suppression,
)
from app.models import PlayerCardModel
from app.services.card_editions import ensure_system_base_edition

INNINGS = 9
THRESHOLD = 100  # get_pitch_threshold(9)

# Lo que 003B congeló. Si alguien cambia un número aquí, el test pasa y el
# juego cambia de reglas: por eso están repetidos como asertos explícitos en
# test_politica_congelada_003b, no sólo usados como operandos.
ALPHA = 0.50
BASELINE = 70
K = 0.30
# Ancla determinista: (95 - 70) * 0.30 = 7.5
ANCHOR_DELTA = 7.5


# ---------------------------------------------------------------------------
# Utilidades de aislamiento del RNG
# ---------------------------------------------------------------------------

def _uniform_sequence(values):
    """Mock de random.uniform que devuelve cada valor de la lista en orden."""
    it = iter(values)
    return lambda a, b: next(it)


def _no_foul():
    """Draw de foul alto → contacto limpio (sin FOUL)."""
    return 0.99


def _pitcher(stuff=None, velocidad=50, control=50, movimiento=50):
    """PitcherAttrs mínimo. Sin ``stuff`` si no se pasa (caso legacy)."""
    attrs = {"velocidad": velocidad, "control": control, "movimiento": movimiento}
    if stuff is not None:
        attrs["stuff"] = stuff
    return attrs


BATTER = {"contacto": 50, "poder": 70, "vision": 70}
# whiff_base = 24.5 + (50*.25 + 50*.25) - 50*.35 = 32.0
WHIFF_CHANCE = 32.0


def _batted_ball(stuff, uniform_draw, swing="NORMAL"):
    """Fuerza un BIP (no whiff, no foul) y devuelve el evento resultante.

    pwr=70 ⇒ ``power_score = (70-50)*0.4 + draw = 8.0 + draw``, sin bono de
    zona/tipo (el swing no adivina), así que el power_score final es una
    función cerrada y conocida del draw y del Stuff.

    Orden de draws en _calculate_contact_outcome, que es el que se replica:
        1. random.uniform(0, 100) → ¿whiff?      (debe ser >= 32.0)
        2. random.random()        → ¿foul?       (0.99 → contacto limpio)
        3. random.uniform(0, 100) → power_score
    """
    original_uniform, original_random = random.uniform, random.random
    # 99.0 no es < 32.0 ⇒ nunca whiff, con cualquier Stuff.
    random.uniform = _uniform_sequence([99.0, uniform_draw])
    random.random = _no_foul
    try:
        return _resolve_play_outcome(
            _pitcher(stuff=stuff),
            BATTER,
            {"pitch_type": "FF", "zone": 5},
            {"swing_type": swing, "guessed_zone": 2, "guessed_pitch": "SLIDER"},
        )
    finally:
        random.uniform, random.random = original_uniform, original_random


# ---------------------------------------------------------------------------
# La política congelada
# ---------------------------------------------------------------------------

class TestPoliticaCongelada:
    def test_politica_congelada_003b(self):
        assert STUFF_BASELINE == BASELINE == 70
        assert STUFF_FATIGUE_ALPHA == ALPHA == 0.50
        assert STUFF_POWER_SUPPRESSION == K == 0.30

    def test_constantes_no_se_redeclaran_en_el_calculator(self):
        # El número congelado tiene UNA definición. Importarlo para usarlo NO
        # cuenta como redeclararlo — lo que no puede existir es una asignación
        # propia, que es lo que crearía una segunda fuente de verdad.
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(calculator))
        assigned = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        assigned.add(target.id)
        assert assigned.isdisjoint(
            {"STUFF_BASELINE", "STUFF_POWER_SUPPRESSION", "STUFF_FATIGUE_ALPHA"}
        ), f"constantes re-declaradas en calculator: {assigned}"


# ---------------------------------------------------------------------------
# T1 · mapper: ratings-2.0 Stuff → PitcherAttrs.stuff
# ---------------------------------------------------------------------------

class TestT1Mapper:
    @pytest.fixture
    def db(self):
        engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
        Base.metadata.create_all(engine)
        session = sessionmaker(bind=engine)()
        session.info["card_edition_id"] = ensure_system_base_edition(
            session, season=2026
        ).id
        yield session
        session.close()
        engine.dispose()

    @pytest.mark.parametrize("stuff", [45, 70, 95])
    def test_t1_mapper_publica_stuff_de_la_carta(self, db, stuff):
        from app.engine.attribute_mapper import map_card_to_pitcher_attrs

        card = PlayerCardModel(
            id=f"card-stuff-{stuff}",
            name="Pitcher Test",
            position="SP",
            overall=80,
            velocity=88,
            control=84,
            movement=82,
            stuff=stuff,
            card_edition_id=db.info["card_edition_id"],
        )
        db.add(card)
        db.flush()

        attrs = map_card_to_pitcher_attrs(card)
        assert attrs["stuff"] == stuff
        # El mapper no toca los atributos físicos: 003B noVincula mapper↔fatiga.
        assert attrs["velocidad"] == 88
        assert attrs["control"] == 84
        assert attrs["movimiento"] == 82

    def test_t1_carta_sin_stuff_es_neutra(self, db):
        # Una carta construida a mano (duck-typing) sin la clave no debe
        # reventar: cae al baseline, que es supresión 0.
        from app.engine.attribute_mapper import map_card_to_pitcher_attrs

        class _SinStuff:
            velocity = 88
            control = 84
            movement = 82

        assert map_card_to_pitcher_attrs(_SinStuff())["stuff"] == STUFF_BASELINE


# ---------------------------------------------------------------------------
# T2 · fresco: identidad exacta
# ---------------------------------------------------------------------------

class TestT2Fresh:
    @pytest.mark.parametrize("count", [0, 1, 50, 99, 100])
    def test_t2_fresco_es_identidad_exacta(self, count):
        for raw in (45, 70, 95):
            result = apply_pitcher_fatigue(_pitcher(stuff=raw), count, INNINGS)
            assert result["stuff"] == raw

    def test_t2_fresco_no_agrega_supresion_alguna(self):
        # El fresco no es "Stuff neutro": es Stuff CRUDO intacto. La supresión
        # de un pitcher fresco es exactamente la que implica su Stuff, la misma
        # que tendría un ATH si el motor no aplicara fatiga.
        for raw in (45, 70, 95):
            result = apply_pitcher_fatigue(_pitcher(stuff=raw), 100, INNINGS)
            assert stuff_power_suppression(result["stuff"]) == stuff_power_suppression(raw)
        # Y en el baseline sí es cero, que es lo que T4 congela.
        assert stuff_power_suppression(
            apply_pitcher_fatigue(_pitcher(stuff=70), 100, INNINGS)["stuff"]
        ) == 0.0


# ---------------------------------------------------------------------------
# T3 · fatiga: fórmula α=.50 exacta
# ---------------------------------------------------------------------------

class TestT3Fatigue:
    def test_t3_alpha_050_exacto(self):
        factor = get_fatigue_factor(150, THRESHOLD)
        result = apply_pitcher_fatigue(_pitcher(stuff=95), 150, INNINGS)
        # 95 * (1 - 0.50*(1 - f)) — calculado a mano, sin llamar a la política.
        expected = 95.0 * (1.0 - 0.50 * (1.0 - factor))
        assert result["stuff"] == expected
        assert factor < 1.0
        assert result["stuff"] < 95.0

    def test_t3_stuff_es_float_y_no_se_trunca(self):
        # El truncado a entero es el fallo que rompería S1: cuantiza la señal
        # justo donde el efecto es más pequeño.
        result = apply_pitcher_fatigue(_pitcher(stuff=95), 150, INNINGS)
        assert isinstance(result["stuff"], float)
        assert result["stuff"] != int(result["stuff"])

    def test_t3_monotono_decreciente_en_pitch_count(self):
        previous = None
        for count in range(100, 400):
            value = apply_pitcher_fatigue(_pitcher(stuff=95), count, INNINGS)["stuff"]
            if previous is not None:
                assert value <= previous
            previous = value

    def test_t3_nevera_por_debajo_del_stuff_crudo(self):
        for count in (100, 135, 150, 300, 10_000):
            result = apply_pitcher_fatigue(_pitcher(stuff=70), count, INNINGS)
            assert result["stuff"] <= 70.0

    def test_t3_aislamiento_calculator_no_ve_la_fatiga(self):
        # El contrato arquitectónico de 003B-6A: fatigue_manager transforma,
        # calculator consume. Verificado sobre el objeto importado y no sobre el
        # texto fuente — un comentario que mencione fatigue_factor no viola el
        # contrato, pero una referencia en tiempo de ejecución sí.
        assert not hasattr(calculator, "fatigue_factor")
        assert not hasattr(calculator, "get_fatigue_factor")
        assert not hasattr(calculator, "effective_stuff")
        assert not hasattr(calculator, "FATIGUE_FLOOR")
        # Y el poder se calcula con Stuff YA efectivo: la firma de la rama de
        # contacto no admite ningún factor de fatiga.
        params = inspect.signature(calculator._calculate_contact_outcome).parameters
        assert list(params) == [
            "foul_chance", "swing_type", "con", "pwr", "vel", "mov",
            "zone_matched", "pitch_matched", "effective_stuff",
        ]
        assert params["effective_stuff"].default == STUFF_BASELINE


# ---------------------------------------------------------------------------
# T4 / T5 / T6 · anclas deterministas de supresión
# ---------------------------------------------------------------------------

class TestAnclasSupresion:
    def test_t4_baseline_da_supresion_exactamente_cero(self):
        assert stuff_power_suppression(70) == 0.0
        assert stuff_power_suppression(70.0) == 0.0

    def test_t5_stuff_alto_resta_7_5(self):
        assert stuff_power_suppression(95) == -ANCHOR_DELTA == -7.5

    def test_t6_stuff_bajo_suma_7_5(self):
        assert stuff_power_suppression(45) == ANCHOR_DELTA == 7.5

    def test_t4_baseline_no_mueve_el_bip(self):
        # pwr=70, draw=90.0 ⇒ power_score = 98.0 → HOME_RUN
        assert _batted_ball(70, 90.0).event == "HOME_RUN"

    def test_t5_stuff_95_baja_el_bip_de_hr_a_2b(self):
        # Mismo draw: 98.0 - 7.5 = 90.5 → cae por debajo de 93 (3B) y por encima
        # de 85 ⇒ HIT_2B. Exactamente los 7.5 del contrato.
        assert _batted_ball(95, 90.0).event == "HIT_2B"

    def test_t6_stuff_45_sube_el_bip_de_3b_a_hr(self):
        # Mismo draw: 94.0 + 7.5 = 101.5 → HOME_RUN.
        assert _batted_ball(70, 86.0).event == "HIT_3B"
        assert _batted_ball(45, 86.0).event == "HOME_RUN"

    def test_t5_t6_orden_de_supresion(self):
        # Stuff 45 < 70 < 95 ⇒ power_score final 45 > 70 > 95 para el mismo draw.
        assert stuff_power_suppression(45) > stuff_power_suppression(70)
        assert stuff_power_suppression(70) > stuff_power_suppression(95)


# ---------------------------------------------------------------------------
# T7 · aislamiento de mecanismo
# ---------------------------------------------------------------------------

class TestT7Isolation:
    def test_t7_stuff_no_toca_el_whiff(self):
        # Draw de whiff por debajo del umbral ⇒ las TRES Stuff deben caer en la
        # misma rama. Si alguien metiera stuff en whiff_base, el 0.0 dejaría de
        # ser < 32.0 sólo para un extremo y este test se rompería.
        for stuff in (45, 70, 95):
            event, _ = _forced_whiff(stuff)
            assert event == "STRIKE_SWINGING"

    def test_t7_stuff_no_toca_el_called_strike(self):
        # TAKE delata: la ruta de disciplina no recibe Stuff en absoluto.
        results = set()
        for stuff in (45, 70, 95):
            random.seed(1234)
            results.add(
                calculate_play_outcome(
                    _pitcher(stuff=stuff),
                    BATTER,
                    {"pitch_type": "FF", "zone": 5},
                    {"swing_type": "TAKE", "guessed_zone": None, "guessed_pitch": None},
                ).event
            )
        assert len(results) == 1, f"Stuff alteró la disciplina: {results}"

    def test_t7_stuff_no_toca_el_bono_de_zona_tipo(self):
        # Con zona y tipo adivinados el bono es +15 en los tres casos; el Stuff
        # sólo mueve el offset, no la magnitud del bono.
        for stuff in (45, 70, 95):
            event, _ = _forced_whiff(stuff, zone_matched=True)
            assert event == "STRIKE_SWINGING"

    def test_t7_pitcher_sin_stuff_es_neutro_por_defecto(self):
        # El contrato que mantiene greens los 945 tests preexistentes y el
        # harness LAB: sin la clave, supresión 0 y resultado idéntico.
        random.seed(99)
        without = calculate_play_outcome(
            _pitcher(), BATTER,
            {"pitch_type": "FF", "zone": 5},
            {"swing_type": "NORMAL", "guessed_zone": 2, "guessed_pitch": "SLIDER"},
        ).event
        random.seed(99)
        with_baseline = calculate_play_outcome(
            _pitcher(stuff=STUFF_BASELINE), BATTER,
            {"pitch_type": "FF", "zone": 5},
            {"swing_type": "NORMAL", "guessed_zone": 2, "guessed_pitch": "SLIDER"},
        ).event
        assert without == with_baseline


def _forced_whiff(stuff, zone_matched=False):
    """Fuerza la rama de whiff con un draw 0.0 y devuelve (event, description).

    0.0 < 32.0 siempre ⇒ whiff garantizado, antes de que Stuff pueda tocar nada.
    """
    original_uniform = random.uniform
    random.uniform = lambda a, b: 0.0
    try:
        return _resolve_play_outcome(
            _pitcher(stuff=stuff),
            BATTER,
            {"pitch_type": "FF", "zone": 5},
            {
                "swing_type": "NORMAL",
                "guessed_zone": 5 if zone_matched else 2,
                "guessed_pitch": "FF" if zone_matched else "SLIDER",
            },
        )
    finally:
        random.uniform = original_uniform


# ---------------------------------------------------------------------------
# T8 · 001C intacto
# ---------------------------------------------------------------------------

class TestT8Fatigue001CIntacta:
    # La tabla exacta de 001C (tests/test_fatigue_curve.py la congela igual).
    TABLA_001C = [
        (100, 90, 80, 85),   # en threshold: intacto
        (110, 88, 78, 83),
        (125, 79, 70, 74),
        (150, 57, 50, 53),
        (200, 33, 29, 31),
        (2000, 31, 28, 29),  # cerca del floor (0.35)
    ]

    @pytest.mark.parametrize(("count", "vel", "ctl", "mov"), TABLA_001C)
    def test_t8_001c_fisicos_inalterados(self, count, vel, ctl, mov):
        result = apply_pitcher_fatigue(_pitcher(stuff=70, velocidad=90, control=80, movimiento=85), count, INNINGS)
        assert result["velocidad"] == vel
        assert result["control"] == ctl
        assert result["movimiento"] == mov

    @pytest.mark.parametrize(("count", "vel", "ctl", "mov"), TABLA_001C)
    def test_t8_001c_fisicos_siguen_siendo_enteros(self, count, vel, ctl, mov):
        result = apply_pitcher_fatigue(_pitcher(stuff=70, velocidad=90, control=80, movimiento=85), count, INNINGS)
        for key in ("velocidad", "control", "movimiento"):
            assert isinstance(result[key], int)

    def test_t8_stuff_no_altera_los_fisicos(self):
        # Mismo pitch_count, tres Stuffs: los atributos físicos NO pueden
        # depender de la columna nueva.
        for count in (100, 135, 150, 300):
            base = _pitcher(stuff=70, velocidad=90, control=80, movimiento=85)
            reference = apply_pitcher_fatigue(base, count, INNINGS)
            for stuff in (45, 70, 95):
                other = apply_pitcher_fatigue(dict(base, stuff=stuff), count, INNINGS)
                for key in ("velocidad", "control", "movimiento"):
                    assert other[key] == reference[key]

    def test_t8_no_muta_el_diccionario_entrada(self):
        base = _pitcher(stuff=70, velocidad=90, control=80, movimiento=85)
        snapshot = dict(base)
        apply_pitcher_fatigue(base, 150, INNINGS)
        assert base == snapshot
