from __future__ import annotations

import asyncio
from concurrent.futures import Executor
from pathlib import Path
from typing import Any

from typesafe_i18n.backends import TranslationBackend, YAMLBackend, get_backend_for_file
from typesafe_i18n.translation_files import find_file_by_stem


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
    path = find_file_by_stem(dir, locale, backend)
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
    locale_dir = dir / locale
    path = find_file_by_stem(locale_dir, namespace, backend)
    if path is None:
        raise FileNotFoundError(
            f"Namespace file not found for locale '{locale}', namespace '{namespace}' in {dir}"
        )
    file_backend = get_backend_for_file(path) or backend
    return file_backend.load(path)
