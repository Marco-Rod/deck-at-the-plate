# Deck at the Plate — UI Responsive Tuning Instructions v1.3

## Objetivo

Ajustar la implementación actual **sin rediseñar la interfaz ni cambiar sus componentes principales**. La estructura responsive ya es correcta; esta iteración debe mejorar proporciones, jerarquía, uso del espacio y legibilidad.

La referencia es la implementación actual mostrada en las capturas: desktop ultrawide/grande y mobile tipo iPhone.

## Regla principal

> No escalar la interfaz completa. Ajustar cada región mediante CSS Grid/Flexbox, `clamp()`, `minmax()`, `aspect-ratio`, gaps y breakpoints.

Mantener la identidad visual actual: HUD oscuro, bordes finos, acentos naranja/púrpura/verde, tipografía deportiva y composición Pitcher → Strike Zone → Batter.

---

# 1. Problema actual en Desktop

La interfaz ya cabe en el viewport, pero los componentes se perciben como islas separadas dentro de un canvas demasiado grande.

Problemas a corregir:

- Exceso de espacio vertical entre Header, Scoreboard y CoreGameplay.
- Exceso de separación horizontal entre Pitcher, Strike Zone y Batter.
- Strike Zone demasiado grande y dominante.
- Actions aislado en la esquina inferior izquierda.
- LANZAR aislado en la esquina inferior derecha.
- Demasiada distancia entre Batter y Next Batter.
- El HUD no se percibe como un único bloque cohesionado.

## Resultado esperado en Desktop

```text
┌──────────────────────────────────────────────────────────────┐
│ AJO VS CPU                                      FINALIZAR    │
├──────────────────────────────────┬───────────────────────────┤
│ SCOREBOARD                       │ R/H/E · INNING · BASES   │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐   ┌──────────────────┐   ┌────────────┐     │
│  │  PITCHER   │   │   STRIKE ZONE    │   │   BATTER   │     │
│  │    #22     │   │       3 × 3      │   │    #20     │     │
│  │   STATS    │   │                  │   │   STATS    │     │
│  │  STAMINA   │   │                  │   └────────────┘     │
│  └────────────┘   └──────────────────┘   ┌────────────┐     │
│                                           │ NEXT #21   │     │
│                                           └────────────┘     │
├──────────────────────────────────────────────────────────────┤
│ [ACTION] [ACTION] [ACTION] [ACTION]             🔥 LANZAR   │
└──────────────────────────────────────────────────────────────┘
```

El HUD debe estar centrado y compacto. En monitores grandes **no intentar llenar todo el ancho y alto del monitor**. El espacio sobrante pertenece al fondo/estadio.

---

# 2. Desktop — Game Shell

Para `>= 1200px`:

```css
.game-page {
  width: 100%;
  min-height: 100dvh;
}

.game-shell {
  width: min(94vw, 1600px);
  height: 100dvh;
  margin-inline: auto;
  overflow: hidden;
}
```

`overflow: hidden` es únicamente una protección. Nunca debe ocultar controles. Si algo queda cortado, corregir tamaños/gaps.

Todo lo necesario para jugar un turno debe verse simultáneamente sin scroll vertical.

---

# 3. Desktop — Compactar la distribución vertical

No distribuir las secciones usando `space-between`, alturas artificiales o filas `1fr` que generen grandes huecos.

Preferir una grid cuyo contenido determine la altura:

```css
.game-shell {
  display: grid;
  grid-template-rows: auto auto minmax(0, 1fr) auto;
  gap: clamp(10px, 1.4dvh, 18px);
}
```

El orden debe ser:

1. Header
2. Scoreboard + Situation
3. CoreGameplay
4. Actions + Primary Action

Reducir especialmente el espacio actualmente existente entre Scoreboard y CoreGameplay.

---

# 4. Desktop — Scoreboard y situación

Mantenerlos en la misma fila.

```css
.score-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, .9fr);
  gap: clamp(10px, 1vw, 18px);
}
```

No permitir que esta fila crezca verticalmente solo para llenar espacio.

El bloque de situación debe contener de forma compacta:

- R / H / E
- inning
- top/bottom
- bases
- outs cuando aplique

---

# 5. Desktop — CoreGameplay

Debe ser el foco visual principal, pero no ocupar todo el espacio disponible.

```css
.core-gameplay {
  display: grid;
  grid-template-columns:
    minmax(250px, .9fr)
    minmax(300px, 430px)
    minmax(250px, .9fr);
  align-items: start;
  justify-content: center;
  gap: clamp(18px, 2.2vw, 40px);
}
```

No utilizar columnas separadas por enormes `1fr`.

La distancia visual entre los tres elementos debe comunicar una confrontación:

```text
Pitcher  →  Strike Zone  ←  Batter
```

No:

```text
Pitcher                Strike Zone                Batter
```

---

# 6. Desktop — Strike Zone

La Strike Zone actual crece demasiado. Limitarla explícitamente.

```css
.strike-zone {
  width: clamp(300px, 25vw, 430px);
  max-height: min(43dvh, 430px);
  aspect-ratio: 1 / 1;
  justify-self: center;
}
```

La cuadrícula interna 3×3 debe ocupar el área disponible de manera uniforme.

No permitir que la Strike Zone llegue a ~500–600 px simplemente porque existe espacio vertical.

El protagonista es el **matchup completo**, no solamente la zona.

---

# 7. Desktop — Pitcher y Batter

Las cartas deben tener peso visual similar.

```css
.player-card {
  width: 100%;
  max-width: 360px;
  min-width: 250px;
}
```

No estirar horizontalmente la carta solo para llenar la columna.

Mantener visibles:

### Pitcher
- número
- nombre
- VEL / CTRL / MOV
- stamina
- pitch count

### Batter
- número
- nombre
- CON / PWR / SPD

Stamina y pitch count existen **solamente dentro de Pitcher**.

---

# 8. Desktop — Next Batter

Colocar inmediatamente debajo de Batter y en la misma columna.

```css
.batter-column {
  display: grid;
  grid-template-rows: auto auto;
  gap: clamp(8px, 1dvh, 12px);
}

.next-batter {
  height: clamp(60px, 7dvh, 80px);
}
```

Jerarquía obligatoria:

> Current Batter >> Next Batter

Next Batter es un preview táctico, no otra carta completa.

Mostrar únicamente:

- NEXT BATTER
- número
- nombre
- CON / PWR / SPD

Debe conservar un acento verde suficientemente visible para distinguirse, pero sin competir con Current Batter.

---

# 9. Desktop — Actions + LANZAR

No dejarlos en extremos aislados de la pantalla.

Crear una sola región inferior:

```css
.action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: clamp(20px, 3vw, 48px);
}
```

A la izquierda: Action Cards.

A la derecha: LANZAR.

El botón LANZAR debe ser claramente la acción primaria, pero debe sentirse conectado al mismo HUD.

No posicionarlo mediante `position: absolute/fixed` para llevarlo a una esquina del viewport.

---

# 10. Desktop Compact

Para pantallas desktop de poca altura, especialmente `1366×768`:

```css
@media (min-width: 1200px) and (max-height: 800px) {
  .game-shell {
    gap: 8px;
  }

  .strike-zone {
    width: clamp(270px, 34dvh, 340px);
  }

  .next-batter {
    height: 60px;
  }
}
```

En Desktop Compact reducir, en este orden:

1. gaps
2. paddings
3. altura de header/scoreboard
4. Strike Zone
5. padding interno de player cards
6. Action Cards

No eliminar información estratégica.

---

# 11. Mobile — Mantener la arquitectura actual

La nueva arquitectura mobile es correcta. **No volver a apilar Pitcher, Strike Zone y Batter verticalmente.**

Debe mantenerse:

```text
PITCHER | STRIKE ZONE | BATTER
```

Los tres deben ser visibles simultáneamente.

El problema actual es que se compactaron más de lo necesario y queda demasiado espacio vacío debajo.

---

# 12. Mobile — Utilizar mejor el espacio disponible

En dispositivos alrededor de `390×844` y `393×852`, aumentar ligeramente CoreGameplay.

Objetivo aproximado respecto a la implementación actual:

- Pitcher: +10–15%
- Strike Zone: +10–15%
- Batter: +10–15%
- Actions: +5–10% cuando exista espacio
- Next Batter: mantener compacto
- LANZAR: tamaño actual o incremento mínimo

No aplicar `transform: scale()` al conjunto.

Los cambios deben venir de dimensiones fluidas.

---

# 13. Mobile — Grid de CoreGameplay

Utilizar una distribución controlada:

```css
.core-gameplay {
  display: grid;
  grid-template-columns:
    minmax(0, .95fr)
    minmax(108px, 1.15fr)
    minmax(0, .95fr);
  gap: clamp(6px, 2vw, 10px);
  align-items: start;
}
```

La Strike Zone puede ser ligeramente más ancha que las cartas, pero nunca debe comprimirlas hasta volver ilegibles las estadísticas.

---

# 14. Mobile — Strike Zone

Mantenerla cuadrada.

```css
.strike-zone {
  width: 100%;
  aspect-ratio: 1 / 1;
}
```

No darle una altura independiente que distorsione las celdas.

Los nueve botones deben mantener targets táctiles razonables y números legibles.

---

# 15. Mobile — Player Cards

Aumentar ligeramente la presencia visual aprovechando la altura disponible.

No aumentar mucho el ancho porque el viewport es limitado.

Priorizar:

- número del jugador
- nombre
- stats
- stamina/pitches en Pitcher

Texto secundario puede ser más pequeño, pero nunca por debajo de una legibilidad razonable.

Evitar que nombres largos rompan el layout; usar truncado controlado:

```css
.player-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
```

---

# 16. Mobile — Next Batter

La posición actual debajo del Batter es correcta.

Debe ganar ligeramente más contraste visual.

- Mantener compacto.
- Recuperar borde/acento verde.
- Aumentar ligeramente contraste del título y stats.
- No aumentar hasta competir con Current Batter.

---

# 17. Mobile — Actions + LANZAR

Mantener la composición horizontal actual mientras quepa correctamente:

```text
┌──────────────────────┐ ┌──────────────┐
│ ACTION ACTION ACTION │ │  🔥 LANZAR   │
└──────────────────────┘ └──────────────┘
```

Esta solución es preferible a colocar LANZAR debajo porque ahorra altura.

Usar aproximadamente:

```css
.action-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: clamp(8px, 3vw, 14px);
  align-items: center;
}
```

Si en un viewport extremadamente estrecho deja de caber, reducir primero gaps/padding/card width antes de cambiar la arquitectura.

---

# 18. Mobile — No forzar contenido al borde superior

La interfaz debe utilizar mejor la altura, pero no mediante `space-between` para distribuir artificialmente todos los bloques de arriba a abajo.

Preferir flujo natural con gaps consistentes.

El espacio sobrante debe quedar principalmente al final de la pantalla, no repartido como enormes huecos entre componentes.

---

# 19. Breakpoints

Usar como base:

```css
/* Mobile */
@media (max-width: 767px) {}

/* Tablet */
@media (min-width: 768px) and (max-width: 1199px) {}

/* Desktop */
@media (min-width: 1200px) {}

/* Desktop Compact */
@media (min-width: 1200px) and (max-height: 800px) {}
```

No crear breakpoints específicos para cada modelo de iPhone salvo que exista un problema imposible de resolver fluidamente.

---

# 20. Regla para alturas

No usar una altura rígida universal para CoreGameplay.

Desktop:

```css
.core-gameplay-region {
  min-height: 0;
}
```

Los componentes internos deben usar `clamp()` y máximos explícitos.

Si se necesita una referencia de altura:

```css
.core-gameplay {
  max-height: clamp(300px, 42dvh, 520px);
}
```

Pero el tamaño final debe estar limitado también por la Strike Zone y las cards.

---

# 21. Prioridad visual final

La jerarquía debe sentirse así:

1. CoreGameplay: Pitcher ↔ Strike Zone ↔ Batter
2. Scoreboard / situación del partido
3. Action Cards + LANZAR
4. Next Batter
5. Header / Finalizar

No permitir que una Strike Zone sobredimensionada rompa esta jerarquía.

---

# 22. No hacer

No realizar ninguna de estas soluciones:

- No usar `transform: scale()` para adaptar todo el HUD.
- No usar zoom global.
- No hacer la Strike Zone gigante para ocupar espacio desktop.
- No separar Actions y LANZAR mediante posicionamiento absoluto.
- No apilar Pitcher/Zone/Batter en mobile.
- No ocultar información necesaria para evitar overflow.
- No agregar scroll al gameplay desktop como solución.
- No estirar cards hasta llenar columnas arbitrariamente.
- No duplicar stamina o pitch count.
- No cambiar el lenguaje visual existente.

---

# 23. Resoluciones obligatorias de prueba

Validar manualmente al menos:

### Mobile
- 375×812
- 390×844
- 393×852
- 430×932

### Tablet
- 768×1024
- 1024×768

### Desktop
- 1366×768
- 1440×900
- 1920×1080
- 2560×1440
- 3840×2160

Prestar especial atención a `390×844`, `430×932` y `1366×768`.

---

# 24. Criterios de aceptación

La tarea se considera terminada cuando:

### Desktop
- No existe scroll vertical durante gameplay.
- Header, Scoreboard, Situation, Pitcher, Strike Zone, Batter, Next Batter, Actions y LANZAR son visibles simultáneamente.
- No existen enormes huecos entre las regiones del HUD.
- Pitcher, Strike Zone y Batter se leen como una única confrontación.
- Strike Zone no domina visualmente toda la pantalla.
- Next Batter está inmediatamente asociado al Batter.
- Actions y LANZAR forman una sola región inferior.
- En monitores grandes el HUD permanece centrado y el espacio sobrante pertenece al fondo.

### Mobile
- Pitcher, Strike Zone y Batter permanecen en la misma fila.
- La interfaz cabe correctamente en un iPhone sin overflow horizontal.
- Las estadísticas siguen siendo legibles.
- CoreGameplay utiliza mejor la altura disponible que la implementación actual.
- Next Batter es visible pero secundario.
- Actions y LANZAR permanecen juntos horizontalmente siempre que exista espacio suficiente.
- No aparecen grandes huecos artificiales entre secciones.

---

# 25. Instrucción final para implementación

Trabaja sobre la implementación existente. **No reconstruyas la UI desde cero.**

Primero identifica qué reglas CSS actuales están generando:

1. crecimiento excesivo de la Strike Zone en desktop;
2. separación excesiva entre regiones;
3. aislamiento de Actions y LANZAR;
4. compactación excesiva de CoreGameplay en mobile.

Corrige esas reglas manteniendo los componentes y comportamiento actuales.

Haz los cambios principalmente en layout/responsive CSS. Modifica markup/componentes únicamente cuando sea necesario para agrupar semánticamente:

- `score-row`
- `core-gameplay`
- `batter-column`
- `action-row`

Después de implementar, prueba todas las resoluciones indicadas y ajusta usando valores fluidos. No optimices únicamente para la captura actual.

## Regla de oro

> Desktop no es Mobile agrandado y Mobile no es Desktop comprimido. Son la misma interfaz, con los mismos componentes y jerarquía, reorganizados y dimensionados según el espacio disponible.
