from __future__ import annotations

from pathlib import Path
from typing import Any

from typesafe_i18n.detectors import (
    detect_locale,
    init_accept_language_header_detector,
    init_cookie_detector,
    init_query_string_detector,
)
from typesafe_i18n.runtime import I18n


class I18nConfig:
    def __init__(
        self,
        translations_dir: str | Path = "translations",
        default_locale: str = "en",
        available_locales: list[str] | None = None,
    ) -> None:
        self.translations_dir = Path(translations_dir)
        self.default_locale = default_locale
        self.available_locales = available_locales or [default_locale]
        self._instances: dict[str, I18n] = {}

    def get_instance(self, locale: str) -> I18n:
        if locale not in self._instances:
            try:
                self._instances[locale] = I18n(self.translations_dir, locale)
            except FileNotFoundError:
                if self.default_locale not in self._instances:
                    self._instances[self.default_locale] = I18n(
                        self.translations_dir, self.default_locale
                    )
                self._instances[locale] = self._instances[self.default_locale]
        return self._instances[locale]

    def detect_locale(
        self,
        accept_language: str | None = None,
        cookie: str | None = None,
        query_string: str | None = None,
    ) -> str:
        detectors = []
        if accept_language:
            detectors.append(init_accept_language_header_detector(accept_language))
        if cookie:
            detectors.append(init_cookie_detector(cookie))
        if query_string:
            detectors.append(init_query_string_detector(query_string))
        return detect_locale(self.default_locale, self.available_locales, *detectors)


_config: I18nConfig | None = None


def configure(
    translations_dir: str | Path = "translations",
    default_locale: str = "en",
    available_locales: list[str] | None = None,
) -> I18nConfig:
    global _config
    _config = I18nConfig(translations_dir, default_locale, available_locales)
    return _config


def _get_config() -> I18nConfig:
    global _config
    if _config is None:
        _config = I18nConfig()
    return _config


class TypesafeI18nMiddleware:
    def __init__(self, app: Any, config: I18nConfig | None = None) -> None:
        self.app = app
        self.config = config or _get_config()

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        accept_language_raw = headers.get(b"accept-language", b"").decode("utf-8", errors="replace")
        cookie_raw = headers.get(b"cookie", b"").decode("utf-8", errors="replace")
        query_string_raw = scope.get("query_string", b"").decode("utf-8", errors="replace")

        locale = self.config.detect_locale(
            accept_language=accept_language_raw or None,
            cookie=cookie_raw or None,
            query_string=query_string_raw or None,
        )

        i18n = self.config.get_instance(locale)
        scope["i18n"] = i18n
        scope["i18n_locale"] = locale

        await self.app(scope, receive, send)


def get_i18n(
    accept_language: str | None = None,
    cookie: str | None = None,
    locale: str | None = None,
) -> I18n:
    config = _get_config()
    if locale:
        resolved = locale
    else:
        resolved = config.detect_locale(
            accept_language=accept_language,
            cookie=cookie,
        )
    return config.get_instance(resolved)


async def _get_i18n_dependency(
    accept_language: str | None = None,
    cookie: str | None = None,
) -> I18n:
    return get_i18n(accept_language=accept_language, cookie=cookie)


def create_dependency() -> Any:
    try:
        from fastapi import Header, Cookie

        async def i18n_dependency(
            accept_language: str | None = Header(default=None),
            i18n_locale: str | None = Cookie(default=None),
        ) -> I18n:
            return get_i18n(accept_language=accept_language, locale=i18n_locale)

        return i18n_dependency
    except ImportError:
        return _get_i18n_dependency


def t(key: str, **kwargs: Any) -> str:
    config = _get_config()
    i18n = config.get_instance(config.default_locale)
    return i18n.t(key, **kwargs)
