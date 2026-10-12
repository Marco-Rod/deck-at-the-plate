# Principios de mantenibilidad para V1

## Propósito

El código de V1 debe poder explicarse, probarse y modificarse sin depender de
una sola persona ni de archivos enormes. La prioridad no es dividir código por
dividirlo: es que cada módulo tenga una responsabilidad reconocible y una
frontera clara.

## Reglas de diseño

### Una responsabilidad por módulo

Cada archivo debe responder una pregunta concreta. Ejemplos:

- Un pipeline orquesta pasos, pero no contiene fórmulas de ratings ni consultas
  complejas.
- Un cálculo de atributo recibe datos y devuelve un resultado; no hace llamadas
  HTTP ni commits a la base de datos.
- Un repositorio consulta o persiste datos; no decide reglas de gameplay.
- Un router valida HTTP, autorización y respuestas; no contiene lógica de
  dominio.
- Un componente de PWA presenta o coordina interacción; no recrea reglas que
  pertenecen al backend.

Cuando un archivo mezcla dos o más de esas responsabilidades, debe dividirse
antes de añadir una característica importante.

### Dependencias en una sola dirección

La dirección deseada es:

```text
PWA → API/routers → servicios de aplicación → dominio/motor → repositorios/modelos
ETL → fuentes/normalizadores → agregadores/cálculos → materialización de cartas
```

El motor de gameplay no importa PWA, routers, ETL ni detalles de persistencia.
El ETL puede materializar cartas, pero el gameplay nunca ejecuta un pipeline ni
depende de que una fuente externa esté disponible durante una partida.

### Contratos explícitos

Los límites entre capas se expresan con tipos, DTOs, esquemas o estructuras de
datos con nombre. No se pasan diccionarios genéricos sin documentar entre capas
críticas.

Los contratos que merecen especial cuidado son:

- Carta base materializada → motor de gameplay.
- Estado de partida → API/WebSocket → PWA.
- Resultado de partida → estadísticas acumuladas por modo.
- Oferta de boost → estado persistido de partida → resolución de turno.

Cambiar un contrato requiere pruebas de sus consumidores antes de mezclarlo con
otros cambios.

### Funciones puras para reglas y cálculos

Las fórmulas de atributos, overall, RNG ponderado, boosts y transiciones de
estado deben ser funciones puras siempre que sea posible:

- entradas explícitas;
- salida determinista para una semilla dada;
- sin commits, red, reloj ni estado global oculto.

Esto permite explicar una jugada, reproducir un fallo y probar el balance sin
levantar toda la aplicación.

### Orquestadores pequeños

Los puntos de entrada pueden coordinar varios pasos, pero no deben convertirse
en archivos que concentran todas las reglas. Como señal de revisión:

- Si una función necesita muchas secciones comentadas para distinguir tareas,
  probablemente debe extraer colaboradores con nombre.
- Si un archivo crece de forma sostenida y ya no se puede resumir en una frase,
  hay que separar responsabilidades antes de seguir extendiéndolo.
- El CLI y los pipelines V1 deben delegar a comandos o casos de uso pequeños;
  no ser el lugar donde viven las fórmulas y políticas.

No se impone un número rígido de líneas. El criterio es comprensión local:
una persona debe poder entender qué hace un módulo sin recorrer todo el
repositorio.

### Configuración y versiones visibles

Pesos, rangos, reglas de tiers, temporadas, políticas de overall y versiones de
motor deben vivir en configuración o políticas con nombre. No se agregan
números mágicos dentro de routers o flujos de orquestación.

Toda política que afecte cartas o partidas debe registrar una versión cuando se
materialice o se inicie una partida.

### Legacy aislado

El código legacy se conserva para consulta, pero no forma parte de rutas activas
por accidente.

- No se agregan imports nuevos desde código V1 hacia `legacy/`.
- Si una transición necesita consultar legacy, se crea un adaptador temporal y
  una fecha o condición para retirarlo.
- Mover código a legacy ocurre sólo después de clasificarlo y comprobar que el
  flujo V1 no lo consume.

## Reglas específicas para ETL V1

- `pipelines/base_catalog_v1.py` será un orquestador legible del único flujo
  activo de catálogo base; reutiliza componentes, no copia cálculos.
- Cada atributo tendrá su módulo o política identificable, fuente de datos,
  rango de salida y prueba propia.
- La materialización de cartas estará separada del cálculo de atributos.
- La validación de rosters CPU y starter packs será una comprobación explícita,
  no un efecto lateral de publicar el catálogo.
- Funciones de auditoría, momentos, ediciones especiales y H2H no se mezclan
  en el flujo V1.

## Reglas específicas para gameplay

- El resolver de lanzamiento recibe estado y modificadores explícitos.
- Las boost cards son modificadores temporales de una partida; no mutan cartas
  base ni agregados históricos.
- Los eventos de juego guardan hechos base; AVG, ERA y otras vistas se derivan
  o se actualizan mediante una política definida.
- La PWA representa el estado recibido; la resolución autoritativa ocurre en
  backend.

## Pruebas mínimas por cambio

Cada cambio relevante debe añadir o ajustar la prueba más cercana a su
responsabilidad:

- Cálculo puro: prueba unitaria.
- Política de carta o ETL: prueba de contrato/materialización.
- Endpoint o WebSocket: prueba de integración.
- Flujo crítico de persona jugadora: prueba de extremo a extremo focalizada.

Una prueba no sustituye a otra: tener pruebas unitarias no demuestra que la PWA
pueda retomar una partida, y una prueba de UI no demuestra que una fórmula de
ratings sea correcta.

## Criterio para aceptar trabajo

Antes de considerar terminada una tarea, debe poder responderse:

1. ¿Qué responsabilidad añade o modifica?
2. ¿Qué contrato consume y cuál produce?
3. ¿Qué prueba demuestra su comportamiento?
4. ¿Qué módulo queda como fuente de verdad?
5. ¿La nueva complejidad pertenece a V1 o debe aplazarse?
