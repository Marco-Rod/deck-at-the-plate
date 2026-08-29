import sys
import os
import random

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine.calculator import calculate_play_outcome
from app.engine.state_manager import process_at_bat_transition

class MockGameSession:
    """Clase ligera para emular el modelo GameSession de SQLAlchemy en memoria."""
    def __init__(self):
        self.id = "sim_game_001"
        self.current_inning = 1
        self.is_top_inning = True
        self.outs = 0
        self.balls = 0
        self.strikes = 0
        self.score_home = 0
        self.score_away = 0
        self.state_data = {
            "runners": {"1b": None, "2b": None, "3b": None},
            "active_batter": "BATTER_MOCK",
            "active_pitcher": "PITCHER_MOCK",
            "active_tactics": {"home": None, "away": None},
            "is_game_over": False,
            "winner_message": "",
            "score_history": {},  # ✅ Inicializar score_history
        }

def run_simulation():
    game = MockGameSession()
    
    pitcher_attrs = {"velocidad": 92, "control": 85, "movimiento": 80}
    batter_attrs = {"contacto": 85, "poder": 88, "vision": 82}
    
    pitch_types = ["FF", "SL", "CH", "CU"]
    swing_types = ["NORMAL", "POWER", "TAKE"]

    pitch_count = 0
    max_pitches_safety = 500  # Freno de seguridad para evitar loops infinitos

    print("=" * 60)
    print("      INICIO DE LA SIMULACIÓN: DECK AT THE PLATE 1v1      ")
    print("=" * 60)

    while not game.state_data.get("is_game_over") and pitch_count < max_pitches_safety:
        pitch_count += 1
        half = "ALTA" if game.is_top_inning else "BAJA"
        
        # 1. El Lanzador elige lanzamiento
        selected_pitch = {
            "pitch_type": random.choice(pitch_types),
            "zone": random.randint(1, 9)
        }

        # 2. El Bateador elige acción
        selected_swing = {
            "swing_type": random.choice(swing_types),
            "guessed_zone": random.randint(1, 9) if random.random() > 0.3 else None,
            "guessed_pitch": random.choice(pitch_types) if random.random() > 0.4 else None
        }

        # 3. Cálculo del resultado (Statcast + RNG)
        raw_event, desc = calculate_play_outcome(
            pitcher_attrs=pitcher_attrs,
            batter_attrs=batter_attrs,
            pitch_selected=selected_pitch,
            swing_selected=selected_swing
        )

        # 4. Transición de estado (Conteo, Corredores, Inning y Game Over)
        at_bat_ended, inning_ended, event, event_description = process_at_bat_transition(game, raw_event, game.state_data, None)

        # 5. Formatear y mostrar evento significativo
        if at_bat_ended or event in ["STRIKE_SWINGING", "STRIKE_LOOKING", "BALL"]:
            runners = game.state_data["runners"]
            r_str = f"[{'1B' if runners['1b'] else '_'}{'2B' if runners['2b'] else '_'}{'3B' if runners['3b'] else '_'}]"
            
            print(f"[{half} {game.current_inning:02d}] {event:<15} | B:{game.balls} S:{game.strikes} O:{game.outs} | "
                  f"Bases: {r_str} | Vis: {game.score_away} - Loc: {game.score_home} | {desc}")

        if inning_ended:
            print("-" * 60)
            print(f"--- FIN DE LA {half} DEL INNING {game.current_inning} ---")
            print("-" * 60)

    print("=" * 60)
    if game.state_data.get("is_game_over"):
        print("RESULTADO FINAL:")
        print(game.state_data.get("winner_message"))
        print(f"Pizarra Final: Visitante {game.score_away} - Local {game.score_home}")
        print(f"Total de Picheos Procesados: {pitch_count}")
    else:
        print("ALERTA: Se alcanzó el límite de lanzamientos de seguridad sin finalizar el partido.")
    print("=" * 60)

if __name__ == "__main__":
    run_simulation()