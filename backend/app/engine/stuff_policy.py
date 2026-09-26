"""
Módulo: stuff_policy
===================
Registro único de la política de Stuff del pitcher (GAMEPLAY-ENGINE-003B).

Por qué existe este módulo:
    La semántica de Stuff tiene TRES constantes y dos extremos de una cadena, y
    se reparten entre subsistemas que no deben depender entre sí:

        attribute_mapper  →  necesita saber el Stuff neutro
        fatigue_manager   →  aplica α al Stuff crudo
        calculator        →  aplica k al Stuff ya fatigado

    Si cada uno declarara su propio número, la política congelada quedaría
    replicada en tres sitios y una divergencia sería invisible hasta que una
    partida real saliera mal. Este módulo es el ÚNICO lugar donde vive la
    política, y los tres importan de aquí. Es el equivalente productivo del
    contrato que el LAB congeló en 003B-3/003B-4/003B-5C.

La cadena (003B-6A, sin acoplar fatigue ↔ calculator):

    card.stuff  (crudo, 0-99, ratings-2.0)
        ↓  attribute_mapper
    PitcherAttrs.stuff  (crudo)
        ↓  fatigue_manager  ·  α          ← el ÚNico que ve fatigue_factor
    PitcherAttrs.stuff  (efectivo, float)
        ↓  calculator  ·  k               ← el ÚNico que ve power_score
    supresión de contact-quality

El calculator NO conoce ``fatigue_factor``: recibe un atributo físico ya
transformado. Eso mantiene fatigue_manager → calculator como una sola dirección
y permite testear la supresión de forma determinista sin simular fatiga.

Valores CONGELADOS (no son hyperparameters):

    STUFF_BASELINE           Stuff neutro: delta 0 → supresión 0. Es el valor de
                             identidad que 003B-1 fijó para que la réplica del
                             engine fuera bit-por-bit exacta en el punto medio.
    STUFF_FATIGUE_ALPHA      Coupling de la fatiga: 0 = Stuff ignorado por la
                             fatiga, 1 = Stuff se multiplica por el factor de
                             fatiga (degradación total). 003B-5B encontró la banda
                             sana {.25,.40,.50,.60}; 003B-5C resolvió el empate
                             .50/.60 a favor de .50 por identidad de élites.
    STUFF_POWER_SUPPRESSION  k del poder: cuánto resta al power_score cada punto
                             de Stuff sobre el baseline. Congelado en 003B-3/4
                             tras el sweep de coeficiente; 003B-5B/5C lo
                             revalidaron con α en juego.

Los tres son valores de diseño, no ajustes: cambiarlos requiere reabrir el
ADR correspondiente, igual que k=.30 o la curva SMOOTH-0.55-F35.
"""

# --- Política de Stuff (GAMEPLAY-ENGINE-003B, congelada en 003B-5C) ---

# Stuff neutro (delta = 0). Sustituye al antiguo STUFF_IDENTITY del LAB; mismo
# valor, mismo significado: el punto en el que Stuff no hace nada.
STUFF_BASELINE = 70

# Coupling Stuff×fatiga (003B-5C). effective_stuff = raw * (1 - α·(1 - factor))
STUFF_FATIGUE_ALPHA = 0.50

# k del poder (003B-3/4). power_score += -(stuff - STUFF_BASELINE) * k
STUFF_POWER_SUPPRESSION = 0.30


def effective_stuff(raw_stuff: float, fatigue_factor: float) -> float:
    """Stuff crudo + factor de fatiga → Stuff efectivo (003B-5A, α congelada).

    Fórmula congelada en 003B-5A (familia multiplicativa parcial) y con α
    resuelta en 003B-5C:

        effective_stuff = raw * (1 - α * (1 - factor))

    Propiedades que la hacen segura para producción:

        factor == 1.0  →  ``1 - α*0`` es exactamente 1.0 → effective == raw
                          (identidad exacta en fresco, contrato T2).
        α == 0         →  effective == raw (el control de 003B-5B).
        monotone       →  más fatiga (menor factor) ⇒ menor Stuff efectivo.

    Devuelve un ``float`` a propósito: truncar a entero en esta frontera rompe
    la reproducción bit-exacta del LAB que exige el contrato S1, porque el
    truncado cuantiza la señal justo donde el efecto es más pequeño (Stuff cerca
    del baseline) y donde la fatiga apenas mueve el valor.

    Args:
        raw_stuff:      Stuff de la carta (0-99, columna persistida).
        fatigue_factor: Factor de fatiga en [FATIGUE_FLOOR, 1.0].

    Returns:
        Stuff efectivo como float. Sin clamp: el producto de un 0-99 por un
        factor en (0, 1] cae en el mismo rango, así que un clamp sólo ocultaría
        un ``raw_stuff`` corrupto en vez de defenderlo.
    """
    return raw_stuff * (1.0 - STUFF_FATIGUE_ALPHA * (1.0 - fatigue_factor))


def stuff_power_suppression(effective_stuff_value: float) -> float:
    """Stuff efectivo → desplazamiento del power_score (003B-3/4, k=.30).

    Stuff ALTO es mejor pitcher (más contact-quality), así que SUPREME el
    poder: el signo es negativo. Éste es el brazo S2 congelado, y el signo está
    fijado por evidencia (003B-2 revirtió explícitamente la hipótesis inicial de
    que el Stuff alto amplificaba).

        stuff 95 → -(25 * 0.30) = -7.5
        stuff 70 → -( 0 * 0.30) =  0.0
        stuff 45 → -(-25 * 0.30) = +7.5

    Esos ±7.5 sobre el baseline 70 son el ancla determinista de los contratos
    T4/T5/T6: exactos, sin Monte Carlo, y ya validados estadísticamente en
    2.7M PA de 003B-5C.

    Args:
        effective_stuff_value: Stuff YA fatigado (lo que publica fatigue_manager).

    Returns:
        desplazamiento a sumar al power_score antes de los umbrales de BABIP.
    """
    return -((effective_stuff_value - STUFF_BASELINE) * STUFF_POWER_SUPPRESSION)
