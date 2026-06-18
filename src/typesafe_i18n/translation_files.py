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
    locales = {path.stem for path in iter_translation_files(translations_dir)}
    return sorted(locales)


def iter_locale_files(translations_dir: Path, locale: str) -> list[Path]:
    files: list[Path] = []
    if not translations_dir.exists():
        return files

    locale_dir = translations_dir / locale
    for path in iter_translation_files(translations_dir):
        if path.parent == translations_dir or path.is_relative_to(locale_dir):
            if path.stem == locale:
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
