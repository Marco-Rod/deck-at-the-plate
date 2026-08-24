"""
Módulo: calculator
==================
Motor matemático del at-bat. Implementa la resolución de una jugada mediante
RNG ponderado calibrado con métricas reales de MLB (Statcast).

Flujo de resolución:
    1. TAKE:        El bateador no hace swing. Se evalúa si el pitcheo era strike
                    basándose en el control del pitcher y la visión del bateador.
    2. Whiff:       Si el bateador hace swing, se calcula la tasa de fallo (whiff%)
                    usando velocidad y movimiento del pitcher vs contacto del bateador.
    3. Foul:        Si hace contacto pero no conectó limpio, probabilidad de foul (~35%).
    4. BABIP:       Bola en juego. Se calcula un power_score que determina el tipo
                    de hit u out según umbrales empíricos de MLB.

Rangos de los eventos en bolas en juego (power_score 0–115 aprox.):
    > 96  → HOME_RUN   (~3%)
    93–96 → HIT_3B     (~2%)
    85–93 → HIT_2B     (~8%)
    63–85 → HIT_1B    (~22%)
    25–63 → OUT_GROUND (~42%)
    < 25  → OUT_FLY    (~23%)
"""
import random
from typing import Dict, Any, Tuple


def calculate_play_outcome(
    pitcher_attrs: Dict[str, int],
    batter_attrs: Dict[str, int],
    pitch_selected: Dict[str, Any],
    swing_selected: Dict[str, Any],
    tactics_modifiers: Dict[str, float] = None
) -> Tuple[str, str]:
    """
    Calcula el resultado de la jugada aplicando RNG ponderado basado en atributos de Statcast.
    
    Args:
        pitcher_attrs: Atributos globales de la carta del pícher.
        batter_attrs: Atributos globales de la carta del bateador.
        pitch_selected: Diccionario con la zona y picheo lanzado.
                        Ejemplo: {
                            "zone": 5, 
                            "pitch_type": "SLIDER",
                            "velocity": 85,  # (Opcional) Especifico del repertorio
                            "control": 88,   # (Opcional) Especifico del repertorio
                            "movement": 94   # (Opcional) Especifico del repertorio
                        }
        swing_selected: Diccionario con el tipo de swing y predicción.
        tactics_modifiers: Modificadores aplicados por cartas tácticas.

    Retorna: (event_code, description)
    """

    tactics = tactics_modifiers or {
        "batter_con": 1.0, 
        "batter_pwr": 1.0, 
        "batter_vis": 1.0, 
        "pitcher_mov": 1.0,
        "pitcher_vel": 1.0,
        "pitcher_ctl": 1.0
    }

    # --- ATRIBUTOS DEL BATEADOR ---
    con = batter_attrs.get("contacto", 50) * tactics.get("batter_con", 1.0)
    pwr = batter_attrs.get("poder", 50) * tactics.get("batter_pwr", 1.0)
    vis = batter_attrs.get("vision", 50) * tactics.get("batter_vis", 1.0)

    # --- ATRIBUTOS DEL PICHEO (Prioriza el repertorio específico, si no usa los globales) ---
    vel = pitch_selected.get("velocity", pitcher_attrs.get("velocidad", 50)) * tactics.get("pitcher_vel", 1.0)
    ctl = pitch_selected.get("control", pitcher_attrs.get("control", 50)) * tactics.get("pitcher_ctl", 1.0)
    mov = pitch_selected.get("movement", pitcher_attrs.get("movimiento", 50)) * tactics.get("pitcher_mov", 1.0)

    swing_type = swing_selected.get("swing_type", "NORMAL")
    guessed_zone = swing_selected.get("guessed_zone")
    guessed_pitch = swing_selected.get("guessed_pitch")

    actual_zone = pitch_selected["zone"]
    actual_pitch = pitch_selected["pitch_type"]

    # Manejo especial de Base por Bolas Intencional
    if actual_pitch == "IBB":
        return "BALL", "Base por bolas intencional."

    zone_matched = (guessed_zone == actual_zone)
    pitch_matched = (guessed_pitch == actual_pitch)

    # --- FASE 1: BATEADOR NO HACE SWING (TAKE) ---
    if swing_type == "TAKE":
        # Base MLB: ~65% de picheos sin swing son strikes
        strike_chance = 0.65 + (ctl - 50) * 0.003 - (vis - 50) * 0.002
        if zone_matched:
            strike_chance -= 0.12  # Bono por anticipar la zona correcta

        if random.random() < max(0.25, min(0.85, strike_chance)):
            return "STRIKE_LOOKING", "Lanzamiento en la zona. ¡Strike cantado!"
        else:
            return "BALL", "Lanzamiento fuera de la zona. ¡Bola!"

    # --- FASE 2: BATEADOR HACE SWING ---
    # Base Whiff%: ~24.5% en MLB para un duelo neutro (50 vs 50)
    # Un picheo con alto movimiento (ej. Slider/Sweeper de 95 MOV) incrementa el whiff%
    whiff_base = 24.5 + (vel * 0.25 + mov * 0.25) - (con * 0.35)

    if zone_matched:
        whiff_base -= 10.0
    if pitch_matched:
        whiff_base -= 8.0

    if swing_type == "POWER":
        whiff_base += 8.0  # El swing de poder aumenta la tasa de abanicado
        pwr *= 1.20

    whiff_chance = max(5.0, min(65.0, whiff_base))

    # Evaluación de contacto
    if random.uniform(0, 100) < whiff_chance:
        return "STRIKE_SWINGING", "Swing abanicado. ¡Strike!"

    # De los contactos que no abanican, ~35% son Fouls en MLB
    if random.uniform(0, 100) < 35.0 and not (zone_matched and pitch_matched):
        return "FOUL", "Batazo de foul."

    # --- FASE 3: BOLA PUESTA EN JUEGO (BABIP MLB REAL) ---
    power_score = (pwr - 50) * 0.4 + random.uniform(0, 100)

    if zone_matched and pitch_matched:
        power_score += 15.0

    if power_score > 96.0:
        return "HOME_RUN", "¡Enorme batazo por todo el jardín central! ¡HOME RUN!"
    elif power_score > 93.0:
        return "HIT_3B", "¡Batazo pegado a la barda! El corredor llega a tercera base. ¡Triple!"
    elif power_score > 85.0:
        return "HIT_2B", "Batazo profundo contra la barda. Doble base."
    elif power_score > 63.0:
        return "HIT_1B", "Contacto limpio sobre el cuadro. Hit sencillo."
    elif power_score > 25.0:
        return "OUT_GROUND", "Roletazo suave al cuadro para out."
    else:
        return "OUT_FLY", "Elevado de rutina atrapado en el jardín."