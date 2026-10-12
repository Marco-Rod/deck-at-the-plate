# Plan de intervención: ETL de cartas base V1

## Objetivo

Con una base de datos migrada y sin seeds, obtener mediante un solo comando un
catálogo `BASE` activo que permita abrir sobres, armar un lineup y jugar contra
CPU. El flujo será repetible, auditable y no dependerá de los documentos ni
scripts legacy.

Este plan resuelve tres asuntos concretos:

1. Elegir una única ruta de ratings para cartas base.
2. Poder crear el primer catálogo desde cero sin un catálogo previo.
3. Impedir que se active un catálogo que no pueda sostener sobres, un starter
   pack y una partida CPU real.

## Decisiones de alcance

| Decisión | V1 |
| --- | --- |
| Modelo de ratings | Sólo `ratings-2.0`. `ratings-1.0` queda disponible como legado, no como entrada del nuevo comando. |
| Catálogo activo | Un único catálogo `BASE` activo por temporada de referencia. |
| Temporada de gameplay actual | El primer lote debe usar `2026`, porque `GameSessionService` hoy busca esa temporada de forma explícita. |
| Fecha de corte | Obligatoria como `--as-of`; hace reproducible el lote y limita los datos usados. |
| Datos históricos avanzados | Fuera: no se calculan enfrentamientos bateador–pitcher ni momentos para desbloquear V1. |
| Activación | Un candidato nunca pasa a `ACTIVE` hasta aprobar todos los gates. |
| Subconjunto de equipos | Permitido sólo para desarrollo y pruebas; no puede activarse como catálogo V1. |

La parametrización de temporada del gameplay se tratará después como una mejora
acotada de configuración. No se mezclará con el bootstrap del ETL.

## Fronteras: dónde sí tocar y dónde no

### Reutilizar sin reescribir

| Componente | Responsabilidad que se conserva |
| --- | --- |
| `etl/pipelines/metadata.py` | Equipos SOURCE y mapeo a franquicias GAME. |
| `etl/pipelines/statcast.py` | Ingesta de eventos de pitcheo. |
| `etl/pipelines/analytics.py` | Reconstrucción de analytics. |
| `etl/services/player_ratings_as_of.py` | Ratings de población por rol y fecha de corte. |
| `etl/services/ratings2_card_profiles.py` | Perfil de generación desde `PlayerRatings`. |
| `etl/services/card_rating_profiles.py` | Conversión a atributos de carta. |
| `app/services/card_editions.py` | Obtención o creación de la edición `BASE` del sistema. |
| `etl/services/card_catalog.py` | Persistencia y lifecycle de catálogo/carta. |
| `app/services/pack_service.py` | Apertura de sobres. |
| `app/services/game_session_service.py` | Construcción del roster CPU y juego. |

### No tocar en esta intervención

- Fórmulas de `ratings-2.0`, distribuciones, normalizadores o agregaciones de
  analytics. Si un lote revela un problema de balance, se abrirá una tarea de
  política de ratings; no se corrige silenciosamente dentro del orquestador.
- El motor de partido, resolución de pitcheo, tácticas, boosts, mini-temporada,
  H2H histórico y UI de la PWA.
- Migraciones de Alembic y seeds legacy.
- La ruta `ratings-1.0` y la materialización antigua, salvo documentarlas como
  no usadas por V1.

### Archivos nuevos previstos

| Archivo | Propósito |
| --- | --- |
| `backend/etl/pipelines/base_catalog_v1.py` | Orquestador pequeño: coordina etapas existentes, no contiene fórmulas. |
| `backend/etl/validators/catalog_gameplay.py` | Gates puros de jugabilidad de un catálogo candidato. |
| `backend/tests/etl/test_base_catalog_v1.py` | Orden, idempotencia y errores del orquestador. |
| `backend/tests/etl/test_catalog_gameplay_validators.py` | Casos de roster CPU, starter pack y pool. |

### Archivos que se modificarán de forma mínima

| Archivo | Cambio limitado |
| --- | --- |
| `backend/etl/cli.py` | Añadir el subcomando y delegar inmediatamente al pipeline nuevo. Sin lógica de negocio nueva en el CLI. |
| `backend/etl/services/card_catalog.py` | Permitir crear el primer catálogo como `VALIDATING`; delegar gates de juego en el validador nuevo antes de promover. |
| Pruebas existentes de lifecycle/catálogo | Ajustar o ampliar sólo para cubrir el bootstrap y la promoción condicionada. |

`materialize_card_catalog_candidate.py` no será el mecanismo de V1: requiere
un catálogo activo como baseline. No se eliminará ni se forzará a cubrir dos
casos distintos; queda como ruta de migración/reemplazo posterior.

## Flujo definitivo

```text
metadata y franquicias
        ↓
rosters + identidades
        ↓
eventos Statcast hasta --as-of
        ↓
analytics → PlayerRatings (bateador y pitcher, ratings-2.0)
        ↓
edición BASE → perfiles de generación → perfiles de rating
        ↓
catálogo candidato VALIDATING
        ↓
gates de atributos, CPU, starter pack y sobres
        ↓
ACTIVE sólo con --activate y todos los gates aprobados
```

Interfaz propuesta:

```text
python -m etl.cli build-base-catalog \
  --season 2026 \
  --as-of YYYY-MM-DD \
  --activate
```

Sin `--activate`, el resultado siempre queda en `VALIDATING` y entrega el
reporte de gates. Con `--activate`, una falla deja el candidato sin activar y
reporta exactamente qué equipo, posición, rareza o etapa faltó.

## Diseño del bootstrap limpio

`publish_card_catalog` ya puede crear un catálogo cuando no existe uno activo,
pero hoy lo activa inmediatamente. Se añadirá una opción explícita —usada sólo
por el pipeline V1— para conservarlo como `VALIDATING` durante el primer alta.
Después el pipeline ejecutará la promoción ordinaria.

Esto evita dos riesgos:

- No se necesita fabricar un catálogo falso ni usar un seed como baseline.
- Un catálogo vacío, con nueve cartas incompatibles o sin pool de sobres no se
  vuelve activo por el simple hecho de ser el primero.

La edición `BASE` se obtendrá con el servicio existente. Cada etapa deberá
buscar su salida por claves estables (temporada, fecha de corte, edición,
jugador y rol) y actualizarla o reutilizarla. Una segunda ejecución con los
mismos argumentos no podrá duplicar cartas ni perfiles.

## Gates que bloquean activación

| Gate | Regla mínima V1 | Motivo |
| --- | --- | --- |
| Atributos | Cada carta tiene identidad, equipo, posición, valores dentro de rango y atributos requeridos no nulos. | El motor y la UI no reciben cartas incompletas. |
| Roster CPU | Por cada franquicia GAME mapeada: al menos 9 bateadores utilizables y al menos 2 pitchers utilizables. | Una alineación y un bullpen básico pueden construirse. |
| Starter pack | Para cada equipo elegible, ejecutar el selector real `select_starter_cards`; debe devolver 13 cartas únicas, pitcher y C, 1B, 2B, 3B, SS, LF, CF, RF, DH. | Se valida el mismo algoritmo que consume el jugador, no una aproximación por conteo. |
| Sobres | Existen cartas `is_pack_eligible` en las rarezas requeridas por el pool activo. | El onboarding puede otorgar cartas. |
| Idempotencia | Repetir el mismo lote no aumenta indebidamente catálogos, cartas o perfiles. | Operación segura y recuperable. |

El mínimo de dos pitchers permite cambio de pitcher básico. Si el diseño del
juego define un bullpen mayor, esa cifra se elevará mediante una constante de
política versionada, no con números dispersos.

## Orden de implementación

### Paso 1 — Contratos y extracción de validadores

Crear `catalog_gameplay.py` con validadores sin efectos secundarios y pruebas
por fixture. Cambiar los wrappers de catálogo para que los usen. Añadir la
posibilidad de que el primer catálogo permanezca `VALIDATING`.

Durante esta transición, `promote_card_catalog` recibe
`enforce_gameplay_gates=True` para aplicar los gates nuevos. Se mantiene
desactivado por defecto exclusivamente para no reinterpretar los callers y
catálogos legacy; el pipeline `build-base-catalog` de V1 deberá pasarlo siempre
y será la única vía soportada para activar un lote base nuevo.

**Salida verificable:** una promoción falla para roster incompleto, starter pack
imposible o rarezas ausentes; un candidato válido puede promoverse aun si no
había catálogo anterior.

### Paso 2 — Construir el pipeline V1

Crear `base_catalog_v1.py` como una clase/función de orquestación con entradas
explícitas: `season`, `as_of`, equipos opcionales de diagnóstico y `activate`.
Debe llamar servicios existentes y producir un objeto de reporte estructurado.
No debe importar PWA ni el motor de partido.

**Salida verificable:** una prueba con dobles comprueba el orden de las etapas,
la interrupción ante error y que un lote sin `activate` no cambie el catálogo
activo.

**Implementado:** `etl/pipelines/base_catalog_v1.py` expresa este flujo y
devuelve un reporte estructurado. Aún no se expone por CLI: primero se prueba
directamente como contrato de orquestación; el siguiente paso será una fachada
CLI mínima. El reporte conserva temporada, corte, catálogo, estado, conteos de
ratings y perfiles, etapas ejecutadas e incidencias; no devuelve entidades ORM
como contrato público.

### Ajuste necesario antes de activar el primer candidato: repertorios

El motor puede seleccionar tipos de pitcheo desde `PlayerCardModel.repertoire`,
pero `ratings-2.0` inicialmente dejaba ese campo vacío. La ruta V1 ahora toma
los `PitcherPitchProfile` ya calculados, traduce códigos Statcast al vocabulario
del motor y guarda hasta cuatro pitcheos por uso. Esta operación no descarga ni
recalcula eventos RAW.

V1 conserva los atributos globales del pitcher para resolver cada pitcheo: aún
no existe una política aprobada que convierta estadísticas por pitch a ratings
de velocidad/control/movimiento. El repertorio sí restringe las opciones de la
CPU a sus tipos reales. La promoción V1 rechaza pitchers sin repertorio válido.

Para actualizar un candidato existente tras desplegar este cambio:

```text
python -m etl.cli sync-catalog-repertoires --catalog-id <catalog-id>
```

### Paso 3 — Exponer una fachada CLI delgada

Añadir `build-base-catalog` al parser existente. El comando valida parámetros,
instancia el pipeline y muestra el reporte; no replica coordinación ni lógica.

**Salida verificable:** `--help` documenta opciones y el comando reporta el ID,
estado, conteos y gates del candidato.

**Implementado:** `python -m etl.cli build-base-catalog --season <temporada>
--as-of <YYYY-MM-DD> [--activate]` delega directamente al pipeline y muestra
un reporte compacto. `--activate` devuelve código distinto de cero si el
catálogo no alcanza `ACTIVE`; sin esa bandera, `VALIDATING` es el resultado
normal para revisión. La receta de base vacía y los comandos operativos viven
en `docs/ARRANQUE_CATALOGO_BASE_V1.md`.

### Paso 4 — Ejecución controlada de primer lote

1. Migrar una base limpia.
2. Ejecutar sin `--activate` para obtener el diagnóstico completo.
3. Corregir únicamente la fuente o política indicada por los gates.
4. Repetir hasta que los gates pasen.
5. Ejecutar con `--activate`.
6. Abrir un sobre, crear lineup y comenzar una partida CPU como aceptación.

La ingesta de una temporada completa puede ser costosa. Se permite un lote de
diagnóstico reducido, pero queda explícitamente prohibido activarlo si no cubre
todas las franquicias configuradas.

### Paso 5 — Compatibilidad posterior, fuera del bloqueo ETL

Tras activar el lote, alinear el tipo `PlayerCard` de PWA con `vision`, `stuff`
y `clutch` (este último neutral e inactivo). Es una corrección de contrato de
presentación, no una condición para calcular el primer catálogo.

## Criterios de terminado

La intervención concluye cuando se cumpla todo lo siguiente:

- Una base sólo con migraciones puede producir un candidato sin seeds.
- Un único comando construye el lote, genera un reporte y puede activarlo.
- La única ruta de V1 usa `ratings-2.0`.
- Ningún catálogo incompleto puede quedar `ACTIVE`.
- La apertura de sobres, el starter pack y una partida CPU funcionan con el
  catálogo activo.
- Las pruebas de pipeline, lifecycle y gates pasan.
- No se añadieron fórmulas grandes al CLI ni se modificó el motor de juego.

## Trabajo que queda deliberadamente fuera

- Balance fino de ratings y rarezas.
- Diseño de boosts temporales.
- Progreso, récords y estadísticas acumuladas por modo.
- Reanudación descubierta por usuario tras login.
- Mini-temporada y su historial aislado.
- Enfrentamientos históricos bateador–pitcher y resolución contextual de cada
  lanzamiento.

Esos frentes podrán construirse sobre un catálogo base reproducible, sin volver
a ampliar el ETL de manera desordenada.
