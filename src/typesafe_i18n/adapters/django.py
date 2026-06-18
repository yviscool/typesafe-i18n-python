from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from typesafe_i18n.runtime import I18n


class DjangoI18nMiddleware:
    """Django middleware that provides i18n translations per request.

    Usage in settings.py:
        MIDDLEWARE = [
            'typesafe_i18n.adapters.django.DjangoI18nMiddleware',
            ...
        ]

    Access in views:
        from typesafe_i18n.adapters.django import t
        def my_view(request):
            return HttpResponse(t(request, "hello", name="World"))
    """

    def __init__(
        self,
        get_response: Callable[..., Any],
        translations_dir: str = "translations",
        default_locale: str = "en",
    ) -> None:
        self.get_response = get_response
        self.translations_dir = Path(translations_dir)
        self.default_locale = default_locale
        self._instances: dict[str, I18n] = {}

    def __call__(self, request: Any) -> Any:
        locale = self._get_locale(request)
        request.i18n = self._get_instance(locale)
        return self.get_response(request)

    def _get_locale(self, request: Any) -> str:
        lang: str | None = getattr(request, "LANGUAGE_CODE", None)
        if lang:
            return str(lang.split("-")[0].split("_")[0])

        accept: str = str(request.META.get("HTTP_ACCEPT_LANGUAGE", ""))
        if accept:
            return str(accept.split(",")[0].split("-")[0].split(";")[0])

        return self.default_locale

    def _get_instance(self, locale: str) -> I18n:
        if locale not in self._instances:
            try:
                self._instances[locale] = I18n(self.translations_dir, locale)
            except FileNotFoundError:
                self._instances[locale] = I18n(self.translations_dir, self.default_locale)
        return self._instances[locale]


def t(request: Any, key: str, **kwargs: Any) -> str:
    """Translate using the request's i18n instance."""
    i18n: I18n = request.i18n
    return i18n.t(key, **kwargs)
