# Instrucciones para auditar Deck at the Plate V1

## Rol

Actúa como auditor técnico y de producto. Tu objetivo es producir evidencia
clara para decidir los siguientes pasos de Deck at the Plate, no reescribir el
proyecto ni proponer una plataforma más grande.

Tu trabajo es **de sólo lectura**. No modifiques archivos, no ejecutes resets,
seeds, migraciones ni comandos que escriban en la base de datos. Puedes ejecutar
inspecciones, búsquedas y pruebas no destructivas cuando sean necesarias.

Lee primero [ALCANCE_V1_GAMEPLAY_Y_ETL.md](ALCANCE_V1_GAMEPLAY_Y_ETL.md). Es la
fuente de verdad de alcance para esta auditoría. La documentación situada en
`_archivo_documentacion_pre_etapa_etl_2026-10-11/` es histórica: puede servir
como contexto, pero no define requisitos actuales.

## Principio rector

> Una capacidad sólo se considera parte de V1 si permite jugar, completar,
> guardar o entender una partida y sus cartas base. Todo lo demás requiere una
> justificación explícita para entrar al alcance.

No confundas “existe código” con “está terminado”. Evalúa tanto la conexión
entre capas como el flujo que ve una persona jugadora.

## Alcance de la auditoría

Audita las siguientes áreas, en este orden. No profundices en ETL que quede
fuera de las cartas base de V1 salvo para explicar una dependencia concreta.

### 1. Gameplay existente

Valida los flujos ya declarados como existentes:

- Registro, inicio de sesión y perfil.
- Creación de club, franquicia, inventario, starter pack y lineup.
- Creación y partida completa contra CPU.
- Pitcheo, swing, zona, cuenta, corredores, outs, innings, marcador y final.
- Cambio de pitcher y cartas tácticas.

Para cada flujo, identifica:

- Ruta de la PWA que lo inicia.
- Endpoint HTTP o WebSocket involucrado.
- Servicio, motor o repositorio del backend que lo resuelve.
- Datos que lee y persiste.
- Pruebas existentes y huecos de pruebas.
- Riesgos concretos que impidan considerarlo estable para V1.

### 2. Persistencia y recuperación de partidas

Determina con precisión:

- Qué estado es autoritativo en backend y en qué momentos se persiste.
- Qué estado sólo existe en el navegador y dónde se guarda.
- Qué ocurre al recargar la página, cerrar el navegador, perder conexión y
  volver a iniciar sesión.
- Cómo descubre una persona que tiene una partida pendiente y cómo la retoma.
- Si se pueden mezclar, perder o exponer estados de usuarios o partidas
  distintas.

No des por resuelto el punto porque exista IndexedDB o una tabla de sesiones;
describe el flujo completo que realmente se ejecuta.

### 3. Perfil, progreso y estadísticas

Revisa qué datos ya se registran por juego y qué puede agregarse sin alterar
los contratos actuales. Evalúa específicamente:

- Récord global, contra CPU y online.
- Monedas o recursos.
- Mejor carta disponible.
- Estadísticas acumuladas de equipo e individuales: HR, hits, SO, AVG, ERA y
  las bases requeridas para calcularlas.
- Separación estricta entre CPU, online y mini temporada.

Clasifica cada métrica como: disponible, derivable con datos existentes,
requiere nueva persistencia o fuera de V1.

### 4. Cartas base y atributos

Comprueba la cadena completa:

```text
fuente de datos → cálculo de atributos → overall → catálogo/carta → motor de juego
```

Evalúa:

- Si los atributos de bateador y pitcher están definidos y dentro de rango.
- Cómo se calcula hoy el overall y si se deriva de atributos finales.
- Qué atributos consume realmente el resolver de lanzamiento.
- Si el catálogo activo puede producir rosters CPU y starter packs válidos.
- Qué rutas siguen dependiendo de seeds o valores manuales legacy.

El objetivo de V1 es una carta base estable por jugador, usando una temporada
de referencia configurable. No conviertas momentos especiales, rareza compleja,
ediciones múltiples ni H2H externo en requisitos de esta auditoría.

### 5. Mejoras de cartas

No diseñes ni implementes el sistema. Identifica únicamente qué extensiones
serían necesarias para soportarlo sin modificar la carta base:

- Dónde se guardarían mejoras e inventario asociado.
- Cómo podrían entrar como modificadores del motor.
- Límites que el modelo actual ya impone o no impone.
- Riesgo de persistencia, balance o compatibilidad.

### 6. Modos e historiales

Valida la separación necesaria entre:

- Partida rápida contra CPU.
- Mini temporada con historial propio.
- Juego online futuro.
- Historial externo de referencia, opcional y limitado a una o dos temporadas.

La conclusión debe dejar claro que una partida se resuelve aun si no existe
historial externo ni de competencia. El historial es un modificador opcional,
nunca una condición para jugar.

### 7. ETL V1 mínimo

Identifica exclusivamente los módulos, modelos y fuentes necesarios para crear
el catálogo inicial de cartas base. Para cada parte actual del ETL, clasifica:

- **Conservar para V1:** necesaria para datos de equipo/jugador, atributos,
  overall, repertorio o materialización de cartas.
- **Aplazar:** valiosa, pero no bloquea el catálogo inicial ni una partida.
- **Legacy o eliminar del flujo activo:** sólo soporta seeds, momentos,
  auditorías o complejidad fuera del alcance.

No propongas borrar código durante la auditoría. La recomendación debe ser de
clasificación y aislamiento, con evidencia.

## Método de trabajo

1. Inspecciona la estructura del repositorio y los documentos de alcance.
2. Sigue cada flujo desde la PWA hasta el backend y la base de datos.
3. Usa búsquedas de referencias, tipos, rutas, migraciones, modelos y pruebas.
4. Ejecuta pruebas focalizadas sólo si el entorno ya está preparado y la prueba
   no modifica servicios ni datos persistentes.
5. Diferencia observaciones confirmadas de inferencias. Para cada conclusión,
   cita rutas de archivo y símbolos concretos.
6. No asumas que una ruta no usada por la PWA está muerta: clasifícala como
   “no observada en el flujo V1” y explica qué comprobaste.

## Formato obligatorio de la respuesta

Entrega un informe en español, conciso pero sustentado, con estas secciones:

1. **Resumen ejecutivo**
   - Estado general de V1 en pocas líneas.
   - Máximo cinco conclusiones que más cambian la priorización.

2. **Matriz de capacidades**

   | Capacidad | Estado | Evidencia | Riesgo o hueco | Próxima decisión |
   | --- | --- | --- | --- | --- |

   Usa sólo estos estados: `estable`, `parcial`, `no verificado`, `ausente`,
   `fuera de V1`.

3. **Hallazgos por área**
   - Gameplay.
   - Persistencia y recuperación.
   - Perfil y estadísticas.
   - Cartas base y atributos.
   - Modos e historiales.
   - ETL V1.

4. **Dependencias críticas**
   - Un diagrama breve o lista de cadenas de dependencia que expliquen qué
     bloquea qué. Incluye PWA, API, modelos, motor y ETL sólo cuando aplique.

5. **Decisiones que necesita tomar el equipo**
   - Formula preguntas concretas y limitadas. No pidas decisiones que se puedan
     comprobar leyendo el código.

6. **Siguiente lote recomendado**
   - Propón entre tres y cinco unidades de trabajo pequeñas y ordenadas por
     impacto y dependencia.
   - Cada unidad debe tener una condición observable de terminado.
   - No propongas refactors amplios ni trabajo ETL fuera del alcance V1.

7. **Apéndice de evidencia**
   - Lista de archivos, endpoints, modelos, pruebas y comandos de lectura
     consultados.

## Criterios de calidad

Una buena auditoría:

- Distingue claramente entre sistema existente, sistema parcialmente conectado
  y sistema deseado.
- Prioriza flujos completos por encima de archivos grandes o sofisticados.
- Protege la experiencia jugable si una fuente externa o un cálculo opcional
  no está disponible.
- Evita recomendaciones basadas en futuros hipotéticos.
- Termina con decisiones ejecutables para el equipo, no sólo con una lista de
  problemas.
