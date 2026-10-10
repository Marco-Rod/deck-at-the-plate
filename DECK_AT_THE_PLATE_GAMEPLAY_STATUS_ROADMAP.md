# Deck at the Plate --- Gameplay: Estado, decisiones y roadmap

> **Documento vivo --- estado consolidado al 1 de octubre de 2026**
>
> Objetivo: conservar en un solo lugar lo ya validado del gameplay, las
> decisiones congeladas, los hallazgos abiertos y el orden recomendado
> para continuar.
>
> **Método:** caracterizar → simular → decidir → implementar → aceptar
> en producción.\
> Un bloque cerrado no se reabre salvo evidencia nueva de un defecto
> real.

------------------------------------------------------------------------

## 1. Objetivo de la etapa de Gameplay

La meta no es sólo que una partida "funcione", sino construir una ruta
reproducible, auditable y versionable:

``` text
Card / Ratings
      ↓
Attribute Mapper
      ↓
Game Session / Registered Roster
      ↓
Fatigue + Tactics + Matchup
      ↓
Gameplay Engine
      ↓
State Transition
      ↓
Persistence
      ↓
WebSocket
      ↓
Telemetry
      ↓
Analytics / Balance
```

Queremos consistencia entre ratings, decisiones del motor, estado
persistido, eventos enviados al cliente y futuras estadísticas.

------------------------------------------------------------------------

## 2. Estado general

### Cerrado / validado

-   Catálogo `ratings-2.0` activo.
-   Ownership y estructura del roster humano.
-   Snapshot inmutable del roster de cada partida.
-   Roster CPU ligado a un único catálogo activo.
-   Selección CPU inicial determinista.
-   Consistencia transaccional DB → WebSocket.
-   Propagación correcta de fatiga hacia atributos específicos del
    pitcheo.
-   Fatigue Policy v2.
-   Estrategia CPU basada en `workload`.
-   UI basada en `fatigue_factor` / `fatigue_band`.
-   Eliminación de modelos frontend paralelos de fatiga.
-   Plate Discipline / Counts.
-   Clamp Control × Vision.
-   `CALIBRATED-BASELINE-v1`.
-   Semántica, magnitud y robustez de `Stuff`.
-   Interacción Power × Stuff.
-   Interacción Stuff × Fatigue.
-   Integración productiva y acceptance de Stuff.
-   `GAMEPLAY-ENGINE-003B — CLOSED / PASS`.
-   `GAMEPLAY-RATING-001 — CLOSED / PASS`.
-   `DATA-STUFF-001A — CLOSED / PASS`.
-   `DATA-STUFF-001B — CLOSED / PASS`.
-   `GAMEPLAY-RATING-002 — DEFERRED` (decisión A: placeholder, sin efecto).
-   `DATA-AUDIT-001 — CLOSED / PASS` (fix `Position.PITCHER`).
-   `GAMEPLAY-PROVENANCE-001 — CLOSED / PASS` (P4).

### Próximo bloque

``` text
P5-RUNTIME-TELEMETRY --- game -> PA -> pitch -> decision -> probability -> RNG -> result
```

(P4-PROVENANCE cerrado: la partida versiona catalogo / ratings / rules /
engine en columnas de `game_sessions` + `engine/build.py`. DATA-AUDIT-001
cerrado: el `or 0` de vision/velocity/movement no era una mina latente sino
un defecto alcanzable, causado por `Position.PITCHER` ("P") ausente de
`Position.is_pitcher`. Corregido en el enum; exposicion `vision=0` en
bateadores = 0. Sin tocar vision/velocity/movement.)

P5-A (identidad de PA + versionado + wiring honesto del pitch log al runtime)
y P5-B (dominio `BatterApproach`: alineación con swing_type/zone_guess/
pitch_guess) cerrados: ver §Paso 6. Sigue P5-C (reconciliación, `TELEMETRY-
PITCH-001`) y lo demás del bloque.

------------------------------------------------------------------------

# 3. Catálogo y ratings

## Catálogo v2 activo

``` text
ID: b2f36619-ff17-459f-b4fe-c88b8c3a07a1
Version: 2
Status: ACTIVE
Cards: 806
Active: 806
Pack eligible: 806
Supersedes: v1
```

Rareza:

  Rareza      Cartas
  --------- --------
  COMMON         297
  BRONZE         219
  SILVER         141
  GOLD           101
  DIAMOND        48

El catálogo v1 permanece histórico/retirado.

Principio:

``` text
ACTIVE catalog ≠ owned card ≠ playable card
```

No introducir filtros `ACTIVE` globales en repositorios históricos. Una
carta retirada puede seguir siendo propiedad del usuario y
potencialmente jugable.

------------------------------------------------------------------------

# 4. Roster humano y ownership

Originalmente `GameSessionService.create()` podía recibir IDs de cartas
suministrados por el cliente sin comprobar propiedad.

Findings:

``` text
GAMEPLAY-LINEUP-001
Arbitrary card IDs could be used.

GAMEPLAY-LINEUP-002
Persisted UserLineup fallback required the same validation boundary.
```

Se implementó `_validate_human_roster()` utilizando ownership y datos
reales de carta.

Regresiones cubiertas:

-   carta no poseída → rechazo;
-   batter duplicado → 400;
-   pitcher como batter → 400;
-   batter como pitcher → 400.

Estado:

``` text
GAMEPLAY-LINEUP-001 — CLOSED / PASS
GAMEPLAY-LINEUP-002 — protected by common validation
```

Principio:

``` text
OWNED BY USER ≠ REGISTERED FOR THIS GAME
```

------------------------------------------------------------------------

# 5. Snapshot de roster por partida

Al crear una partida:

-   se valida el roster humano;
-   se congela el bullpen humano;
-   se fija el catálogo CPU;
-   se selecciona el roster CPU;
-   se congela el bullpen CPU;
-   los IDs registrados quedan en el estado de la partida.

El snapshot representa pertenencia al roster registrado, no
disponibilidad instantánea. Un relevista no se elimina del snapshot al
entrar al juego.

Commit:

``` text
a1323cb4f122e9113d08a4d7c44a80524db0076f
fix(gameplay): freeze game rosters at session creation
```

Estado:

``` text
GAMEPLAY-ROSTER-001 — CLOSED / PASS
GAMEPLAY-ROSTER-002 — CLOSED / PASS
GAMEPLAY-CATALOG-001 — CLOSED / PASS
GAMEPLAY-CPU-001 — CLOSED / PASS
GAMEPLAY-CPU-002 — CLOSED / PASS
```

------------------------------------------------------------------------

# 6. CPU roster

El CPU resuelve:

``` text
get_active_catalog(season=2026, edition_type="BASE")
```

y consulta:

``` text
find_cards_by_team(..., catalog_id=active_catalog.id)
```

No existe fallback global.

Selección determinista:

``` text
pitchers → (-overall, id)
batters  → (-overall, id)

starter = pitchers[0]
lineup  = batters[:9]
```

La dificultad todavía no cambia la calidad del roster elegido. La
selección strongest-by-overall + ID es la política v1.

------------------------------------------------------------------------

# 7. Transacciones y WebSocket

Problema original:

``` text
broadcast
   ↓
DB rollback
   ↓
cliente observaba un estado inexistente
```

Solución: `PendingBroadcast`.

``` text
Mutate state
    ↓
PendingBroadcast[]
    ↓
commit
    ↓
publish
```

Commit:

``` text
4b852d53585e62a05d3b9c01f11f107ccdc1b7f4
fix(gameplay): make broadcasts transaction-safe
```

Estado:

``` text
GAMEPLAY-TX-001 — CLOSED / PASS
```

------------------------------------------------------------------------

# 8. Fatigue v2

La política legacy usaba thresholds demasiado pequeños:

``` text
3 innings → 6
6 innings → 15
9 innings → 25
```

Se calibró una nueva curva:

``` text
SMOOTH-0.55-F35
```

Para `w <= 1`:

``` text
factor = 1
```

Para `w > 1`:

``` text
factor = 0.35 + 0.65 * exp(-((w - 1) / 0.55)^2)
```

Thresholds seleccionados:

``` text
3 innings → 33
6 innings → 67
9 innings → 100
```

Producción:

``` text
STANDARD_PITCH_THRESHOLD = 100
get_pitch_threshold() = round(100 × innings / 9)
```

Commit:

``` text
d8c8804
feat(gameplay): implement calibrated fatigue policy v2
```

------------------------------------------------------------------------

# 9. Fatiga aplicada al pitch específico

Bug original:

``` text
map_card_to_pitcher_attrs()
    ↓
apply_pitcher_fatigue()
    ↓
get_pitch_stats(tipo)
    ↓
current_pitch recuperaba atributos frescos
```

Se derivaron factores entre atributos raw y fatigados y se aplicaron al
repertoire específico.

Commit:

``` text
045584164f73ec66a753ce4466044476834892d1
fix(gameplay): apply fatigue to pitch-specific attributes
```

Estado:

``` text
GAMEPLAY-ENGINE-001A — CLOSED / PASS
```

------------------------------------------------------------------------

# 10. Estrategia CPU y fatiga

Se separaron:

``` text
workload = pitch_count / pitch_threshold
```

para estrategia, y:

``` text
fatigue_factor
```

para degradación física.

Política CPU v1:

``` text
HARD   → workload >= 1.20
MEDIUM → workload >= 1.35
EASY   → workload >= 1.50
```

`fatigue_level` queda sólo como compatibilidad legacy.

Commits principales:

``` text
fb090ff
ec6e98c
23a0ce4
d025eb4
```

------------------------------------------------------------------------

# 11. UI de fatiga

Bandas:

``` text
FRESH      factor >= .95
TIRING     .80 <= factor < .95
FATIGUED   .60 <= factor < .80
EXHAUSTED  factor < .60
```

La banda es la semántica primaria. La barra puede derivarse del factor,
pero no se presenta como un porcentaje literal de "energía".

Se eliminaron implementaciones frontend paralelas/obsoletas.

Commit:

``` text
125b8b6
refactor(frontend): remove obsolete fatigue UI model
```

Estado:

``` text
GAMEPLAY-FATIGUE-UI-001 — CLOSED
```

------------------------------------------------------------------------

# 12. Plate Discipline / Counts

Política productiva congelada:

``` text
TAKE_BASE_STRIKE_CHANCE = 0.30
TAKE_STRIKE_CHANCE_FLOOR = 0.20
TAKE_STRIKE_CHANCE_CEILING = 0.85
FOUL_ON_CONTACT_CHANCE = 0.45
```

TAKE:

``` text
0.30
+ (control - 50) * .003
- (vision - 50) * .002

clamp .20 → .85
```

La estrategia `65/50/30` usada en experimentos es un agente LAB:

``` text
0 strikes → TAKE 65%
1 strike  → TAKE 50%
2 strikes → TAKE 30%
```

No es una regla productiva del motor.

------------------------------------------------------------------------

# 13. Clamp Control × Vision

El floor anterior `.25` creaba una meseta para Control bajo + Vision
alta.

Se caracterizó analíticamente y con Monte Carlo.

Decisión:

``` text
TAKE floor = .20
```

Recuperó aproximadamente el 89% de la sensibilidad perdida sin eliminar
completamente la protección inferior.

Commits:

``` text
84cee31 — production promotion
408722d — production acceptance
```

Estado:

``` text
GAMEPLAY-ENGINE-002 — CLOSED / PASS
GAMEPLAY-ENGINE-002-CLAMP-001 — CLOSED
```

No seguir ajustando TAKE/foul/floor sin evidencia nueva.

------------------------------------------------------------------------

# 14. CALIBRATED-BASELINE-v1

Matriz:

``` text
Pitcher: WEAK / MID / STRONG
Batter:  WEAK / MID / STRONG
```

El contrato original basado en el máximo de pitches/PA fue sustituido
por un contrato de colas prospectivo:

``` text
K5-R

p95 <= 6
P(pitches >= 12) <= .05%
P(pitches >= 16) <= .01%
no CAP accumulation
```

Repetición independiente:

``` text
p95 = 6
P>=12 = .024%
P>=16 = 0
```

Anclas MID/MID:

``` text
Contact/Swing ≈ 65.41%
XBH/BIP ≈ 23.03%
```

Commit:

``` text
bee3bc6
```

Estado:

``` text
GAMEPLAY-ENGINE-003A — CLOSED
```

------------------------------------------------------------------------

# 15. Stuff: finding original

`ratings-2.0` produce:

``` text
Velocity
Control
Movement
Stuff
```

pero el motor sólo consumía los tres primeros.

Finding:

``` text
GAMEPLAY-RATING-001
Stuff exists in ratings but is not consumed by gameplay.
```

Se decidió no agregarlo arbitrariamente y abrir una cadena experimental.

------------------------------------------------------------------------

# 16. 003B-1 --- semántica de Stuff

Candidatos:

``` text
S1 WHIFF
Stuff modifica whiff.

S2 CONTACT QUALITY
Stuff modifica power_score después del contacto.

S3 HYBRID
Stuff modifica parcialmente ambos.
```

750k PA.

Resultado por +10 Stuff, aproximadamente:

  Modelo     Δ Contact/Swing   Δ XBH/BIP
  -------- ----------------- -----------
  S1                   −0.63      \~0.00
  S2                    0.00       −0.61
  S3                   −0.31       −0.32

S1 era redundante con Velocity/Movement.

Decisión:

``` text
Stuff = contact-quality suppression
```

Commit:

``` text
f0584aa
```

------------------------------------------------------------------------

# 17. 003B-2 --- Stuff vs Velocity/Movement

1.25M PA.

Sensibilidad por +10:

``` text
VEL: Contact/Swing −2.441 | XBH/BIP +0.020
MOV: Contact/Swing −2.441 | XBH/BIP +0.020

S1:  −0.628 | −0.002
S2:  +0.000 | −0.609
S3:  −0.308 | −0.318
```

Coseno:

``` text
cos(S1, MOV) = 1.000
cos(S1, VEL) = 1.000

cos(S2, MOV) ≈ -0.008
cos(S2, VEL) ≈ -0.008
```

Modelo conceptual:

``` text
Velocity / Movement → whiff
Control             → zone / called strike
Stuff               → contact quality allowed
```

Commit:

``` text
a582518
```

------------------------------------------------------------------------

# 18. 003B-3 --- magnitud de Stuff

Forma:

``` text
stuff_delta = stuff - 70
effective_power_score =
    power_score - stuff_delta * k
```

2.0M PA.

      k   Δ XBH/10 Stuff   ratio vs Power
  ----- ---------------- ----------------
    .30           −2.945             .742
    .40           −3.968            1.000
    .50           −5.008            1.262

Interpretación:

-   `.40` ≈ `-Power`: dos caras del mismo atributo.
-   `.50` domina demasiado.
-   `.30` suprime sin anular.
-   `.20` quedó como referencia conservadora.

Commit:

``` text
c56d1d8
```

Candidato:

``` text
k = .30
```

------------------------------------------------------------------------

# 19. 003B-4 --- Power × Stuff

Matriz:

``` text
Power = 45 / 55 / 70 / 85 / 95
Stuff = 45 / 70 / 95
```

750k PA.

Resultados:

``` text
Power slope @ ST95 = +4.012 / 10
Stuff slope @ POW95 = −3.013 / 10
```

Strong-vs-strong:

``` text
POW95 × ST95 = 25.59 XBH/BIP
POW70 × ST95 = 15.77
Δ = +9.83pp
```

Diagonal:

``` text
20.72 → 23.03 → 25.59
```

No existe cancelación artificial.

Commit:

``` text
213b3a8
```

Decisión:

``` text
k=.30 → ROBUSTNESS-VALIDATED CANDIDATE
```

------------------------------------------------------------------------

# 20. 003B-5A --- semántica Stuff × Fatigue

Políticas:

``` text
F0 NONE

F1 FULL
effective = raw * fatigue_factor

F2 HALF
effective = raw * (1 - .5 * (1 - fatigue_factor))

F3 ANCHORED
effective = 70 + (raw - 70) * fatigue_factor
```

2.4M PA.

Resultados:

-   `ANCHORED` rechazado: Stuff bajo podía mejorar al fatigarse.
-   `FULL` rechazado: Stuff95 a workload 1.50 terminaba peor que MID
    fresco.
-   `HALF` mostró degradación proporcional y preservación de identidad.

Commit:

``` text
5eb8352
```

Decisión:

``` text
familia multiplicativa parcial
→ promovida a calibración
```

------------------------------------------------------------------------

# 21. 003B-5B --- calibración de alpha

Familia:

``` text
effective_stuff =
raw_stuff * (1 - alpha * (1 - fatigue_factor))
```

Sweep:

``` text
0 / .25 / .40 / .50 / .60 / .75 / 1
```

Hallazgos:

``` text
<= .25 → demasiado cosmético
.40    → conservador
.50    → sano + buena holgura
.60    → sano pero más cerca de perder identidad
>= .75 → fuera por frontera de identidad
```

Frontera interpolada:

``` text
alpha* ≈ .72
```

Finalistas:

``` text
.50 vs .60
```

No se decidió mediante una barra post-hoc.

------------------------------------------------------------------------

# 22. 003B-5C --- alpha .50 vs .60

2.7M PA.

Matriz:

``` text
Power    45 / 70 / 95
Stuff    45 / 70 / 95
Workload 1.00 / 1.35 / 1.50
```

Ambos pasaron R1-R8.

Pero:

``` text
              alpha=.50   alpha=.60
identity       +2.18pp     +1.11pp
```

`.60` añadía magnitud, pero reducía significativamente el margen de
identidad.

`.50` sí expresa claramente fatiga de Stuff:

``` text
ST95 @ w1.35 → +2.98pp XBH
ST95 @ w1.50 → +5.08pp XBH
retention ≈ 83%
```

Decisión:

``` text
alpha = .50
```

Principio: menor intervención cuando ambos cumplen la función y el más
agresivo no justifica su coste.

------------------------------------------------------------------------

# 23. Política final de Stuff

Congelado:

``` text
STUFF_BASELINE = 70
STUFF_POWER_SUPPRESSION = .30
STUFF_FATIGUE_ALPHA = .50
```

Fatiga:

``` text
effective_stuff =
raw_stuff * (
    1 - .50 * (1 - fatigue_factor)
)
```

Calidad de contacto:

``` text
stuff_delta = effective_stuff - 70

power_score -=
stuff_delta * .30
```

Separación:

``` text
fatigue_manager → transforma atributos
calculator      → consume atributos efectivos
```

`calculator` no necesita conocer directamente `fatigue_factor`.

------------------------------------------------------------------------

# 24. 003B-6 --- integración productiva + acceptance

Ruta productiva:

``` text
Ratings / Card
      ↓
attribute_mapper
      ↓
PitcherAttrs.stuff
      ↓
fatigue_manager
      ↓
effective Stuff
      ↓
calculator
      ↓
contact-quality suppression
```

Migración:

``` text
0042
```

Acceptance:

``` text
27 / 27 contracts PASS
0 / 1,350,000 PA divergent PROD vs LAB
```

La reproducción fue bit-exacta.

Baseline fresco:

``` text
0 / 150,000 divergent
```

Suite:

``` text
987 passed
```

Engine build de acceptance:

``` text
4ee14a8
```

Commits:

``` text
512f5bc
feat(gameplay): integrate Stuff into contact quality

6015b50
docs(gameplay): close Stuff integration acceptance
```

> Si el commit documental fue amendado posteriormente para retirar
> `_e003b6_full_run.txt` del tracking, actualizar aquí el hash.

Estado:

``` text
GAMEPLAY-ENGINE-003B — CLOSED / PASS
GAMEPLAY-RATING-001  — CLOSED / PASS
```

**Stuff queda congelado.**

------------------------------------------------------------------------

# 25. Correcciones metodológicas detectadas en 003B-6

## XBH

Definición correcta:

``` text
XBH = 2B + 3B + HR
```

No incluye singles.

El harness inicialmente sumaba `1B`, creando una desviación falsa de
\~21pp pese a que PROD y LAB eran bit-exactos.

## Baseline bajo fatiga

El contrato de equivalencia con el motor anterior sólo aplica en fresco.

Con Stuff70 fatigado:

``` text
effective_stuff < 70
```

y aparece intencionalmente un bono ofensivo.

Exigir igualdad bajo fatiga habría significado exigir `alpha=0`.

## Tolerancias

Las reproducciones Monte Carlo se comparan mediante SE combinado, no
mediante tolerancias fijas arbitrarias.

------------------------------------------------------------------------

# 26. DATA-STUFF-001 — CERRADO

## Problema

El motor ya consume Stuff, pero faltaba cerrar la cadena desde los ratings
reales hasta las cartas publicadas.

Riesgo planteado:

``` text
card.stuff = 70
```

aunque:

``` text
CardRatingProfile.stuff != 70
```

o:

``` text
PlayerRatings.stuff != 70
```

En ese caso:

``` text
el motor habla Stuff
pero el catálogo lo silencia.
```

## DATA-STUFF-001A --- auditoría read-only

Script: `backend/etl/audit_stuff_propagation.py`

Universo:

``` text
ACTIVE BASE catalog v2
expected = 806 cards
```

Entregable: contadores de `total_active`, `stuff_card_eq_70`,
`authoritative_stuff_eq_70`, `silent_default_mismatch`, `exact_match`,
`missing_profile`, `missing_player_rating` y
`conflicting_profile_vs_player_rating`.

Mismo criterio de mismatch crítico:

``` text
card.stuff == 70
AND
authoritative_stuff != 70
```

Precedencia auditada (idéntica a la de `backfill_cards.py`):

``` text
CardRatingProfile
    ↓
PlayerRatings
    ↓
baseline 70
```

### Corrección metodológica: Stuff es sólo de PITCHER

`stuff_rating` es NULL **por diseño** para BATTER — los CHECK de role-shape
(`ck_card_rating_profiles_complete_role_shape` y
`ck_player_ratings_complete_role_shape`) lo imponen — mientras que
`player_cards.stuff` es NOT NULL.

Contar las 806 cartas como una sola población habría producido ~402
"mismatches" falsos. La auditoría segmenta por role (el de
`CardRatingProfile`, no el `position` de la carta) y mide el contrato
crítico sólo sobre pitchers.

Una carta de bateo con `stuff = 70` no es un silencio: es su único valor
legal.

### Hallazgo de entorno

La BD estaba en Alembic `0041`: la columna `player_cards.stuff` (migración
`0042`, ya commiteada) no existía. Sin `al upgrade head` la pregunta del
roadmap no era respondible, y la auditoría lo declara explícitamente en
`schema` en vez de fallar en silencio.

### Contratos D1-D7 --- 7/7 PASS

``` text
D1  universo == 806 cartas ACTIVE            806 / 806
D2  cada carta de pitcher resuelve un
    Stuff autoritativo único y en dominio     404 / 404
D3  las fuentes faltantes se reportan
    missing_profile                0
    missing_player_rating          0
    fallback_to_baseline          12
D4  conflictos Profile ↔ PlayerRatings       0
D5  matches y silent-default clasificados
    exact_at_baseline            12
    silent_default_mismatch     392
    stale_override                0
    divergent                     0
D6  auditoría read-only            PASS (conteos before/after idénticos)
D7  sin mutaciones hasta caracterizar          PASS
```

### Respuesta a la pregunta de §36

``` text
ACTIVE cards = 806

count(
    card.stuff == 70
    AND
    authoritative_stuff != 70
) = 392
```

La pregunta del roadmap estaba bien planteada y la respuesta es
inequívoca: **392**.

Caracterización adicional:

``` text
pitcher_cards                        404
pitcher_cards_materialized            12   (2.97%)
materialization_rate                0.029703

card.stuff      → 1 valor distinto  (70, el server_default)
authoritative   → 53 valores distintos, rango 45..97
delta (card − authoritative) → −27 .. +25
conflicts CardRatingProfile ↔ PlayerRatings → 0
```

Dos consecuencias que importan:

1.  **Stuff no existía en producción.** Con un solo valor en toda la flota,
    la política de 003B (k=.30 / α=.50) se aplicaba sobre una constante.
    El suppression real era `0.00` para los 404 pitchers.
2.  **El error no era unidireccional.** El delta va de −27 a +25: los
    pitchers élites (ST 87-97) no recibían la supresión que les corresponde,
    y los pitchers flojos (ST 45-55) no recibían la penalización de contact
    quality poor. Stuff estaba mal *expresado*, no sólo ausente.

## DATA-STUFF-001B --- materialización

Sólo se abrió porque 001A encontró mismatches.

### B-1 --- causa raíz (publicación)

``` text
etl/services/card_catalog.py::_card_from_profile
```

Leía `stuff_rating` dentro de `_RATING_FIELDS` y lo materializaba en
`values`, pero el constructor de `PlayerCardModel` de esa misma función
nunca asignaba `stuff`. Toda carta publicada caía en el
`server_default='70'` de la migración `0042`.

Correcciones:

-   `_card_from_profile` asigna `stuff` desde el perfil autoritativo.
    Si `stuff_rating` es NULL (BATTER por contrato de role-shape), escribe
    `STUFF_BASELINE` — su valor exacto — y no `0`, que daría supresión
    `+21` a las 402 cartas de bateo.
-   `_validate_rows` valida `stuff` dentro de 0-99.
-   `_validate_rows` reporta `stuff is None` explícitamente: el patrón
    `getattr(card, f) or 0` de los demás campos enmascararía un `None`
    como `0`, que está dentro de rango.

Con esto, un catálogo nuevo no puede reintroducir el silent default: si
`stuff` no llega, la publicación falla en vez de publicar en silencio.

### B-2 --- backfill controlado

`app/seeds/backfill_cards.py::backfill_catalog_stuff()` — reutiliza
`_resolve_stuff_from_ratings()`, o sea la precedencia ya documentada, sin
duplicarla.

``` text
python app/seeds/backfill_cards.py --catalog-stuff            (dry-run)
python app/seeds/backfill_cards.py --catalog-stuff --apply   (escribe)
```

Decisiones:

-   **Dry-run por defecto.** Sin `--apply` calcula el plan y hace
    `rollback`. Nada se escribe sin pedirlo explícitamente.
-   **Alcance explícito por catálogo**, por defecto el ACTIVE BASE. No es un
    filtro global: el catálogo v1 RETIREED se dejó intacto (verificado:
    sigue con 1 valor distinto, todos 70).
-   **Sólo role PITCHER.** El rol se infiere de la fuente autoritativa (el
    `CardRatingProfile`, o un `PlayerRatings` PITCHER si la carta se
    publicó por la ruta fallback), nunca del `position` de la carta: un
    two-way publica un único perfil.
-   **Idempotente** por construcción: escribe `card.stuff != autoritativo`.
-   **No usa** el centinela `rating_model_version IS NULL` de la ruta
    legacy: esas cartas ya están firmadas y son otro caso.

Resultado:

``` text
total_cards                     806
pitcher_cards                   404
batter_cards_untouched          402
changed                         392
unchanged                        12
mean_delta                    0.4031
stuff_sources.card_rating_profile  404
stuff_sources.player_ratings        0
stuff_sources.neutral                0
```

Las 404 resuelven por `CardRatingProfile` (precedencia #1): no hubo
ninguna caída al fallback, y 0 conflictos con `PlayerRatings` (D4), así
que la fuente era inequívoca.

### B-3 --- re-auditoría

``` text
silent_default_mismatch       392  →  0
exact_match                  0 → 392
exact_match_at_baseline     12  →  12
stale_override                0  →  0
divergent                     0  →  0
materialization_rate    0.029703  →  1.0
```

Idempotencia verificada en la BD real: segunda corrida `changed = 0`.

``` text
player_cards.stuff (catálogo ACTIVE v2)
    53 valores distintos, rango 45..97
    414 en exactamente 70  (402 batters + 12 pitchers neutros)

player_cards.stuff (catálogo RETIRED v1)
    1 valor distinto, todos 70  ← intacto, histórico
```

### Verificación de la cadena completa

Con datos reales, la ruta productiva
`mapper → fatigue_manager → calculator`:

``` text
Nathan King     card.stuff=45  profile.stuff=45  effective=45.00  suppression=+7.50
Ronald Hill     card.stuff=70  profile.stuff=70  effective=70.00  suppression=-0.00
Jason Martin    card.stuff=97  profile.stuff=97  effective=97.00  suppression=-8.10

mismo pitcher a w=1.35 (135 lanzamientos)
Jason Martin    raw=97  effective=86.50  suppression=-4.95
```

`card.stuff` coincide con el perfil autoritativo en los tres casos, y la
fatiga degrada el Stuff efectivo como espera α=.50. La supresión real de
la flota pasó de `0.00` a un rango de `+7.50 .. −8.10`.

### Contratos de regresión S1-S4

`backend/tests/etl/test_stuff_propagation.py` --- 16/16 PASS.

``` text
S1  la publicación materializa stuff (pitcher, batter, fallback,
    idempotencia)
S2  la validación falla si stuff no llega (fuera de rango, None)
S3  el backfill es explícito, idempotente y sólo de pitchers
    (dry-run no escribe, apply escribe, 2ª corrida changed=0,
    batters intactos, otro catálogo intacto)
S4  no reintroducción: 0 silent defaults; el mapper lee card.stuff
```

Suite completa:

``` text
987  →  1003 passed     (+16, 0 regresiones)
```

### Estado

``` text
DATA-STUFF-001A — CLOSED / PASS
DATA-STUFF-001B — CLOSED / PASS
```

### Qué NO quedó demostrado

-   **No se midió el impacto en gameplay.** Se verificó que el atributo se
    materializa y llega al motor con el valor correcto, no cómo mueve el
    XBH/BIP del catálogo real. Eso pertenece a
    `GAMEPLAY-RATING-003` (rating expression) o a un acceptance del
    catálogo contra `CALIBRATED-BASELINE-v1`.
-   **No se cambió ningún número de la política.** k=.30, α=.50 y
    `STUFF_BASELINE`=70 siguen congelados. 001B es una corrección de datos,
    no una recalibración.
-   **No se evaluaron las cartas del catálogo v1 RETIRED.** Permanecen en
    70 por diseño (histórico). Si alguna vez se juega con ellas, necesitará
    su propio bloque explícito.
-   **No se tocó el frontend.** `format_pitcher_stats` sigue emitiendo
    sólo VEL/CTA/MCA; `stuff` no es un atributo de presentación hoy.

------------------------------------------------------------------------

# 27. TELEMETRY/FATIGUE

El acceptance de Stuff utiliza shootout:

``` text
workload fijo durante un PA
```

El runtime real incrementa pitch count lanzamiento por lanzamiento.

Esto no invalida 003B: se demostró que un `fatigue_factor` dado produce
exactamente el Stuff efectivo aprobado.

La dinámica temporal pertenece a Fatigue/Telemetry y queda como deuda
separada.

------------------------------------------------------------------------

# 28. GAMEPLAY-RATING-002 --- Clutch --- DEFERRED

## Caracterización (read-only, 2026-10-01)

Se caracterizó antes de proponer fórmulas. Resultado: no hay nada que
calibrar todavía.

### 1. Clutch no lo consume el motor

`attribute_mapper.py:80` publica `"clutch"` en el dict de bateo.
`calculator.py:138-140` lee sólo:

``` python
con = batter_attrs.get("contacto", 50) * tactics.get("batter_con", 1.0)
pwr = batter_attrs.get("poder", 50)   * tactics.get("batter_pwr", 1.0)
vis = batter_attrs.get("vision", 50)  * tactics.get("batter_vis", 1.0)
```

Cero lecturas de `clutch` en `calculator`, `cpu_ai`, `bullpen`,
`state_manager`, `runner_manager`, `tactic_resolver`, telemetría o PWA.
**Ningún efecto observable en ningún PA.** Contraste: `stuff` sí se lee
(`calculator.py:151`) y se aplica (`:241`).

Las dos ramas del resolver consumen atributos distintos:

``` text
SWING → _calculate_contact_outcome(con, pwr, vel, mov, stuff)
TAKE  → _take_strike_probability(take_bias, ctl, vis)
```

### 2. Y tampoco hay señal en los datos

| role | n | valores distintos | min | max |
|------|---|-------------------|-----|-----|
| BATTER | 402 | **1** | 70 | 70 |
| PITCHER | 404 | **1** | 0 | 0 |

`player_ratings.clutch_evidence`: **0 de 869 filas**. El inventario de
`ratings_2_0` ya lo declaraba:
`Clutch situacional | sin agregado situacional | MISSING`.

El 70 no es una medición, es un placeholder explícito. El 0 de los
pitchers era un bug, no un neutral.

### 3. El `or 0` alcanzaba a 4 columnas

`card_catalog.py` usaba `or 0` en todo, y los NULL-por-role-shape caían
al piso del dominio:

| role | velocity | movement | vision | clutch |
|------|----------|----------|--------|--------|
| PITCHER | 43-98 | 46-95 | **0** | **0** |
| BATTER | **0** | **0** | 45-97 | 70 |

Es **latente**, no vivo: `vision` sólo se consume vía `batter_attrs` (un
pitcher no batea) y `velocity`/`movement` sólo vía `pitcher_attrs` (un
bateador no lanza). Son minas dormidas, no un defecto en producción.

También había **dos neutrales**: `backfill_cards.py` decía
`NEUTRAL_CLUTCH = 50` mientras `etl/config/ratings_2.py` decía
`CLUTCH_NEUTRAL_RATING = 70` (que es lo que materializa
`calculate_batter_clutch()`).

### 4. Por qué no se propuso fórmula

Escribir Clutch como coeficiente hoy amplificaría una constante: el
mismo resultado para los 806 jugadores. Si el coeficiente es sizable,
todos se mueven igual — un cambio de ritmo global disfrazado de skill
individual. La variable que lo haría real (inning, score differential,
runners, outs) **no existe** en ratings-2.0: se construye en el paso 5
(telemetría). El propio roadmap prohíbe
`NO introducir parámetros sin fuente documentada`.

## Decisión

``` text
CLUTCH PLACEHOLDER DECISION

Option:          A
Neutral:         70
Gameplay effect: NONE
Current role:    ratings-2.0 placeholder only

GAMEPLAY-RATING-002:
DEFERRED

Future direction:
B — Clutch contextual basado en leverage,
después de que exista el game context / telemetry necesario.

C:
REJECTED FOR NOW (no calibrated source)

Scope of commit:
Clutch only.

Vision / Velocity / Movement:
leave unchanged; audit separately.
```

La definición de leverage que este bloque anticipaba queda **sin
ejecutar**: pasa a ser prerrequisito del paso 5, no del paso 3.

## Lo que se hizo

- `card_catalog.py`: Clutch materializa `CLUTCH_NEUTRAL_RATING` cuando
  `clutch_rating` es NULL, en vez de `or 0`.
- `_validate_rows` rechaza `clutch is None` (el `or 0` lo enmascararía).
- `backfill_cards.py`: `NEUTRAL_CLUTCH` colapsa a la constante canónica;
  nuevo `backfill_catalog_clutch()` con dry-run por defecto, acotado a un
  catálogo, y que **sólo rellena ausencias** (nunca pisa Clutch con fuente
  autoritativa).
- `attribute_mapper.py`: el docstring afirmaba que vision y clutch venían
  de un backfill "NOT NULL sin fallback". Era falso para el catálogo
  ACTIVE, cuya ruta legacy nunca corre. Corregido y anotado que Clutch no
  lo consume el motor.

Datos (404 pitchers `0 → 70`), idempotente, catálogo RETIRED intacto:

``` text
antes   BATTER 402 en 70   PITCHER 404 en 0
después BATTER 402 en 70   PITCHER 404 en 70
2ª corrida: changed = 0
```

## Contratos A1-A4

`backend/tests/etl/test_clutch_placeholder.py`

``` text
A1  el neutral es una sola constante canónica (70)
A2  la publicación materializa el neutral y valida ausencia
A3  el backfill rellena ausencias: dry-run, apply, idempotente,
    no pisa Clutch autoritativo, no toca otros catálogos
A4  Clutch NO cambia el resultado del PA --- verificado
    conductualmente sobre las DOS ramas del resolver
```

A4 es un test de distribución: corre 400 seeds por caso y compara
histogramas de eventos. Incluye contramuestras que demuestran que el
arnés detecta diferencias (variar `poder` en SWING, `vision` en TAKE) y
un contraste de que `stuff` sí mueve la distribución. Verificado que
falla si se cablea Clutch a contact quality.

``` text
suite: 1006 → 1023 passed
```

## Pendiente (fuera de scope por decisión explícita)

`vision`/`velocity`/`movement` en el rol que no les corresponde siguen en
0. Se auditan por separado, y **no** son equivalentes al caso de Clutch:
el peso de `vision` en la rama TAKE es real
(`VISION_TAKE_WEIGHT = 0.002`), así que un 0 futuro en el rol incorrecto
no sería inerte como el de Clutch. Merecen su propio bloque y su propia
decisión de neutral.

------------------------------------------------------------------------

# 29. Telemetría de Gameplay

Existe `PitchEventLog` con infraestructura para:

-   game;
-   plate appearance;
-   pitch number;
-   choices;
-   approach;
-   pitch family;
-   count before;
-   fatigue;
-   modifiers;
-   matchup inputs;
-   probability distribution;
-   RNG;
-   result;
-   engine version.

Pendientes:

``` text
TELEMETRY-PITCH-001
Runtime instrumentation not fully wired.
(parcial P5-A: el pitch log se escribe post-resolución en cada swing/take/bunt
 resuelto; falta el pitch NO resuelto por el bateador — p.ej. toma forzada,
 robo, balks — y la reconciliación con el box score.)

TELEMETRY-PA-001
No robust runtime PA identity.                                   CLOSED (P5-A)

TELEMETRY-EVENT-001 / VERSION-001
GameEventLog fields exist but writer/runtime does not fully populate them.
                                                                 CLOSED (P5-A)

TELEMETRY-DOMAIN-001
BatterApproach telemetry is not fully aligned with runtime
swing_type / zone_guess / pitch_guess.                           CLOSED (P5-B)
```

`TELEMETRY-PITCH-001` sigue abierto: el pitch log cubre cada pitch resuelto por
`resolve_swing`, pero no eventos fuera de él (toma forzada, robo, balks) ni la
reconciliación evento ↔ estado ↔ box score. Es P5-C / Paso 7.

------------------------------------------------------------------------

# 30. Provenance

`GameSession.state_data` conserva el estado operativo, pero no toda la
procedencia necesaria para reproducir históricamente una partida.

Pendientes:

``` text
GAMEPLAY-PROVENANCE-001   CLOSED (P4: columnas en game_sessions)
TELEMETRY-PROVENANCE-001  PENDING
```

Una partida identifica (ver §Paso 5):

``` text
catalog id/version
rating model version
rules version
engine version/build
```

------------------------------------------------------------------------

# 31. Starter pack --- deuda de adquisición

`PackService.assign_starter_pack()` continúa utilizando pools
históricamente no catalog-scoped.

Finding:

``` text
STARTER-001
Starter acquisition pool is not catalog-scoped.
```

No resolver introduciendo `ACTIVE` global en repositorios.

Pertenece a futura `StarterPolicy / Economy`.

------------------------------------------------------------------------

# 32. Roadmap desde aquí

## Paso 1 --- DATA-STUFF-001A --- DONE

Auditar las 806 cartas activas.

``` text
pregunta: ¿cuántas tienen card.stuff = 70
          mientras authoritative ratings-2.0 Stuff != 70?
respuesta: 392
```

Sin mutaciones. Contratos D1-D7: 7/7 PASS.

## Paso 2 --- DATA-STUFF-001B --- DONE

``` text
materialize   → 392 cartas corregidas
verify precedence → 404/404 desde card_rating_profile
check idempotence → segunda corrida changed = 0
re-audit      → 0 silent_default_mismatch, 7/7 PASS
```

Objetivo final alcanzado:

``` text
ratings
→ DB
→ card
→ mapper
→ fatigue
→ engine
```

## Paso 3 --- GAMEPLAY-RATING-002 / Clutch --- DEFERRED

Caracterizado y cerrado como placeholder (opción A). No hay fórmula que
proponer: `clutch_evidence` está vacío y el motor no lee Clutch. La
expresión contextual (dirección B) depende del paso 5.

## Paso 4 --- DATA-AUDIT-001 --- role-shape en vision/velocity/movement --- CERRADO

Audit del mismo `or 0` que queda vivo en las otras tres columnas, antes
de tocar nada. Más sensible que el caso de Clutch porque `vision` sí
pesa en la rama TAKE.

**Resultado: el `or 0` de vision/velocity/movement NO es una mina latente.
Es un defecto alcanzable, causado por un bug de clasificación, no por
el `or 0`.**

### Causa raíz

`Position.is_pitcher` omitía `Position.PITCHER` (`"P"`), y
`PITCHER_POSITIONS` se deriva de ese property
(`backend/app/core/enums.py:183`). Consecuencia sobre el catálogo
activo (806 cartas):

| Métrica | Antes | Después |
| --- | --- | --- |
| `is_pitcher == True` | **1** (solo `TWP`) | **404** |
| `is_batter == True` | 805 | 402 |
| `position='P'` con `is_batter` | **403** | **0** |
| bateadores con `vision == 0` | 403 | **0** |
| lanzadores con `velocity`/`movement == 0` | 0 | **0** |

Las 403 cartas con `role=PITCHER` y `position='P'` devolvían
`is_batter=True`, pasaban las validaciones de lineup
(`game_session_service.py:69` humano, `:237` CPU) y entraban a batear con
`vision=0, contact=0, power=0`. `vision=0` sí pesa en TAKE
(`VISION_TAKE_WEIGHT`), así que la exposición era real y no teórica.

Simultáneamente, el juego quedaba casi injugable: con un solo lanzador
válido en 806 cartas, `game_session_service.py:245` podía rechazar
equipos CPU sin lanzadores.

El bug estaba parcheado por cuarta parte en el propio repo, contra el
docstring de `enums.py:11` ("nunca redefinirla"):

- `etl/services/card_catalog.py:66` --- `PITCHER_POSITIONS | {"P"}`
- `etl/services/statcast_population.py:17` --- tupla local con `"P"`
- `app/seeds/seed_mlb_2026.py:449` --- `position in ("P",)`
- `app/services/team_ratings.py:39` --- `or slot_pos == "P"`

Tres de los cuatro workarounds quedaron redundantes y se eliminaron:

- `etl/services/card_catalog.py:66` --- `PITCHER_POSITIONS | {"P"}` borrado;
  `profile_publish_order` deriva directo de la constante.
- `etl/services/statcast_population.py:17` --- tupla local reemplazada por
  `PITCHER_POSITION_VALUES` / `BATTER_POSITION_VALUES`, derivadas de
  `Position.is_pitcher` / `is_fielder` (+ TWP en bateo). Verificado que los
  dos conjuntos son idénticos a las tuplas anteriores.
- `app/seeds/seed_mlb_2026.py:270,449` --- `in ("P",)` eliminado.
  `seed_mlb_2026._normalize_pitcher_position` sí conserva el colapso
  `"P" -> "SP"`, pero evaluado **antes** de la pertenencia a
  `PITCHER_POSITIONS` a propósito: es comportamiento de salida histórica del
  seed, no un workaround del enum.

**`app/services/team_ratings.py:39` NO era un workaround y se conserva.**
`compute_lineup_ratings` clasifica por dos ejes ortogonales: el slot del
lineup (`UserLineup.slots`, donde `"P"` es el slot lanzador) y la posición de
la carta. Una carta `DH` metida en el slot `"P"` debe seguir contando como
pitcher, y eso depende del clause `slot_pos == "P"`. Sólo se aclar�� el
docstring para explicitar los dos ejes.

### Fix

Añadir `Position.PITCHER` a la tupla de `Position.is_pitcher`
(`backend/app/core/enums.py:158-165`). Una línea; corrige la fuente
única de la que derivan `PITCHER_POSITIONS`, `PlayerCardModel.is_pitcher`
e `is_batter`.

**No se tocó `vision`, `velocity` ni `movement`.** La exposición se
cerró corrigiendo clasificación, no datos: el `or 0` queda latente y
 defendible (un `NULL` de rol ajeno materializado en 0 nunca es leido
por el motor), igual que `clutch` antes de neutralizarse.

### Verificación

- Exposición cerrada en producción: `batters con vision==0: 0`,
  `pitchers con velocity==0 o movement==0: 0`,
  `cartas bateador y lanzador a la vez: 0`.
- `TWP` (Renato Valente) sin cambios: sigue lanzador, no bateador
  (`is_two_way=False` en datos; su vision=0 es correcta porque su
  perfil es `role=PITCHER`).
- Tests nuevos en `backend/tests/test_core.py`: `"P"` es lanzador,
  cobertura total de `PITCHER_POSITIONS`, y ningún puesto es a la vez
  lanzador y de campo.
- Mutación comprobada: revertir el enum hace fallar los tests nuevos.
- Suite completa: **1026 passed** (antes 1023).

### Deuda que queda registrada

`is_two_way` es inalcanzable por construcción
(`card_catalog.py:766-770` exige velocity>0 **y** power>0 **y**
contact>0, pero el role-shape CHECK garantiza el set de bateo *o* el de
pitcher, nunca ambos). El `or self.is_two_way` de
`PlayerCardModel.is_batter/is_pitcher` es rama muerta.

Eso es hoy inofensivo y el fix de arriba lo mantiene inofensivo: con
`is_two_way` siempre `False`, la clasificación depende sólo de
`position`. Pero si alguien "arregla" `is_two_way` sin tocar la
materialización, la carta TWP entra al lineup con
`vision/contact/power = 0` y el defecto se vuelve alcanzable. Es el
mismo patrón que Clutch: una decisión de neutral pendiente que sólo
importa cuando algo más cambie.

## Paso 5 --- Provenance --- CERRADO (GAMEPLAY-PROVENANCE-001)

Una partida deja de ser metadato incidental: identifica con qué catálogo,
modelo de ratings, reglas y build se jugó. Antes, `state_data` (JSON, sin
índices) era lo único persistido y no permitía responder esas preguntas.

### Decisión: columnas, no claves JSON

Cinco columnas nullable en `game_sessions` (migración `0043`):

| Columna | Origen | Responde |
| --- | --- | --- |
| `catalog_id` | FK `card_catalogs.id` (ON DELETE RESTRICT) | ¿Qué cartas? |
| `rating_model_version` | denormalizado del catálogo | ¿Qué modelo de ratings? |
| `rules_version` | `GAMEPLAY_RULES_VERSION` | ¿Qué reglas semánticas? |
| `engine_version` | `ENGINE_VERSION` | ¿Qué versión semántica del motor? |
| `engine_build` | `ENGINE_BUILD` | ¿Qué código estaba desplegado? |

Con columnas se habilitan las consultas que este bloque existe para
permitir (games by engine/rules/catalog, comparar engine A vs B, reproducir
desde catalog v2) sin depender de JSON sin índice.

Sin backfill: la tabla estaba vacía (0 sesiones) y, aun sin estarlo, no hay
provenance retroactivo que inventar. NULL explícito antes que un valor
inventado que parecería verificable.

`rating_model_version` se denormaliza a propósito aunque derive del
catálogo: responde la pregunta sin join y convierte
`session.rating_model_version == catalog.rating_model_version` en un
invariante verificable.

`engine_version` (semántica) y `engine_build` (código) son columnas
distintas porque responden preguntas distintas; separarlas evita otra
migración cuando exista una versión semántica real del motor.

### Snapshot inmutable

`GameSessionService.create()` resuelve `active_catalog` una vez y escribe el
snapshot al crear la sesión. Nunca se relee el catálogo ACTIVE para
reinterpretar una partida existente: si el catálogo se promueve después, la
partida vieja conserva el suyo. La selección CPU sigue catalog-scoped
(`find_cards_by_team(catalog_id=active_catalog.id)`), coherente con el
snapshot.

### Bumps de identidad en `engine/build.py`

El bloque separó tres ejes que antes vivían accidentalmente unidos en un
solo rótulo:

| Constante | Valor | Se mueve |
| --- | --- | --- |
| `CALIBRATED_BASELINE_V1_ENGINE_BUILD` | `4ee14a8` | NO (ancla histórica 003A) |
| `ENGINE_BUILD` | `engine-20261001-datap4` | sí (por DATA-AUDIT-001) |
| `ENGINE_VERSION` | `engine-1.0` | nace |
| `GAMEPLAY_RULES_VERSION` | `rules-1.0` | promoción `lab` -> estable |

- `ENGINE_BUILD` se bumpea por el fix de `Position.PITCHER` (Paso 4): cambió
  comportamiento observable de 403 cartas sin tocar `calculator.py`.
  Mantener el rótulo viejo habría hecho que la provenance afirmara un
  runtime que ya no existe.
- `GAMEPLAY_RULES_VERSION` pasa de `rules-1.0-lab` a `rules-1.0` por
  promoción explícita (Fatigue v2, Plate Discipline y Stuff ya pasaron
  acceptance). NO es efecto colateral del fix, que fue corrección de
  clasificación de dominio y por eso no bumpea reglas.
- El ancla de CALIBRATED-BASELINE-v1 no se mueve: es histórica y no
  describe el runtime. `test_baseline` repartió el rótulo único en cuatro
  asserts (esquema, ancla, runtime, reglas + engine version).

### Verificación

- `test_schema_head_congelado_es_0043`: único head del grafo.
- Contrato: `test_crear_snapshot_provenance_de_la_partida` (cinco columnas
  no-null y `rating_model_version == catalog.rating_model_version`) y
  `test_provenance_no_se_reinterpreta_cuando_el_activo_cambia`.
- `fixtures.SCHEMA_HEAD` se bumpea `0042 -> 0043` para no quedar mintiendo.
- Suite completa: **1030 passed**.

### Deuda registrada

`TELEMETRY-PROVENANCE-001` (sellado de provenance en el stream de eventos /
box score) queda para el bloque de telemetría. Este paso versiona la
partida, no cada evento.

## Paso 6 --- Telemetry v2

Conectar:

``` text
game
→ PA
→ pitch
→ decision
→ probability
→ RNG
→ result
→ state transition
```

### P5-A --- identidad de PA + versionado + wiring honesto --- CERRADO

**Problema / finding.** `GameEventLog` ya tenía columnas de telemetría
(`plate_appearance_id`, `engine_version`, `sequence_no`, distribución, RNG),
`PitchEventLog` ya tenía el builder y el repo, pero el runtime NUNCA los
poblaba: no había identidad de plate-appearance, el box score no sellaba
versión, y el pitch log no se emitía al resolver. `TELEMETRY-PA-001`,
`TELEMETRY-EVENT-001/VERSION-001`.

**Hipótesis.** El runtime puede alimentar la telemetría sin tocar el motor
congelado: la resolución se envuelve con un **trace aditivo** que no consume
RNG y el log se escribe DESPUÉS de resolver el pitch (nunca antes: los
secretos del rival — zona/pitch elegidos por la CPU — no se filtran al
registro del bateador).

**Contratos prefijados.** (de `engine_types.PlayResult` / `PitchEventLog` /
`GameEventLog`)

``` text
TracedPlay(NamedTuple): result: PlayResult; trace: dict
trace = {matchup_inputs, distribution, rng_value, draws}
distribution: {event: p},  Σ p = 1 (±1e-9), claves ∈ Event
rng_value ∈ [0, 1)                (uniform 0-100 normalizado /100)
draws: [{step, value[, threshold]}], orden real de consumo
```

**Implementación.**

- `calculator.py`: nueva pública `calculate_play_outcome_with_trace(...) ->
  TracedPlay`. `_resolve_play_outcome` / `_calculate_take_outcome` /
  `_calculate_contact_outcome` aceptan `_trace` opcional. `calculate_play_outcome`
  queda intacta y **bit-exacta** (mismos draws, mismo orden). Distribución
  final ex-ante calculada SIN consumir RNG: TAKE binaria; swing = whiff / foul
  / 6 clases BIP (`_bip_class_distribution`, umbrales HR>96, 3B 93-96,
  2B 85-93, 1B 63-85, OG 25-63, OF≤25). El `rng_value` guardado es el draw
  DECISIVO del resultado.
- `tactical_actions.py`: `resolve_bunt(..., _trace=None)`; un solo draw.
- `pitch_telemetry.py`: `pitch_family_for_runtime(pitch_type)` — mapeo runtime
  → `PitchFamily` (desconocido → OTHER; nunca se inventa familia).
- `game_stats.py` + `alembic 0044`: `game_event_logs.sequence_no` +
  `UniqueConstraint(game_id, sequence_no)`. `sequence_no` = ordinal contiguo
  del evento de box score (1, 2, 3, …), NO un contador por pitch.
- `record_game_event(...)`: persiste `plate_appearance_id`, `engine_version`,
  `sequence_no`.
- `game_actions.resolve_swing`: captura PRE-pitch (conteo/outs/PA id/pitch nº),
  resuelve con trace, escribe el `PitchEventLog` (paso 6.5) y sella el
  `GameEventLog` terminal con PA id + `engine_version=ENGINE_BUILD` +
  `sequence_no`. La identidad de PA (`pa_<hex12>`) se resetea al cerrar el PA.

**Resultados / verificación.**

- `test_calculator_trace.py` (8): bit-exactitud trace vs producción,
  Σ distribución = 1, IBB → `{BALL: 1.0}`, partición BABIP, `rng_value ∈ [0,1)`
  y coherencia draw↔resultado, frecuencia empírica ≈ analítica (N=20 000).
- `tests/contract/test_pitch_telemetry_contract.py` (2): un `PitchEventLog`
  honesto por swing resuelto; identidad de PA estable y distinta entre PAs;
  pitches contiguos 1..k; `GameEventLog` versionado con `sequence_no` 1..N y PA
  id = último pitch del PA.
- `test_pitch_telemetry.py` (+8): `pitch_family_for_runtime`.
- `fixtures.SCHEMA_HEAD` `0043 -> 0044`; `test_schema_head_congelado_es_0044`.
- Suite completa: **1048 passed**.

**Decisión.** `sequence_no` es el ordinal contiguo del evento de box score, no
un contador por pitch (de lo contrario el stream de eventos tendría huecos
inexplicables). Nada de telemetría fabricada: cada campo es un dato que el
engine ya usó.

**Qué NO quedó demostrado.** `TELEMETRY-PITCH-001` sigue parcial: el pitch log
cubre cada swing/take/bunt resuelto por `resolve_swing`, pero no eventos
generados fuera de él (robos, balks, toma forzada) ni la reconciliación
evento ↔ estado ↔ box score. `TELEMETRY-DOMAIN-001` (alineación de
`BatterApproach`) quedó abierto, resuelto en P5-B.

**Siguiente bloque permitido.** P5-B (dominio `BatterApproach`) y el resto de
Telemetry v2.

**Commit(s).** P5-A (`365e849`, `RUNTIME-TELEMETRY P5-A`), junto a los tests
nuevos.

### P5-B --- dominio `BatterApproach` (TELEMETRY-DOMAIN-001) --- CERRADO

**Problema / finding.** `TELEMETRY-DOMAIN-001`: el log sólo escribía
`REACT`/`TAKE` e ignoraba por completo `guessed_pitch`. `approach_match`
era siempre NULL. El dominio V1 (`BatterApproach` =
FASTBALL/BREAKING/REACT/TAKE) no se derivaba de la decisión real del bateador
(`swing_type` + `guessed_pitch`), así que la apuesta del bateador se perdía.

**Hipótesis.** La decisión del runtime se traduce al dominio V1 sin fabricar:
la apuesta a un lanzamiento concreto es una apuesta de **familia**
(FASTBALL/BREAKING); el resto es REACT; TAKE es TAKE. El acierto del approach
se mide por familia (nivel V1), y el acierto **exacto** del motor pre-V1
(`guessed_pitch == pitch_type`) queda reconstruible desde `matchup_inputs`.

**Contratos prefijados.**

``` text
batter_approach_for_runtime(swing_type, guessed_pitch) -> BatterApproach
    TAKE                              -> TAKE
    familia(guessed_pitch)=FASTBALL   -> FASTBALL
    familia(guessed_pitch)=BREAKING   -> BREAKING
    sin guess / OFFSPEED / unknown    -> REACT
approach_match_for_runtime(approach, actual_pitch) -> bool | None
    FASTBALL / BREAKING -> familia(actual_pitch) == approach
    REACT / TAKE        -> None   (sin acierto binario)
matchup_inputs ahora incluye guessed_zone / guessed_pitch / actual_zone /
actual_pitch / swing_type (la decisión que el engine consumió)
```

**Implementación.**

- `pitch_telemetry.py`: dos helpers PUROS `batter_approach_for_runtime` y
  `approach_match_for_runtime` (una sola fuente de verdad del dominio).
- `calculator.py`: el trace `matchup_inputs` añade `guessed_zone` /
  `guessed_pitch` (decisión consumida por el motor para zone/pitch match).
- `game_actions._record_pitch_telemetry`: recibe `guessed_pitch`, deriva
  `batter_approach` y `approach_match` con los helpers, persiste el
  `matchup_inputs` COMPLETO (antes se truncaba a atributos y se perdía la
  decisión) y propaga `approach_match` al builder (bug de P5-A: se calculaba
  pero no se enviaba).

**Decisión.** El `approach` V1 es **por familia**; `approach_match` es acierto
de familia, NO el reward del motor. El reward exacto del engine se reconstruye
desde `matchup_inputs` (`guessed_pitch` vs `actual_pitch`). No se mezclan porque
el modelo V1 abstrae el tipo concreto a familia; registrarlos juntos haría
creer que un acierto de familia fue premiado por el motor.

**Resultados / verificación.**

- `test_pitch_telemetry.py` (+16): tablas del mapeo de approach (FASTBALL/
  BREAKING/REACT/TAKE, OFFSPEED→REACT, unknown→REACT) y del acierto por familia.
- `test_calculator_trace.py` (+1): `matchup_inputs` expone la decisión y el
  contexto del pitch.
- `test_pitch_telemetry_contract.py` (+3 parametrizados): sobre la API real,
  `guessed_pitch="4-SEAM"→FASTBALL`, `"SLIDER"→BREAKING` (con `approach_match`
  bool coherente con la familia real) y `"CHANGE"→REACT` (`approach_match`
  NULL); la decisión cruda queda en `matchup_inputs`.
- Suite completa: **1068 passed**.

**Qué NO quedó demostrado.** La reconciliación evento ↔ estado ↔ box score y
los pitches no resueltos por el bateador siguen abiertos (`TELEMETRY-PITCH-001`,
P5-C / Paso 7).

**Siguiente bloque permitido.** P5-C (reconciliación `TELEMETRY-PITCH-001`) y
el resto de Telemetry v2.

**Commit(s).** P5-B (`RUNTIME-TELEMETRY P5-B`).

## Paso 7 --- Reconciliation

Demostrar:

``` text
event stream
↔ persisted state
↔ box score / stats
```

## Paso 8 --- Headless simulator

Simulación determinista sin UI/WebSocket:

-   seeds reproducibles;
-   grandes poblaciones;
-   comparación entre perfiles;
-   comparación entre versiones;
-   balance automatizado.

## Paso 9 --- Analytics

Primeros productos:

``` text
game summary
matchups
team duels
pitcher/batter outcomes
fatigue curves
approach effectiveness
rating expression
```

Endpoints candidatos:

``` text
/games/{id}/events
/games/{id}/timeline
/games/{id}/integrity

/analytics/games/{id}/summary
/analytics/matchups
/analytics/teams/{team_id}/duels
```

------------------------------------------------------------------------

# 33. Roadmap posterior: economía y packs

Cadena:

``` text
CardCatalog ACTIVE
        ↓
PackDefinitionVersion
        ↓
Pool / Odds
        ↓
OwnedPack
        ↓
PackOpening
        ↓
Collection
        ↓
Lineup
        ↓
Gameplay
        ↓
Telemetry
        ↓
Analytics
```

Principio:

``` text
ACTIVE catalog = universo publicable
ACTIVE catalog ≠ PackDefinition
```

Fases posteriores:

1.  acquisition inventory;
2.  ledger/economy;
3.  rewards;
4.  `PackDefinition`;
5.  store/offers;
6.  `OwnedPack` / opening;
7.  `StarterPolicy`;
8.  economic telemetry;
9.  Economy Simulator;
10. balance integrado.

------------------------------------------------------------------------

# 34. Decisiones congeladas

No reabrir sin evidencia nueva.

## Fatigue

``` text
9-inning threshold = 100
curve = SMOOTH-0.55-F35

CPU:
HARD   1.20
MEDIUM 1.35
EASY   1.50
```

## Plate Discipline

``` text
TAKE base  = .30
TAKE floor = .20
TAKE ceil  = .85
Foul       = .45
```

## Stuff

``` text
semantics = contact-quality suppression
baseline  = 70
k         = .30
alpha     = .50
```

## Roster

``` text
Roster registered at game creation is frozen.
Owned ≠ registered.
```

## Transactions

``` text
commit before WebSocket publish
```

## Repository semantics

``` text
No global ACTIVE filtering in historical repositories.
```

------------------------------------------------------------------------

# 35. Commits de referencia

``` text
4b852d5  fix(gameplay): make broadcasts transaction-safe
a1323cb  fix(gameplay): freeze game rosters at session creation
0455841  fix(gameplay): apply fatigue to pitch-specific attributes
d8c8804  feat(gameplay): implement calibrated fatigue policy v2
125b8b6  refactor(frontend): remove obsolete fatigue UI model

740b6a5  LAB calculator override bridge
a9e17ab  discipline PROD vs B3-C1
8390bf1  discipline robustness
876967c  clamp sweep
84cee31  plate-discipline production promotion
408722d  production acceptance

bee3bc6  CALIBRATED-BASELINE-v1

f0584aa  003B-1 Stuff semantics
a582518  003B-2 Stuff vs VEL/MOV
c56d1d8  003B-3 Stuff coefficient
213b3a8  003B-4 Power × Stuff
5eb8352  003B-5A Stuff fatigue semantics

512f5bc  feat(gameplay): integrate Stuff into contact quality
6015b50  docs(gameplay): close Stuff integration acceptance

84df0a3  DATA-STUFF-001A audit + contracts S1-S5
f85d645  DATA-STUFF-001B-1 materialize Stuff on publish
27f2e31  DATA-STUFF-001B-2 controlled Stuff backfill
fc890ec  close DATA-STUFF-001, open Clutch

1bb2e8d  GAMEPLAY-RATING-002 decision A: Clutch neutral 70

4e1438c  DATA-AUDIT-001: Position.PITCHER ('P') es lanzador
f203a54  GAMEPLAY-PROVENANCE-001: la partida versiona catalogo/ratings/rules/engine (P4)
e79c1eb  alembic 0001/0010 DDL-only idempotentes
365e849  RUNTIME-TELEMETRY P5-A: identidad de PA, versionado y wiring del pitch log
```

Actualizar hashes si alguno fue amendado.

------------------------------------------------------------------------

# 36. Próximo checkpoint exacto

``` text
DATA-AUDIT-001
ROLE-SHAPE AUDIT: vision / velocity / movement
```

Cerrado sin abrir: `DATA-STUFF-001A/001B`, y `GAMEPLAY-RATING-002`
(caracterizado, decisión A, deferred).

### Por qué este bloque y no otro

`card_catalog.py` materializa los N/A del perfil con `or 0` en seis
columnas. Stuff y Clutch ya están corregidos. Quedan tres:

``` text
PITCHER.vision      404 cartas en 0    (lo consumía vision sí: VISION_TAKE_WEIGHT)
BATTER.velocity     402 cartas en 0
BATTER.movement     402 cartas en 0
```

Diferencia con el caso de Clutch, y es lo que lo hacía más urgente:
Clutch no lo lee nadie, así que su `0` era inerte. `vision` **sí**
pesa en la rama TAKE del resolver.

La premisa de este bloque ("hoy es inalcanzable, un pitcher no batea")
**era falsa.** Sí había camino, y por un motivo que no era de datos.

### Primera consulta — respondida

``` text
¿Existe algún camino por el que un PITCHER entre como batter_attrs
o un BATTER como pitcher_attrs?

   publicación path
    → roster registration / lineup construction
    → pitcher-batter substitution
    → emergency / extra-inning / interleague rules
```

**Sí, y por 403 cartas.** Trazado completo:

| Punto de entrada | Validación | Veredicto |
| --- | --- | --- |
| Lineup humano | `game_session_service.py:69` `is_batter` | acepta |
| Lineup CPU | `game_session_service.py:237` `is_batter` | acepta |
| Pitcher inicial humano | `game_session_service.py:91` `is_pitcher` | rechaza |
| Bullpen humano | `bullpen.py:117` `is_pitcher` | rechaza |
| Bullpen CPU | `game_actions.py:462` `is_pitcher` | rechaza |
| `active_pitcher` → attrs | `game_actions.py:299` por id | sin check |
| `gameplay.py:677` (robo) | lee `state["active_pitcher"]` | slot ya validado |

Todas las validaciones eran correctas. El bug estaba un nivel más arriba:
`Position.is_pitcher` no incluía `Position.PITCHER` (`"P"`), así que las
403 cartas `role=PITCHER` / `position='P'` devolvían `is_batter=True` y
**cualquier lineup las aceptaba** con `vision=0, contact=0, power=0`.

Es decir: los guards de rol eran sólidos, la clasificación del enum no.
Un guard no puede validar un predicado mal definido.

Fix y verificación en §Paso 4. Sin cambios en vision/velocity/movement.

### Después

``` text
si no hay camino:
    → corregir por simetría con Clutch, sin urgencia,
      con el mismo patrón (constante canónica + validación)
si hay camino:
    → corregir y auditar alcance real antes de aceptar
```

Restricciones heredadas:

``` text
NO tocar Clutch (cerrado con decisión A)
NO introducir coeficientes sin fuente
NO reescribir catálogos históricos
```

------------------------------------------------------------------------

# 37. Estado resumido

``` text
ROSTER / OWNERSHIP          CLOSED
CPU CATALOG SCOPING         CLOSED
TX / WEBSOCKET              CLOSED
FATIGUE PROPAGATION         CLOSED
FATIGUE POLICY v2           CLOSED
CPU FATIGUE STRATEGY        CLOSED
FATIGUE UI                  CLOSED
PLATE DISCIPLINE            CLOSED
CALIBRATED BASELINE         CLOSED
STUFF SEMANTICS             CLOSED
STUFF MAGNITUDE             CLOSED
STUFF × POWER               CLOSED
STUFF × FATIGUE             CLOSED
STUFF PROD ACCEPTANCE       CLOSED
STUFF DATA PROPAGATION      CLOSED   (001A + 001B)
CLUTCH                      DEFERRED (placeholder, sin efecto)

DATA-AUDIT-001              CLOSED  (alcance: Position.PITCHER fuera de is_pitcher)
PROVENANCE                  CLOSED  (P4 / GAMEPLAY-PROVENANCE-001)
RUNTIME TELEMETRY           P5-A/P5-B CLOSED  (PA identity + versioning + pitch log wiring + BatterApproach domain); P5-C NEXT
RECONCILIATION              PENDING
HEADLESS SIMULATOR          PENDING
ANALYTICS                   PENDING
ECONOMY / PACK DESIGN       LATER
```

------------------------------------------------------------------------

# 38. Regla para mantener este documento vivo

Cada bloque futuro debe registrar:

1.  Problema / finding.
2.  Hipótesis.
3.  Contratos prefijados.
4.  Experimento o implementación.
5.  Resultados.
6.  Decisión.
7.  Commit(s).
8.  Estado `OPEN / CLOSED / PASS / FAIL`.
9.  Qué **no** quedó demostrado.
10. Siguiente bloque permitido.

Esto conserva la trazabilidad y evita convertir decisiones
experimentales en números mágicos sin contexto.
