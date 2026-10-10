"""Marcadores de versión del motor (GAMEPLAY-PROVENANCE-001).

El plan maestro (secciones 8 y 39 del documento de validación) exige que toda
partida quede ligada a la versión de reglas y del engine utilizadas. Este
módulo es la fuente autoritativa de esos marcadores; no depende de la BD.

## Tres ejes, no uno

Antes estas cuatro preguntas tenían una sola respuesta ambigua. Ahora son
distintas y cada una tiene su constante:

| Eje | Constante | Responde a |
| --- | --- | --- |
| Reglas | ``GAMEPLAY_RULES_VERSION`` | ¿Qué reglas semánticas de juego aplican? |
| Motor | ``ENGINE_VERSION`` | ¿Qué versión semántica del motor? |
| Build | ``ENGINE_BUILD`` | ¿Qué código exacto estaba desplegado? |

La distinción importa: reetiquetar ``GAMEPLAY_RULES_VERSION`` para registrar
un bug fix mezclaría "cambió el comportamiento" con "cambió el diseño del
juego", y volvería imposible auditar si una diferencia observada viene de una
regla o de una corrección.

## Ancla histórica congelada

``CALIBRATED_BASELINE_V1_ENGINE_BUILD`` es la revisión contra la que
CALIBRATED-BASELINE-v1 (003A) demuestra que los mecanismos congelados siguen
idénticos. No se mueve nunca. ``ENGINE_BUILD`` sí se mueve, y por eso dejar
el rótulo viejo en pie "para que test_baseline siga apuntando al mismo valor"
convertiría la provenance en una mentira: el runtime ya no sería ese build.

## Bumps aplicados

- ``rules-1.0-lab`` → ``rules-1.0``: el sufijo ``lab`` tenía sentido mientras
  se calibraba. Fatigue v2, Plate Discipline y Stuff (k=.30 / α=.50) ya
  pasaron acceptance productivo, así que el primer provenance real de las
  partidas arranca con un rótulo limpio.
- ``ENGINE_BUILD`` → ``engine-20261001-datap4``: el fix de
  ``Position.PITCHER`` (DATA-AUDIT-001) cambió comportamiento observable
  para 403 cartas del catálogo activo, aunque no tocara
  ``calculator.py``. Se bumpea el build; las reglas NO cambian, porque fue
  una corrección de clasificación de dominio, no una regla nueva.
- ``ENGINE_VERSION`` nace como ``engine-1.0``: todavía no existe una versión
  semántica real del motor, pero reservarla ahora evita otra migración.
"""

ENGINE_BUILD = "engine-20261001-datap4"

ENGINE_VERSION = "engine-1.0"

GAMEPLAY_RULES_VERSION = "rules-1.0"

# Revisión congelada de CALIBRATED-BASELINE-v1 (003A). No representa el runtime
# actual; es la referencia histórica contra la que se compara.
CALIBRATED_BASELINE_V1_ENGINE_BUILD = "4ee14a8"
