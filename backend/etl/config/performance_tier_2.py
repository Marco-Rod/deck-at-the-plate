"""Metodología de tier de performance basada en posición poblacional."""


# Se conserva el token histórico porque la columna física todavía se llama
# rarity_model_version. El significado de dominio desde este refactor es tier.
PERFORMANCE_TIER_MODEL_VERSION = "rarity-2.0"
OVERALL_RATING_METRIC = "overall_rating"

PERFORMANCE_TIER_THRESHOLDS = {
    "BRONZE": 0.40,
    "SILVER": 0.65,
    "GOLD": 0.82,
    "DIAMOND": 0.95,
}
