"""Generación de CardGenerationProfile (spec §33, plan V2).

Se ejecuta SOLO después de que analytics termina correctamente. Genera perfiles
de carta (NUNCA publica en player_cards). La identidad lógica es
(player_season_id, rating_model_version); input_hash detecta cambios Analytics
y permite una actualización controlada sin confundirlos con cambios de fórmula.
`generate-card-profiles` admite --data-end-date (corte) y --rating-model.
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy.orm import Session

from app.models import CardGenerationProfile, PlayerCardModel, PlayerSeason, BatterSeasonStats, PitcherPitchProfile, PitcherSeasonStats
from etl.config import RATING_MODEL_VERSION
from etl.services.card_catalog import ValidationResult

logger = logging.getLogger("etl.services.card_profiles")

SUPPORTED_RATING_MODELS = frozenset({"ratings-1.0"})


def _as_float(value: Decimal | float | int | None) -> float | None:
    """Convierte valores Numeric del ORM al tipo usado por las fórmulas de ratings."""
    return float(value) if value is not None else None


def _canonical_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _canonical_value(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item) for item in value]
    return value


def _input_hash(payload: dict) -> str:
    encoded = json.dumps(
        _canonical_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _batter_profile_inputs(
    batter: BatterSeasonStats, *, rating_model_version: str, data_end_date: date
) -> dict:
    return {
        "rating_model_version": rating_model_version,
        "data_end_date": data_end_date,
        "season_stats": {
            "contact_rate": batter.contact_rate,
            "slg": batter.slg,
            "whiff_rate": batter.whiff_rate,
            "home_runs": batter.home_runs,
        },
    }


def _pitcher_profile_inputs(
    pitcher: PitcherSeasonStats,
    arsenal: list[PitcherPitchProfile],
    *,
    rating_model_version: str,
    data_end_date: date,
) -> dict:
    arsenal_inputs = [
        {
            "pitch_type": row.pitch_type,
            "pitch_family": row.pitch_family,
            "batter_side": row.batter_side,
            "pitch_count": row.pitch_count,
        }
        for row in arsenal
    ]
    arsenal_inputs.sort(
        key=lambda row: (
            row["pitch_type"] or "",
            _canonical_value(row["pitch_family"]) or "",
            _canonical_value(row["batter_side"]) or "",
        )
    )
    return {
        "rating_model_version": rating_model_version,
        "data_end_date": data_end_date,
        "season_stats": {
            "avg_velocity": pitcher.avg_velocity,
            "whiff_rate": pitcher.whiff_rate,
            "walks": pitcher.walks,
            "strikeouts": pitcher.strikeouts,
            "batters_faced": pitcher.batters_faced,
        },
        "arsenal": arsenal_inputs,
    }


@dataclass
class ProfileRunResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_no_data: int = 0
    rejected: int = 0
    version: str = RATING_MODEL_VERSION
    detail: list[str] = field(default_factory=list)


def _clamp(v: float | None, lo: int = 0, hi: int = 99) -> int:
    if v is None:
        return lo
    return int(max(lo, min(hi, round(v))))


def _linear(percentile: float | None, *, lo: int = 40, hi: int = 99) -> int:
    if percentile is None:
        return lo
    return _clamp(lo + (hi - lo) * float(percentile), lo, hi)


def _build_batter_profile(batter: BatterSeasonStats, model_version: str) -> dict:
    contact = _linear(batter.contact_rate, lo=40)
    power = _linear(batter.slg, lo=40)
    vision = _linear(batter.whiff_rate, lo=60, hi=99)  # menor whiff → mayor visión
    vision = _clamp(99 - 40 * (_as_float(batter.whiff_rate) or 0), 40, 99)
    clutch = _linear(None, lo=50)
    overall = _clamp(round(0.35 * contact + 0.30 * power + 0.20 * vision + 0.15 * clutch))
    return {
        "contact_rating": contact,
        "power_rating": power,
        "vision_rating": vision,
        "clutch_rating": clutch,
        "velocity_rating": 0,
        "control_rating": 0,
        "movement_rating": 0,
        "overall_rating": overall,
        "primary_batter_trait": _batter_trait(batter),
        "primary_pitcher_trait": None,
        "repertoire_payload": None,
        "calculation_metadata": {"batter": True, "model": model_version},
    }


def _build_pitcher_profile(pitcher: PitcherSeasonStats, arsenal: list[PitcherPitchProfile], model_version: str) -> dict:
    avg_velocity = _as_float(pitcher.avg_velocity)
    whiff_rate = _as_float(pitcher.whiff_rate)
    velocity = _linear(avg_velocity / 100.0 if avg_velocity is not None else None, lo=60)
    walk_avoidance = (
        1 - pitcher.walks / pitcher.batters_faced
        if pitcher.batters_faced
        else None
    )
    control = _linear(walk_avoidance, lo=40)
    movement = _linear(1 - (whiff_rate or 0), lo=40)
    overall = _clamp(round(0.40 * velocity + 0.35 * control + 0.25 * movement))
    repertoire = [
        {"pitch_type": a.pitch_type, "pitch_family": a.pitch_family.value if hasattr(a.pitch_family, "value") else a.pitch_family}
        for a in arsenal[:4]
    ]
    return {
        "contact_rating": 0,
        "power_rating": 0,
        "vision_rating": 0,
        "clutch_rating": _clamp(round(overall * 0.4)),
        "velocity_rating": velocity,
        "control_rating": control,
        "movement_rating": movement,
        "overall_rating": overall,
        "primary_batter_trait": None,
        "primary_pitcher_trait": _pitcher_trait(pitcher),
        "repertoire_payload": repertoire or None,
        "calculation_metadata": {"batter": False, "model": model_version, "pitches_in_arsenal": len(arsenal)},
    }


def _batter_trait(batter: BatterSeasonStats) -> str:
    best = max(
        [("contact", batter.contact_rate or 0), ("power", batter.slg or 0), ("power2", batter.home_runs or 0)],
        key=lambda x: x[1],
    )
    return {"contact": "Contact", "power": "Power", "power2": "Power"}[best[0]]


def _pitcher_trait(pitcher: PitcherSeasonStats) -> str:
    best = max(
        [("power", pitcher.avg_velocity or 0), ("control", 100 - pitcher.walks), ("stuff", pitcher.strikeouts or 0)],
        key=lambda x: x[1],
    )
    return {"power": "Velocity", "control": "Control", "stuff": "Strikeout Stuff"}[best[0]]


def _update_card_generation_profile(
    profile: CardGenerationProfile,
    payload: dict,
    *,
    input_hash: str,
    calculated_rarity,
) -> None:
    for field_name in (
        "contact_rating",
        "power_rating",
        "vision_rating",
        "clutch_rating",
        "velocity_rating",
        "control_rating",
        "movement_rating",
        "overall_rating",
        "primary_batter_trait",
        "primary_pitcher_trait",
        "repertoire_payload",
        "calculation_metadata",
    ):
        setattr(profile, field_name, payload[field_name])
    profile.calculated_rarity = calculated_rarity
    profile.input_hash = input_hash


def generate_profiles(
    db: Session,
    *,
    season: int,
    rating_model_version: str | None = RATING_MODEL_VERSION,
    data_end_date: date | None = None,
) -> ProfileRunResult:
    rating_model_version = rating_model_version or RATING_MODEL_VERSION
    if rating_model_version not in SUPPORTED_RATING_MODELS:
        raise ValueError(
            f"rating model no implementado: {rating_model_version}; "
            f"disponibles={sorted(SUPPORTED_RATING_MODELS)}"
        )
    result = ProfileRunResult(version=rating_model_version)
    if not hasattr(PlayerCardModel, "get_rarity_by_overall"):
        raise RuntimeError("PlayerCardModel sin get_rarity_by_overall")

    seasons_query = (
        db.query(PlayerSeason)
        .filter(PlayerSeason.season == season)
    )
    if data_end_date is not None:
        seasons_query = seasons_query.filter(PlayerSeason.data_end_date == data_end_date)
    seasons = seasons_query.order_by(PlayerSeason.data_end_date.desc()).all()
    seen = set()
    for ps in seasons:
        if ps.id in seen:
            continue
        seen.add(ps.id)
        batter = db.query(BatterSeasonStats).filter(BatterSeasonStats.player_season_id == ps.id).one_or_none()
        pitcher = db.query(PitcherSeasonStats).filter(PitcherSeasonStats.player_season_id == ps.id).one_or_none()
        if batter is None and pitcher is None:
            result.skipped_no_data += 1
            continue

        arsenal: list[PitcherPitchProfile] = []
        if batter is not None:
            profile_payload = _build_batter_profile(batter, rating_model_version)
            input_payload = _batter_profile_inputs(
                batter,
                rating_model_version=rating_model_version,
                data_end_date=ps.data_end_date,
            )
        elif pitcher is not None:
            arsenal = (
                db.query(PitcherPitchProfile)
                .filter(PitcherPitchProfile.player_season_id == ps.id, PitcherPitchProfile.batter_side == "ALL")
                .order_by(
                    PitcherPitchProfile.pitch_count.desc(),
                    PitcherPitchProfile.pitch_type.asc(),
                )
                .all()
            )
            profile_payload = _build_pitcher_profile(pitcher, arsenal, rating_model_version)
            input_payload = _pitcher_profile_inputs(
                pitcher,
                arsenal,
                rating_model_version=rating_model_version,
                data_end_date=ps.data_end_date,
            )

        new_input_hash = _input_hash(input_payload)
        profile_payload["calculation_metadata"].update(
            {
                "data_end_date": ps.data_end_date.isoformat(),
                "input_hash": new_input_hash,
            }
        )

        existing = (
            db.query(CardGenerationProfile)
            .filter(
                CardGenerationProfile.player_season_id == ps.id,
                CardGenerationProfile.rating_model_version == rating_model_version,
            )
            .one_or_none()
        )
        if existing is not None and existing.input_hash == new_input_hash:
            result.unchanged += 1
            continue

        rarity = PlayerCardModel.get_rarity_by_overall(profile_payload["overall_rating"])
        if existing is None:
            db.add(CardGenerationProfile(
                player_season_id=ps.id,
                rating_model_version=rating_model_version,
                input_hash=new_input_hash,
                calculated_rarity=rarity,
                **profile_payload,
            ))
            result.created += 1
        else:
            _update_card_generation_profile(
                existing,
                profile_payload,
                input_hash=new_input_hash,
                calculated_rarity=rarity,
            )
            result.updated += 1
    db.commit()
    return result


def validate_profiles(
    db: Session,
    *,
    season: int,
    data_end_date: date | None = None,
    rating_model_version: str = RATING_MODEL_VERSION,
) -> ValidationResult:
    """Gate §52: perfiles dentro de contrato y con identidad/equipo resueltos."""
    issues: list[str] = []
    query = (
        db.query(CardGenerationProfile)
        .join(PlayerSeason, CardGenerationProfile.player_season_id == PlayerSeason.id)
        .filter(PlayerSeason.season == season)
    )
    if data_end_date is not None:
        query = query.filter(PlayerSeason.data_end_date == data_end_date)
    profiles = query.all()
    if not profiles:
        issues.append("sin perfiles para la temporada")
    for profile in profiles:
        player = profile.player_season.player if profile.player_season else None
        if player is None:
            issues.append(f"perfil {profile.id} sin player_season/player")
        elif player.game_identity is None:
            issues.append(f"perfil de mlb_id={player.mlb_id} sin identidad pública")
        if profile.repertoire_payload and len(profile.repertoire_payload) > 4:
            issues.append(f"perfil {profile.id}: repertorio > 4 pitches")
    return ValidationResult(ok=not issues, detail=issues)
