from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from typesafe_i18n.detectors import (
    detect_locale,
    init_accept_language_header_detector,
    init_cookie_detector,
)
from typesafe_i18n.runtime import I18n


class TypesafeI18nMiddleware:
    def __init__(
        self,
        get_response: Callable[..., Any],
        translations_dir: str | Path = "translations",
        default_locale: str = "en",
        available_locales: list[str] | None = None,
    ) -> None:
        self.get_response = get_response
        self.translations_dir = Path(translations_dir)
        self.default_locale = default_locale
        self.available_locales = available_locales or [default_locale]
        self._instances: dict[str, I18n] = {}

    def __call__(self, request: Any) -> Any:
        locale = self._detect_locale(request)
        request.i18n = self._get_instance(locale)
        request._i18n_locale = locale
        return self.get_response(request)

    def _detect_locale(self, request: Any) -> str:
        accept_language = request.META.get("HTTP_ACCEPT_LANGUAGE", "")
        cookie_header = request.META.get("HTTP_COOKIE", "")

        detectors = [
            init_accept_language_header_detector(accept_language),
            init_cookie_detector(cookie_header),
        ]

        return detect_locale(self.default_locale, self.available_locales, *detectors)

    def _get_instance(self, locale: str) -> I18n:
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


def get_i18n(request: Any) -> I18n:
    i18n: I18n | None = getattr(request, "i18n", None)
    if i18n is None:
        raise RuntimeError(
            "I18n instance not found on request. "
            "Add 'typesafe_i18n.contrib.django.TypesafeI18nMiddleware' to MIDDLEWARE."
        )
    return i18n


def t(request: Any, key: str, **kwargs: Any) -> str:
    return get_i18n(request).t(key, **kwargs)
