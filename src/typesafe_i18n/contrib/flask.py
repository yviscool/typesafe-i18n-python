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


class TypesafeI18n:
    def __init__(
        self,
        app: Any = None,
        translations_dir: str | Path = "translations",
        default_locale: str = "en",
        available_locales: list[str] | None = None,
    ) -> None:
        self.translations_dir = Path(translations_dir)
        self.default_locale = default_locale
        self.available_locales = available_locales or [default_locale]
        self._instances: dict[str, I18n] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        self.translations_dir = Path(
            app.config.get("I18N_TRANSLATIONS_DIR", str(self.translations_dir))
        )
        self.default_locale = app.config.get("I18N_DEFAULT_LOCALE", self.default_locale)
        self.available_locales = app.config.get("I18N_AVAILABLE_LOCALES", self.available_locales)
        app.extensions["typesafe_i18n"] = self
        app.before_request(self._set_locale)
        app.context_processor(self._inject_context)

    def _set_locale(self) -> None:
        from flask import g, request

        accept_language = request.headers.get("Accept-Language", "")
        cookie_header = request.headers.get("Cookie", "")
        query_string = request.query_string.decode("utf-8", errors="replace")

        detectors = [
            init_accept_language_header_detector(accept_language),
            init_cookie_detector(cookie_header),
            init_query_string_detector(query_string),
        ]

        locale = detect_locale(self.default_locale, self.available_locales, *detectors)
        g.i18n_locale = locale
        g.i18n = self._get_instance(locale)

    def _inject_context(self) -> dict[str, Any]:
        from flask import g

        i18n: I18n = g.i18n
        return {"i18n": i18n, "t": i18n.t}

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

    def get_i18n(self, locale: str | None = None) -> I18n:
        if locale is not None:
            return self._get_instance(locale)
        from flask import g
        i18n: I18n | None = getattr(g, "i18n", None)
        if i18n is None:
            return self._get_instance(self.default_locale)
        return i18n


def t(key: str, **kwargs: Any) -> str:
    from flask import current_app, g

    _ = current_app.extensions["typesafe_i18n"]
    i18n: I18n = g.i18n
    return i18n.t(key, **kwargs)
