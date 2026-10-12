# 🏟️ Design: Selección de Local/Visitante por Usuario

## 🎯 Requisito
Usuario puede elegir si juega como **LOCAL (Home)** o **VISITANTE (Away)**.
La CPU juega en la posición opuesta.

## 🔍 Estado Actual

### Estructura Actual
```
home_user_id  = Usuario humano (siempre)
away_user_id  = "CPU_BOT" (siempre en PVE)

→ Usuario SIEMPRE es local, CPU siempre visitante
```

### Lógica Actual de Turnos
```
Top Inning (Alta):     Visitante batea, Local lanza
Bottom Inning (Baja):  Local batea, Visitante lanza
```

---

## ✅ Cambios Necesarios (SIN ROMPER GAMEPLAY)

### 1️⃣ Schema: Agregar Campo de Preferencia
**Archivo:** `backend/app/schemas/game.py`

```python
class CreateGameRequest(BaseModel):
    home_user_id: str
    away_user_id: Optional[str] = "CPU_BOT"
    game_mode: str
    difficulty: Optional[str]
    total_innings: Optional[int]
    # ⭐ NUEVO CAMPO
    player_position: str = Field("HOME", description="'HOME' o 'AWAY' - posición del usuario")
    # ... resto de campos
```

### 2️⃣ Router: Mapear Posición a Home/Away
**Archivo:** `backend/app/routers/games.py`

```python
@router.post("/create")
def create_game_session(payload: CreateGameRequest, db: Session = Depends(get_db)):
    """
    Cambio: Mapear player_position a home/away dinámicamente
    """
    
    # ⭐ MAPEO: Si usuario quiere ser visitante, intercambiar posiciones
    if payload.player_position == "AWAY":
        # Usuario es visitante → CPU es local
        home_user_id = "CPU_BOT"
        away_user_id = payload.home_user_id  # El usuario va al away
        home_team_id = payload.away_user_id  # CPU toma el equipo rival
        away_team_id = payload.away_user_id  # Usuario mantiene equipo elegido
    else:
        # Comportamiento actual (HOME)
        home_user_id = payload.home_user_id
        away_user_id = "CPU_BOT"
        home_team_id = payload.away_user_id  # Equipo rival
        away_team_id = payload.away_user_id
    
    # Resto de la lógica igual, pero usar variables mapeadas
    game = GameSession(
        id=...,
        home_user_id=home_user_id,
        away_user_id=away_user_id,
        state_data={...}
    )
```

### 3️⃣ Lógica de Turnos (SIN CAMBIOS)
**Importante:** La lógica de turnos se mantiene igual

```
Top Inning:     away_user_id batea, home_user_id lanza
Bottom Inning:  home_user_id batea, away_user_id lanza
```

**Resultado:**
- Si usuario elige HOME: juega normal (batea en baja)
- Si usuario elige AWAY: batea en alta, lanza en baja ✅

---

## 🗂️ Cambios por Archivo

### A. `schemas/game.py`
- ✅ Agregar `player_position: str = "HOME"`
- ✅ Documentar significado en docstring

### B. `routers/games.py` (función `create_game_session`)
- ✅ Leer `payload.player_position`
- ✅ Intercambiar home/away si es "AWAY"
- ✅ Mantener todo lo demás igual

### C. Frontend (No crítico para backend)
- ✅ Agregar botones/selector en lobby
- ✅ Pasar `player_position` en payload

---

## 🧪 Validación (SIN ROMPER GAMEPLAY)

### Caso 1: Usuario elige HOME (actual)
```
Entrada: player_position = "HOME"
home_user_id = "user_123"
away_user_id = "CPU_BOT"

Top:    CPU batea, Usuario lanza ✓
Bottom: Usuario batea, CPU lanza ✓
```

### Caso 2: Usuario elige AWAY (nuevo)
```
Entrada: player_position = "AWAY"
home_user_id = "CPU_BOT"      ← invertido
away_user_id = "user_123"     ← invertido

Top:    Usuario batea, CPU lanza ✓
Bottom: CPU batea, Usuario lanza ✓
```

---

## 📋 Cambios SEGUROS (NO afectan gameplay)

| Sistema | ¿Se ve afectado? | Por qué |
|---------|------------------|---------|
| Turno de turnos | ✅ NO | Lógica es igual, solo cambia quién está en home/away |
| Cálculos de stats | ✅ NO | Usan datos del jugador, no importa posición |
| Fog of War | ✅ NO | Ya valida por `user_id`, funciona igual |
| Fatiga | ✅ NO | Sigue a pitcher, no a posición |
| Resultados | ✅ NO | Equipos/jugadores tienen stats independientes |

---

## ⚠️ Validaciones Necesarias

```python
if payload.player_position not in ["HOME", "AWAY"]:
    raise HTTPException(
        status_code=400,
        detail="player_position debe ser 'HOME' o 'AWAY'"
    )
```

---

## 🎮 Experiencia del Usuario

### Flujo Actual
```
1. Selecciona rival CPU
2. Crea partida
3. Siempre es LOCAL
```

### Flujo Nuevo
```
1. Selecciona rival CPU
2. Elige: "Jugar como LOCAL" vs "Jugar como VISITANTE"
3. Crea partida
4. Juega en la posición elegida ✓
```

---

## 📝 Resumen de Cambios

| Componente | Cambio | Complejidad |
|-----------|--------|------------|
| Schema | +1 campo | ⭐ Trivial |
| Router create | +8 líneas de mapeo | ⭐⭐ Simple |
| Lógica gameplay | 0 cambios | ✅ Cero riesgo |
| Frontend | UI selector | ⭐⭐⭐ Moderado |
| Tests | Validar ambos caminos | ⭐⭐ Estándar |

