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
    Retorna: (event_code, description)
    """

    tactics = tactics_modifiers or {"batter_con": 1.0, "batter_pwr": 1.0, "batter_vis": 1.0, "pitcher_mov": 1.0}

    # Atributos modificados
    con = batter_attrs.get("contacto", 50) * tactics.get("batter_con", 1.0)
    pwr = batter_attrs.get("poder", 50) * tactics.get("batter_pwr", 1.0)
    vis = batter_attrs.get("vision", 50) * tactics.get("batter_vis", 1.0)

    vel = pitcher_attrs.get("velocidad", 50)
    ctl = pitcher_attrs.get("control", 50)
    mov = pitcher_attrs.get("movimiento", 50) * tactics.get("pitcher_mov", 1.0)

    swing_type = swing_selected.get("swing_type", "NORMAL")
    guessed_zone = swing_selected.get("guessed_zone")
    guessed_pitch = swing_selected.get("guessed_pitch")

    actual_zone = pitch_selected["zone"]
    actual_pitch = pitch_selected["pitch_type"]

    zone_matched = (guessed_zone == actual_zone)
    pitch_matched = (guessed_pitch == actual_pitch)

    # --- FASE 1: BATEADOR NO HACE SWING (TAKE) ---
    if swing_type == "TAKE":
        # Base MLB: ~65% de picheos sin swing son strikes
        strike_chance = 0.65 + (ctl - 50) * 0.003 - (vis - 50) * 0.002
        if zone_matched:
            strike_chance -= 0.12  # Bono por anticipar zona

        if random.random() < max(0.25, min(0.85, strike_chance)):
            return "STRIKE_LOOKING", "Lanzamiento en la zona. ¡Strike cantado!"
        else:
            return "BALL", "Lanzamiento fuera de la zona. ¡Bola!"

    # --- FASE 2: BATEADOR HACE SWING ---
    # Base Whiff%: ~24.5% en MLB para un duelo neutro (50 vs 50)
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
    # Escala ponderada para simular el ~30% de Hits / 70% de Outs en bolas en juego
    power_score = (pwr - 50) * 0.4 + random.uniform(0, 100)

    if zone_matched and pitch_matched:
        power_score += 15.0

    # Distribución empírica MLB
    if power_score > 96.0:
        return "HOME_RUN", "¡Enorme batazo por todo el jardín central! ¡HOME RUN!"
    elif power_score > 89.0:
        return "HIT_2B", "Batazo profundo contra la barda. Doble base."
    elif power_score > 71.0:
        return "HIT_1B", "Contacto limpio sobre el cuadro. Hit sencillo."
    elif power_score > 38.0:
        return "OUT_GROUND", "Roletazo suave al cuadro para out."
    else:
        return "OUT_FLY", "Elevado de rutina atrapado en el jardín."