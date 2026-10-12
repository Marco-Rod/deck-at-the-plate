# Auditoría de integración: ETL V1 a partida jugable

## Alcance y método

Auditoría estática del recorrido actual desde fuentes de datos hasta una partida
contra CPU. No se ejecutaron importaciones, seeds, migraciones ni cambios de
base de datos. Las conclusiones describen el código y contratos encontrados;
la validación contra una base real corresponde a la siguiente tarea.

## Conclusión

El repositorio ya contiene las piezas necesarias para generar cartas, publicar
un catálogo y consumirlo en sobres y partidas. Sin embargo, **no existe todavía
un comando único que genere el primer lote jugable**.

El comando actual `python -m etl.cli run` sólo ingiere un rango de Statcast,
resuelve jugadores presentes en ese rango y recalcula analytics. No genera
ratings de población, perfiles de carta, catálogo, promoción, validación de
rosters ni pool de sobres.

La solución V1 no debe reemplazar esos componentes: debe crear un orquestador
pequeño que los conecte y deje fuera las capacidades avanzadas.

## Trazabilidad actual

| Etapa | Pieza actual | Salida | Uso posterior | Estado para V1 |
| --- | --- | --- | --- | --- |
| Equipos SOURCE | `MetadataPipeline.run_source_teams` | `SourceTeam` | Mapeos y rosters | Conservar |
| Franquicias GAME | `run_game_team_mappings` + configuración de franquicias | `Team` y mapeo SOURCE→GAME | CPU, cartas, starter pack | Conservar |
| Rosters y jugadores | `run_rosters` | `Player`, snapshots y stints | Población de cartas | Conservar |
| Identidad pública | `generate-game-identities` | `GamePlayerIdentity` | Nombre/número de carta publicada | Conservar mientras el catálogo la requiera |
| Datos de pitcheo | `StatcastRawPipeline` | `RawPitchEvent` | Analytics y ratings | Conservar |
| Analytics | `AnalyticsPipeline.rebuild` | perfiles de bateador/pitcher | Cálculo de ratings | Conservar |
| Ratings | `generate_player_ratings_as_of` por rol | `PlayerRatings` | Perfil de carta ratings-2.0 | Conservar, pero unificar bajo un solo flujo |
| Perfil de carta | `generate_card_profile_from_ratings2` y `generate_card_rating_profile` | perfiles de generación/rating | Materialización | Conservar |
| Catálogo | `publish_card_catalog` / lifecycle | `CardCatalog` + `PlayerCardModel` | Sobres, CPU, partidas | Conservar, simplificando el punto de entrada |
| Sobres | `PackService` | inventario y lineup | Jugador humano | Consumidor V1 |
| Roster CPU | `GameSessionService.create` | lineup y bullpen CPU | Partida | Consumidor V1 |
| Motor | `attribute_mapper` + `calculator` | resultado de lanzamiento | Gameplay | Consumidor V1 |

## Integración con gameplay

```text
CardCatalog ACTIVE
  ├─ PlayerCardModel.is_pack_eligible → PackService → inventario / starter pack
  ├─ PlayerCardModel por Team → GameSessionService → lineup y bullpen CPU
  └─ PlayerCardModel atributos → attribute_mapper → calculator
```

El backend resuelve un catálogo `BASE` activo para crear una partida CPU. La
partida guarda `catalog_id` y versión de motor como provenance, por lo que un
cambio posterior de catálogo no reinterpreta una partida en curso.

## Hallazgos relevantes

### 1. El flujo actual está fragmentado

El CLI ofrece muchos subcomandos. Para llegar a cartas base se requieren varias
etapas separadas. El comando `run` no cubre catálogo y, por tanto, no cumple el
objetivo de “ejecutar un comando y jugar”.

### 2. Coexisten dos generaciones de perfiles

- `ratings-1.0`: `generate-card-profiles` usa fórmulas antiguas y no materializa
  `stuff` como señal completa de pitcher.
- `ratings-2.0`: `PlayerRatings`, perfiles de ratings y materialización candidata
  incluyen velocidad, control, movimiento y stuff; se alinea mejor con el motor
  actual.

V1 debe elegir una sola ruta. La candidata recomendada es `ratings-2.0`, porque
representa todos los atributos que usa el motor. La decisión debe validarse con
un lote pequeño antes de retirar la ruta anterior.

### 3. La materialización ratings-2.0 no es bootstrap limpio

`materialize_card_catalog_candidate` exige un catálogo `BASE` ACTIVE previo
como baseline. Eso sirve para sustituir una generación existente, pero no para
crear el primer catálogo en una base migrada y vacía.

El lifecycle general `publish_card_catalog`, en cambio, sí sabe publicar por
primera vez sin un catálogo activo. La limitación real es que activa ese primer
catálogo de inmediato. El flujo V1 debe reutilizar ese lifecycle, pero crear el
primer catálogo como candidato, ejecutar los gates de jugabilidad y sólo
después promoverlo.

### 4. Los validadores existen, pero deben reforzarse

`validate_cpu_rosters` comprueba que cada franquicia mapeada tenga alguna carta,
no que pueda formar un lineup de nueve bateadores y bullpen suficiente.
`validate_pack_pool` sí revisa elegibilidad y disponibilidad por rareza, pero el
starter pack necesita además posiciones requeridas. V1 debe convertir esas
condiciones de juego en gates explícitos.

### 5. El contrato de la PWA no refleja todos los atributos de carta

El modelo backend y el motor manejan `vision`, `clutch` y `stuff`; la interfaz
`PlayerCard` de la PWA sólo declara los campos históricos principales. Esto no
bloquea el cálculo del backend, pero debe alinearse antes de presentar todos los
atributos de las cartas base en la interfaz.

### 6. El CLI actual es un punto de mantenimiento riesgoso

`etl/cli.py` concentra demasiados subcomandos y ramas. El nuevo flujo no debe
agregar otra gran rama con fórmulas internas: debe delegar en un pipeline V1
pequeño, probado y con opciones mínimas.

## Contrato propuesto: primer lote jugable

El nuevo punto de entrada debe representar una intención de producto, no una
cadena manual de comandos. Nombre tentativo:

```text
python -m etl.cli build-base-catalog \
  --season <temporada> \
  --as-of <YYYY-MM-DD> \
  --activate
```

Sin `--activate`, el comando debe crear un candidato validable y reportar sus
gates. Con `--activate`, sólo debe promoverlo si todos los gates pasan.

El comando debe:

1. Sincronizar equipos SOURCE, franquicias GAME y rosters de la temporada.
2. Generar identidades requeridas por las cartas.
3. Ingerir el rango necesario de Statcast hasta la fecha de corte.
4. Generar analytics y ratings para bateadores y pitchers.
5. Construir perfiles de carta y una única edición `BASE`.
6. Materializar un catálogo candidato sin requerir un catálogo previo.
7. Validar atributos, rosters CPU, starter pack y pool de sobres.
8. Promover de forma atómica sólo cuando las validaciones sean exitosas.
9. Imprimir un informe compacto: equipos, jugadores, cartas, omisiones, gates,
   catálogo y versión de política.

Debe ser idempotente: reejecutarlo con los mismos argumentos no duplica equipos,
jugadores, perfiles ni cartas. Debe poder iniciar desde una base vacía que ya
tenga las migraciones aplicadas. No debe invocar seeds legacy.

## Componentes aplazados del flujo V1

- Detección y evaluación de momentos históricos.
- Cartas `MOMENT` y ediciones paralelas.
- H2H histórico como requisito de atributos.
- Auditorías de estabilidad, rareza y evidencia que no bloqueen el catálogo
  base.
- Identidades o clasificaciones alternativas que no sean requeridas para
  materializar una carta utilizable.

## Siguiente trabajo recomendado

1. Diseñar y probar el bootstrap limpio de `ratings-2.0` hasta catálogo
   candidato, reutilizando servicios existentes.
2. Crear `pipelines/base_catalog_v1.py` como orquestador pequeño y extraer del
   CLI la coordinación; no copiar fórmulas.
3. Endurecer los gates de juego: roster CPU, posiciones del starter pack,
   atributos completos y pool elegible.
4. Añadir `build-base-catalog` al CLI como fachada del pipeline.
5. Ejecutar un lote pequeño de prueba y documentar resultados antes de intentar
   una población completa.

## Archivos principales inspeccionados

- `backend/etl/cli.py`
- `backend/etl/pipelines/metadata.py`
- `backend/etl/pipelines/statcast.py`
- `backend/etl/pipelines/analytics.py`
- `backend/etl/services/player_ratings_as_of.py`
- `backend/etl/services/ratings2_card_profiles.py`
- `backend/etl/services/materialize_card_catalog_candidate.py`
- `backend/etl/services/card_catalog.py`
- `backend/app/services/game_session_service.py`
- `backend/app/services/pack_service.py`
- `backend/app/repositories/card_repository.py`
- `backend/app/engine/attribute_mapper.py`
- `backend/app/engine/calculator.py`
- `pwa/src/shared/api/types.ts`
