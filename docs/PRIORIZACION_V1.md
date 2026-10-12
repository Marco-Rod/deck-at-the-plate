# Priorización de trabajo para V1

## Objetivo de esta etapa

La prioridad inmediata no es ampliar gameplay ni terminar todo el ETL actual.
Es demostrar y dejar delimitado el flujo mínimo que permite que las cartas base
alimenten de forma confiable una partida contra CPU:

```text
datos de referencia → atributos de carta → catálogo activo
→ sobres e inventario → lineup y roster CPU → partida completa
```

El ETL debe liberar el gameplay, no convertirse en un proyecto paralelo sin
final. Toda tarea que no fortalezca este recorrido queda aplazada hasta que el
catálogo inicial sea verificable.

## Prioridades

### P0 — Auditoría de integración ETL a gameplay

**Propósito:** conocer el recorrido efectivo de los datos, desde su origen
hasta una partida, y localizar dependencias todavía basadas en seeds o datos
manuales.

**Incluye:**

- Identificar qué comandos y módulos actuales generan atributos, perfiles,
  cartas y catálogos.
- Seguir cómo el backend resuelve el catálogo activo para equipos CPU, starter
  packs, inventario, lineup y creación de partida.
- Comparar el contrato de las cartas materializadas con los atributos que
  consume el motor.
- Distinguir rutas activas, rutas legacy y rutas que existen pero no participan
  en el flujo V1.

**Terminado cuando:** exista una tabla de trazabilidad con cada eslabón del
flujo, sus archivos/commands de origen, entradas, salidas y huecos concretos.
No se modifica código en esta tarea.

### P1 — Definición del contrato de carta base V1

**Propósito:** fijar qué información debe tener una carta para que el juego
funcione, independientemente de cómo evolucionen las fuentes de datos.

**Incluye:**

- Atributos de bateador: contacto, poder y visión; clutch neutral y sin efecto.
- Atributos de pitcher: velocidad, control, movimiento y stuff.
- Posición, repertorio, equipo, identidad, overall derivado y versión de
  política.
- Reglas de valores faltantes, rangos permitidos y población mínima.
- Una sola temporada de referencia y un único catálogo `BASE` activo para V1.

**Terminado cuando:** el contrato se pueda validar contra `PlayerCardModel`,
los payloads de API y el motor, y no dependa de boosts, H2H ni momentos.

### P2 — Catálogo inicial reproducible

**Propósito:** conseguir que el ETL mínimo produzca cartas base suficientes
para jugar, sin invocar sistemas avanzados fuera de V1.

**Incluye:**

- Conservar sólo la ingesta, agregación, cálculo de atributos, overall,
  repertorio y materialización necesarios.
- Aislar o aplazar momentos, ediciones especiales, H2H externo, auditorías
  extensas, identidades alternativas y políticas de rareza complejas.
- Registrar versión de fuente, temporada y política de atributos en el
  catálogo publicado.

**Terminado cuando:** un catálogo `BASE` puede crearse de forma repetible y
queda listo para ser activado sin depender de seeds legacy.

### P3 — Validación de compatibilidad con juego

**Propósito:** demostrar que el catálogo producido sirve al flujo existente de
juego, no sólo que las tablas se llenan.

**Incluye:**

- Verificar que cada equipo CPU elegible tiene al menos nueve bateadores y un
  pitcher; idealmente, bullpen suficiente.
- Verificar que el starter pack puede generar sus 13 cartas con posiciones
  válidas.
- Crear lineup, iniciar partida CPU y comprobar que los atributos llegan al
  resolver de lanzamiento.
- Confirmar que cambios de catálogo no reinterpretan una partida ya iniciada.

**Terminado cuando:** las validaciones pasan para el catálogo activo y existe
una prueba focalizada o procedimiento reproducible para ejecutarlas.

### P4 — Cerrar continuidad de partida y perfil

**Propósito:** completar el ciclo del jugador una vez que las cartas base sean
confiables.

**Incluye:**

- Endpoint y UI para descubrir una partida pendiente al volver a iniciar
  sesión.
- Prueba integral de recarga, desconexión y recuperación.
- Modelo de acumulados por modo: `CPU_QUICK`, `ONLINE` y `SEASON`.
- Acumulados de usuario y de jugador por modo, actualizados al finalizar una
  partida.
- Perfil con récord, recursos, mejor carta por overall y estadísticas
  disponibles.

**Terminado cuando:** una partida puede jugarse, retomarse, finalizarse y
reflejarse correctamente en el perfil sin mezclar modos.

### P5 — Diseño cerrado de boosts y mini temporada

**Propósito:** convertir las ideas posteriores de gameplay en contratos claros,
sin frenar la salida de la base jugable.

**Incluye:**

- Comparar el documento existente de boosts con las decisiones V1.
- Definir pools ofensivo y defensivo, tiers, límites, duración por
  enfrentamiento y semilla RNG persistida por partida.
- Definir mini temporada, `competition_id` e historial interno aislado.

**Terminado cuando:** existen reglas de producto y contratos de datos
suficientes para implementar el sistema sin modificar cartas base ni
estadísticas permanentes.

## Lo que queda explícitamente aplazado

- H2H histórico externo como requisito de resolución.
- Cartas de momentos, eventos y ediciones paralelas.
- Rareza basada en modelos o distribuciones complejas.
- Importaciones históricas exhaustivas y todas las auditorías avanzadas del
  ETL actual.
- Implementación de boosts antes de que su diseño quede acordado.
- Mini temporada y online antes de que perfil, persistencia y estadísticas por
  modo estén bien separados.

## Regla para decidir nuevas tareas

Una tarea entra antes de P4 sólo si responde afirmativamente a esta pregunta:

> ¿Hace más confiable que una persona reciba cartas base válidas y pueda jugar
> una partida completa contra CPU con ellas?

Si no, se coloca en P4 o posterior, salvo que corrija una regresión crítica.
