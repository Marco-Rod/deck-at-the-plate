"""Generador determinista de nombres ficticios (plan V2.1 §63, §70, §71, §73).

Determinismo garantizado por seed estable sha256(player_id | version | intento),
nunca hash() nativo (no estable entre procesos). El intento permite retry
determinista ante colisión/bloqueado. Sin LLM ni APIs (§59).
"""

import hashlib
from dataclasses import dataclass

from etl.config import NAMES_MAX_ATTEMPTS, NAMES_PRESERVE_INITIALS
from etl.services.names.pools import NamePools
from etl.services.names.text import length_bucket, normalize, title_case
from etl.services.names.validator import CollisionValidator


@dataclass(frozen=True)
class GameIdentityName:
    first: str
    last: str
    display: str


def seed_for(player_id: str, generator_version: str, attempt: int) -> int:
    digest = hashlib.sha256(
        f"{player_id}|game-identity|{generator_version}|{attempt}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest, "big")


class FictionalNameGenerator:
    def __init__(
        self,
        pools: NamePools,
        validator: CollisionValidator | None = None,
        max_attempts: int = NAMES_MAX_ATTEMPTS,
        preserve_initials: float = NAMES_PRESERVE_INITIALS,
    ) -> None:
        self._pools = pools
        self._validator = validator or CollisionValidator(pools.blocked)
        self._max_attempts = max_attempts
        self._preserve_initials = preserve_initials

    def generate(
        self,
        *,
        player_id: str,
        generator_version: str,
        first: str,
        last: str,
        profile: str,
        used: set[str],
        source_names: set[str],
    ) -> GameIdentityName:
        pool = self._pools.pool_for(profile)
        given_bucket = length_bucket(first)
        family_bucket = length_bucket(last)

        for attempt in range(1, self._max_attempts + 1):
            digest = seed_for(player_id, generator_version, attempt)

            preserve = (digest >> 8) % 1000 / 1000.0 < self._preserve_initials
            given_cands = self._bucket_candidates(pool.given, given_bucket)
            if given_cands is None:
                given_cands = pool.given
            if preserve and first:
                letter = normalize(first)[:1]
                prefixed = [g for g in given_cands if g.startswith(letter)]
                if prefixed:
                    given_cands = prefixed

            family_cands = self._bucket_candidates(pool.family, family_bucket)
            if family_cands is None:
                family_cands = pool.family

            given_part = given_cands[digest % len(given_cands)]
            family_part = family_cands[(digest >> 32) % len(family_cands)]

            first_case = title_case(given_part)
            last_case = title_case(family_part)
            display = f"{first_case} {last_case}".strip()

            if self._validator.is_acceptable(
                display, used=used, source_names=source_names
            ):
                return GameIdentityName(first=first_case, last=last_case, display=display)

        # Los retries pseudoaleatorios son rápidos, pero una población grande
        # puede no encontrar en 20 intentos una combinación todavía libre. Antes
        # de usar el fallback, recorremos determinísticamente todo el pool.
        candidates = [
            (given, family)
            for given in pool.given
            for family in pool.family
        ]
        if candidates:
            start = seed_for(player_id, generator_version, 0) % len(candidates)
            for offset in range(len(candidates)):
                given_part, family_part = candidates[(start + offset) % len(candidates)]
                first_case = title_case(given_part)
                last_case = title_case(family_part)
                display = f"{first_case} {last_case}".strip()
                if self._validator.is_acceptable(
                    display, used=used, source_names=source_names
                ):
                    return GameIdentityName(
                        first=first_case,
                        last=last_case,
                        display=display,
                    )

        fallback = self._fallback(player_id, generator_version, used)
        return fallback

    @staticmethod
    def _bucket_candidates(candidates: list[str], bucket: str) -> list[str] | None:
        result = [c for c in candidates if length_bucket(c) == bucket]
        return result if result else None

    def _fallback(
        self, player_id: str, generator_version: str, used: set[str]
    ) -> GameIdentityName:
        base = seed_for(player_id, generator_version, 0)
        for offset in range(1000):
            display = f"Player {base % 100000:05d}" if offset == 0 else f"Player {(base + offset) % 100000:05d}"
            if display not in used:
                return GameIdentityName(first="Player", last=display.split()[-1], display=display)
        return GameIdentityName(first="Player", last="Universe", display="Player Universe")
