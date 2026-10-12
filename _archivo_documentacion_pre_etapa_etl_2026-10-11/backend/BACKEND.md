# ⚾ Deck at the Plate — Documentación Técnica del Backend

## 1. Visión General del Sistema y Tecnologías

**Deck at the Plate** es un motor de béisbol táctico 1v1 (PvP y PvE) impulsado por eventos y estadísticas profesionales. Combina mecánicas de cartas coleccionables, simulación probabilística basada en promedios de Statcast (MLB), seguridad con Niebla de Guerra (Fog of War) y comunicación bidireccional en tiempo real.

### Stack Tecnológico
* **Lenguaje & Framework:** Python 3.11+ / FastAPI (Asincrónico)
* **Base de Datos & ORM:** PostgreSQL + SQLAlchemy
* **Containerización:** Docker & Docker-Compose
* **Autenticación & Seguridad:** PyJWT (Tokens JWT) + Guardián de Turnos
* **Tiempo Real:** WebSockets (FastAPI ConnectionManager)
* **Validación de Datos:** Pydantic v2 (DTOs y Esquemas)

---

## 2. Resumen de Jugabilidad y Reglas del Motor

* **Estructura del Enfrentamiento:** Partidas de 9 entradas (con soporte para extra innings / muerte súbita a partir de la entrada 10).
* **Duels Pitcher vs. Batter:** Simulación en dos fases. El lanzador elige tipo de pitcheo y zona (1 al 9). El bateador decide tipo de swing (`NORMAL`, `POWER`, `TAKE`, `BUNT`) y adivina zona/picheo.
* **Modelo Probabilístico Statcast:** Tasa de abanicado (*Whiff%*) ajustada por atributos y lectura de zona, con distribución de BABIP realista (~30% hits, ~70% outs en pelotas en juego).
* **Mecánicas Tácticas Avanzadas:**
  * **Mazos y Manos:** Robo automático de cartas tácticas por entrada, descarte tras su uso y rebarajado automático.
  * **Fatiga del Lanzador:** Degradación progresiva de atributos (*Control*, *Velocidad*, *Movimiento*) tras superar el umbral de 60 picheos.
  * **Muerte Súbita (Extra Innings):** Corredor automático en 2B en la entrada 10+ y habilitación de cartas tácticas exclusivas.
  * **Acciones Especiales:** Soporte para Toque de Bola (*Bunt*) y Robo de Bases (*Steal*).
  * **Modo PvE (vs. CPU):** Inteligencia artificial para selección de lanzamientos y swings con dificultades configurable (`EASY`, `MEDIUM`, `HARD`).

---

## 3. Arquitectura de Módulos Internos (`backend/app/engine/`)

| Archivo | Responsabilidad / Lógica Interna |
| :--- | :--- |
| **`calculator.py`** | Motor matemático base. Evalúa atributos, modificadores tácticos y decisiones de zona para calcular el evento (`STRIKE`, `BALL`, `HIT_1B`, `HOME_RUN`, etc.) según métricas de Statcast. |
| **`state_manager.py`** | Máquina de estados de la partida. Procesa transiciones de conteo (bolas/strikes), cambio de entradas, actualización de outs y rotación automática del lineup (módulo 9). |
| **`runner_manager.py`** | Gestor de base running. Actualiza el mapa de corredores (`1b`, `2b`, `3b`) y la anotación de carreras según la fuerza del batazo o avance forzado. |
| **`game_over_manager.py`** | Evaluador de victoria. Monitorea condiciones de cierre en 9na entrada, walk-offs o definición en extra innings. |
| **`deck_manager.py`** | Control de cartas. Mezcla el mazo, gestiona la mano (máximo 4 cartas), procesa el robo por inning y la pila de descarte. |
| **`fatigue_manager.py`** | Monitorea el conteo de lanzamientos acumulados por píchera y aplica la curva de degradación de atributos (-3% cada 15 envíos extra). |
| **`tactical_actions.py`** | Lógica probabilística independiente para toques de bola (*Bunt*) y robos de base (*Steal* en 2B/3B). |
| **`fog_of_war.py`** | Enmascara la selección de picheo (`current_pitch`) en la API cuando la respuesta es consultada por el jugador a la ofensiva (bateador). |
| **`websocket_manager.py`** | Administra las conexiones activas agrupadas por `game_id` y transmite eventos JSON a los clientes. |
| **`turn_guard.py`** | Validador de seguridad. Garantiza que solo el jugador con el turno activo (y rol correspondiente) pueda ejecutar acciones (con bypass para `CPU_BOT`). |
| **`cpu_ai.py`** | Motor de decisiones para el modo PvE. Selecciona lanzamientos y swings automáticos ajustados según dificultad. |

---

## 4. Módulos de Autenticación, Datos y Esquemas

* **`backend/app/auth.py`**: Generación y decodificación de tokens JWT (`HS256`).
* **`backend/app/models.py`**:
  * `PlayerCard`: Definición de cartas de jugadores y sus atributos base.
  * `TacticCard`: Definición de cartas de potenciamiento y efectos.
  * `GameSession`: Estado persistido del partido en PostgreSQL (`state_data` JSONB).
* **`backend/app/schemas.py`**: Modelos Pydantic para validación de requests (`CreateGameRequest`, `PitchActionRequest`, `SwingActionRequest`, etc.) y respuestas sanitizadas.

---

## 5. Catálogo de Endpoints de la API

### Autenticación y Gestión de Partida (`routers/games.py` y `auth.py`)
* `POST /api/v1/auth/login`: Autentica al usuario y retorna el token JWT.
* `POST /api/v1/games/create`: Inicializa una partida (PvP o PvE), asigna lineups, genera los mazos iniciales y retorna el ID de sesión.
* `GET /api/v1/games/{game_id}?user_id={id}`: Consulta el estado actual de la partida aplicando sanitización por Niebla de Guerra.

### Catálogo de Cartas (`routers/cards.py`)
* `GET /api/v1/cards/players`: Retorna el catálogo de lanzadores y bateadores disponibles.
* `GET /api/v1/cards/tactics`: Consulta el listado de cartas tácticas.

### Motor de Jugabilidad (`routers/gameplay.py`)
* `POST /api/v1/games/{game_id}/pitch`: **[Lanzador]** Selecciona el tipo de picheo y zona. Notifica `PITCH_COMMITTED` vía WebSocket.
* `POST /api/v1/games/{game_id}/swing`: **[Bateador]** Ejecuta el swing, calcula la jugada, actualiza el estado y transmite `PLAY_RESOLVED`.
* `POST /api/v1/games/{game_id}/play-tactic`: Activa una carta táctica de la mano actual (valida restricción de inning 10+ si aplica).
* `POST /api/v1/games/{game_id}/change-pitcher`: Sustituye al lanzador activo por un relevista del bullpen.
* `POST /api/v1/games/{game_id}/steal`: Intenta el robo de base (2B o 3B).

### Canales en Tiempo Real (`routers/ws.py`)
* `WS /ws/games/{game_id}/{user_id}`: Conexión WebSocket persistente por sala para transmisión instantánea de jugadas y cambios de estado.