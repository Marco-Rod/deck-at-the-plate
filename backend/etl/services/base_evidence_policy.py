"""Evidence assessment for BASE cards, without eligibility side effects."""

from dataclasses import asdict, dataclass
from decimal import Decimal

from app.models import PlayerRatings


BASE_EVIDENCE_POLICY_VERSION = "base-evidence-1.0"
UNRESOLVED_ELIGIBILITY = "UNRESOLVED"

CALIBRATED_THRESHOLDS = {
    "contact": Decimal("0.90000"),
    "vision": Decimal("0.90000"),
    "velocity": Decimal("0.50000"),
    "movement": Decimal("0.40000"),
}
UNCALIBRATED_ATTRIBUTES = {"control", "stuff"}
VOLATILE_ATTRIBUTES = {"power"}
ROLE_ATTRIBUTES = {
    "BATTER": ("contact", "power", "vision", "clutch"),
    "PITCHER": ("velocity", "control", "movement", "stuff"),
}
CALIBRATION_NOTES = {
    "control": "candidate >= 0.70; bootstrap confidence interval crosses the stability gate",
    "stuff": "candidate >= 0.80; bootstrap confidence interval crosses the stability gate",
    "power": "material temporal drift remains after evidence reaches 0.90",
    "clutch": "neutral baseline without an evidence estimate",
}


@dataclass(frozen=True)
class AttributeEvidenceAssessment:
    status: str
    evidence: Decimal | None
    threshold: Decimal | None = None
    calibration_note: str | None = None


@dataclass(frozen=True)
class BaseEvidenceAssessment:
    policy_version: str
    attributes: dict[str, AttributeEvidenceAssessment]
    eligibility: str

    def as_dict(self) -> dict:
        return asdict(self)


def assess_base_evidence(*, role: str, player_ratings: PlayerRatings) -> BaseEvidenceAssessment:
    """Describe available evidence without changing ratings or deciding eligibility."""
    normalized_role = role.upper()
    if normalized_role not in ROLE_ATTRIBUTES:
        raise ValueError(f"unsupported role: {role}")
    if player_ratings.role != normalized_role:
        raise ValueError("role does not match PlayerRatings")

    attributes = {}
    for attribute in ROLE_ATTRIBUTES[normalized_role]:
        value = getattr(player_ratings, f"{attribute}_evidence")
        evidence = Decimal(value) if value is not None else None
        if attribute in CALIBRATED_THRESHOLDS:
            threshold = CALIBRATED_THRESHOLDS[attribute]
            status = "PASS" if evidence is not None and evidence >= threshold else "BELOW_THRESHOLD"
            attributes[attribute] = AttributeEvidenceAssessment(
                status=status,
                evidence=evidence,
                threshold=threshold,
            )
        elif attribute in UNCALIBRATED_ATTRIBUTES:
            attributes[attribute] = AttributeEvidenceAssessment(
                status="UNCALIBRATED",
                evidence=evidence,
                calibration_note=CALIBRATION_NOTES[attribute],
            )
        elif attribute in VOLATILE_ATTRIBUTES:
            attributes[attribute] = AttributeEvidenceAssessment(
                status="VOLATILE",
                evidence=evidence,
                calibration_note=CALIBRATION_NOTES[attribute],
            )
        else:
            attributes[attribute] = AttributeEvidenceAssessment(
                status="NOT_APPLICABLE",
                evidence=evidence,
                calibration_note=CALIBRATION_NOTES[attribute],
            )
    return BaseEvidenceAssessment(
        policy_version=BASE_EVIDENCE_POLICY_VERSION,
        attributes=attributes,
        eligibility=UNRESOLVED_ELIGIBILITY,
    )
