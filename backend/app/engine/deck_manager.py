import random
from typing import Dict, Any, List

MAX_HAND_SIZE = 4

def initialize_tactics_state(home_deck: List[str], away_deck: List[str]) -> Dict[str, Any]:
    """Inicializa los mazos mezclados y roba una mano inicial de 3 cartas por jugador."""
    h_deck = home_deck.copy()
    a_deck = away_deck.copy()
    random.shuffle(h_deck)
    random.shuffle(a_deck)

    h_hand = [h_deck.pop() for _ in range(min(3, len(h_deck)))]
    a_hand = [a_deck.pop() for _ in range(min(3, len(a_deck)))]

    return {
        "home": {"deck": h_deck, "hand": h_hand, "discard": []},
        "away": {"deck": a_deck, "hand": a_hand, "discard": []}
    }

def draw_card(tactics_state: Dict[str, Any], player_key: str) -> bool:
    """Roba 1 carta del mazo. Si el mazo está vacío, rebaraja el descarte."""
    player_data = tactics_state[player_key]
    if len(player_data["hand"]) >= MAX_HAND_SIZE:
        return False

    if not player_data["deck"]:
        if not player_data["discard"]:
            return False  # Sin cartas disponibles
        player_data["deck"] = player_data["discard"].copy()
        player_data["discard"] = []
        random.shuffle(player_data["deck"])

    drawn = player_data["deck"].pop()
    player_data["hand"].append(drawn)
    return True

def discard_used_tactic(tactics_state: Dict[str, Any], player_key: str, tactic_id: str) -> None:
    """Remueve la carta de la mano y la mueve al pozo de descarte."""
    player_data = tactics_state[player_key]
    if tactic_id in player_data["hand"]:
        player_data["hand"].remove(tactic_id)
        player_data["discard"].append(tactic_id)