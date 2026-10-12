# Deck at the Plate — Pack Opening / Card Reveal UI Spec v1.0

## Objetivo

Diseñar e implementar la pantalla de **apertura del mazo/sobre inicial** de *Deck at the Plate*, contemplando:

- vista **Desktop**;
- vista **Mobile / Compact**;
- estado de las cartas **sin revelar**;
- estado de las cartas **reveladas**;
- animación de flip;
- diferenciación visual por rareza;
- revelado individual y opción **REVELAR TODAS**;
- continuidad visual con el resto del juego;
- ausencia total de fotografías o retratos reales de jugadores.

La pantalla debe sentirse como un momento de recompensa y descubrimiento, no como una tabla de datos.

---

## 1. Dirección visual general

Mantener continuidad con el lenguaje visual ya establecido para *Deck at the Plate*:

- fondo oscuro tipo estadio nocturno;
- ambiente cinematográfico;
- iluminación cálida y controlada;
- negro carbón / gris oscuro como base;
- verdes muy oscuros;
- acentos oro / bronce;
- bordes finos;
- radios pequeños;
- textura sutil;
- glow corto, nunca excesivo;
- nada de glassmorphism.

La interfaz debe sentirse como una mezcla de **coleccionable premium + estadio de béisbol + HUD técnico + apertura de sobre**.

---

## 2. Fondo de la pantalla

Utilizar un fondo relacionado con el universo visual del gameplay:

- estadio nocturno genérico;
- sin jugadores visibles;
- sin logos MLB;
- sin texto legible;
- gradas oscuras;
- iluminación cálida;
- humo / niebla ligera;
- depth of field;
- centro relativamente limpio para no competir con las cartas.

Aplicar una capa oscura adicional:

```css
.pack-screen::before {
  content: "";
  position: fixed;
  inset: 0;
  background: radial-gradient(circle at 50% 40%, rgba(210,160,80,.06), rgba(0,0,0,.30) 52%, rgba(0,0,0,.62) 100%);
  pointer-events: none;
}
```

---

## 3. Header

Contenido:

```text
¡MAZO INICIAL DESBLOQUEADO!
TU COLECCIÓN DE CARTAS DE BIENVENIDA.
[ REVELAR TODAS ▶ ]
```

Desktop:

```css
.pack-header { text-align: center; margin-bottom: 28px; }
.pack-title { font-size: clamp(28px, 2.5vw, 44px); letter-spacing: .02em; }
.pack-subtitle { margin-top: 8px; font-size: 11px; letter-spacing: .28em; opacity: .62; }
```

Mobile:

```css
@media (max-width: 767px) {
  .pack-title { font-size: clamp(22px, 7vw, 30px); line-height: 1.05; }
  .pack-subtitle { font-size: 9px; letter-spacing: .18em; }
}
```

---

## 4. Botón “REVELAR TODAS”

```css
.reveal-all-button {
  min-height: 38px;
  padding: 0 18px;
  border: 1px solid rgba(197,154,76,.45);
  border-radius: 4px;
  background: rgba(26,38,29,.92);
  color: #d7b56d;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: .06em;
  cursor: pointer;
}
```

Hover Desktop:

```css
.reveal-all-button:hover {
  border-color: rgba(215,181,109,.9);
  box-shadow: 0 0 14px rgba(215,181,109,.10);
}
```

---

## 5. Grid responsive

### Desktop >= 1200px

```css
@media (min-width: 1200px) {
  .pack-grid {
    width: min(88vw, 1320px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: clamp(22px, 2vw, 34px);
  }
}
```

### Tablet 768–1199px

```css
@media (min-width: 768px) and (max-width: 1199px) {
  .pack-grid {
    width: min(92vw, 900px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
  }
}
```

### Mobile < 768px

```css
@media (max-width: 767px) {
  .pack-grid {
    width: calc(100% - 24px);
    margin: 0 auto;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
  }
}
```

No forzar toda la pantalla dentro de `100dvh`. Esta vista puede hacer scroll vertical.

---

## 6. Componente base de carta

```html
<article class="pack-card rarity-gold" data-revealed="false">
  <div class="pack-card__inner">
    <div class="pack-card__face pack-card__back">...</div>
    <div class="pack-card__face pack-card__front">...</div>
  </div>
</article>
```

```css
.pack-card {
  position: relative;
  perspective: 1200px;
  aspect-ratio: .72 / 1;
}

.pack-card__inner {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
  transition: transform .62s cubic-bezier(.2,.72,.2,1), filter .3s ease;
}

.pack-card.is-revealed .pack-card__inner { transform: rotateY(180deg); }

.pack-card__face {
  position: absolute;
  inset: 0;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
}

.pack-card__front { transform: rotateY(180deg); }
```

---

## 7. Carta SIN revelar

La carta cerrada NO debe mostrar nombre, número, posición, OVR, rareza real ni estadísticas.

Debe sentirse como un objeto premium:

```text
┌──────────────────────────┐
│                          │
│       [ EMBLEMA ]        │
│                          │
│        DECK              │
│      AT THE PLATE        │
│                          │
└──────────────────────────┘
```

```css
.pack-card__back {
  border: 1px solid rgba(189,146,74,.45);
  border-radius: 6px;
  background:
    radial-gradient(circle at 50% 42%, rgba(194,145,70,.08), transparent 45%),
    linear-gradient(160deg, #151817, #0f1211 62%, #0a0c0b);
  box-shadow: 0 14px 24px rgba(0,0,0,.35), inset 0 0 0 1px rgba(255,255,255,.025);
}
```

Usar el logo compacto o símbolo del juego al 35–45% del ancho. No revelar visualmente la rareza antes del click/tap.

---

## 8. Interacción de carta cerrada

Desktop:

```css
@media (hover: hover) {
  .pack-card:not(.is-revealed):hover { transform: translateY(-3px); }
  .pack-card:not(.is-revealed):hover .pack-card__inner { filter: brightness(1.06); }
}
```

Mobile:

```css
.pack-card:active { transform: scale(.985); }
```

Toda la carta debe ser tappable/clickable mientras esté cerrada.

---

## 9. Carta REVELADA — concepto

**No usar fotos ni retratos de jugadores.** La identidad del jugador se construye con:

- nombre;
- número;
- equipo;
- posición;
- OVR;
- rareza;
- stats.

La zona central debe recordar una camisola vista desde atrás.

Ejemplo pitcher:

```text
┌─────────────────────────────┐
│ JOSÉ A. FERRER        90 OVR│
│ SEA · SP · #45              │
│─────────────────────────────│
│ DIAMANTE        PÍCHER      │
│                             │
│      JOSÉ A. FERRER         │
│                             │
│            45               │
│                             │
│─────────────────────────────│
│ PWR 40       CON 40         │
│ VEL 92       CTL 70         │
└─────────────────────────────┘
```

Ejemplo bateador:

```text
┌─────────────────────────────┐
│ BROCK RODDEN          85 OVR│
│ SEA · SS · #90              │
│─────────────────────────────│
│ ORO            BATEADOR     │
│                             │
│       BROCK RODDEN          │
│                             │
│             90              │
│                             │
│─────────────────────────────│
│ PWR 70       CON 70         │
└─────────────────────────────┘
```

---

## 10. Identity area tipo jersey

```css
.card-player-identity {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 0;
  text-align: center;
}

.card-player-name {
  font-size: clamp(11px, .9vw, 15px);
  letter-spacing: .08em;
  text-transform: uppercase;
}

.card-player-number {
  margin-top: 8px;
  font-size: clamp(44px, 4vw, 72px);
  line-height: .85;
  font-weight: 900;
}

@media (max-width: 767px) {
  .card-player-name { font-size: 9px; }
  .card-player-number { font-size: clamp(34px, 13vw, 50px); }
}
```

Opcional: número watermark detrás con opacidad aproximada `.025`.

---

## 11. Header de carta revelada

```css
.card-front-header {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 8px;
  align-items: start;
}

.card-front-name {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

El OVR debe ir en un badge pequeño y consistente.

---

## 12. Badge OVR

```css
.ovr-badge {
  min-width: 46px;
  min-height: 46px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(117,171,120,.25);
  border-radius: 6px;
  background: rgba(26,47,34,.62);
}

.ovr-value { font-size: 22px; font-weight: 900; }
.ovr-label { font-size: 8px; opacity: .55; }

@media (max-width: 767px) {
  .ovr-badge { min-width: 38px; min-height: 38px; }
  .ovr-value { font-size: 17px; }
}
```

---

## 13. Rarezas

Contemplar:

```text
COMÚN
BRONCE
PLATA
ORO
DIAMANTE
```

Variables sugeridas:

```css
.rarity-common  { --rarity-color: #8b918d; }
.rarity-bronze  { --rarity-color: #b77a4b; }
.rarity-silver  { --rarity-color: #b9c2c8; }
.rarity-gold    { --rarity-color: #d3ab52; }
.rarity-diamond { --rarity-color: #61c8cf; }
```

La rareza modifica borde, acentos, glow y animación; NO cambia por completo el diseño.

---

## 14. Badge de rareza

```css
.rarity-badge {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 0 10px;
  border: 1px solid color-mix(in srgb, var(--rarity-color) 58%, transparent);
  border-radius: 999px;
  color: var(--rarity-color);
  font-size: 9px;
  letter-spacing: .1em;
}
```

---

## 15. Stats

Bateador: usar las stats reales del juego, por ejemplo `PWR`, `CON`, opcionalmente `SPD`, `FLD` si existen.

Pitcher: usar las stats reales del juego, por ejemplo `PWR`, `CON`, `VEL`, `CTL` si son las ya definidas.

No inventar stats que no existan en el modelo.

```css
.card-stats {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.card-stat {
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  border: 1px solid rgba(83,133,91,.28);
  border-radius: 5px;
  background: rgba(24,43,31,.48);
}
```

Mobile:

```css
@media (max-width: 767px) {
  .card-stats { gap: 5px; }
  .card-stat { min-height: 32px; padding: 0 7px; }
  .card-stat__label { font-size: 7px; }
  .card-stat__value { font-size: 12px; }
}
```

---

## 16. Front card base

```css
.pack-card__front {
  background: linear-gradient(160deg, rgba(18,22,20,.98), rgba(12,16,14,.99));
  border: 1px solid color-mix(in srgb, var(--rarity-color) 35%, #303733);
  border-radius: 6px;
}

@media (min-width: 1200px) {
  .pack-card__front { padding: 14px; }
}

@media (max-width: 767px) {
  .pack-card__front { padding: 9px; }
}
```

---

## 17. Animación básica de reveal

Flujo:

```text
click/tap
↓
anticipación corta
↓
flip 3D
↓
front visible
↓
glow breve según rareza
```

```js
function revealCard(cardEl) {
  if (cardEl.classList.contains('is-revealed')) return;

  cardEl.classList.add('is-revealing');

  setTimeout(() => {
    cardEl.classList.add('is-revealed');
  }, 80);

  setTimeout(() => {
    cardEl.classList.remove('is-revealing');
    cardEl.classList.add('reveal-complete');
  }, 760);
}
```

---

## 18. Anticipación por rareza

Duraciones orientativas:

```text
COMÚN       80–120 ms
BRONCE      120–180 ms
PLATA       160–220 ms
ORO         220–300 ms
DIAMANTE    350–500 ms
```

No superar pausas molestas.

---

## 19. Efectos por rareza

Común: small scale + flip.

Bronce:

```css
.rarity-bronze.is-revealing {
  filter: drop-shadow(0 0 8px rgba(183,122,75,.18));
}
```

Plata:

```css
.rarity-silver.is-revealing {
  filter: brightness(1.08) drop-shadow(0 0 10px rgba(185,194,200,.20));
}
```

Oro:

```css
.rarity-gold.is-revealing {
  filter: brightness(1.1) drop-shadow(0 0 14px rgba(211,171,82,.28));
}
```

Diamante:

```css
.rarity-diamond.is-revealing {
  animation: diamond-anticipation .42s ease;
}

@keyframes diamond-anticipation {
  0%   { transform: scale(1); filter: brightness(1); }
  45%  { transform: scale(.985); }
  75%  { filter: brightness(1.15) drop-shadow(0 0 16px rgba(97,200,207,.38)); }
  100% { transform: scale(1); }
}
```

No usar flash blanco de pantalla completa.

---

## 20. Settle final

```css
@keyframes card-settle {
  0%   { transform: scale(.97); }
  60%  { transform: scale(1.025); }
  100% { transform: scale(1); }
}

.pack-card.reveal-complete {
  animation: card-settle 280ms ease-out;
}
```

---

## 21. Partículas

Opcionales para v2.

Si se usan:

- solo Oro y Diamante;
- 8–16 partículas máximo;
- duración < 900ms;
- `pointer-events: none`;
- nunca loops infinitos.

---

## 22. Reveal All

```js
function revealAll(cards) {
  cards.forEach((card, index) => {
    setTimeout(() => {
      revealCard(card);
    }, index * 130);
  });
}
```

No revelar todas en el mismo frame.

No mover ni reordenar las cartas durante el reveal.

---

## 23. Estado final del botón

Después de revelar todas:

```text
REVELAR TODAS
↓
TODAS REVELADAS
```

Preferir deshabilitar y bajar opacidad antes que eliminarlo para evitar saltos de layout.

---

## 24. Accesibilidad

Usar semántica de botón o controles accesibles.

```html
<button class="pack-card" aria-label="Revelar carta" aria-expanded="false">
```

Tras revelar:

```text
aria-expanded="true"
```

Soportar:

```css
@media (prefers-reduced-motion: reduce) {
  .pack-card__inner,
  .pack-card,
  .particle {
    animation: none !important;
    transition-duration: .01ms !important;
  }
}
```

---

## 25. Arquitectura de estados

Estados sugeridos:

```text
hidden
hovered      [desktop]
pressed      [touch]
is-revealing
is-revealed
reveal-complete
```

Separar rareza de estado:

```text
rarity-gold + is-revealing
```

---

## 26. Arquitectura de clases

```text
pack-card
pack-card__inner
pack-card__face
pack-card__back
pack-card__front

rarity-common
rarity-bronze
rarity-silver
rarity-gold
rarity-diamond

is-revealing
is-revealed
reveal-complete
```

---

## 27. Datos

```js
const playerCard = {
  id: 'player-001',
  name: 'José A. Ferrer',
  number: 45,
  team: 'SEA',
  position: 'SP',
  type: 'pitcher',
  overall: 90,
  rarity: 'diamond',
  stats: {
    pwr: 40,
    con: 40,
    vel: 92,
    ctl: 70,
  },
  revealed: false,
};
```

No guardar estados importantes solo en el DOM.

---

## 28. Componente reutilizable

Ideal:

```jsx
<PlayerPackCard
  player={player}
  revealed={revealed}
  onReveal={handleReveal}
/>
```

No crear `DesktopCard` y `MobileCard` si solo cambia layout. Resolver con CSS responsive.

---

## 29. Nombres largos

```css
.card-front-name,
.card-player-name {
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
```

Nunca permitir que un nombre cambie el ancho de la carta.

---

## 30. Número del jugador

El número debe renderizarse siempre como texto dinámico. No generar imágenes por jugador.

Esto permite escalar a cientos de jugadores sin assets adicionales.

---

## 31. Pitcher vs Batter

Mantener la misma geometría general. Cambian únicamente:

```text
TYPE
STATS
LABELS
```

No crear dos familias visuales completamente distintas.

---

## 32. Rendimiento

Evitar:

- blur gigante por card;
- cientos de partículas;
- shadows de radios enormes;
- animaciones infinitas;
- cambiar layout durante el flip.

Preferir:

```text
transform
opacity
filter moderado
```

No animar `width`, `height`, `top`, `left`.

---

## 33. QA Desktop

Probar:

```text
1366 × 768
1440 × 900
1920 × 1080
2560 × 1440
```

Verificar:

- 4 columnas;
- grid centrado;
- sin overflow horizontal;
- cartas de misma altura;
- reveal no mueve otras cards;
- rarezas legibles pero no exageradas.

---

## 34. QA Mobile

Probar:

```text
360 × 800
390 × 844
393 × 852
430 × 932
```

Verificar:

- 2 columnas;
- sin overflow horizontal;
- nombre no sale de card;
- número sigue siendo protagonista;
- OVR cabe;
- stats caben;
- tap completo funciona;
- animación no genera scroll lateral.

---

## 35. QA Tablet

Probar:

```text
768 × 1024
820 × 1180
1024 × 768
```

Esperado: 3 columnas.

---

## 36. Orden de implementación

```text
1. Grid responsive
2. Card back
3. Card front
4. Flip básico
5. Reveal individual
6. Reveal All
7. Rareza visual
8. Anticipación por rareza
9. Reduced Motion
10. QA responsive
11. Partículas / audio opcional
```

No comenzar por efectos especiales.

---

## 37. MVP aprobado cuando exista

- Desktop;
- Mobile;
- Tablet;
- 2 / 3 / 4 columnas por breakpoint;
- carta cerrada;
- carta revelada;
- nombre;
- número;
- metadata;
- OVR;
- rareza;
- stats;
- flip;
- reveal individual;
- Reveal All;
- cinco rarezas;
- responsive;
- `prefers-reduced-motion`.

Partículas y sonido NO son requisito de v1.

---

## 38. Regla final de diseño

> **La emoción debe venir de la presentación, la rareza, la animación y la identidad tipográfica del jugador; nunca de una fotografía.**

> **Nombre + número + OVR + stats deben ser suficientes para que cada carta tenga presencia propia.**

> **La pantalla debe sentirse como la apertura de un coleccionable premium dentro del mismo universo visual del gameplay.**
