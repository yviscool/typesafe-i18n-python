from __future__ import annotations

from pathlib import Path
from typing import Any

from typesafe_i18n.runtime import I18n

_i18n_instances: dict[str, I18n] = {}
_translations_dir: Path = Path("translations")
_default_locale: str = "en"


def configure(
    translations_dir: str | Path = "translations",
    default_locale: str = "en",
) -> None:
    """Configure the global i18n settings for FastAPI."""
    global _translations_dir, _default_locale
    _translations_dir = Path(translations_dir)
    _default_locale = default_locale


def get_i18n(
    accept_language: str | None = None,
    locale: str | None = None,
) -> I18n:
    """FastAPI dependency that provides an I18n instance.

    Usage:
        from fastapi import Depends
        from typesafe_i18n.adapters.fastapi import get_i18n

        @app.get("/")
        async def index(i18n: I18n = Depends(get_i18n)):
            return {"message": i18n.t("hello", name="World")}
    """
    resolved_locale = locale or _detect_locale(accept_language) or _default_locale
    return _get_instance(resolved_locale)


def _detect_locale(accept_language: str | None) -> str | None:
    if not accept_language:
        return None
    parts = accept_language.split(",")
    for part in parts:
        lang = part.split(";")[0].split("-")[0].strip()
        if lang:
            return lang
    return None


def _get_instance(locale: str) -> I18n:
    if locale not in _i18n_instances:
        try:
            _i18n_instances[locale] = I18n(_translations_dir, locale)
        except FileNotFoundError:
            _i18n_instances[locale] = I18n(_translations_dir, _default_locale)
    return _i18n_instances[locale]


def t(key: str, **kwargs: Any) -> str:
    """Module-level translate function (requires prior configure() call)."""
    i18n = _get_instance(_default_locale)
    return i18n.t(key, **kwargs)
