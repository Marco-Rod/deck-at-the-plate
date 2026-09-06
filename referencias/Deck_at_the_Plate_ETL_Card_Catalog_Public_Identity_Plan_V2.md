# Deck at the Plate — ETL, Card Catalog, CPU Rosters & Public Identity Plan V2

**Fecha:** 05 septiembre 2026  
**Objetivo:** reemplazar progresivamente `seed_mlb_2026.py` como fuente de verdad y definir una primera carga completa y limpia que conecte datos reales MLB/Statcast con analytics, identidad pública ficticia, catálogo de cartas, equipos CPU, starter packs e inventario.

---

## 1. Principio central

Deck at the Plate debe separar claramente:

```text
SOURCE / REAL DATA
```

de:

```text
GAME / PUBLIC DATA
```

La capa SOURCE puede conservar IDs y nombres reales para sincronización, auditoría y trazabilidad.

La capa GAME no debe depender públicamente de nombres, marcas, logos o identidades reales.

---

## 2. Arquitectura objetivo

```text
                        EXTERNAL SOURCES
                  MLB Stats API / Statcast
                             │
                             ▼
                    SOURCE / INTERNAL
              ┌─────────────────────────────┐
              │ SourceTeam                  │
              │ Player                      │
              │ PlayerTeamStint             │
              │ SourceRosterSnapshot        │
              │ RawPitchEvent               │
              └─────────────────────────────┘
                             │
                             ▼
                        ANALYTICS
              ┌─────────────────────────────┐
              │ Batter/Pitcher Season Stats │
              │ Zone Profiles               │
              │ Pitch Profiles              │
              │ Handedness Splits           │
              │ H2H                         │
              └─────────────────────────────┘
                             │
                             ▼
                    GAME IDENTITY LAYER
              ┌─────────────────────────────┐
              │ Team                        │
              │ GamePlayerIdentity          │
              │ Source → Game Team Mapping  │
              └─────────────────────────────┘
                             │
                             ▼
                      CARD GENERATION
              ┌─────────────────────────────┐
              │ CardGenerationProfile       │
              │ Rating Model                │
              │ CardCatalog                 │
              │ PlayerCardModel             │
              └─────────────────────────────┘
                             │
                ┌────────────┼─────────────┐
                ▼            ▼             ▼
             CPU Teams      Packs      User Inventory
                │            │             │
                └────────────┴──────┬──────┘
                                    ▼
                                 GAMEPLAY
                                    │
                                    ▼
                              PvP en el futuro
```

---

## 3. Identidad: regla de oro

```text
MLB IDs
=
identidad externa para sincronización

UUIDs internos
=
identidad de dominio y gameplay
```

Ejemplo:

```text
Player
id = UUID interno
mlb_id = ID externo MLB

SourceTeam
id = UUID interno
external_id = mlb_team_id

Team
id = UUID interno de Deck at the Plate
```

Nunca usar nombres, ciudad o abreviatura como llave de sincronización.

---

## 4. `Player`

`Player` representa a la persona real dentro de la capa técnica.

Campos conceptuales:

```text
id UUID PK
mlb_id UNIQUE
source_name
bats
throws
primary_position
created_at
updated_at
```

`source_name` puede existir para:

- debugging;
- QA;
- comparación con la fuente;
- auditoría.

Pero no debe ser la identidad mostrada en gameplay.

---

## 5. `SourceTeam`

Crear una entidad separada para representar equipos provenientes de MLB.

```text
SourceTeam
----------
id UUID PK
source
external_id
source_name
source_abbreviation
league
division
is_active
created_at
updated_at
```

Constraint:

```text
UNIQUE(source, external_id)
```

Para MLB:

```text
source = MLB
external_id = mlb_team_id
```

---

## 6. `Team`

`Team` representa una franquicia pública de Deck at the Plate.

```text
Team
----
id UUID PK
name
abbreviation
city
slug
primary_color
secondary_color
logo_asset
is_active
created_at
updated_at
```

Los nombres, abreviaturas, logos y assets deben ser propios del juego.

---

## 7. Mapping Source Team → Game Team

Agregar:

```text
SourceTeamGameTeamMapping
-------------------------
id UUID
source_team_id FK
team_id FK
valid_from
valid_to nullable
created_at
```

En V1 tendremos una relación activa 1:1:

```text
SourceTeam A
↓
Team A de Deck at the Plate
```

Esto permite que los movimientos reales se reflejen correctamente sin exponer la identidad MLB.

---

## 8. `GamePlayerIdentity`

Crear:

```text
GamePlayerIdentity
------------------
id UUID PK
player_id FK UNIQUE
display_first_name
display_last_name
display_name
default_jersey_number
created_at
updated_at
```

La identidad pública debe persistirse.

Ejemplo:

```text
Player
mlb_id = 123456
source_name = [nombre fuente]

↓ one-to-one

GamePlayerIdentity
display_name = Marcus Stone
```

En futuros ETL el mismo `Player` conserva la misma identidad pública.

---

## 9. Equipo público de un jugador

La resolución correcta será:

```text
Player
↓
PlayerTeamStint
↓
SourceTeam
↓
SourceTeamGameTeamMapping
↓
Team
```

Nunca:

```text
source team name
→ UI
```

---

## 10. Trades y movimientos

Si la fuente registra:

```text
Player X
SourceTeam A → SourceTeam B
```

se actualiza:

```text
PlayerTeamStint
```

y el mapping resuelve:

```text
SourceTeam B
→ Game Team B
```

La identidad pública del jugador no se regenera.

---

## 11. `PlayerTeamStint`

Responsabilidad:

```text
¿qué relación tuvo el jugador con el equipo fuente y durante qué periodo?
```

Debe continuar usando identidad SOURCE.

Ejemplo conceptual:

```text
player_id
source_team_id
season
start_date
end_date
is_current
```

---

## 12. Roster snapshots

Para reflejar exactamente quién integra el roster de 26 en una fecha, agregar:

```text
SourceTeamRosterSnapshot
------------------------
id
source_team_id
season
as_of_date
roster_type
source
created_at
```

y:

```text
SourceTeamRosterMember
----------------------
roster_snapshot_id
player_id
status
position
jersey_number
```

Constraint:

```text
UNIQUE(roster_snapshot_id, player_id)
```

---

## 13. Por qué snapshot y no sólo `PlayerTeamStint`

`PlayerTeamStint` responde:

```text
¿para qué equipo ha jugado?
```

El snapshot responde:

```text
¿quién estaba en el roster activo en una fecha concreta?
```

Los equipos CPU deben partir del roster snapshot.

---

## 14. Statcast / RAW

El pipeline debe continuar:

```text
Statcast
↓
RawPitchEvent
```

Llave natural:

```text
(game_pk, at_bat_number, pitch_number)
```

Idempotencia:

```text
same key + same hash
→ no-op

same key + different hash
→ controlled update

new key
→ insert
```

---

## 15. Bulk UPSERT

V1 aprobado:

```text
probe acotado por chunks
↓
clasificar inserted / updated / unchanged
↓
ON CONFLICT DO UPDATE por lote
```

Ventajas:

- contadores exactos;
- tests SQLite compatibles;
- PostgreSQL eficiente;
- evita dependencia de `xmax`.

---

## 16. Safe chunking

La importación principal debe usar el path protegido por:

```text
STATCAST_CHUNK_DAYS
STATCAST_SAFE_ROW_THRESHOLD
```

y subdividir rangos si una respuesta supera el umbral seguro.

---

## 17. Analytics

Toda la capa analytics deriva exclusivamente de `RawPitchEvent`.

No debe hacer requests externos.

Debe producir:

```text
BatterSeasonStats
PitcherSeasonStats

BatterZoneProfile
PitcherZoneProfile

BatterPitchFamilyProfile
PitcherPitchProfile

HandednessSplits

H2H
```

---

## 18. H2H y samples pequeños

No usar frecuencias crudas como probabilidades directas.

Aplicar shrinkage/regresión hacia muestras más generales:

```text
MLB average
↓
player overall
↓
handedness
↓
pitch family
↓
zone
↓
pitch + zone
↓
H2H
```

La especificidad aporta información, no sustituye automáticamente a los niveles anteriores.

---

## 19. `CardGenerationProfile`

Es el puente entre analytics y videojuego.

```text
Analytics
↓
Rating Model
↓
CardGenerationProfile
```

Debe almacenar:

```text
player_id
season
data_start_date
data_end_date
rating_model_version
sample/confidence metadata

contact
power
vision
clutch

velocity
control
movement

pitch ratings
overall
rarity candidate
```

No publicar una carta directamente desde Statcast.

---

## 20. Rating Model

Debe estar versionado:

```text
ratings-1.0
ratings-1.1
ratings-2.0
```

El mismo dataset con dos modelos distintos debe poder producir perfiles distintos de forma trazable.

---

## 21. `PlayerCardModel`

Agregar relación explícita:

```text
player_id FK
game_identity_id FK
generation_profile_id FK
catalog_id FK
team_id FK
```

Además:

```text
season
edition_type
edition_version
is_pack_eligible
published_at
```

La carta debe hacer snapshot de:

```text
display_name
jersey_number
position
team
ratings
repertoire
```

No debe copiar identidad SOURCE a contratos públicos.

---

## 22. Carta publicada = objeto inmutable

Ejemplo:

```text
Ohtani-source → Game Player X
BASE 2026 V1
overall 94
```

Si cambia el rating:

```text
BASE 2026 V2
overall 96
```

crear nueva versión.

No modificar silenciosamente una carta que ya posee un usuario.

---

## 23. `CardCatalog`

Agregar desde V1:

```text
CardCatalog
-----------
id UUID
season
edition_type
version
status
rating_model_version
data_end_date
created_at
published_at
```

Estados:

```text
BUILDING
VALIDATING
ACTIVE
RETIRED
FAILED
```

Constraint lógico:

```text
un solo ACTIVE por season + edition_type
```

---

## 24. Por qué `CardCatalog`

Permite publicar la primera carga de forma atómica:

```text
create catalog BUILDING
↓
generate cards
↓
QA
↓
VALIDATING
↓
activate
↓
ACTIVE
```

Si algo falla, el catálogo anterior continúa operativo.

---

## 25. Catálogo limpio V1

Convención inicial:

```text
season = 2026
edition_type = BASE
version = 1
rating_model_version = ratings-1.0
```

Las cartas actuales generadas por seed deben marcarse:

```text
LEGACY
is_pack_eligible = false
```

hasta completar la transición.

---

## 26. `Team.cards`

Ya no debe significar:

```text
roster CPU actual
```

Debe significar:

```text
cartas históricamente asociadas a esa franquicia
```

Porque en el futuro tendremos:

```text
BASE
MVP
All-Star
Postseason
Special
```

para un mismo jugador.

---

## 27. CPU roster

V1 puede resolverse de forma derivada:

```text
latest SourceTeamRosterSnapshot
↓
SourceTeamGameTeamMapping
↓
Player
↓
GamePlayerIdentity
↓
ACTIVE BASE CardCatalog
↓
PlayerCardModel
↓
CPU lineup
```

No es obligatorio persistir `CpuTeamRoster` todavía.

---

## 28. CPU y usuario consumen el mismo catálogo

No crear:

```text
CPUPlayerCard
UserPlayerCard
```

Ambos consumen:

```text
PlayerCardModel
```

Usuario:

```text
UserCardInventory
→ card_id concreto
```

CPU:

```text
current roster player
→ card from ACTIVE BASE catalog
```

---

## 29. Starter pack

El onboarding no debe hacer requests externos.

Flujo:

```text
User registers
↓
chooses favorite Team
↓
PackService
↓
ACTIVE BASE CardCatalog
↓
eligible cards
↓
starter pack
↓
UserCardInventory
↓
initial lineup
```

---

## 30. Elegibilidad de packs

Consultar:

```text
catalog.status = ACTIVE
edition_type = BASE
is_pack_eligible = true
```

Evitar:

- LEGACY;
- test cards;
- retired catalogs;
- special editions no habilitadas.

---

## 31. Starter pack y franquicia favorita

El starter debe usar el `Team` ficticio elegido por el usuario.

Para encontrar jugadores:

```text
Team
↓
SourceTeamGameTeamMapping
↓
active source roster
↓
Player
↓
ACTIVE catalog cards
```

Así el usuario nunca necesita conocer la franquicia real de origen.

---

## 32. PackService

Debe seguir desacoplado:

```text
PackService
→ DB catalog
```

Nunca:

```text
PackService
→ MLB Stats API
```

ni:

```text
PackService
→ Statcast
```

---

## 33. Inventario

`UserCardInventory` mantiene:

```text
user_id
card_id
```

No duplicar atributos dentro del inventario.

La edición concreta queda congelada mediante `card_id`.

---

## 34. Matchup Engine

La carta expresa fuerza general visible.

El motor profundo usa:

```text
player_id
↓
Analytics
↓
zones
pitch family
handedness
H2H
context
fatigue
tactical modifiers
```

Por tanto:

```text
public game identity
≠
statistical identity
```

pero ambas se conectan a través de `player_id`.

---

## 35. APIs públicas

Los endpoints de gameplay no deben exponer por defecto:

```text
mlb_id
mlb_team_id
source_name
source_team_name
raw Statcast IDs
```

Schemas públicos:

```text
card_id
display_name
team
number
position
ratings
rarity
edition
```

Schemas internos/admin pueden incluir información SOURCE.

---

## 36. Generación de identidades ficticias

Agregar comando:

```bash
python -m etl.cli generate-game-identities   --season 2026   --missing-only
```

Reglas:

- idempotente;
- sólo crear identidades faltantes;
- persistirlas;
- no regenerarlas;
- evitar nombres ofensivos;
- evitar duplicados evidentes en un roster;
- evitar nombres reales conocidos cuando sea posible.

---

## 37. Franquicias ficticias

No deben generarse aleatoriamente durante ETL.

Mantener configuración versionada:

```text
game_franchises.yaml
```

Ejemplo conceptual:

```yaml
source_team_external_id: 119
game_team:
  slug: west-coast-stars
  name: West Coast Stars
  abbreviation: WCS
```

Esto permite revisar manualmente nombres, colores y assets.

---

## 38. Logos y assets

No descargar logos desde MLB en el pipeline.

Los assets públicos deben ser propios y administrados por Deck at the Plate.

`Team.logo_asset` sólo referencia recursos internos.

---

## 39. Comandos definitivos

### Source teams

```bash
python -m etl.cli sync-source-teams   --source MLB   --season 2026
```

### Game franchise mappings

```bash
python -m etl.cli sync-game-team-mappings
```

### Rosters

```bash
python -m etl.cli sync-rosters   --season 2026
```

### Public identities

```bash
python -m etl.cli generate-game-identities   --season 2026   --missing-only
```

### RAW

```bash
python -m etl.cli import-statcast   --from YYYY-MM-DD   --to YYYY-MM-DD
```

### Analytics

```bash
python -m etl.cli build-analytics   --season 2026   --data-end-date YYYY-MM-DD
```

### Card profiles

```bash
python -m etl.cli generate-card-profiles   --season 2026   --data-end-date YYYY-MM-DD   --rating-model ratings-1.0
```

### Validate profiles

```bash
python -m etl.cli validate-card-profiles   --season 2026
```

### Publish catalog

```bash
python -m etl.cli publish-card-catalog   --season 2026   --edition BASE
```

### Validate CPU rosters

```bash
python -m etl.cli validate-cpu-rosters   --season 2026
```

### Validate pack pool

```bash
python -m etl.cli validate-pack-pool   --season 2026
```

---

## 40. `run` incremental

`run` diario/incremental no debe consultar los 30 rosters.

Debe hacer:

```text
Statcast
↓
distinct batter/pitcher IDs
↓
resolve missing Players by MLB ID
↓
RawPitchEvent
↓
Analytics
```

No debe publicar cartas automáticamente.

---

## 41. League provisioning

La sustitución real del seed es un workflow distinto:

```text
sync-source-teams
↓
sync-game-team-mappings
↓
sync-rosters
↓
generate-game-identities
↓
import-statcast
↓
build-analytics
↓
generate-card-profiles
↓
QA
↓
publish-card-catalog
↓
validate-cpu-rosters
↓
validate-pack-pool
```

---

## 42. Qué deja de hacer `seed_mlb_2026.py`

Debe dejar de:

- sincronizar liga productiva;
- ser fuente de rosters;
- generar ratings definitivos;
- crear el catálogo productivo;
- borrar inventarios;
- borrar/regenerar todas las cartas;
- controlar contenido CPU.

Puede permanecer temporalmente para:

- fixtures;
- desarrollo local;
- tests;
- legacy compatibility.

---

## 43. Migraciones necesarias

Orden sugerido.

### Migration 1

Crear:

```text
source_teams
```

### Migration 2

Adaptar:

```text
teams
```

como franquicia pública del juego.

### Migration 3

Crear:

```text
source_team_game_team_mappings
```

### Migration 4

Actualizar `PlayerTeamStint` para apuntar explícitamente a `SourceTeam` si aún apunta a `Team`.

### Migration 5

Crear:

```text
source_team_roster_snapshots
source_team_roster_members
```

### Migration 6

Crear:

```text
game_player_identities
```

### Migration 7

Crear:

```text
card_catalogs
```

### Migration 8

Agregar a `player_cards`:

```text
player_id
game_identity_id
generation_profile_id
catalog_id
season
edition_type
edition_version
is_pack_eligible
published_at
```

### Migration 9

Backfill y legacy classification.

---

## 44. Backfill de equipos actuales

No borrar todo de golpe.

```text
existing Team rows
↓
classify legacy
↓
create SourceTeam
↓
create Game Team
↓
create mapping
↓
backfill foreign keys
↓
validate
↓
remove old assumptions
```

---

## 45. Backfill de cartas actuales

```text
legacy PlayerCardModel
↓
resolve Player where possible
↓
resolve GamePlayerIdentity
↓
resolve Game Team
↓
assign LEGACY catalog/edition
↓
is_pack_eligible = false
```

Nunca usar exclusivamente nombre para resolver si hay un ID más estable.

---

## 46. Primera carga limpia

La primera carga real nueva debe quedar completamente separada de legacy:

```text
LEGACY
```

vs.

```text
BASE 2026 V1
```

El onboarding nuevo sólo se cambia al catálogo V1 cuando pase QA.

---

## 47. Flujo de primera carga completa

```text
1. SourceTeams
2. Game Teams
3. mappings
4. source rosters
5. Players
6. GamePlayerIdentity
7. RawPitchEvent
8. Analytics
9. CardGenerationProfile
10. CardCatalog BUILDING
11. PlayerCardModel
12. QA
13. CardCatalog ACTIVE
14. CPU rosters
15. starter packs
16. normal packs
```

---

## 48. Validation Gate — Source

Antes de continuar:

- [ ] existen 30 SourceTeam esperados;
- [ ] `external_id` es único;
- [ ] ningún Player se identifica por nombre;
- [ ] `Player.mlb_id` es único;
- [ ] rosters resuelven correctamente;
- [ ] PlayerTeamStint no tiene huérfanos;
- [ ] snapshots tienen fechas correctas;
- [ ] rerun no crea duplicados.

---

## 49. Validation Gate — Game Identity

- [ ] existen 30 Team públicos;
- [ ] cada uno tiene identidad ficticia;
- [ ] los 30 SourceTeam tienen mapping;
- [ ] no hay mappings activos duplicados;
- [ ] todos los jugadores elegibles tienen GamePlayerIdentity;
- [ ] `display_name` no es vacío;
- [ ] rerun de identidad crea 0 nuevas cuando ya están completas;
- [ ] no se reemplazan nombres existentes.

---

## 50. Validation Gate — RAW

- [ ] importación funciona por safe chunks;
- [ ] segunda importación exacta produce 0 duplicados;
- [ ] correction update funciona;
- [ ] counters son exactos;
- [ ] FAILED llega al CLI;
- [ ] PARTIAL se usa cuando corresponde.

---

## 51. Validation Gate — Analytics

- [ ] analytics lee sólo RAW;
- [ ] sample sizes son consistentes;
- [ ] rates están entre 0 y 1;
- [ ] profiles 1–9 son válidos;
- [ ] pitch family mapping es válido;
- [ ] H2H aplica shrinkage;
- [ ] samples pequeños usan fallback;
- [ ] missing analytics se reportan explícitamente.

---

## 52. Validation Gate — Cards

- [ ] cada carta tiene `player_id`;
- [ ] cada carta tiene GamePlayerIdentity;
- [ ] cada carta tiene Game Team;
- [ ] cada carta pertenece a CardCatalog;
- [ ] no hay `source_name` en snapshot público;
- [ ] no hay nombres MLB en snapshot público;
- [ ] overall y atributos están en rango;
- [ ] repertorios son válidos;
- [ ] edition/version es consistente;
- [ ] rerun de misma versión no duplica.

---

## 53. Validation Gate — CPU

- [ ] 30 equipos CPU pueden resolverse;
- [ ] roster activo está disponible;
- [ ] cada jugador elegible encuentra carta BASE activa;
- [ ] lineup puede cubrir posiciones;
- [ ] SP/RP se resuelven;
- [ ] two-way players no duplican identidad;
- [ ] cartas especiales no entran accidentalmente.

---

## 54. Validation Gate — Packs

- [ ] starter pool tiene suficientes cartas;
- [ ] franquicia favorita puede entregar cartas propias;
- [ ] pool externo completa el pack;
- [ ] sólo ACTIVE BASE;
- [ ] sólo pack eligible;
- [ ] legacy excluido;
- [ ] test cards excluidas;
- [ ] UserCardInventory nunca se borra por refresh.

---

## 55. Vertical Slice antes de toda MLB

No cargar todo directamente.

Orden:

```text
Ohtani + Christopher Sánchez
↓
2 SourceTeams
↓
2 Game Teams
↓
2 mappings
↓
GamePlayerIdentity
↓
RAW
↓
Analytics
↓
Profiles
↓
CardCatalog test
↓
CPU roster subset
↓
starter pack test
```

Después:

```text
1 team
↓
2 teams
↓
30 teams metadata/rosters
↓
small Statcast range
↓
full selected window
↓
full catalog
```

---

## 56. Fallback para jugadores sin suficiente muestra

Un jugador activo no debe desaparecer por tener pocos datos.

Fallback jerárquico:

```text
current-season sample
↓
previous-season sample
↓
player broader profile
↓
league prior
```

Agregar una señal:

```text
profile_confidence
```

No usar stats aleatorios como solución productiva.

---

## 57. Two-way players

Una identidad:

```text
Player
```

puede tener:

```text
batter analytics
+
pitcher analytics
```

La carta debe soportar:

```text
BATTER
PITCHER
TWO_WAY
```

sin crear dos personas distintas.

---

## 58. Actualizaciones posteriores

ETL diario:

```text
new RAW
↓
analytics
↓
new CardGenerationProfile drafts
```

Publicación:

```text
manual/scheduled decision
↓
QA
↓
new CardCatalog version
```

No publicar automáticamente cada ETL.

---

## 59. CPU vs usuario al actualizar catálogo

Usuario:

```text
inventory
→ card_id concreto
→ conserva edición
```

CPU:

```text
ACTIVE BASE catalog
→ usa versión actual
```

Packs:

```text
ACTIVE BASE catalog
→ distribuyen versión actual
```

---

## 60. Contrato del juego

El gameplay sólo necesita:

```text
GamePlayerIdentity
Team
PlayerCardModel
Analytics via player_id
```

No necesita saber:

```text
MLB name
MLB team
MLB external IDs
```

---

## 61. Definition of Done — Primera versión limpia

La primera versión completa se considera lista cuando:

- [ ] 30 SourceTeams sincronizados;
- [ ] 30 Game Teams creados;
- [ ] 30 mappings válidos;
- [ ] rosters fuente sincronizados;
- [ ] Player/PlayerTeamStint consistentes;
- [ ] identidades públicas completas;
- [ ] RAW idempotente;
- [ ] analytics reconstruible;
- [ ] CardGenerationProfile generado;
- [ ] CardCatalog BASE 2026 V1 creado;
- [ ] QA superado;
- [ ] catálogo activado atómicamente;
- [ ] 30 CPU teams resolubles;
- [ ] starter pack funciona;
- [ ] normal packs funcionan;
- [ ] legacy no entra en nuevos packs;
- [ ] inventario existente no se destruye;
- [ ] seed deja de ser fuente de verdad;
- [ ] APIs públicas no exponen datos SOURCE;
- [ ] gameplay no hace requests externos;
- [ ] el sistema puede volver a ejecutar el ETL sin duplicar datos.

---

## 62. Resultado final

```text
REAL PLAYER
↓
Player
↓
RawPitchEvent
↓
Analytics
↓
CardGenerationProfile
↓
GamePlayerIdentity + Game Team
↓
CardCatalog
↓
PlayerCardModel
↓
CPU / Packs / Inventory
↓
Gameplay
```

La información real se utiliza como base estadística y de sincronización.

La identidad visible pertenece a Deck at the Plate.

La carta publicada queda versionada y trazable.

El seed deja de ser el mecanismo productivo de poblado.

Este flujo constituye la base recomendada para generar la primera versión completa y limpia de datos.
