from __future__ import annotations

from typing import Any

from typesafe_i18n.runtime import I18n


class I18nExtension:
    """Jinja2 extension that adds a `t` function and `t` filter to templates.

    Usage:
        from jinja2 import Environment
        from typesafe_i18n.adapters.jinja2 import I18nExtension

        env = Environment(extensions=[I18nExtension])
        env.globals["i18n"] = I18n("translations", "en")

        # In templates:
        # {{ t("hello", name="World") }}
        # {{ "hello" | t(name="World") }}
    """

    def __init__(self, environment: Any) -> None:
        environment.globals["t"] = self._make_t(environment)
        environment.filters["t"] = self._make_filter(environment)

    def _make_t(self, environment: Any) -> Any:
        def t_func(key: str, **kwargs: Any) -> str:
            i18n: I18n = environment.globals.get("i18n")
            if i18n is None:
                return key
            return i18n.t(key, **kwargs)
        return t_func

    def _make_filter(self, environment: Any) -> Any:
        def t_filter(value: str, **kwargs: Any) -> str:
            i18n: I18n = environment.globals.get("i18n")
            if i18n is None:
                return value
            return i18n.t(value, **kwargs)
        return t_filter


def t_filter(value: str, i18n: I18n, **kwargs: Any) -> str:
    """Standalone t filter function for Jinja2 environments."""
    return i18n.t(value, **kwargs)
