from __future__ import annotations

from pathlib import Path
from typesafe_i18n.runtime import I18n as _I18n

_instance: _I18n | None = None


def init(translations_dir: str | Path, locale: str) -> None:
    """Initialize the global i18n instance."""
    global _instance
    _instance = _I18n(translations_dir, locale)


def t(key: str, **kwargs: object) -> str:
    """Translate a key using the global i18n instance."""
    if _instance is None:
        raise RuntimeError("Call init() first")
    return _instance.t(key, **kwargs)


def set_locale(locale: str) -> None:
    """Switch the global i18n instance to a different locale."""
    if _instance is None:
        raise RuntimeError("Call init() first")
    _instance.set_locale(locale)
