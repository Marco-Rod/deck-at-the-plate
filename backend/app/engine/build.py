"""Marcadores de versión del motor (baseline congelado).

El plan maestro (secciones 8 y 39 del documento de validación) exige que toda
partida quede ligada a la versión de reglas y del engine utilizadas. Este
módulo es la fuente autoritativa de esos marcadores; no depende de la BD.

Baseline congelado en la Fase 0:
    - commit: 4ee14a8 (13/sept/2026, rama main)
    - migración: alembic head 0041
    - catálogo ACTIVE: b2f36619 (2026 BASE, edition-2.0, ratings-2.0, 806 cartas)

``GAMEPLAY_RULES_VERSION`` es el rótulo de las reglas del motor en esta etapa
(valor provisional/LAB; el plan pide no fijar balance hasta tener simulador).
"""

ENGINE_BUILD = "engine-20260913-4ee14a8"

GAMEPLAY_RULES_VERSION = "rules-1.0-lab"