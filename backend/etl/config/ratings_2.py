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

STUFF_WEIGHTS = {
    "whiff_rate": 0.50,
    "csw_rate": 0.30,
    "strikeout_rate": 0.20,
}
MIN_STUFF_WEIGHT_COVERAGE = 0.75

# ratings-2.0 (laboratorio): hiperparámetros iniciales por oportunidad real.
CONTACT_RATE_STABILIZATION = 50  # swings
AVG_STABILIZATION = 40  # AB
WHIFF_RATE_STABILIZATION = 50  # swings

BATTER_CONTACT_WEIGHTS = {
    "contact_rate": 0.60,
    "avg": 0.25,
    "whiff_rate": 0.15,
}

BATTER_CONTACT_STABILIZATIONS = {
    "contact_rate": CONTACT_RATE_STABILIZATION,
    "avg": AVG_STABILIZATION,
    "whiff_rate": WHIFF_RATE_STABILIZATION,
}

ISO_STABILIZATION = 40  # AB
BARREL_RATE_STABILIZATION = 30  # batted balls con EV + launch angle
HARD_HIT_RATE_STABILIZATION = 30  # batted balls con EV
SLG_STABILIZATION = 40  # AB

BATTER_POWER_WEIGHTS = {
    "iso": 0.40,
    "barrel_rate": 0.30,
    "hard_hit_rate": 0.20,
    "slg": 0.10,
}

BATTER_POWER_STABILIZATIONS = {
    "iso": ISO_STABILIZATION,
    "barrel_rate": BARREL_RATE_STABILIZATION,
    "hard_hit_rate": HARD_HIT_RATE_STABILIZATION,
    "slg": SLG_STABILIZATION,
}

CHASE_RATE_STABILIZATION = 50  # chase opportunities
WALK_RATE_STABILIZATION = 40  # PA
STRIKEOUT_RATE_STABILIZATION = 40  # PA

BATTER_VISION_WEIGHTS = {
    "chase_rate": 0.40,
    "whiff_rate": 0.30,
    "walk_rate": 0.20,
    "strikeout_rate": 0.10,
}

BATTER_VISION_STABILIZATIONS = {
    "chase_rate": CHASE_RATE_STABILIZATION,
    "whiff_rate": WHIFF_RATE_STABILIZATION,
    "walk_rate": WALK_RATE_STABILIZATION,
    "strikeout_rate": STRIKEOUT_RATE_STABILIZATION,
}

# Temporal hasta disponer de datos situacionales reproducibles para Clutch.
CLUTCH_NEUTRAL_RATING = 70
CLUTCH_SOURCE = "NEUTRAL_BASELINE_PENDING_SITUATIONAL_DATA"

BATTER_OVERALL_WEIGHTS = {
    "contact": 0.30,
    "power": 0.30,
    "vision": 0.25,
    "clutch": 0.15,
}
