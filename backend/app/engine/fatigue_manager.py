from typing import Dict, Any

# Umbrales dinámicos basados en el número de innings
# A menos innings, más rápido se fatiga el pitcher proporcionalmente
FATIGUE_THRESHOLDS = {
    3: 18,   # 3 innings: 18 pitches (60 / 9 * 3)
    6: 40,   # 6 innings: 40 pitches (60 / 9 * 6)
    9: 60,   # 9 innings: 60 pitches (default)
}

# ⭐ MEJORADO: Escala de fatiga más agresiva
# Cada 3 lanzamientos extra = -3% (en lugar de cada 15)
# Esto hace que la fatiga sea proporcional a cada juego
FATIGUE_PENALTY_STEP = 3  # Cada 3 lanzamientos extra aplica -3% penalización

def get_pitch_threshold(total_innings: int = 9) -> int:
    """
    Calcula el umbral de fatiga proporcional al número de innings.
    
    Lógica:
    - 3 innings: 18 pitches antes de fatiga (20% del tiempo)
    - 6 innings: 40 pitches antes de fatiga (66% del tiempo)
    - 9 innings: 60 pitches antes de fatiga (100% del tiempo)
    
    Para otros valores, interpola proporcionalmente.
    """
    if total_innings in FATIGUE_THRESHOLDS:
        return FATIGUE_THRESHOLDS[total_innings]
    
    # Interpolación: threshold = (60 / 9) * total_innings
    return max(6, int((60.0 / 9.0) * total_innings))


def apply_pitcher_fatigue(
    pitcher_attrs: Dict[str, int], 
    pitch_count: int,
    total_innings: int = 9
) -> Dict[str, int]:
    """
    Aplica penalizaciones a Velocidad, Control y Movimiento si el pitcher
    ha superado su umbral de lanzamientos en la partida.
    
    La fatiga es PROPORCIONAL al duración del juego:
    - 3 innings: threshold 18 → cada pitch extra = -3% penalty
    - 6 innings: threshold 40 → cada pitch extra = -1.5% penalty
    - 9 innings: threshold 60 → cada pitch extra = -1% penalty
    
    Fórmula unificada:
      penalty_factor = 1.0 - (fatigue_rate * extra_pitches)
      penalty_rate = 0.03 / (threshold / 20)  # Normaliza a 20 pitches base
    
    Args:
        pitcher_attrs: Diccionario con velocidad, control, movimiento
        pitch_count: Número de lanzamientos realizados
        total_innings: Total de innings en la partida (3, 6, o 9)
    
    Returns:
        Diccionario con atributos modificados por fatiga
    """
    modified_attrs = pitcher_attrs.copy()
    
    # Obtener umbral dinámico basado en innings
    pitch_threshold = get_pitch_threshold(total_innings)
    
    # ⭐ DEBUG: Log de aplicación de fatiga
    print(f"⚙️ [APPLY PITCHER FATIGUE]")
    print(f"   Pitch Count: {pitch_count}")
    print(f"   Total Innings: {total_innings}")
    print(f"   Pitch Threshold: {pitch_threshold}")
    print(f"   Exceeds Threshold: {pitch_count > pitch_threshold}")

    if pitch_count > pitch_threshold:
        extra_pitches = pitch_count - pitch_threshold
        
        # ⭐ MEJORADO: Fatiga proporcional al juego
        # Base: 3% degradación por cada lanzamiento extra en juegos de 3 innings
        # Para otros juegos: escalar proporcionalmente
        # Ej: 3 innings (18 threshold) → -3% por pitch
        #     9 innings (60 threshold) → -1% por pitch (3x más gradual)
        fatigue_rate = 0.03 / (pitch_threshold / 20.0)  # Normaliza a base de 20 pitches
        penalty_factor = 1.0 - (fatigue_rate * extra_pitches)
        penalty_factor = max(0.5, penalty_factor)  # Límite: -50% máximo

        print(f"   Extra Pitches: {extra_pitches}")
        print(f"   Fatigue Rate (per pitch): {fatigue_rate:.4f}")
        print(f"   Penalty Factor: {penalty_factor:.2f}")
        print(f"   Original Stats: VEL={pitcher_attrs.get('velocidad')}, CTR={pitcher_attrs.get('control')}, MOV={pitcher_attrs.get('movimiento')}")

        modified_attrs["velocidad"] = int(modified_attrs.get("velocidad", 50) * penalty_factor)
        modified_attrs["control"] = int(modified_attrs.get("control", 50) * penalty_factor)
        modified_attrs["movimiento"] = int(modified_attrs.get("movimiento", 50) * penalty_factor)
        
        print(f"   Modified Stats: VEL={modified_attrs['velocidad']}, CTR={modified_attrs['control']}, MOV={modified_attrs['movimiento']}")
    else:
        print(f"   No fatigue applied (pitch_count <= threshold)")

    return modified_attrs
