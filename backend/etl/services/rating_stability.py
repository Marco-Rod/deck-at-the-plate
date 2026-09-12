"""Read-only calibration of evidence against later rating stability."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import PlayerRatings


ROLE_ATTRIBUTES = {
    "BATTER": ("contact", "power", "vision"),
    "PITCHER": ("velocity", "control", "movement", "stuff"),
}


@dataclass(frozen=True)
class StabilityBucket:
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
class StabilityAudit:
    final_date: date
    snapshot_dates: tuple[date, ...]
    final_players: int
    matched_player_snapshots: int
    buckets: tuple[StabilityBucket, ...]


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


def _percentile(values: list[int], fraction: Decimal) -> Decimal:
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


def audit_rating_stability(
    db: Session,
    *,
    season: int,
    data_start_date: date,
    final_date: date,
    rating_model_version: str = "ratings-2.0",
    distribution_version: str = "dist-1.0",
    snapshot_dates: tuple[date, ...] | None = None,
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

    earlier = db.query(PlayerRatings).filter(
        *base_filters, PlayerRatings.data_end_date.in_(selected_dates)
    ).all()
    final_by_identity = {(row.player_id, row.role): row for row in finals}
    errors: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    matched = 0
    for snapshot in earlier:
        final = final_by_identity.get((snapshot.player_id, snapshot.role))
        if final is None:
            continue
        matched += 1
        for attribute in ROLE_ATTRIBUTES[snapshot.role]:
            evidence = getattr(snapshot, f"{attribute}_evidence")
            rating = getattr(snapshot, f"{attribute}_rating")
            final_rating = getattr(final, f"{attribute}_rating")
            if evidence is None or rating is None or final_rating is None:
                continue
            errors[(snapshot.role, attribute, _bucket(Decimal(evidence)))].append(
                abs(rating - final_rating)
            )

    buckets = []
    for (role, attribute, evidence_bucket), values in sorted(errors.items()):
        total = len(values)
        mae = (sum(Decimal(value) for value in values) / total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        buckets.append(StabilityBucket(
            role=role,
            attribute=attribute,
            evidence_bucket=evidence_bucket,
            observations=total,
            mae=mae,
            p50_error=_percentile(values, Decimal("0.50")).quantize(Decimal("0.01")),
            p90_error=_percentile(values, Decimal("0.90")).quantize(Decimal("0.01")),
            within_3_pct=_pct(sum(value <= 3 for value in values), total),
            within_5_pct=_pct(sum(value <= 5 for value in values), total),
            within_10_pct=_pct(sum(value <= 10 for value in values), total),
        ))
    return StabilityAudit(
        final_date=final_date,
        snapshot_dates=tuple(sorted(selected_dates)),
        final_players=len(finals),
        matched_player_snapshots=matched,
        buckets=tuple(buckets),
    )
