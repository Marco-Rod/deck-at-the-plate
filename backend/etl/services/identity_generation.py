"""Generación y validación de identidades GAME v2.1 (plan §63-§93).

Reglas medulares:
- "la persistencia gana" (§72): en modo missing_only NO se regenera una
  identidad existente (rerun = unchanged/created=0).
- determinismo estable por seed sha256(player.id | version | intento) (§70).
- --dry-run calcula candidatos y emite el reporte QA sin escribir (§80, §81).
- las APIs públicas jamás ven la fuente: la identidad es solo presentación
  (§88) y el reporte es administrativo (§81).
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import GamePlayerIdentity, Player, PlayerSeason
from etl.config import NAMES_GENERATOR_VERSION
from etl.loaders.core import upsert_game_player_identity
from etl.services.card_catalog import ValidationResult
from etl.services.names import (
    DEFAULT_POOLS,
    VALID_PROFILES,
    FictionalNameGenerator,
    NameProfileClassifier,
    contains_blocked,
)
from etl.services.names.text import normalize

logger = logging.getLogger("etl.services.identity_generation")


@dataclass
class IdentityRunEntry:
    """Fila del reporte administrativo de QA (§81)."""

    mlb_id: int | None
    source_name: str
    profile: str
    confidence: float
    display_name: str
    generator_version: str

    def __str__(self) -> str:
        return f"{self.source_name:<32} {self.profile:<14} {self.display_name}"


@dataclass
class IdentityRunResult:
    created: int = 0
    unchanged: int = 0
    dry_run: bool = False
    version: str = NAMES_GENERATOR_VERSION
    report: list[IdentityRunEntry] = field(default_factory=list)


def _eligible_players(
    db: Session, *, season: int | None, player_id: int | None, limit: int | None
) -> list[Player]:
    query = db.query(Player)
    if player_id is not None:
        query = query.filter(Player.mlb_id == player_id)
    if season is not None:
        player_ids = {
            row[0]
            for row in db.query(PlayerSeason.player_id)
            .filter(PlayerSeason.season == season)
            .all()
        }
        if not player_ids:
            return []
        query = query.filter(Player.id.in_(player_ids))
    if limit is not None:
        query = query.limit(limit)
    return query.all()


def _source_name(player: Player) -> str:
    return (player.full_name or "").strip() or f"{player.first_name or ''} {player.last_name or ''}".strip()


def generate_identity_batch(
    db: Session,
    *,
    season: int | None = None,
    missing_only: bool = True,
    dry_run: bool = False,
    generator_version: str = NAMES_GENERATOR_VERSION,
    player_id: int | None = None,
    limit: int | None = None,
) -> IdentityRunResult:
    """Genera identidades para los jugadores elegibles (batch, diverso de CLI).

    dry_run=True nunca escribe: calcula candidatos y los registra en el reporte.
    """
    classifier = NameProfileClassifier(DEFAULT_POOLS)
    generator = FictionalNameGenerator(DEFAULT_POOLS)
    result = IdentityRunResult(dry_run=dry_run, version=generator_version)

    existing_rows = db.query(GamePlayerIdentity.player_id, GamePlayerIdentity.display_name).all()
    has_identity = {row[0] for row in existing_rows}
    used = {row[1] for row in existing_rows}
    source_names = {normalize(_source_name(p)) for p in db.query(Player).all()}

    players = _eligible_players(db, season=season, player_id=player_id, limit=limit)
    for player in players:
        if missing_only and player.id in has_identity:
            result.unchanged += 1
            continue

        first = player.first_name or ""
        last = player.last_name or ""
        profile, confidence = classifier.classify(first=first, last=last)
        name = generator.generate(
            player_id=player.id,
            generator_version=generator_version,
            first=first,
            last=last,
            profile=profile,
            used=used,
            source_names=source_names,
        )
        used.add(name.display)
        result.report.append(
            IdentityRunEntry(
                mlb_id=player.mlb_id,
                source_name=_source_name(player),
                profile=profile,
                confidence=confidence,
                display_name=name.display,
                generator_version=generator_version,
            )
        )
        if dry_run:
            continue
        upsert_game_player_identity(
            db,
            player=player,
            display_first_name=name.first,
            display_last_name=name.last,
            display_name=name.display,
            name_profile=profile,
            generator_version=generator_version,
        )
        result.created += 1

    if not dry_run:
        db.commit()
    return result


def validate_game_identities(
    db: Session,
    *,
    season: int | None = None,
    generator_version: str = NAMES_GENERATOR_VERSION,
) -> ValidationResult:
    """Gate §83: cada elegible con una identidad válida, estable y sin colisiones."""
    issues: list[str] = []

    players = _eligible_players(db, season=season, player_id=None, limit=None)
    existing: dict[str, GamePlayerIdentity] = {}
    for identity in db.query(GamePlayerIdentity).all():
        existing.setdefault(identity.player_id, identity)

    missing = [p for p in players if p.id not in existing]
    if missing:
        issues.append(f"{len(missing)} jugadores sin identidad")

    seen_display: dict[str, str] = {}
    classifier = NameProfileClassifier(DEFAULT_POOLS)
    generator = FictionalNameGenerator(DEFAULT_POOLS)

    all_displays = {i.display_name for i in existing.values() if i.display_name}
    source_names = {normalize(_source_name(p)) for p in db.query(Player).all()}

    for player in players:
        identity = existing.get(player.id)
        if identity is None:
            continue
        if not identity.display_name or not identity.display_name.strip():
            issues.append(f"mlb_id={player.mlb_id}: display_name vacío")
        if contains_blocked(identity.display_name or "", DEFAULT_POOLS.blocked):
            issues.append(f"mlb_id={player.mlb_id}: nombre bloqueado")
        low = normalize(identity.display_name or "")
        if low == normalize(_source_name(player)):
            issues.append(f"mlb_id={player.mlb_id}: coincide con nombre fuente")
        if not identity.generator_version:
            issues.append(f"mlb_id={player.mlb_id}: generator_version ausente")
        if identity.name_profile and identity.name_profile not in VALID_PROFILES:
            issues.append(f"mlb_id={player.mlb_id}: name_profile inválido {identity.name_profile}")
        elif identity.generator_version:
            profile = identity.name_profile if identity.name_profile else "UNKNOWN"
            used_others = {d for d in all_displays if d != identity.display_name}
            try:
                rerun = generator.generate(
                    player_id=player.id,
                    generator_version=identity.generator_version,
                    first=player.first_name or "",
                    last=player.last_name or "",
                    profile=profile,
                    used=used_others,
                    source_names=source_names,
                ).display
            except Exception as exc:  # defensivo: jamás rompe el gate
                rerun = ""
                issues.append(f"mlb_id={player.mlb_id}: rerun con error ({exc})")
            if rerun and identity.display_name != rerun:
                issues.append(
                    f"mlb_id={player.mlb_id}: rerun no es estable ({identity.display_name} != {rerun})"
                )
        if low in seen_display:
            issues.append(f"display_name duplicado: {identity.display_name}")
        seen_display[low] = player.id

    for identity in existing.values():
        if identity.player_id not in {p.id for p in players}:
            issues.append(f"identidad huérfana de player_id={identity.player_id}")

    return ValidationResult(ok=not issues, detail=issues)


def render_report(result: IdentityRunResult) -> str:
    lines = [
        f"QA report (dry_run={result.dry_run}, version={result.version}, created={result.created}, unchanged={result.unchanged})",
        "source player                     profile        game identity",
        "-" * 70,
    ]
    lines.extend(str(entry) for entry in result.report)
    return "\n".join(lines)