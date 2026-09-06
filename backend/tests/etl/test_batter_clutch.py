"""Contrato congelado de Clutch neutral para batter ratings-2.0."""

from etl.config.ratings_2 import CLUTCH_NEUTRAL_RATING, CLUTCH_SOURCE
from etl.services.batter_clutch import calculate_batter_clutch


def test_clutch_es_neutral_explicito_y_sin_muestra():
    result = calculate_batter_clutch()

    assert result.rating == 70 == CLUTCH_NEUTRAL_RATING
    assert result.source == CLUTCH_SOURCE == "NEUTRAL_BASELINE_PENDING_SITUATIONAL_DATA"
    assert result.sample_size == 0
    assert result.model_version == "ratings-2.0"
