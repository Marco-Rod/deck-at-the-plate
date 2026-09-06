"""Hiperparámetros versionados de la metodología ratings-2.0."""

RATING_MODEL_VERSION = "ratings-2.0"

# ratings-2.0:
# Movement is a physical pitch characteristic and is expected to stabilize
# faster than outcome metrics. 50 pitches gives a profile 50% influence over
# the league pitch-type/family prior.
MOVEMENT_STABILIZATION_PITCHES = 50

CONTROL_WEIGHTS = {
    "walk_rate": 0.45,
    "zone_rate": 0.30,
    "first_pitch_strike_rate": 0.15,
    "hbp_rate": 0.10,
}
MIN_CONTROL_WEIGHT_COVERAGE = 0.75
