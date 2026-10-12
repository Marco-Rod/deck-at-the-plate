# Deck at the Plate — TODO & Bug Tracker

Generado el: 2026-08-23  
Análisis basado en: revisión completa de backend, engine, routers, schemas, seeds y frontend.

---

## Leyenda

- `[x]` Completado
- `[ ]` Pendiente
- `🔴` Bug crítico (rompe en runtime)
- `🟠` Bug lógico (produce resultados incorrectos)
- `🟡` Deuda técnica / Refactor
- `🟢` Feature nueva / Mejora

---

## FASE 1 — Estabilización del Backend (Bugs bloqueantes)

### `[x]` #1 — Crear este archivo TODO.md
> Documentación centralizada de todos los bugs, tareas y progreso del proyecto.

---

### `[x]` #2 — 🔴 BUG: `play_tactic` — Variables usadas antes de definirse (`NameError`)
**Archivo:** `backend/app/routers/gameplay.py`  
**Problema:** El endpoint `play_tactic` usa `game`, `state` y `player_key` en las primeras líneas antes de que estén definidas. Crashea en runtime con `NameError`.  
**Solución:** Reordenar el bloque para primero hacer las queries a la DB y luego acceder a los datos.  
**Fix aplicado:** Reestructurado el endpoint con 5 pasos claros y documentados: queries → leer state → validar mano → restricción inning → registrar táctica.

---

### `[x]` #3 — 🔴 BUG: `PlayerCard` inexistente — Importación incorrecta en routers
**Archivos:** `backend/app/routers/gameplay.py`, `backend/app/routers/games.py`  
**Problema:** Múltiples endpoints importan y usan `PlayerCard` (modelo legacy), que no existe. El modelo correcto es `PlayerCardModel`. Además, `games.py` hace `db.add(new_game)` cuando la variable es `game`.  
**Solución:** Reemplazar todas las referencias `PlayerCard` → `PlayerCardModel` y corregir `new_game` → `game`.  
**Fix aplicado:** Reemplazadas todas las ocurrencias en `gameplay.py` y `games.py`. Corregido también `change_pitcher` que validaba `new_pitcher.role` (campo inexistente) → ahora valida `new_pitcher.position in ("SP", "RP", "TWP")`.

---

### `[x]` #4 — 🔴 BUG: Campo `movement` faltante en `PlayerCardModel` + inconsistencia de atributos
**Archivos:** `backend/app/models/card.py`, `backend/app/engine/calculator.py`, `backend/app/engine/fatigue_manager.py`  
**Problema:** El engine usa atributos en español (`velocidad`, `control`, `movimiento`, `contacto`, `poder`, `vision`). El modelo DB usa inglés (`velocity`, `control`, `power`, `contact`). No hay `movement`/`movimiento` en el modelo. Sin un mapper, el engine siempre usa valores por defecto (50) en lugar de los reales.  
**Solución:** Agregar `movement` al modelo y crear la función `map_card_to_engine_attrs()` que traduce columnas DB → diccionario que espera el engine.  
**Fix aplicado:**
- Agregado `movement = Column(Integer, default=50)` a `PlayerCardModel`.
- Creado `backend/app/engine/attribute_mapper.py` con `map_card_to_pitcher_attrs()` y `map_card_to_batter_attrs()`.
- La visión del bateador se deriva como `contact * 0.70 + overall * 0.30` (no existe como columna propia).
- `gameplay.py` ahora importa y usa el mapper en lugar de leer `.attributes` directamente.

---

### `[x]` #5 — 🟠 BUG: `just_switched_half` nunca se establece
**Archivo:** `backend/app/engine/state_manager.py`  
**Problema:** `game_over_manager.py` depende de `state.get("just_switched_half")` para las condiciones 2 y 3 de fin de juego. Esta clave nunca se escribía en `state_manager.py`, por lo que esas condiciones nunca se activaban. Solo funcionaba la condición de walk-off.  
**Solución:** Establecer `state["just_switched_half"] = True` al cambiar de media entrada y limpiarla al inicio del siguiente at-bat.  
**Fix aplicado:** `state["just_switched_half"] = False` al inicio de cada llamada; se establece `True` dentro del bloque `if game.outs >= 3`.

---

### `[x]` #6 — 🔴 BUG: Ghost runner sobreescribe las bases en medio del juego
**Archivo:** `backend/app/engine/state_manager.py`  
**Problema:** El bloque final `if game.current_inning >= 10: state["runners"] = ...` se ejecutaba en cada jugada cuando el inning era ≥10, sobreescribiendo el avance de corredores calculado por `advance_runners()`.  
**Solución:** Mover el bloque de ghost runner dentro del bloque `if inning_ended`.  
**Fix aplicado:** El ghost runner ahora se coloca exclusivamente cuando `game.outs >= 3` (cambio de media entrada), dentro de la misma rama condicional. El `last_out_batter` se guarda en state para usarlo como corredor fantasma.

---

### `[x]` #7 — 🟠 BUG: `HIT_3B` nunca ocurre — Umbral faltante en `calculator.py`
**Archivo:** `backend/app/engine/calculator.py`  
**Problema:** La distribución de umbrales pasaba de `HIT_2B (>89)` directamente a `HOME_RUN (>96)` sin dejar rango para `HIT_3B`.  
**Solución:** Agregar umbral `HIT_3B` entre `HIT_2B` y `HOME_RUN`.  
**Fix aplicado:** Redistribuidos todos los umbrales con porcentajes calibrados a MLB real: HOME_RUN >96 (~3%), HIT_3B 93–96 (~2%), HIT_2B 85–93 (~8%), HIT_1B 63–85 (~22%), OUT_GROUND 25–63 (~42%), OUT_FLY <25 (~23%).

---

### `[x]` #8 — 🔴 BUG: `cards.router` registrado dos veces en `main.py`
**Archivo:** `backend/app/main.py`  
**Problema:** `cards` se importaba dos veces en la misma línea y `app.include_router(cards.router)` aparecía duplicado.  
**Solución:** Eliminar el import y registro duplicado.  
**Fix aplicado:** `main.py` reescrito limpiamente con un router por línea, sin duplicados, y con docstring completo del módulo.

---

## FASE 2 — Refactorización Estructural

### `[x]` #9 — 🟡 REFACTOR: Consolidar sistema de schemas
**Archivos:** `backend/app/schemas.py` (raíz), `backend/app/schemas/` (directorio)  
**Problema:** Existían dos sistemas de schemas en paralelo con definiciones duplicadas.  
**Solución:** Vaciar `schemas.py` raíz y hacer que re-exporte todo desde `schemas/`.  
**Fix aplicado:** `schemas.py` raíz ahora es un archivo de compatibilidad que re-exporta desde `schemas/game.py`, `schemas/cards.py`, `schemas/user.py` y `schemas/shop.py`. Se agregó docstring explicativo para evitar que se agreguen definiciones directamente ahí.

---

### `[x]` #10 — 🟡 REFACTOR: Limpiar `models.py` raíz y verificar imports
**Archivos:** `backend/app/models.py` (raíz), `backend/app/models/__init__.py`  
**Problema:** `models.py` raíz estaba vacío, `models/__init__.py` ya exportaba todo correctamente.  
**Fix aplicado:** `models.py` raíz ahora tiene un docstring de compatibilidad y re-exporta desde `app.models` (el directorio). `models/__init__.py` recibió su docstring de módulo. Ambos sirven como fuente de verdad y documentación del paquete.

---

## FASE 3 — Autenticación e Infraestructura

### `[x]` #11 — 🟢 FEAT: Crear endpoints de autenticación
**Archivos:** `backend/app/auth.py`, `backend/app/routers/auth.py` (nuevo), `backend/app/schemas/user.py`  
**Problema:** No existía `POST /api/v1/auth/login` ni `POST /api/v1/auth/register`.  
**Fix aplicado:**
- Creado `routers/auth.py` con dos endpoints: `POST /register` (crea usuario + wallet con 1000 stamps) y `POST /login` (verifica credenciales, retorna JWT).
- Contraseñas hasheadas con `bcrypt` usando `passlib[bcrypt]==1.7.4` (agregado a `requirements.txt`).
- Login usa `OAuth2PasswordRequestForm` para compatibilidad con el botón "Authorize" de FastAPI docs.
- Agregados schemas `RegisterRequest` y `LoginResponse` a `schemas/user.py`.
- Router registrado en `main.py`.

---

### `[x]` #12 — 🟡 INFRA: JWT secret key a variable de entorno
**Archivo:** `docker-compose.yml`  
**Fix aplicado:**
- `JWT_SECRET_KEY` cambiada de valor hardcodeado a `${JWT_SECRET_KEY}` (lee del archivo `.env`).
- Creado `.env.example` con todas las variables requeridas y una instrucción para generarlas.
- Verificado que `.env` ya estaba en `.gitignore`.

---

### `[x]` #13 — 🟡 INFRA: Configurar Alembic para migraciones
**Fix aplicado:**
- Creado `backend/alembic.ini` con configuración completa.
- Creado `backend/alembic/env.py` que lee `DATABASE_URL` del entorno, importa todos los modelos y soporta modos online y offline.
- Creado `backend/alembic/script.py.mako` (template para migraciones).
- Creado `backend/alembic/versions/` con `.gitkeep` e instrucciones.
- Para generar la primera migración baseline: `docker compose exec backend alembic revision --autogenerate -m "baseline_schema"`

---

### `[x]` #14 — 🟡 SEED: Actualizar `seed_real_data_2025.py` al modelo actual
**Archivo:** `backend/app/seeds/seed_real_data_2025.py`  
**Fix aplicado:**
- Reescrito completamente para usar `PlayerCardModel` con columnas individuales (`power`, `contact`, `velocity`, `control`, `movement`).
- Agrega 4 equipos (NYY, LAD, HOU, ATL) antes de insertar cartas (respeta FK `team_id`).
- Incluye 10 cartas de jugadores reales MLB 2025 (incluyendo Ohtani como TWP con `is_two_way=True`).
- Incluye 6 cartas tácticas de ejemplo con efectos en español (compatibles con el engine).

---

## FASE 5 — Integración Frontend

### `[x]` #15 — 🟢 FRONTEND: Implementar `api.js` como cliente HTTP centralizado
**Archivo:** `frontend/src/utils/api.js`  
**Fix aplicado:**
- Implementado cliente fetch con base URL desde `VITE_API_URL`.
- Adjunta JWT automáticamente desde `localStorage` en cada request.
- Expone 5 namespaces: `auth`, `games`, `user`, `cards`, `shop`.
- `auth.login()` guarda token y user_id en localStorage automáticamente.
- `auth.logout()` limpia localStorage.
- Manejo de errores descriptivo: extrae el `detail` del servidor cuando el status >= 400.

---

### `[x]` #16 — 🔴 FRONTEND: Corregir URL WebSocket y alinear eventos
**Archivo:** `frontend/src/hooks/useStadiumSocket.ts`  
**Fix aplicado:**
- URL corregida: `/ws/match/` → `/ws/games/{gameId}/{userId}`.
- Hook ahora acepta `userId` como segundo parámetro.
- Implementados handlers para todos los eventos del backend: `INIT_GAME_STATE`, `PITCH_COMMITTED`, `PLAY_RESOLVED`, `STEAL_RESOLVED`.
- Las acciones (pitch, swing, tactic) se envían vía REST usando `api.js` en lugar del WebSocket.
- Añadido estado `isConnected` y `hasPitched` para feedback visual.
- Función `mapPayloadToGameState()` convierte el payload del backend al tipo `GameStateWS` del frontend.

---

### `[x]` #17 — 🟠 FRONTEND: Unificar tipos `PitchType`
**Archivo:** `frontend/src/types/stadium.ts`  
**Fix aplicado:**
- `PitchType` cambiado de `'4-SEAM' | 'SLIDER' | 'CURVE' | 'CHANGE' | 'IBB'` a `'FF' | 'SL' | 'CU' | 'CH' | 'IBB'`.
- Agregado `PITCH_TYPE_LABELS` para display en español.
- Actualizado `GameStateWS` para coincidir con la estructura real del backend (`currentInning`, `isTopInning`, `runners` como strings en lugar de booleans).
- Agregados tipos `PlayResolvedPayload`, `PitchCommittedPayload`, `InitGameStatePayload`.
- Agregado `COMMON` a `CardRarity`.

---

### `[x]` #18 — 🟡 FRONTEND: Reemplazar `StadiumShowcaseScreen.jsx` monolítico por TSX componentizado
**Archivos:** `frontend/src/App.jsx`, `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Fix aplicado:**
- `App.jsx` ahora importa `StadiumShowcaseScreen` desde `components/stadium/` (TSX) en lugar de `pages/` (JSX).
- `StadiumShowcaseScreen.tsx` actualizado: acepta `gameId` y `userId` como props, usa `useStadiumSocket` con los parámetros correctos, integra `PlayResultOverlay`, e incluye indicador de estado de conexión WS.
- Corregidos imports relativos en el TSX (rutas apuntaban a `../components/stadium/` incorrecto).

---

### `[x]` #19 — 🟢 FRONTEND: Conectar `MyTeamScreen` e inventario real
**Archivo:** `frontend/src/pages/MyTeamScreen.jsx`  
**Fix aplicado:**
- Reemplazados datos hardcodeados por `useEffect` que llama a `userApi.getInventory(user.userId)`.
- Separa el inventario en pitchers (`SP`, `RP`, `TWP`) y bateadores automáticamente.
- Maneja estados de carga, error y lista vacía con mensajes al usuario.
- Muestra atributos reales: `contact`, `power`, `velocity`, `control`, `movement`, `overall`.
- La prop `user` ahora se pasa desde `App.jsx` (se actualizó la firma del componente).

---

### `[x]` #20 — 🟢 FRONTEND: Integrar `RosterSelectionScreen` en el flujo de `App.jsx`
**Archivos:** `frontend/src/App.jsx`, `frontend/src/pages/RosterSelectionScreen.jsx`  
**Fix aplicado:**
- Agregado estado `'ROSTER_SELECTION'` en `App.jsx`. El flujo es ahora: Lobby → RosterSelection → Stadium.
- `RosterSelectionScreen` carga el inventario real del usuario y permite seleccionar pitcher y 9 bateadores.
- Al confirmar, llama a `gamesApi.create()` con el roster completo y navega al estadio con el `gameId` real.
- Botón de confirmación deshabilitado hasta tener pitcher + 9 bateadores seleccionados.

---

## Notas adicionales (deuda técnica menor)

- **CORS:** `allow_origins=["*"]` debe restringirse a dominios específicos antes de ir a producción.
- **`/steal` y game over:** El endpoint no llama a `check_game_over` después de registrar un out por robo fallido. Puede dejar juegos en estado inconsistente si ese out es el 3ro en extra innings.
- **Double plays / Sacrifice flies:** No implementados en `runner_manager.py`. Bolas en juego con corredores no producen doble play ni el corredor en 3ra anota en elevados de sacrificio.
- **`StadiumShowcaseScreen.jsx` legacy:** El archivo en `pages/StadiumShowcaseScreen.jsx` ya no se usa (se reemplazó por el TSX) pero sigue existiendo en el repo. Candidato a eliminación.
- **Fotos de jugadores:** Las URLs de ESPN pueden expirar o cambiar. Se necesita un sistema de assets propio o un CDN.

---

## FASE 6 — Completar el loop de juego (P0 — Bloqueantes)

### `[x]` #21 — 🔴 PVE: Invocar `trigger_cpu_response_if_needed()` en los endpoints de juego
**Archivos:** `backend/app/routers/gameplay.py`  
**Problema:** La función existía pero usaba variables inexistentes (`pending_pitch`, `apply_fatigue`, `resolve_play`, `VALID_ZONES`) y nunca se llamaba desde los endpoints.  
**Fix aplicado:**
- Reescrito `gameplay.py` completo eliminando todo el código de placeholder.
- Extraída función `_resolve_swing()`: núcleo compartido humano/CPU que ejecuta los 6 pasos del at-bat (fatiga, tácticas, cálculo, transición, broadcast WS).
- Extraída `_apply_tactic_modifiers()`: centraliza la lectura de efectos de TacticCard.
- Implementada `_is_cpu_turn()`: determina si la CPU actúa según modo PvE, `is_top_inning` y `away_user_id == "CPU_BOT"`.
- Implementada `trigger_cpu_response_if_needed()` completamente funcional:
  - Caso A (Bot inning): CPU batea tras el picheo humano → llama `_resolve_swing`.
  - Caso B (Top inning): CPU pichea con `get_cpu_pitch_action` y emite `PITCH_COMMITTED`.
- Invocada al final de `select_pitch` y `execute_swing`.
- Corregido `steal_base`: agrega llamada a `check_game_over` tras out por robo y establece `just_switched_half`.

---

### `[ ]` #22 — 🔴 FRONTEND: Pantalla de fin de juego (Game Over)
**Archivos:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`, nuevo componente `GameOverScreen`  
**Problema:** Cuando `gameState.isGameOver = true` no ocurre nada en el frontend. El juego queda congelado sin mostrar al ganador ni ofrecer salida.  
**Solución:** Detectar `isGameOver` en `StadiumShowcaseScreen.tsx` y mostrar un modal o pantalla con el `winnerMessage`, stamps ganados y botón para volver al Lobby.

---

### `[ ]` #23 — 🟠 FRONTEND: Cargar estado inicial del juego al conectar al WS
**Archivo:** `frontend/src/hooks/useStadiumSocket.ts`  
**Problema:** El evento `INIT_GAME_STATE` se recibe pero no se procesa: `gameState` queda en `null` hasta la primera jugada. El marcador no muestra nada al entrar al estadio.  
**Solución:** Al recibir `INIT_GAME_STATE`, llamar a `GET /api/v1/games/{gameId}?user_id={userId}` y convertir la respuesta al formato `GameStateWS` para poblar el estado inicial.

---

## FASE 7 — Conectar features pendientes del estadio

### `[ ]` #24 — 🟡 FRONTEND: Cartas tácticas del mazo real en el estadio
**Archivo:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Problema:** `TacticalHand` muestra siempre las mismas 4 cartas hardcodeadas. El backend ya gestiona el deck/hand/discard en `state_data`; solo falta leer la mano del jugador desde el `gameState`.  
**Solución:** Cuando `PLAY_RESOLVED` actualiza `gameState`, extraer `state_data.tactics[playerKey].hand` y mapear los IDs a objetos `TacticalCard` para pasárselos al componente.

---

### `[ ]` #25 — 🟢 FRONTEND: ShopScreen — Pantalla de tienda
**Problema:** Los endpoints de compra de sobres y starter pack están completos en el backend. No existe ninguna página en el frontend para acceder a ellos; el usuario no puede conseguir cartas desde la UI.  
**Solución:** Crear `frontend/src/pages/ShopScreen.jsx` con:
- Panel de starter pack (selector de equipo, botón de reclamar, solo una vez).
- Tres botones de apertura de sobre (BRONZE / GOLD / DIAMOND) con su precio en stamps.
- Animación de reveal de las cartas obtenidas.
- Indicador del wallet actual (stamps y gems).
- Navegación desde el Lobby y desde `App.jsx`.

---

### `[ ]` #26 — 🟢 FRONTEND: Conectar `CardShowcaseScreen` al catálogo real
**Archivo:** `frontend/src/pages/CardShowcaseScreen.jsx`  
**Problema:** La pantalla usa datos hardcodeados. Debería mostrar el inventario real del usuario o el catálogo completo de cartas del backend.  
**Solución:** Llamar a `userApi.getInventory(userId)` o `cardsApi.getTeams()` según el contexto y renderizar las cartas reales.

---

### `[ ]` #27 — 🟢 FRONTEND: Botón de Robo de Base en el estadio
**Archivo:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Problema:** `POST /{game_id}/steal` está completamente funcional en el backend. No hay interfaz para ejecutarlo.  
**Solución:** Agregar un botón "ROBAR BASE" visible solo cuando el rol es BATTER y hay un corredor en 1ra o 2da. Al pulsar, mostrar un selector de base objetivo (2B / 3B) y llamar a `gamesApi.steal()`.

---

### `[ ]` #28 — 🟢 FRONTEND: Panel de Bullpen y cambio de pitcher
**Archivo:** `frontend/src/components/stadium/StadiumShowcaseScreen.tsx`  
**Problema:** `POST /{game_id}/change-pitcher` está funcional en el backend. No hay UI para la sustitución.  
**Solución:** Agregar un panel lateral desplegable visible solo cuando el rol es PITCHER, listando los relevistas disponibles del roster y permitiendo elegir uno para realizar el cambio.

---

### `[ ]` #29 — 🟢 FRONTEND: Opción de BUNT en el selector de swing
**Archivo:** `frontend/src/components/stadium/TacticalHand.tsx`  
**Problema:** `resolve_bunt()` está implementado en el backend pero no hay forma de seleccionarlo desde la UI.  
**Solución:** Agregar un botón "TOQUE" en el área de acciones del bateador que fije `swing_type = 'BUNT'` antes de enviar el swing.

---

## FASE 8 — Modo PvP real

### `[ ]` #30 — 🟢 BACKEND + FRONTEND: Lobby de sala PvP
**Problema:** El `turn_guard` ya valida por `user_id` y el WS soporta múltiples conexiones por partida. Falta la lógica de emparejamiento.  
**Solución:**
- Crear endpoint `POST /api/v1/games/invite` o una sala de espera con código de sala.
- En el frontend, una pantalla de "Esperando rival..." que escuche el evento de conexión del segundo jugador.
- Al conectarse ambos jugadores, el backend emite `GAME_START` y ambos clientes navegan al estadio con sus roles asignados.

---

## FASE 9 — Deuda técnica e infraestructura

### `[ ]` #31 — 🟡 INFRA: Generar y aplicar migración Alembic baseline
**Problema:** Alembic está configurado pero no se ha generado la primera migración. Las tablas se crean con `create_all` sin control de versiones.  
**Solución:**
```bash
docker compose exec backend alembic revision --autogenerate -m "baseline_schema"
docker compose exec backend alembic upgrade head
```
Después de esto, reemplazar `Base.metadata.create_all(bind=engine)` en `main.py` por el comando de migración en el entrypoint del contenedor.

---

### `[ ]` #32 — 🟡 INFRA: Restringir CORS en producción
**Archivo:** `backend/app/main.py`  
**Problema:** `allow_origins=["*"]` acepta peticiones de cualquier dominio.  
**Solución:** Leer los orígenes permitidos desde una variable de entorno y restringirlos al dominio del frontend en producción.

---

### `[ ]` #33 — 🟡 BACKEND: `/steal` no llama a `check_game_over` tras out por robo
**Archivo:** `backend/app/routers/gameplay.py`  
**Problema:** Si el robo fallido es el 3er out en extra innings, el juego no detecta que terminó.  
**Solución:** Después de incrementar `game.outs` en el bloque `else` del steal, llamar a `check_game_over(game, state)` y si retorna `True`, establecer `state["is_game_over"] = True` y emitir el resultado vía WS.

---

### `[ ]` #34 — 🟡 FRONTEND: Eliminar `StadiumShowcaseScreen.jsx` legacy
**Archivo:** `frontend/src/pages/StadiumShowcaseScreen.jsx`  
**Problema:** El archivo JSX monolítico ya no se usa pero sigue en el repo generando confusión.  
**Solución:** Eliminarlo y verificar que no haya imports que lo referencien.

---

### `[ ]` #35 — 🟢 UX: Pantalla de resultado post-partida con stats
**Problema:** Al terminar una partida no hay resumen: no se muestran estadísticas, stamps ganados ni historial.  
**Solución:** Crear un componente `PostGameScreen` que muestre marcador final, inning de cierre, MVP de la partida, stamps ganados y botón para volver al Lobby.

---

### `[ ]` #36 — 🟢 UX: Sonidos contextuales en eventos de juego
**Archivo:** `frontend/src/utils/audioManager.js`  
**Problema:** `audioManager.js` tiene síntesis de sonido funcional pero solo se usa en clicks de UI. Los eventos de juego no tienen sonido.  
**Solución:** Mapear los eventos de `PLAY_RESOLVED` a llamadas de `soundFx`: home run → fanfarria, strikeout → efecto de ponche, walk → silbato, foul → chasquido, etc.

---

_Última actualización: 2026-08-23 — 20 tareas completadas, 16 nuevas registradas (tareas #21–#36)_
