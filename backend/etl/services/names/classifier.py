"""Clasificador lingüístico determinista (plan V2.1 §66, §86, §87).

Asigna un perfil a partir de señales de apellido/nombre y patrones de sufijo.
Sin ML ni modelos: comparación de conjuntos + reglas de terminación. Devuelve
(profile, confidence); si la confianza < umbral cae a UNKNOWN y el generador usa
el pool neutral multiorigen.
"""

from etl.config import NAME_CLASSIFIER_THRESHOLD
from etl.services.names.pools import NamePools
from etl.services.names.profiles import NEUTRAL_PROFILES
from etl.services.names.text import normalize

# Sufijos típicos por origen (señales sin depender del pool).
_FAMILY_SUFFIX_RULES = {
    "SPANISH": ("ez",),
    "SLAVIC": ("ov", "ev", "iev", "och", "ich", "wicz", "enko", "yuk", "sky", "ski"),
    "FRENCH": ("eau", "ois", "oux"),
    "GERMANIC": ("mann", "berg", "burg", "brandt", "stien"),
}

_FAMILY_PREFIX_RULES = {
    "DUTCH": ("van", "van der", "de", "den", "het"),
}


class NameProfileClassifier:
    def __init__(
        self,
        pools: NamePools,
        threshold: float = NAME_CLASSIFIER_THRESHOLD,
    ) -> None:
        self._pools = pools
        self._threshold = threshold
        self._family_sets: dict[str, set[str]] = {}
        self._family_compact: dict[str, set[str]] = {}
        self._given_sets: dict[str, set[str]] = {}
        for pool_name, pool in pools.pools.items():
            if pool_name in NEUTRAL_PROFILES:
                continue
            self._family_sets[pool_name] = set(pool.family)
            self._family_compact[pool_name] = {f.replace(" ", "") for f in pool.family}
            self._given_sets[pool_name] = set(pool.given)

    def classify(self, *, first: str, last: str) -> tuple[str, float]:
        given_tokens = normalize(first).split()
        family_tokens = normalize(last).split()
        family_full = normalize(last).replace(" ", "")

        scores: dict[str, float] = {}
        for name in self._family_sets:
            score = 0.0

            surname_hits = sum(1 for token in family_tokens if token in self._family_sets[name])
            if family_full and family_full in self._family_compact[name]:
                surname_hits += 1
            score += min(surname_hits, 2) * 2.0

            given_hits = sum(1 for token in given_tokens if token in self._given_sets[name])
            score += min(given_hits, 2) * 0.7

            for token in family_tokens:
                if any(
                    token.endswith(suffix) and len(token) > len(suffix)
                    for suffix in _FAMILY_SUFFIX_RULES.get(name, ())
                ):
                    score += 0.8
                if any(token.startswith(prefix) for prefix in _FAMILY_PREFIX_RULES.get(name, ())):
                    score += 0.8
            scores[name] = round(score, 4)

        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        top_name, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0

        threshold_score = self._conf_to_score(self._threshold)
        if top_score < threshold_score:
            return "UNKNOWN", self._score_to_conf(top_score)
        if second_score >= max(threshold_score, top_score * 0.75):
            return "MULTI_ORIGIN", self._score_to_conf(top_score)
        return top_name.upper(), self._score_to_conf(top_score)

    @staticmethod
    def _conf_to_score(conf: float) -> float:
        # conf = 1 - 1/(1+score)  =>  score = conf/(1-conf)
        if conf >= 1.0:
            return 1e9
        return conf / (1.0 - conf)

    @staticmethod
    def _score_to_conf(score: float) -> float:
        return round(score / (1.0 + score), 4)