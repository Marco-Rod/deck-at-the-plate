"""Utilidades de texto compartidas por el motor de nombres (plan V2.1 §63-§93)."""

import unicodedata

_ACCENTS = {
    ord("á"): "a", ord("é"): "e", ord("í"): "i", ord("ó"): "o", ord("ú"): "u",
    ord("ñ"): "n", ord("ü"): "u", ord("à"): "a", ord("è"): "e", ord("ì"): "i",
    ord("ò"): "o", ord("ù"): "u", ord("ä"): "a", ord("ë"): "e", ord("ï"): "i",
    ord("ö"): "o", ord("ü"): "u", ord("ä"): "a", ord("å"): "a", ord("ø"): "o",
    ord("ç"): "c", ord("š"): "s", ord("č"): "c", ord("ž"): "z", ord("đ"): "d",
}


def normalize(value: str) -> str:
    """Minúsculas, sin acentos, solo letras ascii y espacios."""
    value = value.lower().translate(_ACCENTS)
    return "".join(ch for ch in value if ch.isascii() and (ch.isalpha() or ch == " "))


def tokens(value: str) -> list[str]:
    return normalize(value).split()


def length_bucket(value: str, fallback: str = "MEDIUM") -> str:
    size = len(normalize(value))
    if size <= 4:
        return "SHORT"
    if size <= 7:
        return "MEDIUM"
    return "LONG"


def title_case(value: str) -> str:
    return " ".join(part[:1].upper() + part[1:] for part in value.split())