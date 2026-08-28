from typing import Dict, Any, Tuple
import random

def advance_runners(
    runners: Dict[str, Any], 
    event: str, 
    current_batter_id: str = "BATTER"
) -> Tuple[Dict[str, Any], int, str]:
    """
    Calcula el nuevo estado de las bases y el número de carreras anotadas.
    
    runners: {"1b": id_or_None, "2b": id_or_None, "3b": id_or_None}
    Retorna: (new_runners_dict, runs_scored, event_adjusted)
             - event_adjusted puede ser "DOUBLE_PLAY" si se logró un doble play
    """
    new_runners = {"1b": None, "2b": None, "3b": None}
    runs = 0
    event_adjusted = event

    r1 = runners.get("1b")
    r2 = runners.get("2b")
    r3 = runners.get("3b")

    # --- BASE POR BOLAS (WALK) ---
    if event == "WALK":
        if r1:
            new_runners["1b"] = current_batter_id
            if r2:
                new_runners["2b"] = r1
                if r3:
                    new_runners["3b"] = r2
                    runs += 1  # R3 anota por avance forzado
                else:
                    new_runners["3b"] = r2
            else:
                new_runners["2b"] = r1
                new_runners["3b"] = r3
        else:
            new_runners["1b"] = current_batter_id
            new_runners["2b"] = r2
            new_runners["3b"] = r3

    # --- HIT SENCILLO (HIT_1B) ---
    elif event == "HIT_1B":
        if r3: 
            runs += 1
        if r2: 
            new_runners["3b"] = r2  # Avanza a 3B en lugar de anotar directo
        if r1: 
            new_runners["2b"] = r1
        new_runners["1b"] = current_batter_id
    # --- HIT DOBLE (HIT_2B) ---
    elif event == "HIT_2B":
        if r3: runs += 1
        if r2: runs += 1
        if r1: new_runners["3b"] = r1
        new_runners["2b"] = current_batter_id

    # --- HIT TRIPLE (HIT_3B) ---
    elif event == "HIT_3B":
        if r3: runs += 1
        if r2: runs += 1
        if r1: runs += 1
        new_runners["3b"] = current_batter_id

    # --- HOME RUN ---
    elif event == "HOME_RUN":
        runs += 1  # El bateador
        if r1: runs += 1
        if r2: runs += 1
        if r3: runs += 1
        # Las bases quedan vacías (new_runners en Nones)

    # --- OUTS EN JUEGO (OUT_GROUND, OUT_FLY) ---
    #posible DOUBLE PLAY si hay corredor en 1B y es roletazo al cuadro
    elif event in ("OUT_GROUND", "OUT_FLY"):
        # Detectar doble play: corredor en 1B + roletazo al cuadro (OUT_GROUND)
        if event == "OUT_GROUND" and r1 is not None:
            # Hay corredor en primera → intentar doble play
            # Probabilidad base: ~75% en MLB para ground balls con runner en 1B
            dp_chance = 0.75
            # Ajustar por si también hay corredor en 2B (más difícil el doble play)
            if r2 is not None:
                dp_chance = 0.65  # 65% con corredor en ambas
            
            if random.random() < dp_chance:
                # ✅ DOBLE PLAY: corredor en 1B out, bateador out
                print(f"⚾ [DOUBLE PLAY] ¡Doble play! Corredor en 1B ({r1}) eliminado + bateador out")
                event_adjusted = "DOUBLE_PLAY"
                runs = 0
                # El corredor en 1B queda out, bases se limpian hasta donde corresponda
                new_runners = {"1b": None, "2b": r2, "3b": r3} if r2 else {"1b": None, "2b": None, "3b": r3}
            else:
                # ❌ No se logró el doble play, solo out del bateador
                new_runners = {"1b": r1, "2b": r2, "3b": r3}
        else:
            # Sin corredor en 1B o fly ball → out normal sin avance
            new_runners = {"1b": r1, "2b": r2, "3b": r3}

    # --- OUTS SIN CAMBIO EN BASES (otros eventos) ---
    else:
        new_runners = {"1b": r1, "2b": r2, "3b": r3}

    return new_runners, runs, event_adjusted