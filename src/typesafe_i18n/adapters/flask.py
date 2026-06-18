from __future__ import annotations

from pathlib import Path
from typing import Any

from typesafe_i18n.runtime import I18n


class FlaskI18n:
    """Flask extension for typesafe-i18n.

    Usage:
        from flask import Flask
        from typesafe_i18n.adapters.flask import FlaskI18n

        app = Flask(__name__)
        i18n = FlaskI18n(app, translations_dir="translations")

        @app.route("/")
        def index():
            return i18n.t("hello", name="World")
    """

    def __init__(
        self,
        app: Any = None,
        translations_dir: str = "translations",
        default_locale: str = "en",
    ) -> None:
        self.translations_dir = Path(translations_dir)
        self.default_locale = default_locale
        self._instances: dict[str, I18n] = {}
        if app is not None:
            self.init_app(app)

    def init_app(self, app: Any) -> None:
        self.translations_dir = Path(
            app.config.get("I18N_TRANSLATIONS_DIR", str(self.translations_dir))
        )
        self.default_locale = app.config.get("I18N_DEFAULT_LOCALE", self.default_locale)
        app.extensions["i18n"] = self
        app.context_processor(self._inject)

    def _inject(self) -> dict[str, Any]:
        from flask import g, request

        locale = self._detect_locale(request)
        i18n = self._get_instance(locale)
        g.i18n = i18n
        return {"i18n": i18n, "t": i18n.t}

    def _detect_locale(self, request: Any) -> str:
        lang: str | None = request.args.get("lang")
        if lang:
            return str(lang)

        best: str | None = request.accept_languages.best_match(["en", "zh", "de", "fr", "es", "ja", "ko"])
        if best:
            return str(best)

        return self.default_locale

    def _get_instance(self, locale: str) -> I18n:
        if locale not in self._instances:
            try:
                self._instances[locale] = I18n(self.translations_dir, locale)
            except FileNotFoundError:
                self._instances[locale] = I18n(self.translations_dir, self.default_locale)
        return self._instances[locale]

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate using the current request context."""
        from flask import g

        i18n: I18n = g.i18n
        return i18n.t(key, **kwargs)


def t(key: str, **kwargs: Any) -> str:
    """Module-level translate function for Flask."""
    from flask import current_app

    ext: FlaskI18n = current_app.extensions["i18n"]
    return ext.t(key, **kwargs)
