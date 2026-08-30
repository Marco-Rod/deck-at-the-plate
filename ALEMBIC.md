# Migraciones de Base de Datos (Alembic)

El esquema de la base de datos se gestiona **exclusivamente** con Alembic.
No usar `Base.metadata.create_all` en código de la app ni en seeds: eso provoca
esquemas inconsistentes como el error de `teams.is_cpu` (columna existente en el
modelo pero no en la BD).

## Comandos

Ejecutar dentro del contenedor del backend:

```bash
# Aplicar migraciones pendientes
docker compose exec backend alembic upgrade head

# Ver versión actual
docker compose exec backend alembic current

# Ver historial
docker compose exec backend alembic history --verbose

# Retroceder una revisión
docker compose exec backend alembic downgrade -1
```

## Flujo al modificar un modelo

1. Edita el modelo en `backend/app/models/*.py`.
2. Genera la migración automática:
   ```bash
   docker compose exec backend alembic revision --autogenerate -m "descripcion"
   ```
3. Revisa el archivo generado en `backend/alembic/versions/` y ajusta si hace falta.
4. Aplica la migración:
   ```bash
   docker compose exec backend alembic upgrade head
   ```

## Reset total del esquema

> ⚠️ **Importante:** en PostgreSQL, `DROP TABLE` **no** elimina los tipos ENUM
> (p. ej. `cardrarity`). Por eso `alembic downgrade base` + `alembic upgrade head`
> falla con *"type cardrarity already exists."* Usa siempre `DROP SCHEMA CASCADE`:

```bash
docker exec baseball_db psql -U game_user -d baseball_game \
  -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker compose exec backend alembic upgrade head
```

O directamente con el script ya preparado:
```bash
docker compose exec backend python app/seeds/reset_tables.py
```

## Notas

- `alembic/env.py` importa `app.models` y lee `DATABASE_URL` del entorno, así que
  `--autogenerate` detecta los modelos correctamente.
- Los seeds **no** crean el esquema: las tablas deben existir vía `alembic upgrade head`.
