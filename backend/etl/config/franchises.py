"""Configuración versionada de franquicias públicas (plan V2 §37).

Lee etl/config/game_franchises.yaml: la fuente de verdad del branding público
(una franquicia GAME por franquicia SOURCE/MLB). El universo GAME es ficcional:
abreviatura, slug, nombre y paleta son inventados y únicos, mientras que la
ciudad es la referencia real de la fuente. El id del Team público es
determinístico: uuid5("team:<public_abbreviation>") → backfill estable.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml

GAME_FRANCHISES_PATH = Path(__file__).parent / "game_franchises.yaml"
EXPECTED_FRANCHISE_COUNT = 30
REAL_LEAGUE_ABBREVIATIONS = {
    "AZ",
    "ATH",
    "ATL",
    "BAL",
    "BOS",
    "CHC",
    "CIN",
    "CLE",
    "COL",
    "CWS",
    "DET",
    "HOU",
    "KC",
    "LAA",
    "LAD",
    "MIA",
    "MIL",
    "MIN",
    "NYM",
    "NYY",
    "PHI",
    "PIT",
    "SD",
    "SEA",
    "SF",
    "STL",
    "TB",
    "TEX",
    "TOR",
    "WSH",
}
MIN_PALETTE_DISTANCE = 35


@dataclass(frozen=True)
class GameTeamConfig:
    source_team_external_id: int
    public_abbreviation: str
    slug: str
    name: str
    city: str
    primary_color: str
    secondary_color: str
    logo_asset: str | None = None
    is_cpu: bool = True

    @property
    def game_team_id(self) -> str:
        from app.core.identities import game_team_id_for

        return game_team_id_for(self.public_abbreviation)


def load_game_franchises(path: str | Path | None = None) -> list[GameTeamConfig]:
    source = Path(path) if path else GAME_FRANCHISES_PATH
    raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    entries = raw.get("game_franchises", [])
    return [GameTeamConfig(**entry) for entry in entries]


def _hex_rgb(color: str) -> tuple[int, int, int]:
    value = color.strip().lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def _color_distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((ac - bc) ** 2 for ac, bc in zip(a, b)) ** 0.5


def franchise_config_issues(configs: Iterable[GameTeamConfig]) -> list[str]:
    """Gate estructural del YAML: integridad, singularidad y paleta mínima."""
    issues: list[str] = []
    items = list(configs)

    if len(items) != EXPECTED_FRANCHISE_COUNT:
        issues.append(f"esperaba {EXPECTED_FRANCHISE_COUNT} franquicias, hay {len(items)}")

    seen_source: dict[int, str] = {}
    seen_abbr: dict[str, str] = {}
    seen_slug: dict[str, str] = {}
    seen_name: dict[str, str] = {}
    palette: list[tuple[int, int, int]] = []

    for cfg in items:
        if cfg.source_team_external_id in seen_source:
            issues.append(
                f"source_team_external_id duplicado: {cfg.source_team_external_id} "
                f"({seen_source[cfg.source_team_external_id]} y {cfg.name})"
            )
        seen_source[cfg.source_team_external_id] = cfg.name

        abbr = cfg.public_abbreviation.upper()
        if not abbr.isalnum() or not (2 <= len(abbr) <= 3):
            issues.append(f"{cfg.name}: public_abbreviation '{abbr}' debe ser 2-3 alfanumérica")
        if abbr in REAL_LEAGUE_ABBREVIATIONS:
            issues.append(f"{cfg.name}: public_abbreviation '{abbr}' coincide con la liga real")
        if abbr in seen_abbr:
            issues.append(f"public_abbreviation duplicado: {abbr} ({seen_abbr[abbr]} y {cfg.name})")
        seen_abbr[abbr] = cfg.name

        slug = cfg.slug.strip().lower()
        if not slug or any(not (c.isalnum() or c == "-") for c in slug):
            issues.append(f"{cfg.name}: slug inválido '{cfg.slug}'")
        if slug in seen_slug:
            issues.append(f"slug duplicado: {slug} ({seen_slug[slug]} y {cfg.name})")
        seen_slug[slug] = cfg.name

        name = cfg.name.strip()
        if not name:
            issues.append(f"franquicia {cfg.source_team_external_id}: name vacío")
        if name.lower() in seen_name:
            issues.append(f"name duplicado: {name} ({seen_name[name.lower()]} y el actual)")
        seen_name[name.lower()] = name

        if not cfg.is_cpu:
            issues.append(f"{cfg.name}: is_cpu debe ser true")

        for label, color in (("primary_color", cfg.primary_color), ("secondary_color", cfg.secondary_color)):
            if len(color) != 7 or color[0] != "#":
                issues.append(f"{cfg.name}: {label} '{color}' no es #RRGGBB")
                continue
            try:
                palette.append(_hex_rgb(color))
            except ValueError:
                issues.append(f"{cfg.name}: {label} '{color}' no es un hex válido")

    for i, first in enumerate(palette):
        for second in palette[i + 1 :]:
            if _color_distance(first, second) < MIN_PALETTE_DISTANCE:
                issues.append(
                    f"colores muy próximos: {first} y {second} "
                    f"(distancia < {MIN_PALETTE_DISTANCE})"
                )

    return issues


def validate_game_franchises(configs: Iterable[GameTeamConfig] | None = None) -> list[GameTeamConfig]:
    """Valida el YAML en firma y lo devuelve; lanza ValueError si hay problemas."""
    items = list(configs) if configs is not None else load_game_franchises()
    issues = franchise_config_issues(items)
    if issues:
        raise ValueError("game_franchises.yaml inválido:\n" + "\n".join(f"- {issue}" for issue in issues))
    return items