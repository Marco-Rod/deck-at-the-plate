# Deck at the Plate --- Desktop CoreGameplay Height Fix v1.6

## Objetivo

Corregir definitivamente la relación de tamaño entre:

-   Pitcher Card
-   Strike Zone
-   Batter Card
-   Next Batter

Esta corrección aplica **únicamente a Desktop (`min-width: 1200px`)**.

> **IMPORTANTE:** No modificar el layout, tamaños ni comportamiento de
> la versión Mobile actualmente aprobada.

------------------------------------------------------------------------

## 1. Problema detectado

La implementación actual está intentando cumplir simultáneamente estas
reglas:

1.  La Strike Zone debe ser cuadrada.
2.  La Strike Zone debe tener la misma altura visual que Pitcher y
    Batter.
3.  La columna central usa una proporción fluida basada en `fr`.
4.  Las Player Cards tienden a ajustar su altura según su contenido.

Estas reglas entran en conflicto.

Cuando la columna central crece horizontalmente y la Strike Zone tiene:

``` css
aspect-ratio: 1 / 1;
```

el navegador puede terminar calculando la altura de la Strike Zone a
partir de su ancho.

Ejemplo:

``` text
Columna central = 400px de ancho
Strike Zone = aspect-ratio 1 / 1

Resultado:
Strike Zone ≈ 400px de alto
```

Mientras tanto, Pitcher y Batter pueden seguir midiendo únicamente lo
necesario para su contenido.

Resultado visual incorrecto:

``` text
            ┌──────────────┐
┌────────┐  │              │  ┌────────┐
│Pitcher │  │ Strike Zone  │  │ Batter │
│        │  │              │  │        │
└────────┘  │              │  └────────┘
            └──────────────┘
```

La Strike Zone termina dominando verticalmente el CoreGameplay.

------------------------------------------------------------------------

# 2. Nueva regla definitiva

En Desktop, `CoreGameplay` debe tener **una única fuente de verdad para
la altura del matchup**.

Crear una variable:

``` css
--matchup-height
```

Esta variable debe controlar simultáneamente:

-   altura de Pitcher Card;
-   altura de Batter Card;
-   altura de Strike Zone;
-   ancho de Strike Zone.

Por tanto:

``` text
Pitcher height     = --matchup-height
Batter height      = --matchup-height
Strike Zone height = --matchup-height
Strike Zone width  = --matchup-height
```

Esto garantiza matemáticamente:

``` text
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│              │  │              │  │              │
│              │  │              │  │              │
│   PITCHER    │  │ STRIKE ZONE  │  │    BATTER    │
│              │  │              │  │              │
│              │  │              │  │              │
│              │  │              │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
       ↑                 ↑                 ↑
       └──── MISMO TOP + MISMO BOTTOM ─────┘
```

------------------------------------------------------------------------

# 3. No usar `fr` para dimensionar la Strike Zone

Eliminar patrones como:

``` css
grid-template-columns:
    minmax(260px, 1fr)
    minmax(var(--core-height), 1.2fr)
    minmax(260px, 1fr);
```

La parte problemática es:

``` css
1.2fr
```

porque permite que la columna central crezca por encima de la altura que
queremos usar como referencia.

En Desktop, la columna de Strike Zone debe ser determinista.

Usar:

``` css
grid-template-columns:
    minmax(260px, 340px)
    var(--matchup-height)
    minmax(260px, 340px);
```

------------------------------------------------------------------------

# 4. Implementación recomendada de CoreGameplay

``` css
@media (min-width: 1200px) {
    .core-gameplay {
        --matchup-height: clamp(260px, 30dvh, 330px);

        display: grid;

        grid-template-columns:
            minmax(260px, 340px)
            var(--matchup-height)
            minmax(260px, 340px);

        grid-template-rows:
            var(--matchup-height)
            auto;

        grid-template-areas:
            "pitcher zone batter"
            ".       .    next";

        column-gap: clamp(24px, 3vw, 48px);
        row-gap: 8px;

        justify-content: center;
        align-items: stretch;
    }
}
```

La altura inicial recomendada es:

``` css
--matchup-height: clamp(260px, 30dvh, 330px);
```

No aumentar todavía el máximo a 390px.

Primero validar visualmente el rango `260–330px`.

------------------------------------------------------------------------

# 5. Pitcher Card

Pitcher debe ocupar exactamente la altura del matchup:

``` css
@media (min-width: 1200px) {
    .pitcher-card {
        grid-area: pitcher;

        width: 100%;
        height: var(--matchup-height);

        display: flex;
        flex-direction: column;
    }
}
```

Su contenido no debe determinar la altura exterior de la tarjeta.

------------------------------------------------------------------------

# 6. Batter Card

Batter debe utilizar exactamente la misma altura:

``` css
@media (min-width: 1200px) {
    .batter-card {
        grid-area: batter;

        width: 100%;
        height: var(--matchup-height);

        display: flex;
        flex-direction: column;
    }
}
```

Aunque Batter tenga menos información que Pitcher, **no debe encogerse
hasta su contenido**.

------------------------------------------------------------------------

# 7. Distribución interna de Player Cards

Usar Flexbox para permitir que la estructura exterior mantenga su altura
mientras el contenido interno se distribuye correctamente.

Ejemplo:

``` css
.player-card {
    display: flex;
    flex-direction: column;
}

.player-card__header {
    flex: 0 0 auto;
}

.player-card__body {
    flex: 1 1 auto;
}

.player-card__footer {
    flex: 0 0 auto;
    margin-top: auto;
}
```

En Pitcher, el footer puede contener:

``` text
STAMINA
████████ 80%

⚾ 6 LANZ.
```

En Batter, el footer puede quedar vacío si no existe información real
que mostrar.

No agregar contenido ficticio únicamente para llenar espacio.

------------------------------------------------------------------------

# 8. Strike Zone Wrapper

La columna central debe medir exactamente lo mismo que
`--matchup-height`.

``` css
@media (min-width: 1200px) {
    .strike-zone-wrapper {
        grid-area: zone;

        width: var(--matchup-height);
        height: var(--matchup-height);

        min-width: 0;
        min-height: 0;
    }
}
```

No utilizar:

``` css
width: 100%;
```

si el wrapper está dentro de una columna que puede crecer mediante `fr`.

La dimensión debe venir directamente de:

``` css
var(--matchup-height)
```

------------------------------------------------------------------------

# 9. Strike Zone

La Strike Zone interna debe ocupar completamente su wrapper:

``` css
@media (min-width: 1200px) {
    .strike-zone {
        width: 100%;
        height: 100%;

        aspect-ratio: 1 / 1;
    }
}
```

Con esta estructura:

``` text
wrapper:
330 × 330

strike-zone:
100% × 100%

resultado:
330 × 330
```

No existe ninguna ambigüedad para el navegador.

------------------------------------------------------------------------

# 10. Next Batter debe estar fuera de la altura del matchup

`Next Batter` no forma parte del enfrentamiento actual.

No debe participar en el cálculo de:

``` css
--matchup-height
```

Debe vivir en una segunda fila del Grid.

``` css
grid-template-areas:
    "pitcher zone batter"
    ".       .    next";
```

Y:

``` css
.next-batter {
    grid-area: next;
}
```

Resultado:

``` text
              CURRENT MATCHUP

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   PITCHER   │ │ STRIKE ZONE │ │   BATTER    │
│             │ │             │ │             │
│             │ │             │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
                                      │
                                      │ 8px
                                      ▼
                                ┌─────────────┐
                                │ NEXT BATTER │
                                └─────────────┘
```

Esto refuerza también la jerarquía conceptual:

``` text
Current Pitcher ↔ Strike Zone ↔ Current Batter
                         ↓
                    Next Batter
```

------------------------------------------------------------------------

# 11. No envolver Batter + Next Batter en una columna que determine la altura

Evitar que la estructura principal sea:

``` html
<div class="batter-column">
    <BatterCard />
    <NextBatter />
</div>
```

si `.batter-column` es el elemento utilizado por el Grid para calcular
la altura del matchup.

Eso provoca que la altura de esa columna sea:

``` text
Batter
+
gap
+
Next Batter
```

y deja de representar la altura real del Batter actual.

Preferir que Grid conozca los elementos individualmente:

``` html
<div class="core-gameplay">

    <PitcherCard class="pitcher-card" />

    <StrikeZone class="strike-zone-wrapper" />

    <BatterCard class="batter-card" />

    <NextBatter class="next-batter" />

</div>
```

Conceptualmente:

``` text
Grid item 1 = Pitcher
Grid item 2 = Zone
Grid item 3 = Batter
Grid item 4 = Next Batter
```

------------------------------------------------------------------------

# 12. Geometría esperada

Ejemplo si:

``` css
--matchup-height: 320px;
```

Resultado esperado:

``` text
Pitcher:
width  = 260–340px
height = 320px

Strike Zone:
width  = 320px
height = 320px

Batter:
width  = 260–340px
height = 320px

Next Batter:
width  = ancho de Batter
height = ~60–80px
```

Visualmente:

``` text
        ~300px             320px             ~300px
     ←────────→         ←────────→         ←────────→

     ┌──────────┐       ┌──────────┐       ┌──────────┐
     │          │       │          │       │          │
     │ Pitcher  │       │  Strike  │       │ Batter   │
320  │          │  320  │   Zone   │  320  │          │
px   │          │  px   │          │  px   │          │
     │          │       │          │       │          │
     └──────────┘       └──────────┘       └──────────┘
                                               │
                                               │ 8px
                                               ▼
                                         ┌──────────┐
                                         │   Next   │
                                         └──────────┘
```

------------------------------------------------------------------------

# 13. No confundir ancho de Player Cards con altura

Pitcher y Batter no necesitan ser cuadrados.

Correcto:

``` text
Player Card
width: 300px
height: 320px
```

Strike Zone sí debe ser cuadrada:

``` text
Strike Zone
width: 320px
height: 320px
```

La igualdad requerida es:

``` text
Pitcher height = Zone height = Batter height
```

NO:

``` text
Pitcher width = Zone width = Batter width
```

------------------------------------------------------------------------

# 14. Desktop Compact

Para viewports desktop con poca altura, reducir únicamente
`--matchup-height`.

Ejemplo:

``` css
@media (min-width: 1200px) and (max-height: 800px) {
    .core-gameplay {
        --matchup-height: clamp(240px, 28dvh, 290px);
    }
}
```

El resto de la estructura debe seguir funcionando automáticamente porque
todos los componentes dependen de la misma variable.

------------------------------------------------------------------------

# 15. Desktop con mayor altura

Para pantallas con más espacio vertical se puede permitir un crecimiento
moderado:

``` css
@media (min-width: 1200px) and (min-height: 900px) {
    .core-gameplay {
        --matchup-height: clamp(280px, 30dvh, 340px);
    }
}
```

No hacer crecer indefinidamente la Strike Zone en monitores grandes.

------------------------------------------------------------------------

# 16. Mobile no debe ser modificado

Esta corrección es Desktop-only.

No reutilizar estas dimensiones en:

``` text
Mobile < 768px
Tablet 768–1199px
```

En particular, no cambiar:

-   composición móvil actual;
-   tamaño actual de las cards móviles;
-   Strike Zone móvil;
-   Actions;
-   LANZAR;
-   scoreboard móvil;
-   posición de Next Batter móvil.

Todas las reglas nuevas deben estar encapsuladas dentro de:

``` css
@media (min-width: 1200px) {
    /* Desktop CoreGameplay fix */
}
```

------------------------------------------------------------------------

# 17. Qué eliminar de la implementación actual

Revisar y eliminar cualquier regla Desktop que compita con
`--matchup-height`.

Buscar especialmente:

``` css
height: auto;
min-height: ...;
max-height: ...;
aspect-ratio: ...;
align-self: ...;
grid-auto-rows: ...;
```

en:

``` text
.pitcher-card
.batter-card
.strike-zone
.strike-zone-wrapper
.batter-column
.core-gameplay
```

También revisar reglas heredadas de breakpoints anteriores.

La nueva variable debe ser la fuente de verdad.

------------------------------------------------------------------------

# 18. Revisar `box-sizing`

Asegurar:

``` css
*,
*::before,
*::after {
    box-sizing: border-box;
}
```

Así:

``` css
height: 320px;
```

incluye:

-   contenido;
-   padding;
-   border.

Esto evita diferencias visuales de algunos píxeles entre Zone y Player
Cards.

------------------------------------------------------------------------

# 19. Criterios de aceptación

La implementación se considera correcta cuando en Desktop:

### Alineación

``` text
Pitcher top = Strike Zone top = Batter top
```

y:

``` text
Pitcher bottom = Strike Zone bottom = Batter bottom
```

La diferencia aceptable debe ser visualmente cero.

### Dimensiones

Si:

``` css
--matchup-height: 320px;
```

entonces DevTools debe mostrar aproximadamente:

``` text
Pitcher height     320px
Strike Zone height 320px
Batter height      320px
Strike Zone width  320px
```

### Next Batter

Debe comenzar debajo del Batter:

``` text
Batter bottom
     ↓
   8px gap
     ↓
Next Batter
```

Next Batter no debe modificar la altura del matchup.

### Responsive

La versión móvil debe permanecer visualmente igual a la versión aprobada
antes de esta corrección.

------------------------------------------------------------------------

# 20. Debug recomendado

Antes de ajustar visualmente otros componentes, inspeccionar en
DevTools:

``` js
document.querySelector('.pitcher-card').getBoundingClientRect()
document.querySelector('.strike-zone-wrapper').getBoundingClientRect()
document.querySelector('.batter-card').getBoundingClientRect()
```

Los tres objetos deben devolver el mismo:

``` text
top
height
bottom
```

Ejemplo correcto:

``` text
Pitcher:
top:    310
height: 320
bottom: 630

Zone:
top:    310
height: 320
bottom: 630

Batter:
top:    310
height: 320
bottom: 630
```

Si los valores son diferentes, existe otra regla CSS sobrescribiendo la
geometría.

No compensar el problema agregando márgenes manuales.

Encontrar y eliminar la regla conflictiva.

------------------------------------------------------------------------

# 21. Regla de oro

> En Desktop, Pitcher, Strike Zone y Batter forman una sola unidad
> geométrica llamada Matchup. La altura de los tres elementos debe
> proceder de una única variable `--matchup-height`. La Strike Zone
> utiliza esa misma variable como ancho para conservar su forma
> cuadrada. Next Batter queda fuera de esa unidad y ocupa una segunda
> fila.

------------------------------------------------------------------------

# 22. Prompt directo para la IA

Usar el siguiente texto como instrucción de implementación:

> Corrige únicamente el CoreGameplay de Desktop de Deck at the Plate. No
> modifiques la versión Mobile actualmente aprobada.
>
> El problema actual es que la Strike Zone está calculando parte de su
> tamaño a partir del ancho de una columna flexible y
> `aspect-ratio: 1 / 1`, mientras Pitcher y Batter pueden encogerse
> según su contenido. Esto provoca que las tres piezas no tengan la
> misma altura.
>
> Elimina esta ambigüedad creando una única variable CSS
> `--matchup-height`.
>
> En Desktop (`min-width: 1200px`), Pitcher Card, Strike Zone y Batter
> Card deben tener exactamente `height: var(--matchup-height)`.
>
> La Strike Zone debe tener además `width: var(--matchup-height)`, de
> forma que sea matemáticamente cuadrada.
>
> No uses `fr` para determinar el ancho de la columna central. Define
> `grid-template-columns` como:
>
> ``` css
> minmax(260px, 340px)
> var(--matchup-height)
> minmax(260px, 340px)
> ```
>
> Utiliza inicialmente:
>
> ``` css
> --matchup-height: clamp(260px, 30dvh, 330px);
> ```
>
> CoreGameplay debe usar dos filas y estas áreas:
>
> ``` css
> grid-template-areas:
>     "pitcher zone batter"
>     ".       .    next";
> ```
>
> Pitcher, Zone y Batter deben compartir exactamente el mismo top y
> bottom.
>
> Next Batter debe vivir en la segunda fila debajo de Batter, separado
> aproximadamente 8px, y NO debe participar en el cálculo de altura del
> matchup.
>
> No utilices un wrapper `batter-column` que contenga Batter + Next
> Batter como una sola unidad para calcular la altura principal. Grid
> debe tratar Batter y Next Batter como elementos independientes.
>
> Las Player Cards deben utilizar Flexbox internamente para ocupar toda
> la altura aunque su contenido sea menor. El footer del Pitcher puede
> quedar abajo mediante `margin-top: auto`. Batter puede tener espacio
> libre; no agregues contenido ficticio para llenarlo.
>
> Revisa reglas CSS heredadas que puedan sobrescribir `height`,
> `min-height`, `max-height`, `align-self`, `aspect-ratio` o grid sizing
> en estos componentes.
>
> Usa `box-sizing: border-box`.
>
> Después del cambio, valida con `getBoundingClientRect()` que Pitcher,
> Strike Zone y Batter tengan exactamente el mismo `top`, `height` y
> `bottom`.
>
> No compenses diferencias con márgenes manuales. Si las medidas no
> coinciden, encuentra la regla CSS conflictiva.
>
> Mantén intactos Mobile, Tablet, Actions, LANZAR, Scoreboard y el resto
> del HUD.
