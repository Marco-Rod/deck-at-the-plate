# Deck at the Plate --- Desktop Composition Tuning v1.5

## Objetivo

Ajustar **únicamente la vista Desktop** de la pantalla de gameplay para
que se sienta diseñada específicamente para escritorio, manteniendo
intacta la composición móvil actual.

La versión móvil se considera aprobada como base. **No modificar su
arquitectura, tamaños, orden, breakpoints ni comportamiento visual como
consecuencia de estas correcciones Desktop.**

------------------------------------------------------------------------

## 1. Regla principal: Desktop y Mobile deben desacoplarse

Implementar los siguientes cambios solamente dentro del breakpoint
Desktop:

``` css
@media (min-width: 1200px) {
    /* ajustes descritos en este documento */
}
```

No modificar reglas base compartidas si el cambio puede alterar Mobile o
Tablet. Cuando sea necesario, sobrescribir propiedades específicamente
dentro de Desktop.

### Regla de protección

> Ningún ajuste realizado en esta iteración puede cambiar la composición
> móvil ya aprobada.

Antes y después de implementar Desktop, comprobar al menos 390×844 y
430×932.

------------------------------------------------------------------------

## 2. Problema actual en Desktop

Los componentes individuales son correctos, pero el HUD se percibe
demasiado disperso dentro del viewport.

El problema **no es que exista espacio vacío alrededor del HUD**. En
monitores grandes ese espacio exterior es deseable y puede utilizarse
para fondo, estadio o ambientación.

El problema es el exceso de espacio vacío **entre los componentes que
forman el propio HUD**.

Actualmente se perciben varias islas independientes:

``` text
Scoreboard                     Situation


Pitcher          Strike Zone             Batter
                                            Next Batter

Actions                                      LANZAR
```

La nueva composición debe sentirse como un único tablero de juego cuyo
centro de gravedad sea:

``` text
PITCHER  ↔  STRIKE ZONE  ↔  BATTER
```

------------------------------------------------------------------------

## 3. No convertir Desktop en un dashboard

No estirar los componentes para llenar artificialmente un monitor de
27", 32", ultrawide o 4K.

Mantener un HUD central contenido y permitir espacio exterior.

``` css
@media (min-width: 1200px) {
    .game-shell {
        width: min(92vw, 1500px);
        height: 100dvh;
        margin-inline: auto;
    }
}
```

Se permite ajustar el máximo entre aproximadamente `1450px` y `1600px`
si las pruebas visuales lo justifican.

El objetivo no es usar cada píxel disponible, sino mantener distancias
internas coherentes.

------------------------------------------------------------------------

## 4. Estructura Desktop deseada

La composición general debe aproximarse a:

``` text
┌─────────────────────────────────────────────────────────────┐
│ AJO VS CPU                                      FINALIZAR    │
├───────────────────────────────────┬─────────────────────────┤
│ SCOREBOARD                        │ R/H/E · INNING · BASES  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   ┌────────────┐   ┌──────────────────┐   ┌────────────┐    │
│   │  PITCHER   │   │   STRIKE ZONE    │   │   BATTER   │    │
│   │            │   │                  │   │            │    │
│   │    #22     │   │       3 × 3      │   │    #20     │    │
│   │            │   │                  │   │            │    │
│   │   STATS    │   │                  │   │   STATS    │    │
│   │  STAMINA   │   │                  │   │            │    │
│   └────────────┘   └──────────────────┘   └────────────┘    │
│                                               ┌─────────┐   │
│                                               │ NEXT #21│   │
│                                               └─────────┘   │
├─────────────────────────────────────────────────────────────┤
│ [ACTION] [ACTION] [ACTION] [ACTION]             🔥 LANZAR   │
└─────────────────────────────────────────────────────────────┘
```

No interpretar el esquema como dimensiones absolutas. Representa
jerarquía, proximidad y alineación.

------------------------------------------------------------------------

## 5. Compactar verticalmente las regiones principales

En la implementación actual existe demasiado espacio entre:

-   Header y Score Area;
-   Score Area y CoreGameplay;
-   CoreGameplay y Action Area.

Reducir esos espacios para que el HUD se lea como una sola composición.

Recomendación:

``` css
.desktop-game-layout {
    display: grid;
    grid-template-rows: auto auto minmax(0, 1fr) auto;
    row-gap: clamp(10px, 1.5dvh, 20px);
}
```

Evitar márgenes verticales grandes definidos con `vh` que separen
artificialmente las secciones.

------------------------------------------------------------------------

## 6. Scoreboard y Game Situation forman una sola región

Mantener ambos paneles en la misma fila, con igual altura y un gap
reducido.

``` css
@media (min-width: 1200px) {
    .score-area {
        display: grid;
        grid-template-columns: minmax(0, 2.2fr) minmax(300px, 1fr);
        gap: clamp(10px, 1vw, 18px);
        align-items: stretch;
    }

    .scoreboard,
    .game-situation {
        height: 100%;
    }
}
```

No permitir que parezcan dos widgets flotantes sin relación.

------------------------------------------------------------------------

## 7. CoreGameplay debe ser el centro visual

Desktop debe organizar Pitcher, Strike Zone y Batter como una
confrontación compacta.

No distribuirlos usando todo el ancho disponible mediante
`space-between`.

Evitar:

``` css
justify-content: space-between;
```

si eso genera grandes vacíos.

Preferir un grid contenido:

``` css
@media (min-width: 1200px) {
    .core-gameplay {
        width: min(100%, 1120px);
        margin-inline: auto;

        display: grid;
        grid-template-columns:
            minmax(250px, 0.9fr)
            minmax(340px, 1.15fr)
            minmax(250px, 0.9fr);

        column-gap: clamp(18px, 2vw, 36px);
        align-items: start;
    }
}
```

Los valores pueden adaptarse al código real, pero conservar esta
relación conceptual:

``` text
Pitcher       Zone        Batter
  ~24%        ~36%         ~24%
```

La zona debe ser protagonista, pero no absorber el viewport.

------------------------------------------------------------------------

## 8. Limitar el crecimiento de Strike Zone

En Desktop la Strike Zone no debe crecer en función de toda la altura
disponible.

Debe mantener proporción cuadrada y límites claros.

``` css
@media (min-width: 1200px) {
    .strike-zone {
        width: clamp(320px, 25vw, 430px);
        max-width: 100%;
        aspect-ratio: 1 / 1;
        height: auto;
    }
}
```

No permitir zonas de strike gigantes en 1440p o 4K.

En resoluciones grandes, el espacio adicional debe aparecer **fuera del
HUD**, no dentro de la Strike Zone.

------------------------------------------------------------------------

## 9. Player Cards Desktop

Pitcher y Batter deben:

-   compartir el mismo top;
-   mantener la misma altura exterior;
-   tener dimensiones visualmente equivalentes;
-   conservar la información existente.

No hacer que las tarjetas crezcan verticalmente simplemente porque
existe más espacio de pantalla.

Ejemplo:

``` css
@media (min-width: 1200px) {
    .player-card {
        width: 100%;
        height: clamp(300px, 38dvh, 390px);
    }
}
```

El máximo debe impedir cartas exageradamente altas.

------------------------------------------------------------------------

## 10. Next Batter permanece debajo del Batter

Esta decisión queda cerrada.

En Desktop:

``` text
BATTER
  ↓
NEXT BATTER
```

Debe:

-   usar exactamente el ancho de la columna Batter;
-   estar separado por aproximadamente `8–12px`;
-   ser claramente secundario respecto al Current Batter;
-   tener una altura aproximada de `60–80px`.

``` css
@media (min-width: 1200px) {
    .batter-column {
        display: flex;
        flex-direction: column;
        gap: clamp(8px, 1dvh, 12px);
    }

    .next-batter {
        width: 100%;
        height: clamp(60px, 7dvh, 80px);
    }
}
```

No mover Next Batter a otra región del Desktop.

------------------------------------------------------------------------

## 11. Actions y LANZAR deben formar una sola Action Area

Actualmente Actions y LANZAR se perciben como bloques separados.

En Desktop deben formar una misma fila visual.

``` text
┌─────────────────────────────────────────────┬──────────────┐
│ [A1]   [A2]   [A3]   [A4]                  │ 🔥 LANZAR    │
└─────────────────────────────────────────────┴──────────────┘
```

Implementación sugerida:

``` css
@media (min-width: 1200px) {
    .action-area {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: clamp(18px, 2vw, 32px);
        align-items: stretch;
    }
}
```

El bloque Actions puede contener sus cuatro cartas en una grid interna:

``` css
.actions-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 6px;
}
```

No dejar `LANZAR` flotando varios cientos de píxeles a la derecha de las
cartas.

------------------------------------------------------------------------

## 12. LANZAR debe seguir siendo la acción primaria

Integrarlo en la misma región no significa reducir su jerarquía.

Debe conservar:

-   borde/glow cálido;
-   icono de fuego;
-   tipografía de mayor peso;
-   tamaño suficiente;
-   texto secundario `MANTÉN`.

Puede ser ligeramente más alto o más destacado que una Action Card, pero
debe compartir su línea visual con Actions.

Ejemplo:

``` css
@media (min-width: 1200px) {
    .pitch-button {
        min-width: clamp(150px, 12vw, 190px);
        align-self: stretch;
    }
}
```

------------------------------------------------------------------------

## 13. Crear líneas visuales compartidas

Aplicar esta regla a todo Desktop:

> Toda región horizontal importante debe compartir una línea visual
> clara de inicio y cierre.

### Score Area

``` text
──────── Score top ────────
│ Scoreboard │ Situation │
──────── Score bottom ─────
```

### CoreGameplay

``` text
──────── Core top ─────────
│ Pitcher │ Zone │ Batter │
```

Pitcher, Zone y Batter deben comenzar exactamente en el mismo top.

### Action Area

``` text
──────── Action top ───────
│ Actions       │ LANZAR  │
──────── Action bottom ────
```

Esta consistencia geométrica es prioritaria en el lenguaje visual
actual.

------------------------------------------------------------------------

## 14. El espacio vacío debe desplazarse al exterior

No intentar eliminar todo el espacio vacío de un monitor grande.

Debe ocurrir esto:

``` text
      AMBIENT BACKGROUND / STADIUM

        ┌─────────────────────┐
        │                     │
        │      GAME HUD       │
        │                     │
        └─────────────────────┘

      AMBIENT BACKGROUND / STADIUM
```

No esto:

``` text
┌───────────────────────────────────────────┐
│ Score                               Info  │
│                                           │
│ Pitcher         Zone             Batter  │
│                                           │
│ Actions                             Throw │
└───────────────────────────────────────────┘
```

El segundo ejemplo llena el viewport pero pierde cohesión.

------------------------------------------------------------------------

## 15. Desktop Compact

Para Desktop con poca altura, especialmente `1366×768`, compactar sin
cambiar arquitectura.

``` css
@media (min-width: 1200px) and (max-height: 800px) {
    .desktop-game-layout {
        row-gap: 8px;
    }

    .player-card {
        height: clamp(260px, 35dvh, 310px);
    }

    .strike-zone {
        width: clamp(280px, 23vw, 340px);
    }

    .next-batter {
        height: 60px;
    }
}
```

Reducir primero:

1.  gaps;
2.  padding;
3.  alturas secundarias;
4.  tamaño de CoreGameplay dentro de límites;

antes de ocultar contenido.

------------------------------------------------------------------------

## 16. `100dvh` y scroll

En Desktop Gameplay:

``` css
.game-shell {
    height: 100dvh;
    overflow: hidden;
}
```

Todo lo necesario para jugar el turno debe caber simultáneamente:

-   Header;
-   marcador;
-   inning / outs / bases;
-   Pitcher;
-   stamina y pitch count;
-   Strike Zone;
-   Batter;
-   Next Batter;
-   Action Cards;
-   LANZAR.

`overflow: hidden` es únicamente una protección. **Nunca debe utilizarse
para esconder contenido que no cupo.**

Si un control queda cortado, se considera un bug responsive.

------------------------------------------------------------------------

## 17. No modificar Mobile

Esta sección es obligatoria.

No cambiar como parte de esta tarea:

-   grid móvil de `Pitcher | Strike Zone | Batter`;
-   tamaño actual de las cartas móviles;
-   posición móvil de Next Batter;
-   composición móvil de Actions + LANZAR;
-   Score Area móvil;
-   paddings móviles;
-   breakpoints menores a 1200px;
-   tipografía móvil;
-   comportamiento táctil móvil.

Si una clase es compartida, aplicar la corrección mediante
`@media (min-width: 1200px)`.

No solucionar Desktop modificando estilos globales que provoquen
regresiones Mobile.

------------------------------------------------------------------------

## 18. Resoluciones de prueba obligatorias

Después de implementar, validar visualmente:

### Protección Mobile

``` text
390 × 844
430 × 932
```

El resultado debe permanecer equivalente al diseño móvil aprobado.

### Desktop

``` text
1366 × 768
1440 × 900
1920 × 1080
2560 × 1440
```

### Pantalla grande

Si es posible:

``` text
3840 × 2160
```

En 4K el HUD no debe estirarse indefinidamente.

------------------------------------------------------------------------

## 19. Criterios de aceptación Desktop

La iteración se considera correcta cuando:

-   el HUD se percibe como un único tablero y no como widgets flotantes;
-   Scoreboard y Situation están visualmente unidos;
-   Pitcher, Strike Zone y Batter forman claramente el centro del juego;
-   las distancias Pitcher → Zone y Zone → Batter son controladas y
    equilibradas;
-   Strike Zone no domina excesivamente la pantalla;
-   Pitcher y Batter mantienen dimensiones equivalentes;
-   Next Batter permanece integrado debajo del Batter;
-   Actions y LANZAR forman una sola región horizontal;
-   no existe scroll vertical durante el gameplay Desktop;
-   en monitores grandes el espacio adicional queda alrededor del HUD;
-   390×844 y 430×932 no presentan regresiones respecto al diseño móvil
    actual.

------------------------------------------------------------------------

## 20. Instrucción directa para la IA

Copiar este bloque como prompt de implementación:

> Ajusta exclusivamente la composición Desktop de la pantalla Gameplay
> de Deck at the Plate. La versión móvil actual está aprobada y no debe
> modificarse ni sufrir regresiones.
>
> Implementa todos los cambios de esta iteración dentro de
> `@media (min-width: 1200px)` o mediante estilos Desktop equivalentes.
> No cambies reglas globales si pueden alterar Mobile o Tablet.
>
> El problema Desktop actual no es la existencia de espacio vacío
> alrededor del HUD, sino el exceso de espacio entre sus componentes. El
> HUD debe sentirse como un único tablero compacto cuyo centro visual
> sea `Pitcher ↔ Strike Zone ↔ Batter`.
>
> Mantén el `game-shell` centrado y limitado aproximadamente a
> `min(92vw, 1500px)`; no estires el HUD para llenar monitores grandes.
> El espacio adicional debe quedar fuera del HUD y puede utilizarse como
> ambientación.
>
> Compacta las distancias verticales entre Header, Score Area,
> CoreGameplay y Action Area. Scoreboard y Game Situation deben formar
> una misma fila, compartir altura y tener un gap pequeño.
>
> En CoreGameplay, evita `space-between` o cualquier distribución que
> empuje Pitcher y Batter hacia extremos lejanos. Usa un grid contenido
> de tres columnas con una relación aproximada Pitcher 24%, Strike Zone
> 36%, Batter 24%, gaps controlados y todo el grupo centrado.
>
> Limita la Strike Zone a aproximadamente `clamp(320px, 25vw, 430px)` y
> conserva `aspect-ratio: 1 / 1`. No debe crecer indefinidamente en
> 1440p o 4K.
>
> Pitcher y Batter deben compartir top alignment y altura exterior
> equivalente. Next Batter debe permanecer inmediatamente debajo del
> Batter, utilizar exactamente su ancho de columna y una altura
> aproximada de 60--80px.
>
> Convierte Actions y LANZAR en una sola `Action Area` horizontal: las
> cuatro Action Cards ocupan el espacio principal y LANZAR aparece a la
> derecha como acción primaria, compartiendo la misma línea visual. No
> dejes LANZAR flotando separado del resto.
>
> En Desktop Gameplay todo debe caber dentro de `100dvh` sin scroll
> vertical. Para resoluciones con poca altura, como 1366×768, activa un
> modo Desktop Compact reduciendo gaps, paddings y tamaños dentro de
> límites antes de eliminar información.
>
> No modifiques el layout móvil `Pitcher | Strike Zone | Batter`, ni su
> Score Area, Next Batter, Actions + LANZAR, paddings, tamaños o
> comportamiento táctil. Después de los cambios verifica específicamente
> 390×844 y 430×932 para confirmar que Mobile permanece visualmente
> igual.
>
> Trata cualquier regresión móvil provocada por esta tarea como un bug.
> Esta iteración es exclusivamente un ajuste de composición Desktop, no
> un rediseño general.
