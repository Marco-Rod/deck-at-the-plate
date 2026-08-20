from typing import Dict, Any, Tuple

def advance_runners(
    runners: Dict[str, Any], 
    event: str, 
    current_batter_id: str = "BATTER"
) -> Tuple[Dict[str, Any], int]:
    """
    Calcula el nuevo estado de las bases y el número de carreras anotadas.
    
    runners: {"1b": id_or_None, "2b": id_or_None, "3b": id_or_None}
    Retorna: (new_runners_dict, runs_scored)
    """
    new_runners = {"1b": None, "2b": None, "3b": None}
    runs = 0

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

    # --- OUTS SIN CAMBIO EN BASES ---
    else:
        new_runners = {"1b": r1, "2b": r2, "3b": r3}

    return new_runners, runs