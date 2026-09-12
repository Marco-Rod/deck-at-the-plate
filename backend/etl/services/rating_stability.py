"""Read-only calibration of evidence against later rating stability."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import random
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import BatterSeasonStats, Player, PlayerRatings, PlayerSeason
from etl.services.batter_power import calculate_batter_power


ROLE_ATTRIBUTES = {
    "BATTER": ("contact", "power", "vision"),
    "PITCHER": ("velocity", "control", "movement", "stuff"),
}


@dataclass(frozen=True)
class StabilityBucket:
    comparison: str
    role: str
    attribute: str
    evidence_bucket: str
    observations: int
    mae: Decimal
    p50_error: Decimal
    p90_error: Decimal
    within_3_pct: Decimal
    within_5_pct: Decimal
    within_10_pct: Decimal


@dataclass(frozen=True)
class StabilityThreshold:
    comparison: str
    role: str
    attribute: str
    minimum_evidence: Decimal
    observations: int
    players: int
    mae: Decimal
    median_error: Decimal
    p90_error: Decimal
    p95_error: Decimal
    within_3_pct: Decimal
    within_5_pct: Decimal
    within_10_pct: Decimal
    p90_ci_low: Decimal
    p90_ci_high: Decimal
    within_5_ci_low: Decimal
    within_5_ci_high: Decimal


@dataclass(frozen=True)
class PowerComponentDiagnostic:
    metric: str
    observed: Decimal
    sample_size: int
    stabilization: int
    evidence: Decimal
    adjusted: Decimal
    percentile: Decimal
    rating: int
    component_weight: Decimal


@dataclass(frozen=True)
class PowerTailDiagnostic:
    player_id: str
    mlb_id: int
    full_name: str
    snapshot_date: date
    snapshot_rating: int
    final_rating: int
    absolute_error: int
    aggregate_evidence: Decimal
    plate_appearances: int
    iso: Decimal | None
    slg: Decimal | None
    barrel_opportunities: int
    hard_hit_opportunities: int
    components: tuple[PowerComponentDiagnostic, ...]
    final_plate_appearances: int
    final_iso: Decimal | None
    final_slg: Decimal | None
    final_barrel_opportunities: int
    final_hard_hit_opportunities: int
    final_components: tuple[PowerComponentDiagnostic, ...]


@dataclass(frozen=True)
class StabilityAudit:
    final_date: date
    snapshot_dates: tuple[date, ...]
    final_players: int
    matched_player_snapshots: int
    next_matched_player_snapshots: int
    buckets: tuple[StabilityBucket, ...]
    thresholds: tuple[StabilityThreshold, ...]


def select_fractional_snapshots(
    available_dates: Iterable[date],
    *,
    data_start_date: date,
    final_date: date,
    fractions: tuple[Decimal, ...] = (
        Decimal("0.25"),
        Decimal("0.50"),
        Decimal("0.75"),
    ),
) -> tuple[date, ...]:
    """Select the available snapshot nearest each elapsed-season fraction."""
    available = sorted({value for value in available_dates if value < final_date})
    if not available:
        return ()
    span = (final_date - data_start_date).days
    targets = [data_start_date.toordinal() + round(span * float(f)) for f in fractions]
    selected = {
        min(available, key=lambda value: (abs(value.toordinal() - target), value))
        for target in targets
    }
    return tuple(sorted(selected))


def _bucket(value: Decimal) -> str:
    index = min(int(value * 10), 9)
    lower = Decimal(index) / 10
    upper = Decimal("1.00") if index == 9 else lower + Decimal("0.09")
    return f"{lower:.2f}-{upper:.2f}"


def _percentile(values, fraction: Decimal) -> Decimal:
    ordered = sorted(values)
    if len(ordered) == 1:
        return Decimal(ordered[0])
    position = Decimal(len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return Decimal(ordered[lower]) + (
        Decimal(ordered[upper] - ordered[lower]) * weight
    )


def _pct(count: int, total: int) -> Decimal:
    return (Decimal(count) * 100 / Decimal(total)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _summaries(values: list[int]) -> dict[str, Decimal]:
    total = len(values)
    return {
        "mae": (sum(Decimal(value) for value in values) / total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "median": _percentile(values, Decimal("0.50")).quantize(Decimal("0.01")),
        "p90": _percentile(values, Decimal("0.90")).quantize(Decimal("0.01")),
        "p95": _percentile(values, Decimal("0.95")).quantize(Decimal("0.01")),
        "within_3": _pct(sum(value <= 3 for value in values), total),
        "within_5": _pct(sum(value <= 5 for value in values), total),
        "within_10": _pct(sum(value <= 10 for value in values), total),
    }


def _bootstrap_intervals(
    errors_by_player: dict[str, list[int]], *, iterations: int, seed: int
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    players = tuple(sorted(errors_by_player))
    rng = random.Random(seed)
    p90_samples = []
    within_5_samples = []
    for _ in range(iterations):
        sampled_errors = []
        for _player in players:
            sampled_id = players[rng.randrange(len(players))]
            sampled_errors.extend(errors_by_player[sampled_id])
        p90_samples.append(_percentile(sampled_errors, Decimal("0.90")))
        within_5_samples.append(
            Decimal(sum(value <= 5 for value in sampled_errors))
            * 100
            / Decimal(len(sampled_errors))
        )
    return tuple(
        _percentile(samples, quantile).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        for samples, quantile in (
            (p90_samples, Decimal("0.025")),
            (p90_samples, Decimal("0.975")),
            (within_5_samples, Decimal("0.025")),
            (within_5_samples, Decimal("0.975")),
        )
    )


def audit_rating_stability(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    final_date: date,
    rating_model_version: str = "ratings-2.0",
    distribution_version: str = "dist-1.0",
    snapshot_dates: tuple[date, ...] | None = None,
    thresholds: tuple[Decimal, ...] = tuple(
        Decimal(value) for value in (
            "0.10", "0.20", "0.30", "0.40", "0.50",
            "0.60", "0.70", "0.80", "0.90", "0.95",
        )
    ),
    bootstrap_iterations: int = 1000,
    bootstrap_seed: int = 20260902,
) -> StabilityAudit:
    """Compare persisted earlier snapshots with the final persisted snapshot."""
    base_filters = (
        PlayerRatings.season == season,
        PlayerRatings.data_start_date == data_start_date,
        PlayerRatings.rating_model_version == rating_model_version,
        PlayerRatings.distribution_version == distribution_version,
    )
    finals = db.query(PlayerRatings).filter(
        *base_filters, PlayerRatings.data_end_date == final_date
    ).all()
    if not finals:
        raise ValueError("no final PlayerRatings snapshot matches the requested identity")

    earlier_query = db.query(PlayerRatings.data_end_date).filter(
        *base_filters, PlayerRatings.data_end_date < final_date
    ).distinct()
    available_dates = tuple(row[0] for row in earlier_query.all())
    selected_dates = snapshot_dates or select_fractional_snapshots(
        available_dates,
        data_start_date=data_start_date,
        final_date=final_date,
    )
    if not selected_dates:
        raise ValueError("no earlier PlayerRatings snapshots are available")
    unavailable = set(selected_dates) - set(available_dates)
    if unavailable:
        rendered = ", ".join(sorted(value.isoformat() for value in unavailable))
        raise ValueError(f"requested snapshots are unavailable: {rendered}")

    comparison_dates = tuple(sorted(set(selected_dates + (final_date,))))
    earlier = db.query(PlayerRatings).filter(
        *base_filters, PlayerRatings.data_end_date.in_(comparison_dates)
    ).all()
    by_identity_date = {
        (row.player_id, row.role, row.data_end_date): row for row in earlier
    }
    errors: dict[tuple[str, str, str, str], list[int]] = defaultdict(list)
    observations: dict[
        tuple[str, str, str], list[tuple[str, Decimal, int]]
    ] = defaultdict(list)
    matched = 0
    next_matched = 0
    next_date = {
        selected_dates[index]: comparison_dates[index + 1]
        for index in range(len(selected_dates))
    }
    for snapshot in earlier:
        if snapshot.data_end_date not in selected_dates:
            continue
        targets = (
            ("FINAL", by_identity_date.get(
                (snapshot.player_id, snapshot.role, final_date)
            )),
            ("NEXT", by_identity_date.get(
                (snapshot.player_id, snapshot.role, next_date[snapshot.data_end_date])
            )),
        )
        if targets[0][1] is not None:
            matched += 1
        if targets[1][1] is not None:
            next_matched += 1
        for comparison, target in targets:
            if target is None:
                continue
            for attribute in ROLE_ATTRIBUTES[snapshot.role]:
                evidence = getattr(snapshot, f"{attribute}_evidence")
                rating = getattr(snapshot, f"{attribute}_rating")
                target_rating = getattr(target, f"{attribute}_rating")
                if evidence is None or rating is None or target_rating is None:
                    continue
                error = abs(rating - target_rating)
                errors[(comparison, snapshot.role, attribute, _bucket(Decimal(evidence)))].append(error)
                observations[(comparison, snapshot.role, attribute)].append(
                    (snapshot.player_id, Decimal(evidence), error)
                )

    buckets = []
    for (comparison, role, attribute, evidence_bucket), values in sorted(errors.items()):
        total = len(values)
        summary = _summaries(values)
        buckets.append(StabilityBucket(
            comparison=comparison,
            role=role,
            attribute=attribute,
            evidence_bucket=evidence_bucket,
            observations=total,
            mae=summary["mae"],
            p50_error=summary["median"],
            p90_error=summary["p90"],
            within_3_pct=summary["within_3"],
            within_5_pct=summary["within_5"],
            within_10_pct=summary["within_10"],
        ))

    if bootstrap_iterations < 1:
        raise ValueError("bootstrap_iterations must be positive")
    threshold_rows = []
    for (comparison, role, attribute), attribute_observations in sorted(observations.items()):
        for threshold_index, threshold in enumerate(thresholds):
            eligible = [row for row in attribute_observations if row[1] >= threshold]
            if not eligible:
                continue
            errors_by_player = defaultdict(list)
            for player_id, _evidence, error in eligible:
                errors_by_player[player_id].append(error)
            values = [error for _player_id, _evidence, error in eligible]
            summary = _summaries(values)
            ci = _bootstrap_intervals(
                errors_by_player,
                iterations=bootstrap_iterations,
                seed=bootstrap_seed + threshold_index,
            )
            threshold_rows.append(StabilityThreshold(
                comparison=comparison,
                role=role,
                attribute=attribute,
                minimum_evidence=threshold,
                observations=len(values),
                players=len(errors_by_player),
                mae=summary["mae"],
                median_error=summary["median"],
                p90_error=summary["p90"],
                p95_error=summary["p95"],
                within_3_pct=summary["within_3"],
                within_5_pct=summary["within_5"],
                within_10_pct=summary["within_10"],
                p90_ci_low=ci[0],
                p90_ci_high=ci[1],
                within_5_ci_low=ci[2],
                within_5_ci_high=ci[3],
            ))
    return StabilityAudit(
        final_date=final_date,
        snapshot_dates=tuple(sorted(selected_dates)),
        final_players=len(finals),
        matched_player_snapshots=matched,
        next_matched_player_snapshots=next_matched,
        buckets=tuple(buckets),
        thresholds=tuple(threshold_rows),
    )


def power_tail_diagnostics(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    final_date: date,
    snapshot_dates: tuple[date, ...],
    minimum_evidence: Decimal = Decimal("0.90"),
    rating_model_version: str = "ratings-2.0",
    distribution_version: str = "dist-1.0",
    limit: int = 20,
) -> tuple[PowerTailDiagnostic, ...]:
    """Explain the largest high-evidence Power changes component by component."""
    rows = db.query(PlayerRatings).filter(
        PlayerRatings.season == season,
        PlayerRatings.role == "BATTER",
        PlayerRatings.rating_model_version == rating_model_version,
        PlayerRatings.distribution_version == distribution_version,
        PlayerRatings.data_start_date == data_start_date,
        PlayerRatings.data_end_date.in_(snapshot_dates + (final_date,)),
    ).all()
    finals = {
        row.player_id: row for row in rows if row.data_end_date == final_date
    }
    candidates = []
    for row in rows:
        final = finals.get(row.player_id)
        if (
            row.data_end_date == final_date
            or final is None
            or row.power_evidence is None
            or Decimal(row.power_evidence) < minimum_evidence
        ):
            continue
        candidates.append((abs(row.power_rating - final.power_rating), row, final))
    candidates.sort(key=lambda value: (-value[0], value[1].player_id, value[1].data_end_date))

    diagnostics = []
    for error, snapshot, final in candidates[:limit]:
        player = db.get(Player, snapshot.player_id)
        def stats_for(end_date):
            return db.query(BatterSeasonStats).join(
                PlayerSeason, PlayerSeason.id == BatterSeasonStats.player_season_id
            ).filter(
                PlayerSeason.player_id == snapshot.player_id,
                PlayerSeason.season == season,
                PlayerSeason.data_start_date == data_start_date,
                PlayerSeason.data_end_date == end_date,
            ).one()

        stats = stats_for(snapshot.data_end_date)
        final_stats = stats_for(final_date)
        calculation = calculate_batter_power(
            db,
            mlb_id=player.mlb_id,
            season=season,
            data_start_date=data_start_date,
            data_end_date=snapshot.data_end_date,
            distribution_version=distribution_version,
        )
        final_calculation = calculate_batter_power(
            db,
            mlb_id=player.mlb_id,
            season=season,
            data_start_date=data_start_date,
            data_end_date=final_date,
            distribution_version=distribution_version,
        )

        def component_diagnostics(calculation):
            return tuple(PowerComponentDiagnostic(
                metric=component.metric,
                observed=Decimal(str(component.observed)),
                sample_size=component.sample_size,
                stabilization=component.stabilization,
                evidence=Decimal(str(component.shrinkage_weight)).quantize(Decimal("0.00001")),
                adjusted=Decimal(str(component.adjusted)),
                percentile=Decimal(str(component.percentile)),
                rating=component.rating,
                component_weight=Decimal(str(component.component_weight)),
            ) for component in calculation.components)

        components = component_diagnostics(calculation)
        final_components = component_diagnostics(final_calculation)
        iso = None if stats.slg is None or stats.avg is None else stats.slg - stats.avg
        final_iso = (
            None if final_stats.slg is None or final_stats.avg is None
            else final_stats.slg - final_stats.avg
        )
        diagnostics.append(PowerTailDiagnostic(
            player_id=player.id,
            mlb_id=player.mlb_id,
            full_name=player.full_name,
            snapshot_date=snapshot.data_end_date,
            snapshot_rating=snapshot.power_rating,
            final_rating=final.power_rating,
            absolute_error=error,
            aggregate_evidence=Decimal(snapshot.power_evidence),
            plate_appearances=stats.pa,
            iso=iso,
            slg=stats.slg,
            barrel_opportunities=stats.barrel_opportunities,
            hard_hit_opportunities=stats.hard_hit_opportunities,
            components=components,
            final_plate_appearances=final_stats.pa,
            final_iso=final_iso,
            final_slg=final_stats.slg,
            final_barrel_opportunities=final_stats.barrel_opportunities,
            final_hard_hit_opportunities=final_stats.hard_hit_opportunities,
            final_components=final_components,
        ))
    return tuple(diagnostics)
