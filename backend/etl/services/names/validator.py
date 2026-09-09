"""Validación de identidades candidatas (plan V2.1 §74, §77, §78).

CollisionValidator decide si un candidato es aceptable:
- ningún token en la blocklist (§77);
- el display completo no coincide con ningún nombre fuente del dataset (§78);
- el display completo no repite una identidad ya usada (§75).
El retry determinista vive en el generador (§70).
"""

from dataclasses import dataclass, field

from etl.services.names.text import normalize


@dataclass
class _TrieNode:
    children: dict = field(default_factory=dict)
    terminal: bool = False


def _build_trie(words: set[str]) -> _TrieNode:
    root = _TrieNode()
    for word in words:
        node = root
        for ch in word:
            node = node.children.setdefault(ch, _TrieNode())
        node.terminal = True
    return root


def contains_blocked(display: str, blocked: set[str]) -> bool:
    """Detecta subcadenas ofensivas sin importar separadores/acentos."""
    if not blocked:
        return False
    haystack = normalize(display).replace(" ", "")
    trie = _build_trie({normalize(w).replace(" ", "") for w in blocked if w})
    for start in range(len(haystack)):
        node = trie
        for end in range(start, len(haystack)):
            node = node.children.get(haystack[end])
            if node is None:
                break
            if node.terminal:
                return True
    return False


class CollisionValidator:
    def __init__(self, blocked: set[str] | None = None) -> None:
        self._blocked = set(blocked or ())

    def is_acceptable(
        self,
        display: str,
        *,
        used: set[str],
        source_names: set[str],
    ) -> bool:
        if contains_blocked(display, self._blocked):
            return False
        normalized_display = normalize(display)
        if normalized_display in {normalize(value) for value in used}:
            return False
        if normalized_display in source_names:
            return False
        if not display or not display.strip():
            return False
        return True
