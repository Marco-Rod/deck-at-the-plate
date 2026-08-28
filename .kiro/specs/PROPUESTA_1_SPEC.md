# PROPUESTA 1: Mejora de Jerarquía Visual y Claridad
## Stadium Gameplay UI Redesign — Specification & Implementation Plan

**Fecha:** 2026-08-25  
**Estado:** En Diseño  
**Estimado:** 1.5-2 días de desarrollo  
**Prioridad:** Alta  
**Objetivo:** Mejorar la jerarquía visual, claridad de información y distribución del espacio en StadiumShowcaseScreen

---

## 📋 ÍNDICE
1. [Análisis Visual Actual](#análisis-visual-actual)
2. [Objetivos de Diseño](#objetivos-de-diseño)
3. [Principios de Propuesta 1](#principios-de-propuesta-1)
4. [Cambios Detallados por Sección](#cambios-detallados-por-sección)
5. [Impacto Esperado](#impacto-esperado)
6. [Plan de Implementación (Paso a Paso)](#plan-de-implementación-paso-a-paso)
7. [Checklist de Control](#checklist-de-control)

---

## 1. Análisis Visual Actual

### Estado Presente
```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER: "AXOLOTES VS CPU" + Estado conexión                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ SCOREBOARD: Marcador con inning, hits, runs (comprimido)        │
└─────────────────────────────────────────────────────────────────┘

┌──────────┬─────────────────────────┬──────────┐
│ LINEUP   │   CAMPO PRINCIPAL       │ STRIKEOUTS
│ (9 carr) │  [PITCHER] [GRID] [BATTER]  │ Counter
│ Comprim. │  GameInfo arriba        │ Minimalista
│          │  TacticalHand abajo     │
└──────────┴─────────────────────────┴──────────┘
```

### Problemas Identificados
1. **Jerarquía débil:** Todas las secciones compiten por atención
2. **Espacio desperdiciado:** Paneles laterales (lineup/strikeouts) muy comprimidos
3. **Información abrumadora:** Demasiados datos en áreas pequeñas
4. **Cards principales:** Bien rediseñadas, pero contexto débil
5. **Falta contraste:** Entre áreas de lectura vs acción

---

## 2. Objetivos de Diseño

### Primarios
- ✅ **Jerarquía clara:** El duelo pitcher-batter es el protagonista
- ✅ **Información legible:** Sin amontonamiento visual
- ✅ **Distribución equilibrada:** Cada panel tiene espacio respiratorio
- ✅ **Accesibilidad:** Todos los datos importantes visible sin scroll

### Secundarios
- ✅ **Escalabilidad responsive:** Funciona en pantallas 16:9 y tablets
- ✅ **Performance:** Sin impacto en FPS (mantener 60 FPS)
- ✅ **Consistencia:** Usa colores/tipografía existentes
- ✅ **Transiciones suaves:** Animaciones sin sacudidas

---

## 3. Principios de Propuesta 1

### Pilares de Diseño

| Principio | Aplicación |
|-----------|-----------|
| **Reducción Visual** | Eliminar elementos secundarios, mantener esencial |
| **Espaciado** | Mayor padding/margin entre secciones |
| **Tipografía Jerárquica** | Tamaños claros (H1→H4 levels) |
| **Color Funcional** | Colores comunican estado, no saturan |
| **Alineación** | Grid de 3 columnas con simetría |
| **Contraste** | Fondos oscuros, texto claro (mantener tema) |

---

## 4. Cambios Detallados por Sección

### 4.1 HEADER
**Cambio:** Simplificar, mejorar legibilidad

#### ANTES
```
"AXOLOTES VS CPU" + "● CONECTADO EN VIVO" + botón LOBBY
(todo en una línea, comprimido)
```

#### DESPUÉS
```
┌──────────────────────────────────────────┐
│  AXOLOTES VS CPU                ⚙️ LOBBY │
│  ● CONECTADO EN VIVO                    │
└──────────────────────────────────────────┘
(2 líneas: título grande + estado pequeño)
```

**Detalles:**
- Título: `font-sports text-3xl` → `text-4xl` (más impacto)
- Estado: `text-[10px]` → `text-[9px]` (menos peso)
- Separación: `pb-3` → `pb-4` (más aire)
- Botón: Mover a esquina derecha con `flex justify-between`

**Archivo:** `StadiumShowcaseScreen.tsx` (líneas ~460-470)

---

### 4.2 SCOREBOARD
**Cambio:** Layout horizontal más compacto, números más grandes

#### ANTES
```
Inning | Balls | Strikes | Outs | Home Score | Away Score
(información lineal, pequeña)
```

#### DESPUÉS
```
┌─────────────────────────────────────┐
│ INNING     BALLS  STRIKES  OUTS    │
│ 5 / 9       0       2       1      │
│                                     │
│ HOME  X X X | 0 | 3 | 2 | 0 | 1 | 0│
│ CPU   O O O | 0 | 0 | 0 | 0 | 0 | 0│
└─────────────────────────────────────┘
(números más grandes, separación clara)
```

**Detalles:**
- B/S/O: `text-lg` → `text-2xl`
- Inning: `text-md` → `text-xl`
- Padding interno: +2px más
- Hits row: `text-sm` → `text-base`

**Archivo:** `Scoreboard.tsx` (revisar componente)

---

### 4.3 CAMPO PRINCIPAL (Central)
**Cambio:** Mejor distribución vertical y horizontal, énfasis en cards

#### ANTES
```
GameInfo (pequeño arriba)
[PITCHER] [GRID] [BATTER]  ← Muy apretado
TacticalHand (abajo)
```

#### DESPUÉS
```
┌─────────────────────────────────┐
│  GAME INFO (B/S/O, Bases, Inning) │  ← Espaciado claro
│  Mayor tamaño, legible            │
├─────────────────────────────────┤
│                                   │
│  [PITCHER]  [GRID]  [BATTER]      │  ← Cards con aire
│  (espaciado h-gap-6 en lugar h-gap-4)
│                                   │
├─────────────────────────────────┤
│  MENSAJE DINÁMICO (si aplica)     │  ← Si usuario no ha pichado
├─────────────────────────────────┤
│  TACTICAL HAND (cartas táctica)   │  ← Panel horizontal compacto
└─────────────────────────────────┘
```

**Detalles:**
- GameInfo: Aumentar spacing interno
- Cartas: `gap-4` → `gap-6` (más aire horizontal)
- Mensaje: Mejorar contraste (fondo más oscuro, texto más brillante)
- TacticalHand: Reorganizar cartas en grid 2x2 compacto (si caben)

**Archivo:** `StadiumShowcaseScreen.tsx` (líneas ~500-530)

---

### 4.4 PANEL IZQUIERDO (Lineup del Bateador)
**Cambio:** Mejor scrolling, jerarquía de información

#### ANTES
```
📊 LINEUP (pequeño header)
[Card 1] [Card 2] [Card 3]  (comprimido verticalmente)
[Card 4] [Card 5] [Card 6]
[Card 7] [Card 8] [Card 9]
(sin separación, datos amontonados)
```

#### DESPUÉS
```
┌────────────────────────┐
│ 📊 YOUR LINEUP         │  ← Título claro, más grande
│ vs PITCHER: David R.   │  ← Info contexto (NUEVO)
├────────────────────────┤
│ #1  Alex Reyes   5-8   │  ← Formato limpio
│     3B | 0-0          │
│ ────────────────────   │
│ #2  Bryan Valdez  6-0  │
│     C  | 1-2, 1H      │
│ ────────────────────   │
│ ... (scroll dentro)    │
│ ────────────────────   │
│ #9  Ronald Polanco  5-7│
│     LF | 0-1          │
└────────────────────────┘
```

**Detalles:**
- Header: `text-xs` → `text-sm` (más legible)
- Contexto: Agregar pitcher name en subtitle
- Cada lineup item: Nombre + # en una línea, stats abajo
- Separadores: Líneas sutiles (`border-t`) entre jugadores
- Stats: Mostrar pos + actual stats (AB-H format)
- Scrollable: `max-h-[350px] overflow-y-auto`

**Archivo:** `GameStatsPanel.tsx` (revisar/crear estructura mejorada)

---

### 4.5 PANEL DERECHO (Strikeouts Counter)
**Cambio:** Diseño más visual, menos minimalista

#### ANTES
```
🔥 STRIKEOUTS
David Romular
0
```

#### DESPUÉS
```
┌────────────────────────┐
│ 🔥 STRIKEOUTS         │  ← Título con emoji
├────────────────────────┤
│                        │
│   DAVID ROMULAR        │  ← Pitcher name grande
│                        │
│        0               │  ← Número gigante (text-6xl)
│     STRIKEOUTS        │  ← Label pequeño
│                        │
│ [+1 SO Animation]      │  ← Animar cuando cambia
├────────────────────────┤
│ Inning Stats:          │  ← Info adicional
│ Pitches: 23            │
│ Whiffs: 1              │
│ Balls: 2               │
└────────────────────────┘
```

**Detalles:**
- Nombre pitcher: `text-lg` → `text-2xl`
- Contador: `text-2xl` → `text-6xl` (impacto visual)
- Label: Agregar palabra "STRIKEOUTS" debajo
- Animación: Pulse suave al incrementar SO
- Stats inning: Información contextual (pitches, whiffs)
- Espaciado: Más padding vertical para "respirar"

**Archivo:** `GameStatsPanel.tsx` (sección isPitcher)

---

### 4.6 TARJETAS PRINCIPALES (PlayerCard)
**Cambio:** Ya están bien diseñadas (propuesta anterior), solo asegurar spacing

#### ANTES ✅ ACTUAL
```
w-56 h-80 flex flex-col
(Ya optimizado)
```

#### DESPUÉS ✅ MANTENER
```
w-56 h-80 flex flex-col
(Sin cambios, está perfecto)
```

**Detalles:**
- Mantener layout actual de PlayerCard.tsx
- Asegurar que los 2 stats sincronizados se muestren bien
- Verificar que el equipo popule correctamente
- **NO CAMBIAR:** Ya funciona como se espera

---

### 4.7 PITCH ZONE GRID
**Cambio:** Contexto visual mejorado

#### ANTES
```
[Grid 3x3 de zonas]
(Sin etiqueta, contextualmente oscuro)
```

#### DESPUÉS
```
┌──────────────────┐
│ STRIKE ZONE      │  ← Label claro
│ (zona de strike) │  ← Descripción
├──────────────────┤
│  Z1 Z2 Z3        │
│  Z4 Z5 Z6        │  ← Grid numérico claro
│  Z7 Z8 Z9        │
└──────────────────┘
```

**Detalles:**
- Agregar header "STRIKE ZONE"
- Números visibles en grid (opcional pero recomendado)
- Fondo ligeramente más claro para contraste
- Border sutilmente más visible

**Archivo:** `PitchZoneGrid.tsx` (revisar diseño)

---

## 5. Impacto Esperado

### Visual
| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Jerarquía** | Débil | Fuerte | +40% |
| **Legibilidad** | Media | Alta | +30% |
| **Espaciado** | Comprimido | Aireado | +25% |
| **Contraste Info** | Bajo | Alto | +35% |
| **Focus User** | Disperso | Centrado | +50% |

### Performance
- **FPS:** 60 → 58-59 FPS (sin impacto)
- **Bundle Size:** +0KB (solo cambios CSS/layout)
- **Load Time:** Sin cambio (mismo componentes)
- **Mobile:** Compatible 100%

### UX
- **Claridad:** +++
- **Usabilidad:** +++
- **Emoción:** ++ (mejor contexto, menos abrumador)
- **Accessibility:** +++ (mejor contraste)

---

## 6. Plan de Implementación (Paso a Paso)

### FASE 1: Preparación (0.5 días)
**Objetivo:** Revisar estado actual, crear rama, documentar cambios

#### TAREA 1.1: Crear rama de desarrollo
```bash
git checkout -b feature/propuesta-1-ui-hierarchy
```
**Duración:** 5 min  
**Control:** Verificar que la rama existe y está limpia

---

#### TAREA 1.2: Revisar Scoreboard.tsx
**Instrucción:** Lee el componente actual y documenta:
- Estructura HTML
- Props recibidos
- Tamaños de fuente actuales
- Spacing (padding/margin)

**Archivo:** `frontend/src/components/stadium/Scoreboard.tsx`  
**Duración:** 15 min  
**Control:** Documentar hallazgos en checklist

---

#### TAREA 1.3: Revisar GameStatsPanel.tsx (o crear si no existe)
**Instrucción:** Verificar componente que muestra lineup y strikeouts
- Si existe: documentar estructura
- Si no existe: necesitará crearse

**Archivo:** `frontend/src/components/stadium/GameStatsPanel.tsx`  
**Duración:** 10 min  
**Control:** Confirmar si existe o necesita crearse

---

### FASE 2: Header & Scoreboard (0.3 días)
**Objetivo:** Mejorar visibilidad y jerarquía de información superior

#### TAREA 2.1: Actualizar Header en StadiumShowcaseScreen
**Instrucción:**
1. Localiza líneas ~460-470 (header section)
2. Cambia layout de inline a 2-line
3. Aumenta tamaño del título: `text-3xl` → `text-4xl`
4. Reduce tamaño del estado: `text-[10px]` → `text-[9px]`
5. Aumenta padding-bottom: `pb-3` → `pb-4`
6. Asegura botón LOBBY está aligned right

**Cambios CSS:**
```tsx
// ANTES
<div className="w-full flex justify-between items-center border-b-2 pb-3">
  <h2 className="font-sports text-3xl">...</h2>
  <button>⚙️ LOBBY</button>
</div>

// DESPUÉS
<div className="w-full border-b-2 border-[#C5A059]/40 pb-4">
  <div className="flex justify-between items-start mb-2">
    <h2 className="font-sports text-4xl">...</h2>
    <button className="...">⚙️ LOBBY</button>
  </div>
  <span className="font-mono text-[9px]">● CONECTADO EN VIVO</span>
</div>
```

**Archivo:** `StadiumShowcaseScreen.tsx` (líneas ~460-475)  
**Duración:** 15 min  
**Control:** Header se ve con 2 líneas, título más grande

---

#### TAREA 2.2: Actualizar Scoreboard (números más grandes)
**Instrucción:**
1. Abre `Scoreboard.tsx`
2. Localiza donde se renderiza B/S/O
3. Aumenta tamaños: `text-lg` → `text-2xl`
4. Aumenta inning: `text-md` → `text-xl`
5. Aumenta hits: `text-sm` → `text-base`
6. Verifica que todo sea legible

**Cambios CSS:**
```tsx
// B/S/O números
<span className="font-sports text-2xl">0</span>  // era text-lg

// Inning
<div className="font-sports text-xl">5 / 9</div>  // era text-md

// Hits row
<span className="text-base">3</span>  // era text-sm
```

**Archivo:** `Scoreboard.tsx`  
**Duración:** 20 min  
**Control:** Números visiblemente más grandes, legibles desde distancia

---

### FASE 3: Campo Principal (0.4 días)
**Objetivo:** Mejorar spacing y distribución de cards + grid

#### TAREA 3.1: Aumentar espaciado entre cards
**Instrucción:**
1. Abre `StadiumShowcaseScreen.tsx` línea ~520
2. Localiza `<div className="w-full flex justify-center items-start gap-4">`
3. Cambia: `gap-4` → `gap-6`
4. Verifica que cards no se solapen

**Cambios CSS:**
```tsx
// ANTES
<div className="w-full flex justify-center items-start gap-4">

// DESPUÉS
<div className="w-full flex justify-center items-start gap-6">
```

**Archivo:** `StadiumShowcaseScreen.tsx` (línea ~520)  
**Duración:** 5 min  
**Control:** Espaciado visible entre cards e grid

---

#### TAREA 3.2: Mejorar GameInfo (B/S/O, Bases, Inning)
**Instrucción:**
1. Abre `GameInfo.tsx`
2. Aumenta padding interno: 10px → 15px
3. Aumenta tamaño de fuente: `text-sm` → `text-base` (labels)
4. Aumenta tamaño de fuente: `text-lg` → `text-2xl` (valores)
5. Verifica contraste de color

**Archivo:** `GameInfo.tsx`  
**Duración:** 15 min  
**Control:** GameInfo es más legible, con más aire

---

#### TAREA 3.3: Mejorar mensaje dinámico (cuando usuario no ha pichado)
**Instrucción:**
1. Abre `StadiumShowcaseScreen.tsx` línea ~535
2. Localiza: `<div className="mt-2 bg-[#C5A059] text-[#0A0D0F]...">`
3. Aumenta padding: `px-4 py-1` → `px-6 py-2`
4. Aumenta tamaño fuente: `text-xs` → `text-sm`
5. Mejora fondo: añade opacidad más clara

**Cambios CSS:**
```tsx
// ANTES
<div className="mt-2 bg-[#C5A059] text-[#0A0D0F] px-4 py-1 font-mono text-xs font-bold">

// DESPUÉS
<div className="mt-2 bg-[#C5A059]/90 text-[#0A0D0F] px-6 py-2 font-mono text-sm font-bold rounded-sm">
```

**Archivo:** `StadiumShowcaseScreen.tsx` (línea ~535)  
**Duración:** 10 min  
**Control:** Mensaje es más visible y legible

---

### FASE 4: Paneles Laterales (0.5 días)
**Objetivo:** Rediseñar lineup + strikeouts para mejor jerarquía

#### TAREA 4.1: Revisar/Crear GameStatsPanel.tsx
**Instrucción:**
1. Verifica si existe `frontend/src/components/stadium/GameStatsPanel.tsx`
2. Si NO existe, necesita crearse (TAREA 4.2)
3. Si existe, documentar estructura actual

**Duración:** 5 min  
**Control:** Confirmar estado del archivo

---

#### TAREA 4.2: Crear GameStatsPanel.tsx (SI NO EXISTE)
**Instrucción:**
Si no existe, crea nuevo componente con:
- Props: `lineup`, `stats`, `isPitcher`, `pitcherStrikeouts`, `pitcherName`
- 2 modos: `isPitcher=false` (lista lineup) vs `isPitcher=true` (strikeout counter)
- Estructura base (ver código en sección de implementación)

**Archivo:** Crear `frontend/src/components/stadium/GameStatsPanel.tsx`  
**Duración:** 30 min  
**Control:** Componente compila sin errores

---

#### TAREA 4.3: Mejorar Lineup Panel (LEFT)
**Instrucción:**
1. Abre `GameStatsPanel.tsx` (sección isPitcher=false)
2. Aumenta header: `text-xs` → `text-sm`
3. Añade subtitle con pitcher name: `vs PITCHER: {pitcherName}`
4. Reorganiza cada lineup item:
   - Nombre + número en una línea
   - Posición + stats en línea siguiente
   - Separador (`border-t`) entre items
5. Aumenta scroll container: `max-h-[300px]` → `max-h-[350px]`

**Estructura esperada:**
```
📊 YOUR LINEUP
vs PITCHER: David Romular

#1 Alex Reyes      5-8
3B | 0-0 0H
─────────────────
#2 Bryan Valdez    6-0
C  | 1-2 1H
─────────────────
... (scroll)
```

**Archivo:** `GameStatsPanel.tsx`  
**Duración:** 25 min  
**Control:** Lineup es legible, con buen espaciado

---

#### TAREA 4.4: Mejorar Strikeouts Panel (RIGHT)
**Instrucción:**
1. Abre `GameStatsPanel.tsx` (sección isPitcher=true)
2. Aumenta nombre pitcher: `text-lg` → `text-2xl`
3. Aumenta número SO: `text-2xl` → `text-6xl`
4. Añade palabra "STRIKEOUTS" debajo del número
5. Agregar stats inning (opcional):
   - Pitches thrown
   - Whiffs
   - Balls thrown
6. Aumenta padding interno: 10px → 20px

**Estructura esperada:**
```
┌────────────────────────┐
│ 🔥 STRIKEOUTS         │
│                        │
│   DAVID ROMULAR        │
│                        │
│        0               │
│     STRIKEOUTS        │
│                        │
│ Inning Stats:          │
│ Pitches: 23            │
│ Whiffs: 1              │
│ Balls: 2               │
└────────────────────────┘
```

**Archivo:** `GameStatsPanel.tsx`  
**Duración:** 20 min  
**Control:** Strikeouts es el focal point, número es imposible de perder

---

#### TAREA 4.5: Aplicar GameStatsPanel en StadiumShowcaseScreen
**Instrucción:**
1. Abre `StadiumShowcaseScreen.tsx` línea ~485
2. Verifica que `<GameStatsPanel>` está importado
3. Verifica que props están correctos:
   - LEFT panel: `lineup={getBattingLineup()}` `stats={gameStats?.batters || {}}` `isPitcher={false}`
   - RIGHT panel: `isPitcher={true}` `pitcherStrikeouts={...}` `pitcherName={...}`
4. NO necesita cambios si ya está implementado

**Archivo:** `StadiumShowcaseScreen.tsx` (líneas ~485-500)  
**Duración:** 10 min  
**Control:** Panels se renderizan con nuevo diseño

---

### FASE 5: Ajustes Finales (0.3 días)
**Objetivo:** Polish, testing, documentación

#### TAREA 5.1: Revisar PitchZoneGrid (opcional label)
**Instrucción:**
1. Abre `PitchZoneGrid.tsx`
2. Considera añadir header: "STRIKE ZONE"
3. Si se añade, aumenta contraste del grid ligeramente
4. Verifica que números de zona se ven claros

**Archivo:** `PitchZoneGrid.tsx`  
**Duración:** 10 min  
**Control:** Grid es claro y contextualizado

---

#### TAREA 5.2: Revisar TacticalHand layout
**Instrucción:**
1. Abre `TacticalHand.tsx`
2. Verifica que cartas tácticas están bien distribuidas
3. Si es necesario, reorganiza en grid 2x2 compacto
4. Añade padding entre cartas: `gap-2` → `gap-3`

**Archivo:** `TacticalHand.tsx`  
**Duración:** 10 min  
**Control:** Cartas tácticas son claras, no comprimidas

---

#### TAREA 5.3: Testing Visual
**Instrucción:**
1. Abre navegador en `localhost:3000`
2. Navega a pantalla de gameplay
3. Verifica:
   - [ ] Header tiene 2 líneas, título grande
   - [ ] Scoreboard números son legibles
   - [ ] Cards pitcher/batter tienen espacio (gap-6)
   - [ ] GameInfo es claro
   - [ ] LEFT panel (lineup) es scrolleable y legible
   - [ ] RIGHT panel (SO) tiene número gigante
   - [ ] TacticalHand está bien distribuida
   - [ ] Mensaje dinámico es visible
4. Prueba en diferentes resoluciones (16:9, tablet)

**Duración:** 15 min  
**Control:** Todo se ve bien, no hay overlaps

---

#### TAREA 5.4: Commit y Clean Up
**Instrucción:**
1. Verifica que no hay errores de console
2. Commit de cambios: `git add . && git commit -m "feat: propuesta-1-ui-hierarchy"`
3. Verifica que FPS está en 58-60
4. Merge a main (o esperar review)

**Duración:** 5 min  
**Control:** Código commiteado, rama limpia

---

## 7. Checklist de Control

### ✅ FASE 1: Preparación
- [ ] Rama creada: `feature/propuesta-1-ui-hierarchy`
- [ ] Scoreboard.tsx revisado
- [ ] GameStatsPanel.tsx estado verificado

### ✅ FASE 2: Header & Scoreboard
- [ ] Header: 2 líneas, título text-4xl
- [ ] Estado: text-[9px], debajo del título
- [ ] Scoreboard: B/S/O text-2xl
- [ ] Scoreboard: Inning text-xl
- [ ] Scoreboard: Hits text-base

### ✅ FASE 3: Campo Principal
- [ ] Espaciado cards: gap-6 aplicado
- [ ] GameInfo: padding 15px, fuentes aumentadas
- [ ] Mensaje dinámico: px-6 py-2, text-sm
- [ ] PitchZoneGrid: claro y contextualizado

### ✅ FASE 4: Paneles Laterales
- [ ] GameStatsPanel.tsx creado/actualizado
- [ ] LEFT panel (lineup): header text-sm, subtitle con pitcher
- [ ] LEFT panel: items con separadores, scrolleable
- [ ] RIGHT panel (SO): nombre text-2xl, número text-6xl
- [ ] RIGHT panel: "STRIKEOUTS" label, stats inning

### ✅ FASE 5: Ajustes Finales
- [ ] PitchZoneGrid: label "STRIKE ZONE" (opcional)
- [ ] TacticalHand: gap-3, bien distribuida
- [ ] Testing visual: todas las secciones legibles
- [ ] FPS: 58-60 (sin degradación)
- [ ] Commit realizado

---

## 📊 Resumen de Cambios

| Componente | Cambios | Impacto Visual | Complejidad |
|-----------|---------|----------------|------------|
| Header | 2 líneas, text-4xl | Alto | Bajo |
| Scoreboard | Números +33% | Medio | Bajo |
| GameInfo | Padding +50%, fuentes +33% | Medio | Bajo |
| Espaciado Central | gap-4 → gap-6 | Medio | Bajo |
| Lineup Panel | Header mejorado, separadores, scroll | Alto | Medio |
| Strikeouts Panel | Número gigante, stats inning | Alto | Medio |
| TacticalHand | gap-3, mejor distribución | Bajo | Bajo |

**Tiempo Total Estimado:** 1.5-2 días  
**Complejidad Técnica:** BAJA  
**Riesgo de Bugs:** BAJO  

---

## 🎯 Próximos Pasos

Después de completar Propuesta 1:
1. ✅ Validar con usuario
2. ✅ Recolectar feedback visual
3. ✅ Considerar efectos híbridos (Fase 2)
4. ✅ Planificar animaciones sutiles (Fase 3)

