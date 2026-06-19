from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from typesafe_i18n.config import TypesafeI18nConfig


class TestTypesafeI18nConfigDefaults:
    def test_default_values(self):
        config = TypesafeI18nConfig()
        assert config.base_locale == "en"
        assert config.output_path == "./_generated"
        assert config.translations_path == "./translations"
        assert config.adapter is None
        assert config.generate_only_types is False
        assert config.esm_imports is False
        assert config.banner == ""


class TestConfigFromFile:
    def test_load_snake_case_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".typesafe-i18n.json"
            data = {
                "base_locale": "zh",
                "output_path": "./output",
                "translations_path": "./i18n",
                "adapter": "django",
                "generate_only_types": True,
                "esm_imports": True,
                "banner": "// auto-generated",
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            config = TypesafeI18nConfig.from_file(path)
            assert config.base_locale == "zh"
            assert config.output_path == "./output"
            assert config.translations_path == "./i18n"
            assert config.adapter == "django"
            assert config.generate_only_types is True
            assert config.esm_imports is True
            assert config.banner == "// auto-generated"

    def test_load_camel_case_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".typesafe-i18n.json"
            data = {
                "baseLocale": "ja",
                "outputPath": "./dist",
                "translationsPath": "./locales",
                "generateOnlyTypes": True,
            }
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)

            config = TypesafeI18nConfig.from_file(path)
            assert config.base_locale == "ja"
            assert config.output_path == "./dist"
            assert config.translations_path == "./locales"
            assert config.generate_only_types is True

    def test_load_partial_config(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".typesafe-i18n.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"baseLocale": "fr"}, f)

            config = TypesafeI18nConfig.from_file(path)
            assert config.base_locale == "fr"
            assert config.output_path == "./_generated"
            assert config.adapter is None

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            TypesafeI18nConfig.from_file("/nonexistent/.typesafe-i18n.json")


class TestConfigFind:
    def test_find_in_current_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / ".typesafe-i18n.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"baseLocale": "de"}, f)

            config = TypesafeI18nConfig.find(tmpdir)
            assert config.base_locale == "de"

    def test_find_in_parent_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            child = parent / "sub" / "deep"
            child.mkdir(parents=True)

            path = parent / ".typesafe-i18n.json"
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"baseLocale": "es"}, f)

            config = TypesafeI18nConfig.find(child)
            assert config.base_locale == "es"

    def test_find_returns_defaults_when_missing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = TypesafeI18nConfig.find(tmpdir)
            assert config.base_locale == "en"
            assert config.output_path == "./_generated"
