"""
Selección del Starter Pack (lógica pura)
==========================================
Extrae de ``app/services/pack_service.py`` la LÓGICA de selección de las 13
cartas iniciales (sin acceso a base de datos): dado el mazo del equipo favorito
y las cartas del resto de equipos, devuelve la selección final ya barajada.

Este módulo NO importa SQLAlchemy ni FastAPI: solo trabaja sobre las entidades
(modelos) que recibe como argumentos, por lo que es testeable con cartas fake.
"""

import random
from typing import Collection, List, Sequence

from app.core.enums import PITCHER_POSITIONS

# Posiciones requeridas en el campo (la "P" se cubre con los pitchers del pack).
REQUIRED_POSITIONS: Collection[str] = ["C", "1B", "2B", "3B", "SS", "LF", "CF", "RF", "DH"]

# Totales del sobre base
FAVORITE_TEAM_CARDS = 7
OTHER_TEAMS_CARDS = 6
TOTAL_CARDS = FAVORITE_TEAM_CARDS + OTHER_TEAMS_CARDS

# Orden de rareza (de mayor a menor)
TIER_PRIORITY: Sequence[str] = ["DIAMOND", "GOLD", "SILVER", "BRONZE", "COMMON"]


def _is_pitcher(card: object) -> bool:
    """Determina si una carta puede lanzar (posiciones de pitcher o two-way)."""
    return card.position in PITCHER_POSITIONS or bool(getattr(card, "is_two_way", False))


def _is_sacrificable(card: object, selected_cards: Sequence) -> bool:
    """
    True si eliminar ``card`` no deja sin cobertura ninguna posición requerida
    (es decir, es una carta duplicada o un relleno sin posición requerida).
    """
    if card.position not in REQUIRED_POSITIONS:
        return True
    count = sum(1 for c in selected_cards if c.position == card.position)
    return count > 1


def _get_missing_positions(selected_cards: Sequence, required_positions=REQUIRED_POSITIONS) -> List[str]:
    """
    Identifica qué posiciones del campo aún no están cubiertas.

    Returns:
        Lista de posiciones faltantes (p. ej. ['3B', 'SS']).
    """
    covered = {pos: 0 for pos in required_positions}
    for card in selected_cards:
        pos = card.position
        if pos in covered:
            covered[pos] += 1
    return [pos for pos in required_positions if covered[pos] == 0]


def select_starter_cards(
    team_cards: Sequence,
    other_team_cards: Sequence,
    rng: random.Random | None = None,
) -> List:
    """
    Selecciona las ``TOTAL_CARDS`` (13) cartas del sobre de bienvenida.

    Estrategia (compatible con la lógica legada de PackService):
      1. Equipo favorito (7 cartas): 1 carta del tier máximo + 6 de tiers
         inferiores (máximo 2 lanzadores SP en todo el pack).
      2. Otros equipos (6 cartas): garantiza al menos 1 lanzador, cubre
         posiciones faltantes con cartas COMMON de esa posición y rellena los
         slots restantes con COMMON sin posición.
      3. Fallback: si tras elegir no hubiera ningún lanzador, reemplaza una
         carta no esencial por un lanzador disponible.
      4. Devuelve la selección barajada.

    Args:
        team_cards: Cartas del equipo favorito del usuario.
        other_team_cards: Cartas de todos los demás equipos.
        rng: Generador aleatorio inyectable (útil en tests); usa ``random`` si es None.

    Returns:
        Lista final (barajada) de cartas seleccionadas.
    """
    rng = rng or random
    selected = []
    selected_set = set()

    # ── 1. Equipo favorito ─────────────────────────────────────────────
    team_by_tier = {tier: [c for c in team_cards if c.rarity.name == tier] for tier in TIER_PRIORITY}

    highest_tier = next((t for t in TIER_PRIORITY if team_by_tier[t]), None)
    if not highest_tier:
        return []  # Sin cartas clasificadas: no hay selección posible.

    # 1 carta del tier máximo (sin restricción, podría ser SP)
    top_card = rng.choice(team_by_tier[highest_tier])
    team_selected = [top_card]
    selected_set.add(top_card.id)
    sp_count = 1 if top_card.position == "SP" else 0

    # Rellenar 6 cartas restantes con tiers inferiores (respetando límite de SP)
    remaining_needed = FAVORITE_TEAM_CARDS - 1
    highest_idx = TIER_PRIORITY.index(highest_tier)
    lower_tiers = TIER_PRIORITY[highest_idx + 1:]
    last_available_tier = None

    for tier in lower_tiers:
        if remaining_needed <= 0:
            break
        available = [c for c in team_by_tier[tier] if c.id not in selected_set]
        if sp_count >= 2:
            available = [c for c in available if c.position != "SP"]
        if available:
            card = rng.choice(available)
            team_selected.append(card)
            selected_set.add(card.id)
            if card.position == "SP":
                sp_count += 1
            remaining_needed -= 1
            last_available_tier = tier

    # Si aún faltan cartas, rellenar con el último tier disponible
    if remaining_needed > 0 and last_available_tier is not None:
        available = [c for c in team_by_tier[last_available_tier] if c.id not in selected_set]
        if sp_count >= 2:
            available = [c for c in available if c.position != "SP"]
        while remaining_needed > 0 and available:
            card = rng.choice(available)
            team_selected.append(card)
            selected_set.add(card.id)
            if card.position == "SP":
                sp_count += 1
            available.remove(card)
            remaining_needed -= 1

    selected.extend(team_selected)

    # ── 2. Otros equipos ───────────────────────────────────────────────
    cards_needed = TOTAL_CARDS - len(selected)
    other_selected = []

    # FASE 0: garantizar al menos 1 lanzador (P) si aún no hay ninguno.
    if cards_needed > 0 and not any(_is_pitcher(c) for c in selected):
        pitcher_pool = [
            c for c in other_team_cards
            if c.id not in selected_set and _is_pitcher(c)
        ]
        if pitcher_pool:
            card = rng.choice(pitcher_pool)
            other_selected.append(card)
            selected_set.add(card.id)

    # FASE 1: cubrir posiciones faltantes con cartas COMMON de la posición
    missing_positions = _get_missing_positions([*selected, *other_selected])
    for pos in missing_positions:
        if len(other_selected) >= cards_needed:
            break
        common_cards = [
            c for c in other_team_cards
            if c.position == pos and c.rarity.name == "COMMON" and c.id not in selected_set
        ]
        if common_cards:
            card = rng.choice(common_cards)
            other_selected.append(card)
            selected_set.add(card.id)

    # FASE 2: rellenar los slots restantes con COMMON (cualquier posición)
    remaining_common = [
        c for c in other_team_cards
        if c.rarity.name == "COMMON" and c.id not in selected_set
    ]
    need_more = cards_needed - len(other_selected)
    if need_more > 0 and remaining_common:
        fillback = rng.sample(remaining_common, min(need_more, len(remaining_common)))
        other_selected.extend(fillback)
        selected_set.update(c.id for c in fillback)

    selected.extend(other_selected)

    # ── 2.5 Fallback: garantizar lanzador reemplazando una carta no esencial ──
    if not any(_is_pitcher(c) for c in selected):
        pitcher_pool = [
            c for c in [*team_cards, *other_team_cards]
            if c.id not in selected_set and _is_pitcher(c)
        ]
        if pitcher_pool:
            pitcher = rng.choice(pitcher_pool)
            victim = next(
                (c for c in reversed(selected) if _is_sacrificable(c, selected)),
                None,
            )
            if victim is not None:
                selected.remove(victim)
                selected.append(pitcher)

    # ── 3. Barajar y retornar ──────────────────────────────────────────
    rng.shuffle(selected)
    return selected