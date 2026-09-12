"""Publicación del catálogo de cartas (plan V2 §22-§27).

publish_card_catalog genera las cartas jugables (PlayerCardModel) a partir de
los CardGenerationProfile válidos, con transiciones de estado:

    BUILDING -> VALIDATING -> ACTIVE   (o FAILED/RETIRED)

Reglas:
    - Inmutabilidad (§22): re-publicar la misma (season, edition_type, version)
      es un no-op; una version nueva crea una edición nueva (edition_version+1).
    - Publicación atómica (§23-§24): un solo ACTIVE por (season, edition_type);
      las cartas solo marcan published_at/catálogo cuando el catálogo sube ACTIVE.
    - Legacy NUNCA entra al pool (§25): solo cartas con game_identity_id y
      catalog_id son pack-eligible.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    CardCatalog,
    CardEdition,
    CardGenerationProfile,
    CardRatingProfile,
    PlayerCardModel,
    PlayerSeason,
    RatingDistribution,
    SourceTeamGameTeamMapping,
    SourceTeamRosterMember,
    SourceTeamRosterSnapshot,
)
from app.services.card_editions import ensure_system_base_edition
from etl.services.rarity_policies import (
    final_performance_tier,
    resolve_card_rarity,
)

logger = logging.getLogger("etl.services.card_catalog")

_CARD_STATUSES = CardCatalog.STATUSES


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class CatalogRunResult:
    catalog_id: str = ""
    catalog_version: int = 1
    status: str = "FAILED"
    created: int = 0
    skipped_unresolved: int = 0
    issues: list[str] = field(default_factory=list)


def _latest_catalog(db: Session, *, season: int, edition_type: str) -> CardCatalog | None:
    return (
        db.query(CardCatalog)
        .filter(
            CardCatalog.season == season,
            CardCatalog.edition_type == edition_type,
        )
        .order_by(CardCatalog.version.desc())
        .first()
    )


def _active_catalog(db: Session, *, season: int, edition_type: str) -> CardCatalog | None:
    return (
        db.query(CardCatalog)
        .filter(
            CardCatalog.season == season,
            CardCatalog.edition_type == edition_type,
            CardCatalog.status == "ACTIVE",
        )
        .first()
    )


def publish_card_catalog(
    db: Session,
    *,
    season: int,
    card_edition_id: str,
    rating_model_version: str | None = None,
    data_end_date: date | None = None,
) -> CatalogRunResult:
    card_edition = db.get(CardEdition, card_edition_id)
    if card_edition is None:
        raise ValueError(f"CardEdition inexistente: {card_edition_id}")
    if card_edition.season != season:
        raise ValueError("CardEdition no pertenece a la temporada solicitada")
    edition_type = card_edition.edition_type.value
    active = _active_catalog(db, season=season, edition_type=edition_type)
    if active is not None:
        # No-op §22: ya publicada esta edición; no se duplica nada.
        existing = (
            db.query(PlayerCardModel)
            .filter(PlayerCardModel.catalog_id == active.id)
            .count()
        )
        result = CatalogRunResult(
            catalog_id=active.id,
            catalog_version=active.version,
            status="ACTIVE",
            created=existing,
        )
        result.issues.append("catálogo ya publicado (no-op)")
        return result

    latest = _latest_catalog(db, season=season, edition_type=edition_type)
    next_version = (latest.version + 1) if latest else 1

    proposal = db.query(CardCatalog).filter(
        CardCatalog.season == season,
        CardCatalog.edition_type == edition_type,
        CardCatalog.version == next_version,
        CardCatalog.status != "ACTIVE",
    ).one_or_none()
    catalog = proposal
    if catalog is None:
        catalog = CardCatalog(
            season=season,
            edition_type=edition_type,
            version=next_version,
            status="BUILDING",
            rating_model_version=rating_model_version,
            data_end_date=data_end_date,
        )
        db.add(catalog)
        db.flush()

    # ------ BUILDING: candidatos = perfiles válidos del corte ----------
    profile_query = (
        db.query(CardGenerationProfile)
        .join(PlayerSeason, CardGenerationProfile.player_season_id == PlayerSeason.id)
        .filter(PlayerSeason.season == season)
    )
    if data_end_date is not None:
        profile_query = profile_query.filter(PlayerSeason.data_end_date == data_end_date)
    if rating_model_version is not None:
        profile_query = profile_query.filter(CardGenerationProfile.rating_model_version == rating_model_version)
    profiles = profile_query.all()

    rows_to_insert: list[PlayerCardModel] = []
    seen_players: set[str] = set()
    skipped_unresolved = 0
    rarity_failures: list[str] = []

    for profile in profiles:
        player = profile.player_season.player
        if player is None or player.game_identity is None:
            skipped_unresolved += 1
            continue
        game_team = _game_team_for_player(db, player.id)
        if game_team is None:
            skipped_unresolved += 1
            continue
        if player.id in seen_players:
            continue
        seen_players.add(player.id)
        rating_profile = _resolve_rating_profile(
            db, card_edition, profile, player.id
        )
        source = rating_profile if rating_profile is not None else profile
        try:
            rarity = _resolve_published_rarity(
                db, card_edition, profile, source.overall_rating
            )
        except ValueError as exc:
            rarity_failures.append(f"mlb_id={player.mlb_id}: {exc}")
            continue
        payload = _card_from_profile(
            catalog,
            card_edition,
            profile,
            player,
            game_team,
            rating_profile,
            rarity=rarity,
        )
        if payload is None:
            skipped_unresolved += 1
            continue
        rows_to_insert.append(payload)

    # ------ VALIDATING: gates de calidad (§52) --------------------------
    issues = rarity_failures + _validate_rows(rows_to_insert)
    if issues:
        catalog.status = "FAILED"
        db.commit()
        result = CatalogRunResult(
            catalog_id=catalog.id,
            catalog_version=catalog.version,
            status="FAILED",
            issues=issues,
        )
        return result

    # Se materializan las cartas SOLO si la validación pasó.
    db.add_all(rows_to_insert)
    catalog.status = "VALIDATING"
    db.commit()

    # ------ ACTIVE: publicación atómica --------------------------------
    catalog.status = "ACTIVE"
    from app.core.time import utcnow

    catalog.published_at = utcnow()
    for card in rows_to_insert:
        card.is_active = True
        card.is_pack_eligible = True
    db.commit()

    logger.info(
        "catalog ACTIVE season=%s edition=%s version=%s cards=%s",
        season, edition_type, catalog.version, len(rows_to_insert),
    )
    return CatalogRunResult(
        catalog_id=catalog.id,
        catalog_version=catalog.version,
        status="ACTIVE",
        created=len(rows_to_insert),
        skipped_unresolved=skipped_unresolved,
    )


def _game_team_for_player(db: Session, player_id: str) -> str | None:
    # Stint vigente -> SourceTeam -> mapping activa -> Team público.
    row = (
        db.query(
            SourceTeamGameTeamMapping.team_id,
            SourceTeamRosterMember.player_id,
        )
        .join(SourceTeamRosterSnapshot, SourceTeamRosterSnapshot.source_team_id == SourceTeamGameTeamMapping.source_team_id)
        .join(SourceTeamRosterMember, SourceTeamRosterMember.roster_snapshot_id == SourceTeamRosterSnapshot.id)
        .filter(SourceTeamGameTeamMapping.valid_to.is_(None))
        .filter(SourceTeamRosterMember.player_id == player_id)
        .order_by(SourceTeamRosterSnapshot.as_of_date.desc())
        .first()
    )
    return row[0] if row else None


_RATING_FIELDS = (
    "contact_rating",
    "power_rating",
    "vision_rating",
    "clutch_rating",
    "velocity_rating",
    "control_rating",
    "movement_rating",
    "stuff_rating",
    "overall_rating",
)


def _resolve_rating_profile(
    db: Session,
    card_edition: CardEdition,
    profile: CardGenerationProfile,
    player_id: str,
) -> CardRatingProfile | None:
    """CardRatingProfile autoritativo, determinista y del mismo snapshot.

    Identidad = (player, edición, role) + rating_policy_version que la edición
    declara. La uq_card_rating_profiles_identity garantiza a lo sumo un perfil
    por esa tupla, sin depender de orden temporal de inserción. Si la edición
    no declara política (legacy) se devuelve None y la publicación usa el
    CardGenerationProfile como puente de compatibilidad (frontera a revisar).
    """
    if profile.player_ratings_id is None or profile.role is None:
        return None
    if card_edition.rating_policy_version is None:
        return None
    return (
        db.query(CardRatingProfile)
        .filter(
            CardRatingProfile.player_id == player_id,
            CardRatingProfile.card_edition_id == card_edition.id,
            CardRatingProfile.role == profile.role,
            CardRatingProfile.rating_policy_version
            == card_edition.rating_policy_version,
            CardRatingProfile.source_player_ratings_id == profile.player_ratings_id,
        )
        .one_or_none()
    )


def _resolve_published_rarity(
    db: Session,
    card_edition: CardEdition,
    profile: CardGenerationProfile,
    final_overall: int,
):
    """Rareza publicada: legacy si la edición no declara política; si la
    declara, resolución obligatoria sobre el OVR final publicado (nunca COMMON
    silencioso). El tier se recalcula sobre la población del mismo snapshot
    (rating_distribution_id persistido en generación); el tier histórico de
    metadata solo queda como provenance.
    """
    if card_edition.rarity_policy_version is None:
        return profile.calculated_rarity
    distribution_id = (profile.calculation_metadata or {}).get(
        "rating_distribution_id"
    )
    if distribution_id is None:
        raise ValueError(
            "generation profile sin rating_distribution_id; "
            "no se puede resolver el tier final"
        )
    distribution = db.get(RatingDistribution, distribution_id)
    if distribution is None:
        raise ValueError(f"rating_distribution inexistente: {distribution_id}")
    tier = final_performance_tier(final_overall, distribution)
    return resolve_card_rarity(
        card_edition,
        final_overall=final_overall,
        performance_tier=tier.performance_tier,
    )


def _card_from_profile(
    catalog,
    card_edition: CardEdition,
    profile,
    player,
    game_team_id: str,
    rating_profile: CardRatingProfile | None = None,
    rarity=None,
) -> PlayerCardModel | None:
    source = rating_profile if rating_profile is not None else profile
    values = {field: getattr(source, field) for field in _RATING_FIELDS}
    overall = values["overall_rating"]
    if not 0 <= overall <= 99:
        return None
    identity = player.game_identity
    is_two_way = (
        (values["velocity_rating"] or 0) > 0
        and (values["power_rating"] or 0) > 0
        and (values["contact_rating"] or 0) > 0
    )
    position = player.primary_position or "UT"
    if is_two_way:
        position = "TWP" if position in ("SP", "RP", "P") else position
    return PlayerCardModel(
        id=_new_id(),
        team_id=game_team_id,
        name=identity.display_name,
        number=identity.default_jersey_number or "00",
        position=position,
        overall=overall,
        rarity=rarity,
        is_two_way=is_two_way,
        # PlayerCard conserva el contrato numérico del motor; los N/A del
        # perfil estadístico se materializan aquí, no en el perfil.
        power=values["power_rating"] or 0,
        contact=values["contact_rating"] or 0,
        velocity=values["velocity_rating"] or 0,
        control=values["control_rating"] or 0,
        movement=values["movement_rating"] or 0,
        vision=values["vision_rating"] or 0,
        clutch=values["clutch_rating"] or 0,
        repertoire=profile.repertoire_payload,
        player_id=player.id,
        player_season_id=profile.player_season_id,
        generation_profile_id=profile.id,
        card_rating_profile_id=source.id if rating_profile is not None else None,
        edition_type=catalog.edition_type,
        edition_version=catalog.version,
        season=catalog.season,
        is_active=False,
        is_pack_eligible=False,
        published_at=None,
        rating_model_version=profile.rating_model_version,
        game_identity_id=identity.id,
        catalog_id=catalog.id,
        card_edition_id=card_edition.id,
    )


def _validate_rows(rows: list[PlayerCardModel]) -> list[str]:
    issues: list[str] = []
    if not rows:
        issues.append("sin candidatos válidos para publicar")
    for card in rows:
        for field_name, label in (
            ("overall", "overall"),
            ("power", "power"),
            ("contact", "contact"),
            ("velocity", "velocity"),
            ("control", "control"),
            ("movement", "movement"),
            ("vision", "vision"),
            ("clutch", "clutch"),
        ):
            value = getattr(card, field_name) or 0
            if not 0 <= value <= 99:
                issues.append(f"{label} fuera de rango: {value}")
        if card.repertoire and len(card.repertoire) > 4:
            issues.append(f"repertorio excede 4 pitches: {card.name}")
        if not card.game_identity_id or not card.team_id:
            issues.append(f"carta sin identidad pública o equipo: {card.name}")
    return issues


# ---------- Validadores derivados (plan V2 §53-§54) ----------------------

@dataclass
class ValidationResult:
    ok: bool
    detail: list[str] = field(default_factory=list)


def validate_pack_pool(db: Session, *, season: int, edition_type: str = "BASE") -> ValidationResult:
    """Pack pool: catálogo ACTIVE y cartas elegibles (jamás legacy)."""
    active = _active_catalog(db, season=season, edition_type=edition_type)
    detail = []
    if active is None:
        return ValidationResult(ok=False, detail=["sin catálogo ACTIVE"])
    cards = (
        db.query(PlayerCardModel)
        .filter(PlayerCardModel.catalog_id == active.id)
        .all()
    )
    detail.append(f"catálogo ACTIVE {active.id} v{active.version}")
    if not cards:
        detail.append("catálogo ACTIVE sin cartas")
        return ValidationResult(ok=False, detail=detail)
    pack_eligible = [c for c in cards if c.is_pack_eligible]
    detail.append(f"cartas={len(cards)} elegibles={len(pack_eligible)}")
    if len(pack_eligible) != len(cards):
        detail.append(
            f"{len(cards) - len(pack_eligible)} cartas del catálogo sin is_pack_eligible"
        )
    return ValidationResult(ok=len(pack_eligible) == len(cards), detail=detail)


def validate_cpu_rosters(db: Session, *, season: int, edition_type: str = "BASE") -> ValidationResult:
    """Cada franquicia pública con mapa+snapshot debe tener cartas publicadas."""
    detail = []
    active = _active_catalog(db, season=season, edition_type=edition_type)
    if active is None:
        return ValidationResult(ok=False, detail=["sin catálogo ACTIVE"])
    rows = (
        db.query(SourceTeamGameTeamMapping.team_id)
        .filter(SourceTeamGameTeamMapping.valid_to.is_(None))
        .all()
    )
    missing = []
    for (team_id,) in rows:
        count = (
            db.query(PlayerCardModel)
            .filter(
                PlayerCardModel.team_id == team_id,
                PlayerCardModel.catalog_id == active.id,
            )
            .count()
        )
        if count == 0:
            missing.append(team_id)
    detail.append(f"franquicias mapeadas={len(rows)} sin cartas={len(missing)}")
    if missing:
        detail.append(f"sin cartas publicadas: {', '.join(missing[:20])}")
    return ValidationResult(ok=not missing, detail=detail)
