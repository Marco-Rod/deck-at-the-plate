"""Generación de CardGenerationProfile (spec §33).

Se ejecuta SOLO después de que analytics termina correctamente. Genera perfiles
de carta (NUNCA publica en player_cards). Inmutable: upsert por
(player_season_id, rating_model_version) — si el modelo cambia, nueva fila.
"""

import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.models import CardGenerationProfile, PlayerCardModel, PlayerSeason, BatterSeasonStats, PitcherPitchProfile, PitcherSeasonStats
from etl.config import RATING_MODEL_VERSION

logger = logging.getLogger("etl.services.card_profiles")


@dataclass
class ProfileRunResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    version: str = RATING_MODEL_VERSION
    detail: list[str] = field(default_factory=list)


def _clamp(v: float | None, lo: int = 0, hi: int = 99) -> int:
    if v is None:
        return lo
    return int(max(lo, min(hi, round(v))))


def _linear(percentile: float | None, *, lo: int = 40, hi: int = 99) -> int:
    if percentile is None:
        return lo
    return _clamp(lo + (hi - lo) * percentile, lo, hi)


def _build_batter_profile(batter: BatterSeasonStats) -> dict:
    contact = _linear(batter.contact_rate, lo=40)
    power = _linear(batter.slg, lo=40)
    vision = _linear(batter.whiff_rate, lo=60, hi=99)  # menor whiff → mayor visión
    vision = _clamp(99 - 40 * (batter.whiff_rate or 0), 40, 99)
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
        "calculation_metadata": {"batter": True, "model": RATING_MODEL_VERSION},
    }


def _build_pitcher_profile(pitcher: PitcherSeasonStats, arsenal: list[PitcherPitchProfile]) -> dict:
    velocity = _linear(pitcher.avg_velocity / 100.0 if pitcher.avg_velocity else None, lo=60)
    control = _linear(1 - (pitcher.walks / pitcher.batters_faced if pitcher.batters_faced else None), lo=40)
    movement = _linear(1 - (pitcher.whiff_rate or 0), lo=40)
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
        "calculation_metadata": {"batter": False, "model": RATING_MODEL_VERSION, "pitches_in_arsenal": len(arsenal)},
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


def generate_profiles(db: Session, *, season: int) -> ProfileRunResult:
    result = ProfileRunResult()
    if not hasattr(PlayerCardModel, "get_rarity_by_overall"):
        raise RuntimeError("PlayerCardModel sin get_rarity_by_overall")

    seasons = (
        db.query(PlayerSeason)
        .filter(PlayerSeason.season == season)
        .order_by(PlayerSeason.data_end_date.desc())
        .all()
    )
    seen = set()
    for ps in seasons:
        if ps.id in seen:
            continue
        seen.add(ps.id)
        existing = (
            db.query(CardGenerationProfile)
            .filter(
                CardGenerationProfile.player_season_id == ps.id,
                CardGenerationProfile.rating_model_version == RATING_MODEL_VERSION,
            )
            .one_or_none()
        )
        if existing is not None:
            result.skipped += 1
            continue

        batter = db.query(BatterSeasonStats).filter(BatterSeasonStats.player_season_id == ps.id).one_or_none()
        pitcher = db.query(PitcherSeasonStats).filter(PitcherSeasonStats.player_season_id == ps.id).one_or_none()
        if batter is None and pitcher is None:
            result.skipped += 1
            continue
        if not batter:
            batter_stats = None
        if not pitcher:
            pitcher_stats = None

        profile_payload = None
        if batter is not None:
            profile_payload = _build_batter_profile(batter)
        elif pitcher is not None:
            arsenal = (
                db.query(PitcherPitchProfile)
                .filter(PitcherPitchProfile.player_season_id == ps.id, PitcherPitchProfile.batter_side == "ALL")
                .order_by(PitcherPitchProfile.pitch_count.desc())
                .all()
            )
            profile_payload = _build_pitcher_profile(pitcher, arsenal)
        else:
            profile_payload = _build_batter_profile(batter) if batter else None

        if profile_payload is None:
            result.skipped += 1
            continue

        rarity = PlayerCardModel.get_rarity_by_overall(profile_payload["overall_rating"])
        db.add(
            CardGenerationProfile(
                player_season_id=ps.id,
                rating_model_version=RATING_MODEL_VERSION,
                calculated_rarity=rarity,
                **profile_payload,
            )
        )
        result.created += 1
    db.commit()
    return result