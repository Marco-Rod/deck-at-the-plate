"""Ensamblador no persistente de batter ratings-2.0."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from sqlalchemy.orm import Session

from etl.config.ratings_2 import BATTER_OVERALL_WEIGHTS, RATING_MODEL_VERSION
from etl.services.batter_clutch import BatterClutchRating, calculate_batter_clutch
from etl.services.batter_contact import BatterContactRating, calculate_batter_contact
from etl.services.batter_power import BatterPowerRating, calculate_batter_power
from etl.services.batter_vision import BatterVisionRating, calculate_batter_vision
from etl.services.rating_math import round_rating
from etl.services.rating_evidence import component_evidence


@dataclass(frozen=True)
class BatterRatings2:
    mlb_id: int
    contact: BatterContactRating
    power: BatterPowerRating
    vision: BatterVisionRating
    clutch: BatterClutchRating
    overall_rating: int | None
    model_version: str
    skipped_components: tuple[str, ...]

    @property
    def contact_evidence(self) -> Decimal | None:
        return component_evidence(self.contact)

    @property
    def power_evidence(self) -> Decimal | None:
        return component_evidence(self.power)

    @property
    def vision_evidence(self) -> Decimal | None:
        return component_evidence(self.vision)

    @property
    def clutch_evidence(self) -> Decimal | None:
        return None


def calculate_batter_ratings2(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
    contact_calculator: Callable = calculate_batter_contact,
    power_calculator: Callable = calculate_batter_power,
    vision_calculator: Callable = calculate_batter_vision,
    clutch_calculator: Callable = calculate_batter_clutch,
) -> BatterRatings2:
    kwargs = {
        "mlb_id": mlb_id,
        "season": season,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "distribution_version": distribution_version,
    }
    contact = contact_calculator(db, **kwargs)
    power = power_calculator(db, **kwargs)
    vision = vision_calculator(db, **kwargs)
    clutch = clutch_calculator()
    components = {
        "contact": contact,
        "power": power,
        "vision": vision,
        "clutch": clutch,
    }
    skipped = tuple(
        name for name, component in components.items() if component.rating is None
    )
    overall = None
    if not skipped:
        overall = round_rating(sum(
            components[name].rating * weight
            for name, weight in BATTER_OVERALL_WEIGHTS.items()
        ))
    return BatterRatings2(
        mlb_id=mlb_id,
        contact=contact,
        power=power,
        vision=vision,
        clutch=clutch,
        overall_rating=overall,
        model_version=RATING_MODEL_VERSION,
        skipped_components=skipped,
    )
