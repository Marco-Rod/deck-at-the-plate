"""Carga de pools versionados de nombres + blocklist (plan V2.1 §69, §77).

Recursos offline en etl/resources/names/<pool>/{given,family}.txt:
una línea por nombre en minúsculas. La blocklist vive en blocked_names.txt.
La versión del conjunto se declara en profiles.yaml (generator_version).
"""

import logging
import yaml
from dataclasses import dataclass, field
from pathlib import Path

from etl.services.names.profiles import NAME_PROFILE_POOLS

logger = logging.getLogger("etl.services.names.pools")

_RESOURCE_DIR = Path(__file__).resolve().parents[2] / "resources" / "names"

_DEFAULT_GENERATOR_VERSION = "names-1.0"


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    out = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip().lower()
        if value and not value.startswith("#"):
            out.append(value)
    return out


@dataclass
class NamePool:
    given: list[str] = field(default_factory=list)
    family: list[str] = field(default_factory=list)


class NamePools:
    """Registro global de pools y perfiles resueltos."""

    def __init__(self, resource_dir: Path = _RESOURCE_DIR) -> None:
        self._resource_dir = resource_dir
        self._pools: dict[str, NamePool] = {}
        self._blocked: set[str] = set()
        self._generator_version = _DEFAULT_GENERATOR_VERSION
        self._profiles = dict(NAME_PROFILE_POOLS)
        self._load()

    def _load(self) -> None:
        for pool in NAME_PROFILE_POOLS.values():
            base = self._resource_dir / pool
            self._pools[pool] = NamePool(
                given=_read_lines(base / "given.txt"),
                family=_read_lines(base / "family.txt"),
            )
        self._blocked.update(_read_lines(self._resource_dir / "blocked_names.txt"))

        meta = self._resource_dir / "profiles.yaml"
        if meta.exists():
            try:
                data = yaml.safe_load(meta.read_text(encoding="utf-8")) or {}
                version = data.get("generator_version")
                if version:
                    self._generator_version = str(version)
            except yaml.YAMLError:
                logger.warning("profiles.yaml inválido; uso defaults")

    @property
    def generator_version(self) -> str:
        return self._generator_version

    @property
    def blocked(self) -> set[str]:
        return self._blocked

    def pool_for(self, profile: str) -> NamePool:
        pool_name = self._profiles.get(profile, self._profiles["UNKNOWN"])
        return self._pools[pool_name]

    def given_for(self, profile: str) -> list[str]:
        return self.pool_for(profile).given

    def family_for(self, profile: str) -> list[str]:
        return self.pool_for(profile).family

    @property
    def pools(self) -> dict[str, NamePool]:
        return dict(self._pools)