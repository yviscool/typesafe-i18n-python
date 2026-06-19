from __future__ import annotations

from pathlib import Path
from typing import Any

from typesafe_i18n.backends import TranslationBackend, get_backend_for_file

SUPPORTED_EXTENSIONS = (".yaml", ".yml", ".json", ".toml")


def flatten_translation_tree(data: dict[str, Any], prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in data.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            result.update(flatten_translation_tree(value, full_key))
        elif isinstance(value, str):
            result[full_key] = value
    return result


def iter_translation_files(translations_dir: Path) -> list[Path]:
    if not translations_dir.exists():
        return []
    files = [
        path
        for path in translations_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and get_backend_for_file(path) is not None
    ]
    return sorted(files)


def collect_locales(translations_dir: Path) -> list[str]:
    if not translations_dir.exists():
        return []
    locales = {
        path.stem
        for path in translations_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and get_backend_for_file(path) is not None
    }
    return sorted(locales)


def find_file_by_stem(directory: Path, stem: str, backend: TranslationBackend | None = None) -> Path | None:
    if backend is not None:
        for ext in backend.extensions():
            path = directory / f"{stem}{ext}"
            if path.exists():
                return path
    for ext in SUPPORTED_EXTENSIONS:
        path = directory / f"{stem}{ext}"
        if path.exists():
            return path
    return None


def collect_namespaces(translations_dir: Path, locale: str) -> list[str]:
    locale_dir = translations_dir / locale
    if not locale_dir.is_dir():
        return []
    namespaces: list[str] = []
    for path in iter_translation_files(locale_dir):
        if path.parent == locale_dir:
            namespaces.append(path.stem)
    return sorted(namespaces)


def iter_locale_files(translations_dir: Path, locale: str) -> list[Path]:
    files: list[Path] = []
    if not translations_dir.exists():
        return files

    locale_dir = translations_dir / locale
    for path in iter_translation_files(translations_dir):
        if path.parent == translations_dir:
            if path.stem == locale:
                files.append(path)
        elif path.is_relative_to(locale_dir):
            if path.parent == locale_dir and path.stem != locale:
                continue
            files.append(path)
    return files


def locale_prefix(translations_dir: Path, locale: str, path: Path) -> str:
    if path.parent == translations_dir:
        return ""

    locale_dir = translations_dir / locale
    try:
        relative = path.relative_to(locale_dir)
    except ValueError:
        return ""

    parts = relative.parts[:-1]
    return ".".join(parts)


def load_locale_sections(
    translations_dir: Path,
    locale: str,
    backend: TranslationBackend | None = None,
) -> dict[str, dict[str, Any]]:
    sections: dict[str, dict[str, Any]] = {}
    for path in iter_locale_files(translations_dir, locale):
        prefix = locale_prefix(translations_dir, locale, path)
        file_backend = get_backend_for_file(path) or backend
        if file_backend is None:
            continue
        data = file_backend.load(path)
        if isinstance(data, dict):
            sections[prefix] = dict(data)
    return sections


def extend_dictionary(base: dict, overrides: dict) -> dict:
    result = dict(base)
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = extend_dictionary(result[key], value)
        else:
            result[key] = value
    return result


def load_locale_with_fallback(
    translations_dir: Path,
    locale: str,
    fallback_locale: str,
    backend: TranslationBackend | None = None,
) -> dict[str, Any]:
    base_sections = load_locale_sections(translations_dir, fallback_locale, backend)
    locale_sections = load_locale_sections(translations_dir, locale, backend)
    merged: dict[str, Any] = {}
    for prefix, data in base_sections.items():
        merged[prefix] = data
    for prefix, data in locale_sections.items():
        if prefix in merged:
            merged[prefix] = extend_dictionary(merged[prefix], data)
        else:
            merged[prefix] = data
    result: dict[str, Any] = {}
    for prefix, data in merged.items():
        if prefix:
            parts = prefix.split(".")
            target = result
            for part in parts[:-1]:
                target = target.setdefault(part, {})
            target[parts[-1]] = data
        else:
            result.update(data)
    return result
