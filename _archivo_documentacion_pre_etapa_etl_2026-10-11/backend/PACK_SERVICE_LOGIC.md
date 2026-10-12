# Pack Service Logic - Starter Pack (13 Cartas)

## Overview
El servicio `PackService` asigna un mazo inicial de 13 cartas al usuario cuando completa la onboarding.

**Lógica simplificada y clara:**
- **7 cartas del equipo favorito:** 1 del tier máximo + 6 de tiers inferiores
- **6 cartas de otros equipos:** para cubrir posiciones y rellenar
- **Total:** 13 cartas con cobertura de posiciones

---

## Clases y Constantes

### `StarterPackConfig`
Configuración centralizada del starter pack.

```python
REQUIRED_POSITIONS = {"P", "C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}
PITCHER_POSITIONS = {"SP", "RP", "CP"}
FIELDER_POSITIONS = {"C", "1B", "2B", "3B", "SS", "LF", "CF", "RF"}

FAVORITE_TEAM_CARDS = 7  # Cartas del equipo favorito
OTHER_TEAMS_CARDS = 6    # Cartas de otros equipos
TOTAL_CARDS = 13         # Total del pack

TIER_PRIORITY = ["DIAMOND", "GOLD", "SILVER", "BRONZE", "COMMON"]
```

### `PackService`
Servicio para gestionar starter packs y sobre de cartas.

Drop rates para sobres de pago:
- **BRONZE:** 500 stamps, 3 cartas
- **GOLD:** 1500 stamps, 4 cartas  
- **DIAMOND:** 4000 stamps, 5 cartas

---

## Métodos Estáticos

### `_group_cards_by_rarity(cards)`
Agrupa cartas por rareza.

**Input:**
- `cards`: Lista de cartas

**Output:**
```python
{
    "DIAMOND": [...cartas DIAMOND...],
    "GOLD": [...cartas GOLD...],
    "SILVER": [...cartas SILVER...],
    "BRONZE": [...cartas BRONZE...],
    "COMMON": [...cartas COMMON...]
}
```

---

### `_get_missing_positions(selected_cards)`
Identifica qué posiciones NO están cubiertas.

**Input:**
- `selected_cards`: Cartas ya seleccionadas

**Output:**
```python
['3B', 'SS', 'RF']  # Posiciones faltantes
```

---

## Función Principal: `assign_starter_pack`

### PASO 1: Obtener Usuario y Equipo
```python
# Buscar usuario
user = db.query(User).filter(User.id == user_id).first()

# Asignar favorite_team_id si no existe (respeta valor previo)
if not user.favorite_team_id:
    user.favorite_team_id = team_id
```

**Salida:** Usuario con `favorite_team_id` establecido

---

### PASO 2: Obtener Cartas del Equipo Favorito
```python
team_cards = db.query(PlayerCardModel).filter(
    PlayerCardModel.team_id == team_id
).all()
```

**Salida:** Lista de todas las cartas del equipo elegido

---

### PASO 3: Seleccionar 7 Cartas del Equipo Favorito

**Lógica:**
1. Agrupar cartas por tier
2. Encontrar el tier **MÁXIMO** que el equipo TENGA en BD
3. Tomar **1 carta** del tier máximo (random)
4. Rellenar **6 cartas** con tiers inferiores (descendente: próximo tier → siguiente → etc.)

**Ejemplo:**
- Tier máximo = GOLD
- Tomar 1 GOLD
- Rellenar 6 con: SILVER → BRONZE → COMMON

```python
# Encontrar tier máximo
highest_tier = next((t for t in TIER_PRIORITY if team_by_tier[t]), None)

# Tomar 1 del tier máximo
selected_team_cards = [random.choice(team_by_tier[highest_tier])]

# Rellenar 6 restantes
remaining_needed = 6
for tier in TIER_PRIORITY[highest_idx + 1:]:  # Tiers INFERIORES
    available = [c for c in team_by_tier[tier] if c.id not in selected_set]
    take_count = min(remaining_needed, len(available))
    selected = random.sample(available, take_count)
    selected_team_cards.extend(selected)
    remaining_needed -= take_count
```

**Salida:** 7 cartas del equipo favorito (diversificadas por tier)

---

### PASO 4: Verificar Posiciones Cubiertas
```python
missing_positions = _get_missing_positions(selected_cards)
cards_needed = TOTAL_CARDS - len(selected_cards)  # Normalmente 6
```

**Salida:**
- `missing_positions`: Posiciones sin cubrir (Ej: ['3B', 'SS', ...])
- `cards_needed`: Cartas a obtener de otros equipos

---

### PASO 5: Obtener Cartas de Otros Equipos
```python
other_team_cards = db.query(PlayerCardModel).filter(
    PlayerCardModel.team_id != team_id
).all()
```

**Salida:** Lista de cartas de todos los demás equipos

---

### PASO 6: Seleccionar Cartas de Otros Equipos

**Lógica de Priorización:**
1. **FASE 1:** Cubrir posiciones faltantes (prioridad máxima)
2. **FASE 2:** Rellenar slots restantes sin restricción

```python
other_team_selected = []

# FASE 1: Cubrir posiciones faltantes
for pos in missing_positions:
    if len(other_team_selected) >= cards_needed:
        break
    matching = [c for c in other_team_cards 
                if c.position == pos and c.id not in selected_set]
    if matching:
        card = random.choice(matching)
        other_team_selected.append(card)
        selected_set.add(card.id)

# FASE 2: Rellenar slots restantes
if len(other_team_selected) < cards_needed:
    remaining = [c for c in other_team_cards if c.id not in selected_set]
    need_more = cards_needed - len(other_team_selected)
    fillback = random.sample(remaining, min(need_more, len(remaining)))
    other_team_selected.extend(fillback)
```

**Salida:** 6 cartas de otros equipos con posiciones prioprizadas

---

### PASO 7: Mezclar Cartas
```python
random.shuffle(selected_cards)
```

**Salida:** 13 cartas en orden aleatorio

---

### PASO 8: Resumen Final
Log de composición:
- **Por equipo:** Cuántas cartas de cada equipo
- **Por rareza:** Cuántas de cada tier
- **Por posición:** Cobertura de posiciones

---

### PASO 9: Guardar en Inventario
```python
for card in selected_cards:
    existing = db.query(UserCardInventory).filter(
        UserCardInventory.user_id == user_id,
        UserCardInventory.card_id == card.id
    ).first()
    
    if not existing:
        inventory_item = UserCardInventory(user_id=user_id, card_id=card.id)
        db.add(inventory_item)
```

**Salida:** Cartas guardadas en `UserCardInventory`

---

### PASO 10: Actualizar Estado del Usuario
```python
user.has_completed_onboarding = True
```

**Salida:** Usuario marcado como onboarding completado

---

### PASO 11: Inicializar Cartera
```python
wallet = db.query(UserWallet).filter(UserWallet.user_id == user_id).first()
if not wallet:
    wallet = UserWallet(user_id=user_id, stamps=1000)
    db.add(wallet)
```

**Salida:** Cartera creada con 1000 stamps (si no existe)

---

### PASO 12: Guardar en BD
```python
db.commit()
```

**Salida:** Todos los cambios persistidos

---

## Función: `open_pack`

Abre un sobre de cartas usando stamps del usuario.

**Pasos:**
1. Validar tipo de sobre (BRONZE/GOLD/DIAMOND)
2. Verificar saldo de stamps
3. Deducir costo
4. Generar cartas según drop rates (probabilidad ponderada)
5. Guardar en inventario
6. Guardar en BD

**Retorna:** Lista de cartas obtenidas

---

## Logging

Todos los pasos generan logs detallados con formato:
```
[PASO N] Descripción
  [INFO_TYPE] Detalle
    - Subdetalle
```

**Ejemplo:**
```
[PASO 3] Seleccionar 7 cartas del equipo favorito
  [TIER_MAXIMO] GOLD (5 cartas disponibles)
    1. Player Name (TEAM) - Pos: SP - GOLD
  [SILVER] Tomadas 3 cartas
    2. Player 2 (TEAM) - Pos: C - SILVER
```

---

## Notas Importantes

✅ **El tier máximo es automático:** Se detecta de las cartas disponibles en BD
✅ **Siempre 1 del tier máximo:** Garantizado en el sobre
✅ **Posiciones prioritarias:** Se intentan cubrir todas las 9 posiciones
✅ **Sin duplicados:** El inventario valida que no existan cartas duplicadas
✅ **favorite_team_id no se sobrescribe:** Respeta valor previo si existe
