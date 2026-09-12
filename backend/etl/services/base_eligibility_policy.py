"""Base eligibility: capa de decisión sobre evidencia (sin efectos en ratings).

base-evidence-1.0 DESCRIBE lo medido por atributo (PASS/BELOW_THRESHOLD/
UNCALIBRATED/VOLATILE/NOT_APPLICABLE). La eligibilidad es la DECISIÓN: qué
jugadores pasan al pool jugable de BASE. Está versionada para que una futura
calibración de control/stuff/power cambie el mapeo sin tocar la descripción.

base-eligibility-1.1 separa DOS fronteras distintas (medidas y validadas por
auditoría dry-run sobre las 829 cartas):

    CALIBRATED_THRESHOLDS        >= robustez temporal para llamarlo PASS
                                 (contact/vision .90, velocity .50,
                                  movement .40) — sin cambios en 1.1.
    MINIMUM_BASE_EVIDENCE        <   muestra mínima para que la carta BASE
                                 exista; evidencia por debajo es demasiado
                                 poca para representar una temporada.

Eligibility NO reinterpreta los statuses de base-evidence-1.0: consume el
status Y el valor de evidencia. Un atributo puede ser BELOW_THRESHOLD y el
jugador PROVISIONAL (evidencia sustancial pero sin estabilidad calibrada).

Precedencia global:
    INELIGIBLE  -> algún atributo calibrado del rol con evidencia None o
                   debajo de MINIMUM_BASE_EVIDENCE (exclusión conservadora
                   y visible; decisión INSUFFICIENT_EVIDENCE).
    PROVISIONAL -> si no, alguna señal de calibración pendiente: atributo
                   calibrado BELOW_THRESHOLD, power VOLATILE o
                   control/stuff UNCALIBRATED. clutch NOT_APPLICABLE es
                   neutral (baseline sin requisito de evidencia).
    ELIGIBLE    -> todo PASS/N/A.

Con base-evidence-1.0 ELIGIBLE sigue siendo inalcanzable hoy (power/control/
stuff sin calibrar): *decide_base_eligibility* permite verificar el contrato
inyectando un assessment completo.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models import PlayerRatings
from etl.services.base_evidence_policy import (
    BASE_EVIDENCE_POLICY_VERSION,
    CALIBRATED_THRESHOLDS,
    ROLE_ATTRIBUTES,
    BaseEvidenceAssessment,
    assess_base_evidence,
)


BASE_ELIGIBILITY_POLICY_VERSION = "base-eligibility-1.1"

ELIGIBLE = "ELIGIBLE"
PROVISIONAL = "PROVISIONAL"
INELIGIBLE = "INELIGIBLE"

# Frontera de suficiencia mínima de muestra (ver docstring): por debajo, una
# carta BASE no debería existir todavía. Independiente y distinta de la
# calibración temporal.
MINIMUM_BASE_EVIDENCE = {
    "contact": Decimal("0.25"),
    "vision": Decimal("0.25"),
    "velocity": Decimal("0.25"),
    "movement": Decimal("0.25"),
}

# Sub-decisión documentada para razones de exclusión.
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"

# Señales de provisionalidad (clutch NOT_APPLICABLE queda fuera: es baseline
# neutral, no una deuda de calibración).
_PROVISIONAL_STATUS_SIGNALS = ("VOLATILE", "UNCALIBRATED")


@dataclass(frozen=True)
class BaseEligibilityAssessment:
    policy_version: str
    decision: str
    reasons: tuple[dict, ...]
    evidence: BaseEvidenceAssessment

    def as_dict(self) -> dict:
        return {
            "policy_version": self.policy_version,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "evidence": self.evidence.as_dict(),
        }


def assess_base_eligibility(
    *, role: str, player_ratings: PlayerRatings
) -> BaseEligibilityAssessment:
    """Decide eligibilidad de BASE a partir de la evidencia del jugador."""
    evidence = assess_base_evidence(role=role, player_ratings=player_ratings)
    return decide_base_eligibility(role=role, evidence=evidence)


def decide_base_eligibility(
    *, role: str, evidence: BaseEvidenceAssessment
) -> BaseEligibilityAssessment:
    """Decisión pura sobre un assessment de evidencia (inyectable para tests)."""
    normalized_role = role.upper()
    if normalized_role not in ROLE_ATTRIBUTES:
        raise ValueError(f"unsupported role: {role}")
    role_attributes = ROLE_ATTRIBUTES[normalized_role]
    mandatory = [
        attribute
        for attribute in role_attributes
        if attribute in CALIBRATED_THRESHOLDS
    ]

    insufficient = []
    for attribute in mandatory:
        item = evidence.attributes[attribute]
        if item.evidence is None or item.evidence < MINIMUM_BASE_EVIDENCE[attribute]:
            insufficient.append({
                "attribute": attribute,
                "assessment": item.status,
                "evidence": str(item.evidence) if item.evidence is not None else None,
                "minimum_evidence": str(MINIMUM_BASE_EVIDENCE[attribute]),
                "calibrated_threshold": str(item.threshold) if item.threshold is not None else None,
                "decision": INSUFFICIENT_EVIDENCE,
            })
    if insufficient:
        return BaseEligibilityAssessment(
            policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            decision=INELIGIBLE,
            reasons=tuple(insufficient),
            evidence=evidence,
        )

    signals = []
    for attribute in role_attributes:
        item = evidence.attributes[attribute]
        if item.status == "BELOW_THRESHOLD":
            signals.append({
                "attribute": attribute,
                "assessment": item.status,
                "evidence": str(item.evidence) if item.evidence is not None else None,
                "minimum_evidence": str(MINIMUM_BASE_EVIDENCE.get(attribute, "")),
                "calibrated_threshold": str(item.threshold) if item.threshold is not None else None,
            })
        elif item.status in _PROVISIONAL_STATUS_SIGNALS:
            signals.append({"attribute": attribute, "assessment": item.status})
    if signals:
        return BaseEligibilityAssessment(
            policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            decision=PROVISIONAL,
            reasons=tuple(signals),
            evidence=evidence,
        )
    return BaseEligibilityAssessment(
        policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
        decision=ELIGIBLE,
        reasons=(),
        evidence=evidence,
    )