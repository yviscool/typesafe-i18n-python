from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TypesafeI18nConfig:
    base_locale: str = "en"
    output_path: str = "./_generated"
    translations_path: str = "./translations"
    adapter: str | None = None
    generate_only_types: bool = False
    esm_imports: bool = False
    banner: str = ""

    @classmethod
    def from_file(cls, path: str | Path) -> TypesafeI18nConfig:
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            data: dict = json.load(f)
        return cls(
            base_locale=data.get("baseLocale", data.get("base_locale", "en")),
            output_path=data.get("outputPath", data.get("output_path", "./_generated")),
            translations_path=data.get("translationsPath", data.get("translations_path", "./translations")),
            adapter=data.get("adapter"),
            generate_only_types=data.get("generateOnlyTypes", data.get("generate_only_types", False)),
            esm_imports=data.get("esmImports", data.get("esm_imports", False)),
            banner=data.get("banner", ""),
        )

    @classmethod
    def find(cls, start_dir: str | Path | None = None) -> TypesafeI18nConfig:
        current = Path(start_dir) if start_dir else Path.cwd()
        filename = ".typesafe-i18n.json"
        for parent in [current, *current.parents]:
            config_path = parent / filename
            if config_path.exists():
                return cls.from_file(config_path)
        return cls()
