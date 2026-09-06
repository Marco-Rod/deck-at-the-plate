# Ratings 2.0 — Inventario real de Analytics

Este inventario aplica el checkpoint requerido por
`Deck_at_the_Plate_Ratings_2_0_Ajustes.md`. No se debe publicar un perfil como
`ratings-2.0` hasta completar las métricas y distribuciones marcadas como
`MISSING`.

## Bateador

| Métrica | Fuente | Estado | Denominador | Uso |
|---|---|---|---|---|
| Contact% | `BatterSeasonStats.contact_rate` | AVAILABLE | swings | Contact |
| BA | `BatterSeasonStats.avg` | AVAILABLE (fallback de xBA) | AB | Contact |
| xBA | sin columna RAW/Analytics | MISSING | BBE/AB | Contact |
| Whiff% | `BatterSeasonStats.whiff_rate` | AVAILABLE | swings | Contact/Vision |
| ISO | `slg - avg` | DERIVABLE | PA/AB | Power |
| Barrel% | `BatterSeasonStats.barrel_rate` | AVAILABLE | BBE | Power |
| HardHit% | `BatterSeasonStats.hard_hit_rate` | AVAILABLE | BBE | Power |
| SLG | `BatterSeasonStats.slg` | AVAILABLE | AB | Power |
| Chase% | `BatterSeasonStats.chase_rate` | AVAILABLE | pitches fuera de zona | Vision |
| BB% | `walks / pa` | DERIVABLE | PA | Vision |
| K% | `strikeouts / pa` | DERIVABLE | PA | Vision |
| Clutch situacional | sin agregado situacional | MISSING | PA situacionales | Clutch |

## Pitcher

| Métrica | Fuente | Estado | Denominador | Uso |
|---|---|---|---|---|
| Avg Velocity | `PitcherSeasonStats.avg_velocity` | AVAILABLE | pitches con velocidad | Velocity |
| BB% | `walks / batters_faced` | DERIVABLE | BF | Control |
| Zone% | solo derivable desde RAW; no persistida en Analytics | MISSING | pitches | Control |
| FirstPitchStrike% | no persistida en Analytics | MISSING | PA/BF | Control |
| HBP% | contador interno no expuesto en `PitcherSeasonStats` | MISSING | BF | Control |
| Horizontal break | `PitcherPitchProfile.avg_horizontal_break` | AVAILABLE por pitch | pitch_count | Movement |
| Vertical break | `PitcherPitchProfile.avg_vertical_break` | AVAILABLE por pitch | pitch_count | Movement |
| Pitch usage | `PitcherPitchProfile.usage_rate` | AVAILABLE | pitch_count | Movement |
| Whiff% | `PitcherSeasonStats.whiff_rate` | AVAILABLE | swings | Stuff |
| CalledStrike% | `PitcherSeasonStats.called_strike_rate` | AVAILABLE | pitches | Stuff/CSW |
| CSW% | called strikes + whiffs / pitches | DERIVABLE con contadores de arsenal | pitches | Stuff |
| K% | `strikeouts / batters_faced` | DERIVABLE | BF | Stuff |
| inverse Contact% | `1 - whiff_rate` solo si el denominador es swings | DERIVABLE | swings | Stuff |

## Infraestructura que falta

- Distribuciones MLB reales y versionadas por temporada, rol y métrica.
- Distribuciones de movimiento por `pitch_type` o, como fallback explícito, por
  `pitch_family`.
- Versión de baseline y versión de distribución incluidas en `input_hash`.
- `stuff_rating` en `CardGenerationProfile` y en el contrato/snapshot de carta.
- Métricas Analytics de `zone_rate`, `first_pitch_strike_rate` y `hbp_rate`.
- Muestra situacional para Clutch; hasta entonces debe usarse neutral explícito.

## Gate

`ratings-1.0` permanece operativo. `ratings-2.0` debe rechazarse explícitamente
mientras este gate no esté completo, para impedir que fórmulas 1.0 se persistan
bajo una versión engañosa.
