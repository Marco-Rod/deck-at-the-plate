"""Ensamblador no persistente de los cuatro atributos de pitcher ratings-2.0."""

from dataclasses import dataclass, field
from datetime import date
from typing import Callable

from sqlalchemy.orm import Session

from etl.config.ratings_2 import RATING_MODEL_VERSION
from etl.services.pitcher_control import PitcherControlResult, calculate_control_candidate
from etl.services.pitcher_movement import MovementCandidateResult, calculate_movement_candidate
from etl.services.pitcher_stuff import PitcherStuffResult, calculate_stuff_candidate
from etl.services.pitcher_velocity import PitcherVelocityResult, calculate_velocity_candidate
from etl.services.rating_math import round_rating


PITCHER_OVERALL_WEIGHTS = {
    "velocity": 0.20,
    "control": 0.30,
    "movement": 0.25,
    "stuff": 0.25,
}


@dataclass(frozen=True)
class PitcherRatings2Result:
    mlb_id: int
    rating_model_version: str
    velocity: PitcherVelocityResult
    control: PitcherControlResult
    movement: MovementCandidateResult
    stuff: PitcherStuffResult
    overall: int | None
    unavailable_attributes: list[str] = field(default_factory=list)


def calculate_pitcher_ratings2(
    db: Session,
    *,
    mlb_id: int,
    season: int,
    data_start_date: date,
    data_end_date: date,
    distribution_version: str | None = None,
    velocity_calculator: Callable = calculate_velocity_candidate,
    control_calculator: Callable = calculate_control_candidate,
    movement_calculator: Callable = calculate_movement_candidate,
    stuff_calculator: Callable = calculate_stuff_candidate,
) -> PitcherRatings2Result:
    kwargs = {
        "mlb_id": mlb_id,
        "season": season,
        "data_start_date": data_start_date,
        "data_end_date": data_end_date,
        "distribution_version": distribution_version,
    }
    velocity = velocity_calculator(db, **kwargs)
    control = control_calculator(db, **kwargs)
    movement = movement_calculator(db, **kwargs)
    stuff = stuff_calculator(db, **kwargs)
    results = {
        "velocity": velocity,
        "control": control,
        "movement": movement,
        "stuff": stuff,
    }
    unavailable = [name for name, result in results.items() if result.rating is None]
    overall = None
    if not unavailable:
        raw_overall = sum(
            results[name].rating * weight
            for name, weight in PITCHER_OVERALL_WEIGHTS.items()
        )
        overall = round_rating(raw_overall)
    return PitcherRatings2Result(
        mlb_id=mlb_id,
        rating_model_version=RATING_MODEL_VERSION,
        velocity=velocity,
        control=control,
        movement=movement,
        stuff=stuff,
        overall=overall,
        unavailable_attributes=unavailable,
    )
