from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

from typesafe_i18n.backends import TranslationBackend, YAMLBackend, get_backend_for_file
from typesafe_i18n.parser import ArgPart, PluralPart, TextPart, parse_translation
from typesafe_i18n.plural import get_plural_form


class I18n:
    """Internationalization runtime with type-safe translations.

    Thread-safe. Supports YAML, JSON, and TOML translation files.
    Uses LRU caching for parsed templates.
    """

    def __init__(
        self,
        translations_dir: str | Path,
        locale: str,
        cache_size: int = 256,
        backend: TranslationBackend | None = None,
    ) -> None:
        self._translations_dir = Path(translations_dir)
        self._locale = locale
        self._cache_size = cache_size
        self._backend = backend or YAMLBackend()
        self._lock = threading.Lock()
        self._translations: dict[str, Any] = {}
        self._cache: OrderedDict[str, list[ArgPart | PluralPart | TextPart]] = OrderedDict()
        self._formatters: dict[str, Callable[..., str]] = {}
        self._load(self._translations_dir, locale)

    def _load(self, translations_dir: Path, locale: str) -> None:
        path = self._find_translation_file(translations_dir, locale)
        if path is None:
            raise FileNotFoundError(f"Translation file not found for locale '{locale}' in {translations_dir}")
        backend = get_backend_for_file(path) or self._backend
        self._translations = backend.load(path)

    def _find_translation_file(self, dir: Path, locale: str) -> Path | None:
        for ext in self._backend.extensions():
            path = dir / f"{locale}{ext}"
            if path.exists():
                return path
        for backend_ext in [".yaml", ".yml", ".json", ".toml"]:
            path = dir / f"{locale}{backend_ext}"
            if path.exists():
                return path
        return None

    @property
    def locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        """Switch to a different locale, reloading translations from disk."""
        with self._lock:
            self._locale = locale
            self._translations = {}
            self._cache.clear()
            self._load(self._translations_dir, locale)

    def set_formatters(self, formatters: dict[str, Callable[..., str]]) -> None:
        """Register custom formatter functions."""
        with self._lock:
            self._formatters = formatters

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate a key with the current locale. Thread-safe."""
        template = self._get_template(key)
        parts = self._get_parts(template)
        return self._render(parts, kwargs)

    def _get_template(self, key: str) -> str:
        keys = key.split(".")
        obj: Any = self._translations
        for k in keys:
            if isinstance(obj, dict):
                obj = obj.get(k)
                if obj is None:
                    return key
            else:
                return key
        if isinstance(obj, str):
            return obj
        if isinstance(obj, dict):
            return str(obj.get("other", ""))
        return str(obj) if obj is not None else key

    def _get_parts(self, template: str) -> list[ArgPart | PluralPart | TextPart]:
        with self._lock:
            if template in self._cache:
                self._cache.move_to_end(template)
                return self._cache[template]
        parts = parse_translation(template)
        with self._lock:
            self._cache[template] = parts
            if len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return parts

    def _render(self, parts: list[ArgPart | PluralPart | TextPart], kwargs: dict[str, Any]) -> str:
        result: list[str] = []
        pending_plural_count: int | None = None

        for part in parts:
            if isinstance(part, TextPart):
                result.append(part.text)

            elif isinstance(part, ArgPart):
                value = kwargs.get(part.name)
                if value is None:
                    if part.optional:
                        continue
                    result.append(f"{{{part.name}}}")
                    continue
                if isinstance(value, (int, float)):
                    pending_plural_count = int(value)
                formatted = self._format_value(value, part)
                result.append(formatted)

            elif isinstance(part, PluralPart):
                if pending_plural_count is not None:
                    form = get_plural_form(self._locale, pending_plural_count)
                    idx = self._plural_index(form, len(part.forms))
                    text = part.forms[idx]
                    text = text.replace("??", str(pending_plural_count))
                    result.append(text)
                    pending_plural_count = None
                elif len(part.forms) == 1:
                    result.append(part.forms[0])
                else:
                    result.append(part.forms[-1])

        return "".join(result)

    def _format_value(self, value: Any, part: ArgPart) -> str:
        result = str(value)

        if part.type and part.type in self._formatters:
            try:
                result = self._formatters[part.type](result)
            except Exception:
                pass

        for fmt_name in part.formatters:
            if fmt_name in self._formatters:
                try:
                    result = self._formatters[fmt_name](result)
                except Exception:
                    pass

        if part.switch:
            if result in part.switch.cases:
                result = part.switch.cases[result]
            elif part.switch.default:
                result = part.switch.default

        return result

    @staticmethod
    def _plural_index(form: str, num_forms: int) -> int:
        if num_forms == 1:
            return 0
        if num_forms == 2:
            return 0 if form == "one" else 1
        if num_forms == 3:
            mapping = {"zero": 0, "one": 1, "other": 2}
            return mapping.get(form, 2)
        full = {"zero": 0, "one": 1, "two": 2, "few": 3, "many": 4, "other": 5}
        idx = full.get(form, 5)
        return min(idx, num_forms - 1)
