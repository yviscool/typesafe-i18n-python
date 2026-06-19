from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from pathlib import Path
from typing import Any

from typesafe_i18n.backends import TranslationBackend, YAMLBackend, get_backend_for_file


async def load_locale_async(
    translations_dir: str | Path,
    locale: str,
    backend: TranslationBackend | None = None,
    executor: Executor | None = None,
) -> dict[str, Any]:
    resolved_dir = Path(translations_dir)
    effective_backend = backend or YAMLBackend()
    return await _to_thread(_find_and_load, resolved_dir, locale, effective_backend, executor=executor)


async def load_namespace_async(
    translations_dir: str | Path,
    locale: str,
    namespace: str,
    backend: TranslationBackend | None = None,
    executor: Executor | None = None,
) -> dict[str, Any]:
    resolved_dir = Path(translations_dir)
    effective_backend = backend or YAMLBackend()
    return await _to_thread(
        _find_and_load_namespace, resolved_dir, locale, namespace, effective_backend, executor=executor
    )


async def _to_thread(func: Any, *args: Any, executor: Executor | None = None, **kwargs: Any) -> Any:
    loop = asyncio.get_running_loop()
    if executor is not None:
        return await loop.run_in_executor(executor, lambda: func(*args, **kwargs))
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


def _find_and_load(
    dir: Path,
    locale: str,
    backend: TranslationBackend,
) -> dict[str, Any]:
    path = _find_translation_file(dir, locale, backend)
    if path is None:
        raise FileNotFoundError(f"Translation file not found for locale '{locale}' in {dir}")
    file_backend = get_backend_for_file(path) or backend
    return file_backend.load(path)


def _find_and_load_namespace(
    dir: Path,
    locale: str,
    namespace: str,
    backend: TranslationBackend,
) -> dict[str, Any]:
    path = _find_namespace_file(dir, locale, namespace, backend)
    if path is None:
        raise FileNotFoundError(
            f"Namespace file not found for locale '{locale}', namespace '{namespace}' in {dir}"
        )
    file_backend = get_backend_for_file(path) or backend
    return file_backend.load(path)


def _find_translation_file(
    dir: Path,
    locale: str,
    backend: TranslationBackend,
) -> Path | None:
    for ext in backend.extensions():
        path = dir / f"{locale}{ext}"
        if path.exists():
            return path
    for ext in (".yaml", ".yml", ".json", ".toml"):
        path = dir / f"{locale}{ext}"
        if path.exists():
            return path
    return None


def _find_namespace_file(
    dir: Path,
    locale: str,
    namespace: str,
    backend: TranslationBackend,
) -> Path | None:
    locale_dir = dir / locale
    for ext in backend.extensions():
        path = locale_dir / f"{namespace}{ext}"
        if path.exists():
            return path
    for ext in (".yaml", ".yml", ".json", ".toml"):
        path = locale_dir / f"{namespace}{ext}"
        if path.exists():
            return path
    return None
