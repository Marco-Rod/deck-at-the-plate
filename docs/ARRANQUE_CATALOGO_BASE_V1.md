# Arranque desde cero: catálogo BASE V1

Esta guía prepara una base de datos nueva y ejecuta el flujo que crea el primer
catálogo de cartas jugable. El proceso no usa seeds legacy ni requiere cargar
equipos, jugadores, eventos, ratings o cartas manualmente.

## Qué crea el comando

`build-base-catalog` coordina, en este orden:

```text
esquema migrado
  → equipos SOURCE y franquicias GAME
  → rosters y jugadores
  → identidades visibles ficticias
  → eventos Statcast hasta la fecha de corte
  → analytics y ratings-2.0
  → perfiles, cartas y catálogo candidato
  → gates de CPU, starter pack y sobres
```

Sin `--activate`, el catálogo queda en `VALIDATING`. Con `--activate`, sólo
queda `ACTIVE` si todos los gates pasan.

Si una ejecución falla antes de crear cartas —por ejemplo, por un insumo de
perfiles incompleto—, se puede corregir el código o el insumo y repetir el
comando con `--skip-statcast`. El catálogo `FAILED` sin cartas se reutiliza de
forma controlada y se aprovecha el RAW ya persistido; no hace falta reiniciar
la base ni volver a descargar Statcast.

## Estado inicial requerido

La base debe contener únicamente el esquema de Alembic:

- PostgreSQL accesible mediante `DATABASE_URL`.
- Todas las migraciones aplicadas.
- Sin seeds legacy.
- Sin una `CardEdition`/`CardCatalog` `BASE` previa para la misma temporada.

No es necesario crear antes equipos, jugadores, rosters, identidades, eventos
Statcast, ratings, perfiles ni cartas. El comando los obtiene o genera.

También se requiere:

- Entorno Python del backend con sus dependencias, incluido el driver de
  PostgreSQL (`psycopg2` o equivalente compatible).
- Acceso de red a MLB Stats API y Statcast.
- El archivo versionado de franquicias GAME:
  `backend/etl/config/game_franchises.yaml`.
- Una fecha de corte perteneciente a la temporada y con datos suficientes para
  formar rosters completos.

## Comandos

Ejecutar desde `backend/`.

## Reinicio con Docker para una base ya existente

> **Atención:** las dos alternativas siguientes eliminan todos los datos de la
> base `baseball_game`: usuarios, inventarios, partidas, catálogos y datos del
> ETL. No ejecutarlas si hay información que se quiera conservar.

El compose persiste PostgreSQL en el volumen nombrado `postgres_data`. Para un
primer lote V1 se recomienda eliminar el volumen completo, porque garantiza
que no sobrevivan catálogos, seeds o tipos de PostgreSQL de una etapa anterior.

Ejecutar desde la raíz del repositorio:

```powershell
docker compose down --volumes --remove-orphans
docker compose up -d --build db backend
docker compose ps
```

Espera a que `db` esté saludable antes de continuar. Después aplica el esquema
desde el contenedor del backend:

```powershell
docker compose exec backend alembic upgrade head
```

El contenedor del backend instala `psycopg2-binary` desde
`backend/requirements.txt`, por lo que esta ruta evita depender del driver de
PostgreSQL del entorno Python local.

### Alternativa: conservar el volumen y vaciar sólo el esquema

Si por alguna razón se necesita mantener el volumen Docker, se puede reconstruir
el esquema público. También borra todos los datos de la aplicación:

```powershell
docker compose exec db psql -U game_user -d baseball_game `
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec backend alembic upgrade head
```

No usar `alembic downgrade base` como reset general: PostgreSQL conserva tipos
ENUM y una migración posterior puede fallar al volver a crearlos.

### 1. Aplicar el esquema

```powershell
alembic upgrade head
```

Con Docker, sustituirlo por:

```powershell
docker compose exec backend alembic upgrade head
```

### 2. Crear y revisar el candidato

```powershell
python -m etl.cli build-base-catalog `
  --season 2026 `
  --as-of 2026-06-15
```

Con Docker:

```powershell
docker compose exec backend python -m etl.cli build-base-catalog `
  --season 2026 `
  --as-of 2026-06-15
```

El reporte debe indicar `status=VALIDATING`. Revísalo antes de continuar: debe
mostrar conteos de ratings y perfiles, el identificador de catálogo y cualquier
incidencia.

Para reintentar después de una falla ocurrida tras la ingesta RAW, agrega
`--skip-statcast` al mismo comando. El flujo vuelve a generar analytics,
ratings, distribuciones, perfiles y catálogo, pero no consulta Statcast otra
vez.

### 3. Activar sólo cuando los gates estén resueltos

```powershell
python -m etl.cli build-base-catalog `
  --season 2026 `
  --as-of 2026-06-15 `
  --activate
```

Con Docker:

```powershell
docker compose exec backend python -m etl.cli build-base-catalog `
  --season 2026 `
  --as-of 2026-06-15 `
  --activate
```

El resultado esperado es `status=ACTIVE`. Si no alcanza ese estado, el comando
termina con código distinto de cero y deja el detalle en el reporte; no activa
un catálogo incompleto.

### Actualizar sólo el repertorio de un candidato ya creado

Si un candidato fue generado antes de la materialización de repertorios V1, no
hace falta reiniciar la base ni repetir la descarga de Statcast. Tras aplicar
el código actualizado, usa el ID mostrado por el reporte:

```powershell
docker compose exec backend python -m etl.cli sync-catalog-repertoires `
  --catalog-id <catalog-id>
```

El comando sólo admite catálogos `VALIDATING`: regenera únicamente los perfiles
de pitcher desde los ratings y analytics ya persistidos, después actualiza sus
cartas. No modifica catálogos `ACTIVE` o históricos ni vuelve a descargar datos.

Después de revisar que `missing=0`, se puede promover el mismo candidato sin
repetir el pipeline completo:

```powershell
docker compose exec backend python -m etl.cli promote-card-catalog `
  --catalog-id <catalog-id>
```

Esta promoción vuelve a ejecutar los gates de roster CPU, starter pack, pool de
sobres y repertorio de pitchers.

## Gates de activación

Un catálogo BASE V1 sólo se activa si cumple:

- Atributos e identidad pública completos en cada carta.
- Por cada franquicia mapeada: al menos 9 bateadores y 2 pitchers.
- El selector real puede producir un starter pack de 13 cartas, con pitcher y
  C, 1B, 2B, 3B, SS, LF, CF, RF y DH.
- El pool contiene las rarezas requeridas para sobres.

## Si falla una ejecución

- No borres ni apliques seeds para "destrabar" el resultado.
- Conserva el reporte y corrige sólo la capa que indique el gate: datos de
  roster, cobertura de posiciones, elegibilidad o pool de rarezas.
- Repite exactamente el mismo comando. Metadata, perfiles y catálogo usan
  claves idempotentes; una edición ya activa se trata como no-op.
- Si la base no es nueva o ya hay un catálogo `BASE` de esa temporada, primero
  revisa su estado. Este comando no borra ni sustituye catálogos existentes.

## Verificación funcional posterior

Después de obtener `ACTIVE`, validar desde la aplicación:

1. Abrir un sobre.
2. Recibir el starter pack y construir un lineup válido.
3. Crear una partida contra CPU con una franquicia disponible.

Estas tres comprobaciones validan el recorrido completo desde el ETL hasta
gameplay.
