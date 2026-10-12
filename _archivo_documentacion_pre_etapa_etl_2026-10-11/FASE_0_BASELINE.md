# Fase 0 · Baseline reproducible

**Gate que cierra:** *"Un entorno donde una misma seed/fixture produzca el mismo
escenario base"* y *"no cambiar reglas durante la auditoría"* (plan maestro,
secciones 3-5 y §32 checklist).

**Estado del gate:** CERRADO

---

## Baseline congelado (13/sept/2026)

| Concepto | Valor |
|---|---|
| Commit de referencia | `4ee14a8` (`feat(cards): permitir reapertura explícita de catálogos retirados`, rama `main`) |
| Alembic head | `0041` (aplicado en BD: `alembic_version = 0041`) |
| Catálogo ACTIVE | `b2f36619` — 2026 BASE, `edition-2.0`, `ratings-2.0`, **806 cartas** (806 activas + pack-eligible) |
| Catálogo RETIRED | `6fb611a6` — v1 `ratings-1.0`, 829 cartas (off), cadena `supersedes` reversible |
| Engine build | `engine-20260913-4ee14a8` (`backend/app/engine/build.py`) |
| Reglas de juego | `rules-1.0-lab` (provisional/LAB, sin valores de balance) |
| BD | PostgreSQL 15 (`docker-compose`), tests: SQLite in-memory |
| Suite | **807 passed** en ~46s (contenedor `deck-at-the-plate-backend`, Python 3.11) |

## Dataset de prueba congelado

- **`backend/tests/fixtures.py`** — módulo canónico sin dependencia de pytest:
  - Escenarios F01–F08 del plan §15 (smoke at-bat, bases llenas 3-2, fatiga+
    bullpen lleno/vacío, steal 1B/2B, tácticas duales, bottom 9 walk-off,
    extra innings con ghost runner). Cada uno es un par `(game, state)`
    reproducible e idéntico entre builds.
  - Builders puros de estado, lineups y cartas (pitcher/batter) para la suite
    de invariantes (Fase 4) y el runner headless (Fase 11).
  - Infra BD canónica `new_db()` (SQLite + FKs + metadata completo) y seed de
    catálogo publicable `seed_catalog()` (1 jugador por rareza, eligibility
    PROVISIONAL) usado por las Fases 2-3.
- **`backend/tests/test_baseline.py`** — fija el entorno:
  - head de alembic == `0041` (derivado del grafo, sin ejecutar migraciones);
  - engine build/rules version congelados;
  - reproducibilidad y validez estructural de F01–F08;
  - seed de catálogo reproducible entre dos sesiones BD independientes.

## Archivos tocados

| Archivo | Cambio |
|---|---|
| `backend/app/engine/build.py` | **Nuevo** — marcadores `ENGINE_BUILD` y `GAMEPLAY_RULES_VERSION` |
| `backend/tests/fixtures.py` | **Nuevo** — dataset canónico congelado (F01–F08 + BD/catálogo) |
| `backend/tests/conftest.py` | Expone fixture compartida `db` (SQLite) |
| `backend/tests/test_baseline.py` | **Nuevo** — verificación del freeze |
| `backend/tests/etl/test_player_card_editions.py` | Repara fixture desactualizado (ver desviación) |

## Comandos de ejecución (resultados)

```bash
docker run --rm -v "$PWD/backend:/app" -w /app deck-at-the-plate-backend \
  sh -c "pip install -q pytest; python -m pytest"
# => 807 passed, 3 warnings in 45.73s
```

## Desviaciones y decisiones

1. **Test rojo pre-existente en `main`:** `test_rerun_del_publicador_no_duplica_carta`
   fallaba por el contrato de eligibility agregado en `8d08d5d` (una CardEdition
   BASE declara `base-eligibility-1.1`; publicar sin `CardRatingProfile` con
   eligibility es fail-closed → FAILED). Se reparó el **fixture** (no las reglas):
   ahora crea `PlayerRatings` + `CardRatingProfile` con eligibility PROVISIONAL,
   alineado con el fixture vigente de `test_card_catalog_lifecycle.py`.
2. **Working tree pre-existente:** hay ediciones sin commitear en las
   migraciones `0001_base.py` y `0010_public_identity.py` (DDL-only/idempotentes,
   ajenas a esta fase). **No se incluyen en este commit**; quedan fuera del
   gate de gameplay.
3. **`GAMEPLAY_RULES_VERSION = "rules-1.0-lab"`** se marca LAB: el plan pide no
   fijar balance definitivo sin simulador. El freeze real de esta fase es el
   comportamiento del engine y del catálogo, no ajuste de números.
4. Sin cambios de reglas de gameplay: esta fase solo congela infraestructura de
   prueba y datos. El `db` fixture del conftest es sobreescribible por cada test
   (resolución pytest por cercanía), por lo que no altera la suite existente.