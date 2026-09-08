"""Resolución compartida de límites reales de temporada MLB."""

from datetime import date

from etl.sources.mlb import MLBStatsApiClient


def resolve_regular_season_start(
    client: MLBStatsApiClient, *, season: int, date_to: date
) -> date:
    """Resuelve el primer juego de temporada regular hasta el corte solicitado."""
    if date_to.year != season:
        raise ValueError("date_to debe pertenecer a season")
    schedule = client.get_schedule(
        date(season, 1, 1), date_to, game_type="R"
    )
    dates = []
    for day in schedule.get("dates", []):
        try:
            game_date = date.fromisoformat(day.get("date"))
        except (TypeError, ValueError):
            continue
        if any(game.get("gameType") == "R" for game in day.get("games", [])):
            dates.append(game_date)
    if not dates:
        raise ValueError(
            f"MLB Schedule no contiene juegos regulares de {season} hasta {date_to}"
        )
    return min(dates)
