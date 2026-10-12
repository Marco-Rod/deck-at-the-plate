# Deck at the Plate — Desktop Game Situation / Count Panel Redesign v1.7

## Objetivo

Reestructurar visualmente el panel de **Balls, Strikes, Outs, Inning y jugadores en base** para lograr una lectura más rápida, compacta y propia de un HUD de béisbol.

> **Importante:** este ajuste es interno/visual. No modificar la posición general del panel ni alterar el CoreGameplay que ya funciona correctamente.

## 1. Estructura propuesta

Dividir el contenido en tres zonas:

1. **Count:** Balls / Strikes / Outs.
2. **Inning:** entrada actual, total y Top/Bottom.
3. **Bases:** diamante con corredores.

```text
┌────────────────────────────────────┐
│   BALLS       STRIKES       OUTS   │
│  ● ○ ○ ○       ● ○          ○ ○    │
│ ────────────────────────────────── │
│             INNING                 │
│              1 / 3                 │
│              ▲ TOP                 │
│                                    │
│              BASES                 │
│                ◇                   │
│              ◇   ◇                 │
└────────────────────────────────────┘
```

Evitar la sensación de datos flotando con demasiado espacio entre ellos.

## 2. Balls / Strikes / Outs mediante dots

Eliminar los valores numéricos `0 / 0 / 0` como representación principal y utilizar dots.

```text
0 Balls      ○ ○ ○ ○
1 Ball       ● ○ ○ ○
2 Balls      ● ● ○ ○
3 Balls      ● ● ● ○

0 Strikes    ○ ○
1 Strike     ● ○
2 Strikes    ● ●

0 Outs       ○ ○
1 Out        ● ○
2 Outs       ● ●
```

Los dots deben permitir entender el conteo de un vistazo.

## 3. Colores

```css
.count--balls   { --count-color: #4ade80; }
.count--strikes { --count-color: #facc15; }
.count--outs    { --count-color: #ef4444; }
```

- **Balls — Verde `#4ade80`**: glow corto y controlado.
- **Strikes — Amarillo `#facc15`**: diferenciar del acento naranja/dorado estructural de la UI.
- **Outs — Rojo `#ef4444`**: estado más crítico, sin glow excesivo.

## 4. Diseño de los dots

```css
.count-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 1px solid color-mix(in srgb, var(--count-color) 35%, transparent);
  background: transparent;
}

.count-dot.active {
  background: var(--count-color);
  border-color: var(--count-color);
  box-shadow: 0 0 6px color-mix(in srgb, var(--count-color) 55%, transparent);
}
```

Los dots inactivos deben seguir visibles, pero claramente secundarios.

## 5. Layout del Count

Los tres contadores deben aparecer en una sola fila.

```css
.count-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  align-items: start;
  text-align: center;
}
```

Cada bloque:

```text
   BALLS
 ● ● ○ ○
```

Reducir el espacio entre label y dots para que se perciban como una unidad.

```css
.count-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: .10em;
  text-transform: uppercase;
  opacity: .75;
}

.count-dots {
  display: flex;
  justify-content: center;
  gap: 5px;
  margin-top: 5px;
}
```

Los dots activos son el principal indicador cromático. No colorear grandes superficies.

## 6. Inning

Convertir el inning en un bloque visual único:

```text
       INNING
        1 / 3
        ▲ TOP
```

Jerarquía:

- `INNING`: label secundario.
- `1 / 3`: información principal.
- `TOP / BOT`: asociado claramente al inning.

Mantener colores neutros para no competir con el Count.

## 7. Bases

Dar al diamante una zona visual propia:

```text
       BASES

         ◇
       ◇   ◇
```

Conservar la lógica actual de bases ocupadas/vacías. El objetivo es evitar que el diamante parezca un elemento flotante.

## 8. Separación entre zonas

Todo debe seguir sintiéndose como **un único módulo**, no varias tarjetas dentro de otra tarjeta.

Usar como máximo un divisor sutil:

```css
.situation-divider {
  height: 1px;
  background: rgba(255, 255, 255, .08);
}
```

## 9. Desktop: aprovechar el ancho

En Desktop (`>=1200px`) preferir una composición más horizontal para evitar exceso de espacio vertical:

```text
┌──────────────────────────────────────────────────┐
│ BALLS       STRIKES       OUTS │ INNING │ BASES │
│ ● ● ○ ○       ● ○          ○ ○ │ 1/3 ▲  │  ◇   │
│                                │  TOP   │ ◇ ◇  │
└──────────────────────────────────────────────────┘
```

Estructura conceptual:

```text
[ BALLS | STRIKES | OUTS ]   [ INNING ]   [ BASES ]
```

Se pueden utilizar divisores verticales muy tenues entre Count, Inning y Bases.

La prioridad es **densidad + legibilidad**, no llenar artificialmente el alto disponible.

```css
@media (min-width: 1200px) {
  .game-situation {
    display: grid;
    grid-template-columns: minmax(0, 1.8fr) minmax(90px, .6fr) minmax(100px, .7fr);
    align-items: center;
    gap: 14px;
    padding: 12px 16px;
  }
}
```

## 10. Compact / Mobile

La vista Compact/Mobile actual funciona bien. **No provocar regresiones por este cambio Desktop.**

Puede conservar una distribución más vertical:

```text
BALLS   STRIKES   OUTS
 dots     dots     dots

       INNING
        1/3
        TOP

       BASES
         ◇
```

Encapsular los cambios específicos de Desktop en:

```css
@media (min-width: 1200px) {
  /* Desktop-only situation layout */
}
```

## 11. Microanimaciones

Cuando se active un nuevo dot, utilizar un pequeño `pop` de unos 180 ms.

```css
@keyframes count-pop {
  0%   { transform: scale(.75); opacity: .5; }
  65%  { transform: scale(1.18); }
  100% { transform: scale(1); opacity: 1; }
}

.count-dot.just-activated {
  animation: count-pop 180ms ease-out;
}
```

No utilizar pulsaciones infinitas. El glow representa estado, no una animación permanente.

## 12. Reglas importantes

- No modificar la geometría estable del CoreGameplay.
- No modificar `--matchup-height`.
- No modificar Pitcher/Batter cards.
- No modificar la Strike Zone.
- No alterar la posición general del panel de situación.
- Proteger Compact/Mobile.
- Evitar glassmorphism.
- Mantener bordes finos y radios pequeños.
- Evitar glow excesivo.
- **Balls = verde.**
- **Strikes = amarillo.**
- **Outs = rojo.**
- Los colores comunican estado; no son decoración general.

## 13. Resultado esperado

El usuario debe reconocer inmediatamente:

```text
BALLS      ● ● ○ ○
STRIKES    ● ○
OUTS       ○ ○

INNING     1 / 3 — TOP
BASES      ◇
```

La sensación buscada es:

**marcador de béisbol + HUD técnico + lectura inmediata.**

En Desktop debe verse más compacto, deliberado y horizontal, conservando la buena densidad que ya existe en Compact/Mobile.
