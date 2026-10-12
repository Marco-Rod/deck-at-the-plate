# Alcance V1: Gameplay y ETL

## Propósito

Este documento define el producto mínimo que queremos entregar y los límites
del ETL que lo respalda. Es una referencia de alcance y decisiones de producto;
no es un plan técnico de implementación ni un inventario de tareas.

La regla que guía esta etapa es simple:

> El ETL existe para entregar las cartas que el gameplay necesita. No se
> construirán capacidades de datos sólo por si pudieran ser útiles después.

## Experiencia objetivo de Gameplay V1

Una persona puede registrarse, crear su club, elegir una franquicia, recibir
un mazo inicial, definir un lineup, jugar una partida completa contra CPU y
consultar el resultado.

La primera versión cubre:

- Registro, inicio de sesión y perfil de jugador.
- Creación de club y elección de franquicia.
- Inventario, mazo inicial y lineup válido.
- Partidas contra CPU de principio a fin.
- Pitcheo, swing, zona, cuenta, corredores, outs, innings, marcador y final
  de partida.
- Cambio de pitcher y cartas tácticas cuando formen parte de un flujo estable.
- Cartas de mejora aplicables a jugadores, con efectos explícitos y acotados.
- Persistencia y recuperación básica de una partida.

### Estado conocido del alcance

Las siguientes capacidades ya existen en el backend y la PWA, por lo que en
esta etapa se consideran base que se debe conservar y validar, no trabajo a
rediseñar:

| Capacidad | Estado para V1 |
| --- | --- |
| Registro e inicio de sesión | Existe |
| Creación de club y elección de franquicia | Existe |
| Inventario, mazo inicial y lineup válido | Existe |
| Crear y completar una partida contra CPU | Existe |
| Pitcheo, swing, zona, cuenta, corredores, outs, innings, marcador y final de partida | Existe |
| Cambio de pitcher y cartas tácticas | Existe |
| Persistencia y recuperación de partida | Requiere validación específica |
| Cartas de mejora de jugadores | Pendiente de diseño |

Que una capacidad exista no elimina su validación: debe seguir funcionando con
las cartas base y el catálogo que defina el ETL V1. Las cartas de mejora no se
implementarán hasta definir sus tipos, límites, duración, forma de obtención y
qué atributos pueden modificar.

## Perfil de jugador y progreso

El perfil debe ser el lugar donde una persona entiende su progreso, aun cuando
algunos valores comiencen en cero o ciertas fuentes se habiliten en etapas
posteriores. La información se organiza por modo para no mezclar contextos
distintos.

El perfil objetivo incluye:

- Récord global y récord separado contra CPU y en juego online: victorias,
  derrotas y, cuando aplique, empates o abandonos.
- Monedas o recursos disponibles.
- Mejor jugador disponible, definido de forma explícita por el `overall` de la
  carta actualmente poseída.
- Acumulados de equipo separados para CPU y online: carreras, hits, home runs,
  strikeouts, promedio de bateo (`AVG`), efectividad (`ERA`) y las estadísticas
  que se incorporen después.
- Resúmenes individuales de jugadores cuando exista suficiente información:
  por ejemplo HR, hits, SO, AVG y ERA según su rol.

No todas estas métricas tienen que estar pobladas desde el primer día. El
contrato del perfil debe permitir mostrar valores iniciales claros y fuentes
pendientes sin inventar estadísticas. Cada juego terminado debe poder aportar
eventos o un resumen que alimente los acumulados correspondientes a su modo.

Una partida contra CPU nunca altera el récord ni los acumulados online, y una
mini temporada conserva además sus métricas propias dentro de su competencia.

El resultado de un lanzamiento debe sentirse informado por las cartas y las
decisiones de ambos lados, pero conservar incertidumbre mediante RNG
reproducible.

## Resolución de un lanzamiento

El motor resuelve cada lanzamiento combinando señales, en este orden:

1. Atributos base de pitcher y bateador.
2. Decisiones de ambos jugadores: tipo de lanzamiento, zona, tipo de swing y
   predicción de zona o pitcheo.
3. Contexto de juego: cuenta, fatiga y situación de bases cuando aplique.
4. Modificadores opcionales disponibles para el modo de juego.
5. RNG ponderado que determina el resultado final.

El `overall` no decide una jugada. Sirve para presentar y comparar cartas,
formar lineups y apoyar la rareza; el motor usa los atributos específicos.

## Cartas base

Cada jugador del catálogo inicial tiene una sola carta base estable. Se genera
a partir de una temporada de referencia configurable y de los datos suficientes
para ese jugador. Las cartas base no cambian durante una partida.

### Atributos de bateador

- **Contacto:** capacidad de poner la bola en juego y producir contacto útil.
- **Poder:** potencial de extra bases y contacto de impacto.
- **Visión:** disciplina y capacidad de evitar swings fallidos.
- **Clutch:** se conserva como campo neutral en V1; no modifica todavía la
  resolución del motor.

### Atributos de pitcher

- **Velocidad:** velocidad de los lanzamientos.
- **Control:** capacidad de ubicar y evitar boletos.
- **Movimiento:** quiebre y movimiento del repertorio.
- **Stuff:** capacidad de provocar fallos y de limitar contacto peligroso.

Los atributos se expresan en una escala de 40 a 99 y se calculan frente a la
población del catálogo, no como valores arbitrarios por jugador.

## Overall de cartas

El `overall` se deriva de los atributos finales de la carta. La política base
actual es la referencia para V1:

| Rol | Componentes del overall |
| --- | --- |
| Bateador | 30% contacto, 30% poder, 25% visión, 15% clutch |
| Pitcher | 20% velocidad, 30% control, 25% movimiento, 25% stuff |

Mientras `clutch` sea neutral, su participación en el overall debe considerarse
una decisión transitoria y versionada. Activarlo, modificar sus pesos o
reemplazarlo por otro atributo no debe alterar contratos ni partidas existentes.

## Historiales y modos de juego

Hay dos fuentes de historial que nunca deben confundirse:

- **Historial de referencia:** datos externos de hasta una o dos temporadas.
  Puede usarse como modificador opcional y de peso limitado para un duelo
  pitcher–bateador.
- **Historial de competencia:** datos generados dentro de un modo de juego.
  Sólo viven en ese contexto competitivo y no modifican el historial externo
  ni otras partidas.

Las partidas rápidas pueden usar únicamente las cartas base. Una mini temporada
comparte un identificador de competencia y conserva sus propios enfrentamientos:
resultados pitcher–bateador, tipos de lanzamiento y estadísticas acumuladas.
Ese historial aporta una señal reciente, pero no vuelve determinista el juego.

Las mejoras de cartas y los historiales de competencia son modificadores sobre
la carta base, no reescrituras de sus atributos de origen.

## Límite del ETL V1

El ETL V1 debe producir un catálogo inicial jugable de cartas base para los
equipos predeterminados. Puede reutilizar las piezas existentes para:

- Obtener y normalizar metadatos de equipos y jugadores.
- Ingerir la temporada de referencia necesaria.
- Agregar estadísticas para los atributos definidos arriba.
- Calcular atributos, overall y repertorios.
- Materializar cartas que el backend y el gameplay puedan consumir.

No forma parte de esta etapa:

- Cartas de momentos históricos, eventos especiales o múltiples ediciones.
- Ciclos complejos de publicación, rareza basada en distribuciones extensas y
  auditorías de catálogo.
- Identidades ficticias, backfills históricos y modelos de evidencia avanzados.
- Importar datos exhaustivos de todas las temporadas o todas las situaciones.
- Hacer que H2H histórico sea necesario para crear una carta o jugar un partido.

## Principios de evolución

- Una partida siempre debe poder resolverse con cartas base y contexto local.
- Datos nuevos sólo agregan modificadores opcionales; no se vuelven requisitos
  ocultos del gameplay.
- Los contratos entre PWA, backend y motor deben mantenerse estables cuando se
  agreguen fuentes de datos o modos.
- Toda política de atributos, overall o mejora debe tener versión y dejar clara
  su fuente.
- Se prioriza una experiencia completa y jugable sobre una simulación histórica
  exhaustiva.
