from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import yaml


class TranslationBackend(ABC):
    """Abstract base class for translation file backends."""

    @abstractmethod
    def load(self, path: Path) -> dict[str, Any]:
        """Load translations from a file."""
        ...

    @abstractmethod
    def save(self, path: Path, data: dict[str, Any]) -> None:
        """Save translations to a file."""
        ...

    @abstractmethod
    def extensions(self) -> list[str]:
        """Return supported file extensions."""
        ...


class YAMLBackend(TranslationBackend):
    """YAML translation file backend."""

    def load(self, path: Path) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            raw: Any = yaml.safe_load(f)
        if isinstance(raw, dict):
            return dict(raw)
        return {}

    def save(self, path: Path, data: dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    def extensions(self) -> list[str]:
        return [".yaml", ".yml"]


class JSONBackend(TranslationBackend):
    """JSON translation file backend."""

    def load(self, path: Path) -> dict[str, Any]:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return data

    def save(self, path: Path, data: dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def extensions(self) -> list[str]:
        return [".json"]


class TOMLBackend(TranslationBackend):
    """TOML translation file backend."""

    def load(self, path: Path) -> dict[str, Any]:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]
        with open(path, "rb") as f:
            return tomllib.load(f)

    def save(self, path: Path, data: dict[str, Any]) -> None:
        try:
            import tomli_w
            with open(path, "wb") as f:
                tomli_w.dump(data, f)
        except ImportError:
            raise ImportError("tomli_w is required for TOML write support: pip install tomli_w")

    def extensions(self) -> list[str]:
        return [".toml"]


_BACKENDS: dict[str, TranslationBackend] = {
    "yaml": YAMLBackend(),
    "json": JSONBackend(),
    "toml": TOMLBackend(),
}


def get_backend(format: str) -> TranslationBackend:
    """Get a backend by format name."""
    backend = _BACKENDS.get(format.lower())
    if not backend:
        raise ValueError(f"Unknown backend format: {format}. Supported: {list(_BACKENDS.keys())}")
    return backend


def get_backend_for_file(path: Path) -> TranslationBackend | None:
    """Get the appropriate backend for a file based on its extension."""
    suffix = path.suffix.lower()
    for backend in _BACKENDS.values():
        if suffix in backend.extensions():
            return backend
    return None
