"""Base eligibility: capa de decisión sobre evidencia (sin efectos en ratings).

base-evidence-1.0 DESCRIBE lo medido por atributo (PASS/BELOW_THRESHOLD/
UNCALIBRATED/VOLATILE/NOT_APPLICABLE). La eligibilidad es la DECISIÓN:
qué jugadores pasan al pool jugable de BASE. Esta capa está versionada para que
una futura calibración de control/stuff/power corra la versión de la política y
cambie el mapeo sin tocar la descripción de evidencia.

Regla v1 ("base-eligibility-1.0"), candidata y medible, NO activada en la
publicación todavía:

    INELIGIBLE   -> algún atributo CALIBRADO del rol con BELOW_THRESHOLD
                    (contacto/visión para bateadores; velocidad/movimiento
                    para lanzadores).
    PROVISIONAL  -> no ineligible, pero el rol arrastra señales de calibración
                    pendiente (power VOLATILE, control/stuff UNCALIBRATED).
                    clutch NOT_APPLICABLE NO es señal: baseline neutral sin
                    requisito de evidencia.
    ELIGIBLE     -> todos los atributos calibrados PASAN y no hay señales.

Con base-evidence-1.0 esto significa: hoy ningún jugador puede ser ELIGIBLE
porque power/control/stuff aún no están calibrados; la auditoría dry-run mide
el impacto real de esa frontera antes de inventar reglas duras.
"""

from dataclasses import dataclass

from app.models import PlayerRatings
from etl.services.base_evidence_policy import (
    BASE_EVIDENCE_POLICY_VERSION,
    CALIBRATED_THRESHOLDS,
    ROLE_ATTRIBUTES,
    BaseEvidenceAssessment,
    assess_base_evidence,
)


BASE_ELIGIBILITY_POLICY_VERSION = "base-eligibility-1.0"

ELIGIBLE = "ELIGIBLE"
PROVISIONAL = "PROVISIONAL"
INELIGIBLE = "INELIGIBLE"

# Solo estos statuses cuentan como señal de provisionalidad (clutch queda fuera:
# su NOT_APPLICABLE es baseline neutral, no una deuda de calibración).
_PROVISIONAL_SIGNALS = ("UNCALIBRATED", "VOLATILE")


@dataclass(frozen=True)
class BaseEligibilityAssessment:
    policy_version: str
    decision: str
    reasons: tuple[str, ...]
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
    role_attributes = ROLE_ATTRIBUTES[role.upper()]
    mandatory = [
        attribute
        for attribute in role_attributes
        if attribute in CALIBRATED_THRESHOLDS
    ]
    reasons: list[str] = []

    below = [
        attribute
        for attribute in mandatory
        if evidence.attributes[attribute].status == "BELOW_THRESHOLD"
    ]
    if below:
        reasons.append(f"evidencia insuficiente en: {', '.join(sorted(below))}")
        return BaseEligibilityAssessment(
            policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            decision=INELIGIBLE,
            reasons=tuple(reasons),
            evidence=evidence,
        )

    signals = [
        attribute
        for attribute in role_attributes
        if evidence.attributes[attribute].status in _PROVISIONAL_SIGNALS
    ]
    if signals:
        reasons.append(
            f"señales de calibración pendiente: {', '.join(sorted(signals))}"
        )
        return BaseEligibilityAssessment(
            policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
            decision=PROVISIONAL,
            reasons=tuple(reasons),
            evidence=evidence,
        )
    return BaseEligibilityAssessment(
        policy_version=BASE_ELIGIBILITY_POLICY_VERSION,
        decision=ELIGIBLE,
        reasons=(),
        evidence=evidence,
    )