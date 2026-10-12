# Deck at the Plate — Compact Situation Panel Fix v1.8

## Objetivo

Corregir únicamente las versiones **Compact / Mobile / Tablet** del panel de situación para que:

- no afecten en absoluto la versión Desktop ya aprobada;
- mantengan los dots de Balls / Strikes / Outs;
- eviten la sensación visual de que labels, dots, inning o bases se salen del contenedor;
- recuperen una composición más compacta, centrada y segura;
- mantengan el lenguaje visual actual del HUD.

> **Regla principal:** el layout Desktop actual se considera correcto y no debe modificarse.

---

# 1. Breakpoints y alcance

Usar esta separación:

```css
/* Mobile */
@media (max-width: 767px) {
}

/* Tablet / Compact */
@media (min-width: 768px) and (max-width: 1199px) {
}

/* Desktop */
@media (min-width: 1200px) {
}
```

La nueva distribución horizontal Desktop:

```text
[ BALLS / STRIKES / OUTS ] | [ INNING ] | [ BASES ]
```

debe permanecer exclusivamente dentro de:

```css
@media (min-width: 1200px) {
}
```

No modificarla desde reglas globales ni desde breakpoints inferiores.

---

# 2. Mantener los dots en Compact

Los dots sí pueden mantenerse en todas las versiones.

Colores:

```css
.count--balls {
  --count-color: #4ade80;
}

.count--strikes {
  --count-color: #facc15;
}

.count--outs {
  --count-color: #ef4444;
}
```

Estados:

```text
BALLS      ○ ○ ○ ○
STRIKES    ○ ○
OUTS       ○ ○
```

No volver a los números como indicador principal.

---

# 3. Problema actual en Compact

En Compact el panel da la impresión de que ciertos elementos:

- están demasiado cerca de los bordes;
- ocupan más ancho del disponible;
- se estiran horizontalmente;
- parecen salirse del módulo;
- compiten entre sí.

Esto ocurre porque la lógica horizontal pensada para Desktop se está intentando comprimir dentro de un contenedor demasiado estrecho.

La solución no es reducir todo hasta hacerlo ilegible.

La solución es cambiar la distribución interna.

---

# 4. Layout Compact recomendado

Para Compact utilizar una composición vertical en tres bloques:

```text
┌──────────────────────────────┐
│                              │
│   BALLS   STRIKES    OUTS    │
│   ○○○○      ○○       ○○      │
│                              │
│ ──────────────────────────── │
│                              │
│          INNING              │
│           1 / 3              │
│           ▲ TOP              │
│                              │
│ ──────────────────────────── │
│                              │
│           BASES              │
│             ◇                │
│                              │
└──────────────────────────────┘
```

La prioridad es que cada grupo tenga su propio espacio y que ninguno dependa del ancho de los otros.

---

# 5. Grid del Count en Compact

```css
@media (max-width: 1199px) {
  .count-row {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));

    width: 100%;
    min-width: 0;

    align-items: start;
    justify-items: center;

    gap: 4px;
  }
}
```

La clave es:

```css
minmax(0, 1fr)
```

y:

```css
min-width: 0;
```

Esto evita que las columnas empujen el contenedor más allá de su ancho.

---

# 6. Cada contador debe poder encogerse

```css
@media (max-width: 1199px) {
  .count-item {
    width: 100%;
    min-width: 0;

    display: flex;
    flex-direction: column;
    align-items: center;

    overflow: hidden;
  }
}
```

No utilizar anchuras fijas para BALLS, STRIKES u OUTS.

Evitar:

```css
width: 90px;
min-width: 90px;
```

en Compact.

---

# 7. Labels Compact

Actualmente `STRIKES` es el label más largo y puede generar sensación de desborde.

Usar:

```css
@media (max-width: 1199px) {
  .count-label {
    max-width: 100%;

    font-size: clamp(7px, 1.7vw, 9px);
    letter-spacing: .06em;

    white-space: nowrap;
    overflow: hidden;
    text-overflow: clip;

    text-align: center;
  }
}
```

No reducir agresivamente el tamaño.

El objetivo es mantener las tres etiquetas visualmente equilibradas.

---

# 8. Dots Compact

Reducir ligeramente los dots respecto a Desktop:

```css
@media (max-width: 1199px) {
  .count-dots {
    display: flex;
    justify-content: center;

    gap: 4px;
    margin-top: 5px;

    max-width: 100%;
  }

  .count-dot {
    width: 7px;
    height: 7px;
    flex: 0 0 7px;
  }
}
```

Para Mobile muy estrecho:

```css
@media (max-width: 430px) {
  .count-dot {
    width: 6px;
    height: 6px;
    flex-basis: 6px;
  }

  .count-dots {
    gap: 3px;
  }
}
```

No permitir que los dots crezcan mediante `flex: 1`.

---

# 9. Inning Compact

El inning debe permanecer centrado y ocupar su propio bloque:

```css
@media (max-width: 1199px) {
  .inning-block {
    width: 100%;
    min-width: 0;

    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    text-align: center;
  }
}
```

Referencia:

```text
INNING
 1 / 3
 ▲ TOP
```

No colocar el inning al lado de Balls/Strikes/Outs en Compact.

---

# 10. Bases Compact

Las bases deben quedar centradas dentro de su propia zona.

```css
@media (max-width: 1199px) {
  .bases-block {
    width: 100%;
    min-width: 0;

    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;

    overflow: hidden;
  }

  .bases-diamond {
    max-width: 42px;
    max-height: 42px;
  }
}
```

Evitar que el diamante use dimensiones derivadas del ancho total del panel.

---

# 11. Padding seguro del panel

Para evitar la sensación de que el contenido toca o atraviesa los bordes:

```css
@media (max-width: 1199px) {
  .game-situation {
    box-sizing: border-box;

    width: 100%;
    min-width: 0;

    padding: 12px 10px;

    overflow: hidden;
  }
}
```

En Mobile:

```css
@media (max-width: 430px) {
  .game-situation {
    padding-inline: 8px;
  }
}
```

`overflow: hidden` aquí funciona únicamente como protección visual.

No debe utilizarse para esconder contenido que realmente no cabe.

---

# 12. Evitar overflow causado por hijos

Aplicar de forma defensiva:

```css
@media (max-width: 1199px) {
  .game-situation *,
  .game-situation *::before,
  .game-situation *::after {
    box-sizing: border-box;
  }

  .game-situation__content,
  .count-row,
  .count-item,
  .inning-block,
  .bases-block {
    min-width: 0;
    max-width: 100%;
  }
}
```

Evitar:

```css
width: max-content;
```

```css
min-width: max-content;
```

```css
white-space: nowrap;
```

en contenedores estructurales.

`white-space: nowrap` solo puede usarse en labels pequeños.

---

# 13. No heredar el layout Desktop

Si actualmente existe una regla global similar a:

```css
.game-situation {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr;
}
```

moverla al media query Desktop:

```css
@media (min-width: 1200px) {
  .game-situation {
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
  }
}
```

Y establecer explícitamente Compact:

```css
@media (max-width: 1199px) {
  .game-situation {
    display: flex;
    flex-direction: column;
  }
}
```

No depender únicamente del cascade esperando que Mobile sobrescriba parcialmente Desktop.

---

# 14. Divisores Compact

Usar divisores horizontales:

```text
COUNT
────────────
INNING
────────────
BASES
```

CSS:

```css
@media (max-width: 1199px) {
  .situation-divider {
    width: 100%;
    height: 1px;

    margin: 10px 0;

    background: rgba(255,255,255,.08);
  }
}
```

No usar divisores verticales en Compact.

Los divisores verticales son únicamente Desktop.

---

# 15. Altura y densidad

El panel no debe intentar ocupar todo el alto disponible.

Usar contenido natural:

```css
@media (max-width: 1199px) {
  .game-situation {
    height: auto;
    min-height: 0;
  }
}
```

Evitar:

```css
height: 100%;
```

si el padre es significativamente más alto que el contenido.

Esto reduce la sensación de espacios vacíos innecesarios.

---

# 16. Mobile muy estrecho

Para 390–430 px:

```css
@media (max-width: 430px) {
  .count-row {
    gap: 2px;
  }

  .count-label {
    font-size: 7px;
    letter-spacing: .04em;
  }

  .inning-value {
    font-size: 14px;
  }

  .bases-diamond {
    max-width: 34px;
    max-height: 34px;
  }
}
```

No apilar Balls / Strikes / Outs verticalmente.

Deben conservarse en una sola fila.

---

# 17. Desktop protegido

Estas reglas NO deben cambiar:

```css
@media (min-width: 1200px) {
  /*
    Mantener la versión Desktop actual exactamente
    como está aprobada.
  */
}
```

No modificar:

- distribución horizontal Desktop;
- ancho del módulo Desktop;
- separadores verticales Desktop;
- tamaño de dots Desktop;
- posición de Inning Desktop;
- posición de Bases Desktop.

Si hay reglas compartidas necesarias para los colores o estados de los dots, pueden mantenerse globales.

Las reglas de geometría deben separarse por breakpoint.

---

# 18. Regla de arquitectura CSS recomendada

Separar:

```css
/* GLOBAL: apariencia */
.count-dot {}
.count-dot.active {}
.count--balls {}
.count--strikes {}
.count--outs {}

/* COMPACT: geometría */
@media (max-width: 1199px) {
}

/* DESKTOP: geometría */
@media (min-width: 1200px) {
}
```

De esta manera:

- colores y comportamiento se comparten;
- distribución no se comparte;
- modificar Compact no puede romper Desktop fácilmente.

---

# 19. Checklist visual

En Compact comprobar:

- BALLS, STRIKES y OUTS caben completamente dentro del panel.
- Ningún label toca los bordes.
- Ningún dot aparenta salirse.
- STRIKES conserva suficiente espacio.
- El diamante está perfectamente centrado.
- INNING está centrado.
- Los divisores terminan antes del borde interior.
- Existe padding visible a izquierda y derecha.
- No aparece scroll horizontal.
- El panel no crece artificialmente en altura.

---

# 20. Resoluciones de prueba obligatorias

### Mobile

```text
390 × 844
393 × 852
430 × 932
```

### Tablet / Compact

```text
768 × 1024
820 × 1180
1024 × 768
```

### Desktop — solo regresión

```text
1366 × 768
1920 × 1080
2560 × 1440
```

En Desktop únicamente verificar que no haya cambiado absolutamente nada.

---

# 21. Criterio de aceptación

Compact debe verse aproximadamente así:

```text
┌─────────────────────────────┐
│ BALLS    STRIKES     OUTS   │
│ ○ ○ ○ ○    ○ ○       ○ ○    │
│─────────────────────────────│
│           INNING            │
│            1 / 3            │
│            ▲ TOP            │
│─────────────────────────────│
│            BASES            │
│              ◇              │
└─────────────────────────────┘
```

Con suficiente espacio interno en ambos laterales.

Desktop debe conservar exactamente:

```text
┌────────────────────────────────────────────────────┐
│ BALLS STRIKES OUTS │    INNING    │     BASES      │
│ ○○○○    ○○    ○○   │    1/3 ▲     │       ◇        │
└────────────────────────────────────────────────────┘
```

---

## Regla final

> **Dots y colores = compartidos.**
>
> **Geometría Compact y Desktop = completamente independientes.**
>
> **Nunca ajustar Desktop para resolver un problema de Compact.**
