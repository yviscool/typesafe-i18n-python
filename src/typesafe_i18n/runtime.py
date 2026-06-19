from __future__ import annotations

import threading
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable

import asyncio

from typesafe_i18n.backends import TranslationBackend, YAMLBackend, get_backend_for_file
from typesafe_i18n.parser import ArgPart, PluralPart, TextPart, normalize_placeholder_name, parse_translation
from typesafe_i18n.plural import get_plural_form
from typesafe_i18n.translation_files import find_file_by_stem


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
        self._fallback_locale: str | None = None
        self._fallback_translations: dict[str, Any] = {}
        self._fallback_namespaces: dict[str, dict[str, Any]] = {}
        self._namespaces: dict[str, dict[str, Any]] = {}
        self._load(self._translations_dir, locale)

    def _load(self, translations_dir: Path, locale: str) -> None:
        path = self._find_translation_file(translations_dir, locale)
        if path is None:
            raise FileNotFoundError(f"Translation file not found for locale '{locale}' in {translations_dir}")
        backend = get_backend_for_file(path) or self._backend
        self._translations = backend.load(path)

    def _find_translation_file(self, dir: Path, locale: str) -> Path | None:
        return find_file_by_stem(dir, locale, self._backend)

    @property
    def locale(self) -> str:
        return self._locale

    def set_locale(self, locale: str) -> None:
        """Switch to a different locale, reloading translations from disk."""
        with self._lock:
            self._locale = locale
            self._translations = {}
            self._cache.clear()
            self._namespaces.clear()
            self._load(self._translations_dir, locale)

    def set_fallback_locale(self, locale: str) -> None:
        with self._lock:
            self._fallback_locale = locale
            self._fallback_translations = {}
            self._fallback_namespaces = {}
            self._load_fallback(self._translations_dir, locale)

    def _load_fallback(self, translations_dir: Path, locale: str) -> None:
        path = self._find_translation_file(translations_dir, locale)
        if path is None:
            return
        backend = get_backend_for_file(path) or self._backend
        self._fallback_translations = backend.load(path)

        locale_dir = translations_dir / locale
        if not locale_dir.is_dir():
            return
        for ns_file in locale_dir.iterdir():
            if ns_file.is_file() and get_backend_for_file(ns_file) is not None:
                ns_backend = get_backend_for_file(ns_file) or backend
                self._fallback_namespaces[ns_file.stem] = ns_backend.load(ns_file)

    def set_formatters(self, formatters: dict[str, Callable[..., str]]) -> None:
        """Register custom formatter functions."""
        with self._lock:
            self._formatters = formatters

    def load_namespace(self, namespace: str) -> None:
        locale_dir = self._translations_dir / self._locale
        path = self._find_namespace_file(locale_dir, namespace)
        if path is None:
            raise FileNotFoundError(
                f"Namespace file not found for locale '{self._locale}', namespace '{namespace}' in {self._translations_dir}"
            )
        backend = get_backend_for_file(path) or self._backend
        data = backend.load(path)
        with self._lock:
            self._namespaces[namespace] = data
            self._cache.clear()

    async def load_namespace_async(self, namespace: str) -> None:
        with self._lock:
            locale = self._locale
            translations_dir = self._translations_dir
        data = await asyncio.to_thread(
            _find_and_load_namespace, translations_dir, locale, namespace, self._backend
        )
        with self._lock:
            self._namespaces[namespace] = data
            self._cache.clear()

    def _find_namespace_file(self, locale_dir: Path, namespace: str) -> Path | None:
        if not locale_dir.is_dir():
            return None
        return find_file_by_stem(locale_dir, namespace, self._backend)

    def t(self, key: str, **kwargs: Any) -> str:
        """Translate a key with the current locale. Thread-safe."""
        template = self._get_template(key)
        parts = self._get_parts(template)
        return self._render(parts, kwargs)

    def _get_template(self, key: str) -> str:
        if ":" in key:
            namespace, _, ns_key = key.partition(":")
            ns_data = self._namespaces.get(namespace)
            if ns_data is not None:
                result = self._resolve_key(ns_data, ns_key)
                if isinstance(result, str):
                    return result
            fb_ns = self._fallback_namespaces.get(namespace)
            if fb_ns is not None:
                result = self._resolve_key(fb_ns, ns_key)
                if isinstance(result, str):
                    return result
            return self._get_fallback_template(key)

        result = self._resolve_key(self._translations, key)
        if isinstance(result, str):
            return result
        return self._get_fallback_template(key)

    @staticmethod
    def _resolve_key(data: dict[str, Any], key: str) -> Any:
        keys = key.split(".")
        obj: Any = data
        for k in keys:
            if isinstance(obj, dict):
                obj = obj.get(k)
                if obj is None:
                    return None
            else:
                return None
        return obj

    def _get_fallback_template(self, key: str) -> str:
        if not self._fallback_translations:
            return key
        result = self._resolve_key(self._fallback_translations, key)
        if isinstance(result, str):
            return result
        if isinstance(result, dict):
            return key
        return str(result) if result is not None else key

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
                value = kwargs.get(normalize_placeholder_name(part.name))
                if value is None:
                    if part.optional:
                        continue
                    result.append(f"{{{part.name}}}")
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    pending_plural_count = int(value)
                formatted = self._format_value(value, part)
                result.append(formatted)

            elif isinstance(part, PluralPart):
                count_value = kwargs.get(normalize_placeholder_name(part.key))
                if count_value is None:
                    count_value = pending_plural_count

                if count_value is not None:
                    form = get_plural_form(self._locale, int(count_value))
                    idx = self._plural_index(form, len(part.forms))
                    text = part.forms[idx]
                    text = text.replace("??", str(count_value))
                    result.append(text)
                    pending_plural_count = None
                elif len(part.forms) == 1:
                    result.append(part.forms[0])
                else:
                    result.append(part.forms[-1])

        return "".join(result)

    def _format_value(self, value: Any, part: ArgPart) -> str:
        result = str(value)

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


def _find_and_load_namespace(
    translations_dir: Path, locale: str, namespace: str, backend: TranslationBackend
) -> dict[str, Any]:
    locale_dir = translations_dir / locale
    if not locale_dir.is_dir():
        raise FileNotFoundError(
            f"Namespace file not found for locale '{locale}', namespace '{namespace}' in {translations_dir}"
        )
    path = find_file_by_stem(locale_dir, namespace, backend)
    if path is None:
        raise FileNotFoundError(
            f"Namespace file not found for locale '{locale}', namespace '{namespace}' in {translations_dir}"
        )
    file_backend = get_backend_for_file(path) or backend
    return file_backend.load(path)
