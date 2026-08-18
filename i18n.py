"""Tiny JSON-based i18n. Language: auto | en | pl | de."""

from __future__ import annotations

import json
import locale
from pathlib import Path

LOCALES_DIR = Path(__file__).resolve().parent / "locales"
SUPPORTED = ("en", "pl", "de")


def detect_language() -> str:
    for src in (locale.getlocale()[0], locale.getdefaultlocale()[0]):
        if not src:
            continue
        code = src.replace("-", "_").split("_", 1)[0].lower()
        if code in SUPPORTED:
            return code
    return "en"


def resolve_language(requested: str | None) -> str:
    req = (requested or "auto").strip().lower()
    if req in ("auto", ""):
        return detect_language()
    return req if req in SUPPORTED else "en"


class I18n:
    def __init__(self, language: str = "auto") -> None:
        self._cache: dict[str, dict[str, str]] = {}
        self.language = resolve_language(language)

    def set_language(self, language: str) -> str:
        self.language = resolve_language(language)
        return self.language

    def _load(self, lang: str) -> dict[str, str]:
        if lang not in self._cache:
            path = LOCALES_DIR / f"{lang}.json"
            self._cache[lang] = json.loads(path.read_text(encoding="utf-8"))
        return self._cache[lang]

    def t(self, key: str, **kwargs) -> str:
        table = self._load(self.language)
        if key not in table and self.language != "en":
            table = self._load("en")
        text = table.get(key, key)
        return text.format(**kwargs) if kwargs else text


_i18n: I18n | None = None


def get_i18n(language: str | None = None) -> I18n:
    global _i18n
    if _i18n is None or language is not None:
        _i18n = I18n(language or "auto")
    return _i18n
