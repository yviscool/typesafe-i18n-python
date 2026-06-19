from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from typesafe_i18n.runtime import I18n


# ---------------------------------------------------------------------------
# T1: _get_template handles dict / None / non-string values correctly
# ---------------------------------------------------------------------------


class TestGetTemplateDictNone:
    """Verify that non-string resolved values fall back correctly."""

    def _make_i18n(self, tmpdir: str, data: dict, locale: str = "en") -> I18n:
        with open(Path(tmpdir) / f"{locale}.yaml", "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True)
        return I18n(tmpdir, locale)

    def test_key_pointing_to_dict_returns_key(self):
        """A key that resolves to an intermediate dict should return the raw key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"user": {"name": "Alice", "age": "30"}}
            i18n = self._make_i18n(tmpdir, data)
            assert i18n.t("user") == "user"

    def test_key_pointing_to_dict_with_fallback(self):
        """Dict value in primary locale should fall through to fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"user": {"greeting": "Hello!"}, "other": "Other"}
            zh = {"user": {"name": "Alice"}}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            # "user" is a dict in zh, fallback also has "user" as dict → returns key
            assert i18n.t("user") == "user"
            # but "other" exists only in fallback
            assert i18n.t("other") == "Other"

    def test_explicit_yaml_null_returns_key(self):
        """YAML null (~) should be treated as missing and return the raw key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"greeting": "Hello", "empty": None}
            i18n = self._make_i18n(tmpdir, data)
            assert i18n.t("greeting") == "Hello"
            assert i18n.t("empty") == "empty"

    def test_yaml_null_with_fallback(self):
        """YAML null in primary locale should fall back to fallback locale value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"greeting": "Hello", "empty": "Not empty"}
            zh = {"greeting": "你好", "empty": None}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("empty") == "Not empty"

    def test_integer_value_returns_key(self):
        """A non-string, non-None, non-dict value (int) should return the raw key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"count": 42, "label": "Count"}
            i18n = self._make_i18n(tmpdir, data)
            assert i18n.t("count") == "count"
            assert i18n.t("label") == "Count"

    def test_nested_dict_at_leaf(self):
        """Deeply nested key that resolves to a dict at the leaf."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"a": {"b": {"c": "deep"}}}
            i18n = self._make_i18n(tmpdir, data)
            assert i18n.t("a.b.c") == "deep"
            # intermediate nodes are dicts
            assert i18n.t("a") == "a"
            assert i18n.t("a.b") == "a.b"

    def test_missing_key_no_fallback(self):
        """Missing key without fallback returns the raw key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "Hello"}
            i18n = self._make_i18n(tmpdir, data)
            assert i18n.t("nonexistent") == "nonexistent"

    def test_missing_key_with_fallback(self):
        """Missing key in primary locale falls back to fallback locale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello", "bye": "Bye"}
            zh = {"hello": "你好"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("bye") == "Bye"

    def test_namespace_key_not_dict(self):
        """Namespace key that resolves to a string works normally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns = {"title": "Settings"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            ns_dir = Path(tmpdir) / "en"
            ns_dir.mkdir()
            with open(ns_dir / "settings.yaml", "w") as f:
                yaml.dump(ns, f)
            i18n = I18n(tmpdir, "en")
            i18n.load_namespace("settings")
            assert i18n.t("settings:title") == "Settings"


# ---------------------------------------------------------------------------
# T2: CLI args vs config precedence
# ---------------------------------------------------------------------------


class TestCLIConfigPrecedence:
    """Verify that explicit CLI args override config file values."""

    def _run_cli(self, args: list[str], cwd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "typesafe_i18n.cli", *args],
            capture_output=True, text=True, cwd=cwd,
        )

    def test_explicit_dir_overrides_config(self):
        """--dir should take precedence over config translations_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config_trans"
            cli_dir = Path(tmpdir) / "cli_trans"
            out_dir = Path(tmpdir) / "output"
            config_dir.mkdir()
            cli_dir.mkdir()

            # config points to config_trans
            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(config_dir)}, f)

            # translations in cli_trans (not config_trans)
            with open(cli_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            result = self._run_cli(
                ["generate", "-d", str(cli_dir), "-o", str(out_dir)],
                cwd=tmpdir,
            )
            assert result.returncode == 0
            assert (out_dir / "types.pyi").exists()

    def test_explicit_output_overrides_config(self):
        """--output should take precedence over config output_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            config_out = Path(tmpdir) / "config_out"
            cli_out = Path(tmpdir) / "cli_out"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"outputPath": str(config_out)}, f)

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            result = self._run_cli(
                ["generate", "-d", str(trans_dir), "-o", str(cli_out)],
                cwd=tmpdir,
            )
            assert result.returncode == 0
            assert (cli_out / "types.pyi").exists()
            assert not config_out.exists()

    def test_explicit_locale_overrides_config(self):
        """--locale should take precedence over config base_locale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            out_dir = Path(tmpdir) / "output"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"baseLocale": "zh"}, f)

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)
            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)

            result = self._run_cli(
                ["generate", "-d", str(trans_dir), "-o", str(out_dir), "-l", "en"],
                cwd=tmpdir,
            )
            assert result.returncode == 0
            assert (out_dir / "types.pyi").exists()

    def test_config_used_when_no_cli_args(self):
        """Config values should be used when CLI args are not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "my_translations"
            out_dir = Path(tmpdir) / "my_output"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({
                    "translationsPath": str(trans_dir),
                    "outputPath": str(out_dir),
                    "baseLocale": "zh",
                }, f)

            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)

            result = self._run_cli(["generate"], cwd=tmpdir)
            assert result.returncode == 0
            assert (out_dir / "types.pyi").exists()

    def test_no_config_uses_defaults(self):
        """Without config file, CLI defaults should work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            result = self._run_cli(
                ["generate", "-d", str(trans_dir), "-o", str(Path(tmpdir) / "out")],
                cwd=tmpdir,
            )
            assert result.returncode == 0

    def test_validate_uses_config_dir(self):
        """validate command should read translations_path from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "my_trans"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(trans_dir)}, f)

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            result = self._run_cli(["validate"], cwd=tmpdir)
            assert result.returncode == 0

    def test_validate_uses_config_locale(self):
        """validate command should read base_locale from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"baseLocale": "zh"}, f)

            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)

            result = self._run_cli(
                ["validate", "-d", str(trans_dir)],
                cwd=tmpdir,
            )
            assert result.returncode == 0

    def test_export_uses_config_dir(self):
        """export command should read translations_path from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "my_trans"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(trans_dir)}, f)

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            json_out = Path(tmpdir) / "out.json"
            result = self._run_cli(["export", "-o", str(json_out)], cwd=tmpdir)
            assert result.returncode == 0
            assert json_out.exists()

    def test_import_uses_config_dir(self):
        """import command should read translations_path from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "my_trans"

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(trans_dir)}, f)

            json_file = Path(tmpdir) / "data.json"
            with open(json_file, "w") as f:
                json.dump({"en": {"hello": "Hello"}}, f)

            result = self._run_cli(["import", str(json_file)], cwd=tmpdir)
            assert result.returncode == 0
            assert (trans_dir / "en.yaml").exists()

    def test_extract_uses_config_locale(self):
        """extract command should read base_locale from config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            src_dir = Path(tmpdir) / "src"
            trans_dir.mkdir()
            src_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"baseLocale": "zh"}, f)

            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)

            with open(src_dir / "app.py", "w") as f:
                f.write('i18n.t("hello")\n')

            result = self._run_cli(
                ["extract", str(src_dir), "-d", str(trans_dir)],
                cwd=tmpdir,
            )
            assert result.returncode == 0


# ---------------------------------------------------------------------------
# T3: load_namespace_async race condition (locale snapshot)
# ---------------------------------------------------------------------------


class TestLoadNamespaceAsyncRace:
    """Verify that load_namespace_async snapshots the locale correctly."""

    @pytest.mark.asyncio
    async def test_async_namespace_uses_current_locale(self):
        """Namespace should be loaded for the locale at call time."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings"}
            ns_zh = {"title": "设置"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)
            (base / "zh").mkdir()
            with open(base / "zh" / "settings.yaml", "w") as f:
                yaml.dump(ns_zh, f)

            i18n = I18n(tmpdir, "en")
            await i18n.load_namespace_async("settings")
            assert i18n.t("settings:title") == "Settings"

    @pytest.mark.asyncio
    async def test_async_namespace_after_locale_switch(self):
        """After set_locale, async namespace load should use new locale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            zh = {"hello": "你好"}
            ns_en = {"title": "Settings"}
            ns_zh = {"title": "设置"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)
            (base / "zh").mkdir()
            with open(base / "zh" / "settings.yaml", "w") as f:
                yaml.dump(ns_zh, f)

            i18n = I18n(tmpdir, "en")
            i18n.set_locale("zh")
            await i18n.load_namespace_async("settings")
            assert i18n.t("settings:title") == "设置"

    @pytest.mark.asyncio
    async def test_concurrent_async_namespace_loads(self):
        """Multiple concurrent namespace loads should all succeed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns1 = {"title": "Settings"}
            ns2 = {"name": "Profile"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            en_dir = base / "en"
            en_dir.mkdir()
            with open(en_dir / "settings.yaml", "w") as f:
                yaml.dump(ns1, f)
            with open(en_dir / "profile.yaml", "w") as f:
                yaml.dump(ns2, f)

            i18n = I18n(tmpdir, "en")
            await asyncio.gather(
                i18n.load_namespace_async("settings"),
                i18n.load_namespace_async("profile"),
            )
            assert i18n.t("settings:title") == "Settings"
            assert i18n.t("profile:name") == "Profile"


# ---------------------------------------------------------------------------
# T5: Namespace fallback
# ---------------------------------------------------------------------------


class TestNamespaceFallback:
    """Verify that namespace keys fall back to fallback locale namespaces."""

    def test_namespace_key_from_fallback_locale(self):
        """Namespace not loaded in primary locale should fall back to fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings", "save": "Save"}
            zh = {"hello": "你好"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            # settings namespace not loaded in zh, but exists in en fallback
            assert i18n.t("settings:title") == "Settings"
            assert i18n.t("settings:save") == "Save"

    def test_namespace_primary_overrides_fallback(self):
        """Loaded namespace in primary locale should take precedence over fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings (EN)"}
            zh = {"hello": "你好"}
            ns_zh = {"title": "设置"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)
            (base / "zh").mkdir()
            with open(base / "zh" / "settings.yaml", "w") as f:
                yaml.dump(ns_zh, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            i18n.load_namespace("settings")
            # primary locale namespace should win
            assert i18n.t("settings:title") == "设置"

    def test_namespace_missing_in_both_returns_key(self):
        """Namespace key missing in both primary and fallback returns raw key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            zh = {"hello": "你好"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("nonexistent:key") == "nonexistent:key"

    def test_namespace_key_in_fallback_not_in_primary(self):
        """Key exists in fallback namespace but not in primary namespace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings", "extra": "Extra"}
            zh = {"hello": "你好"}
            ns_zh = {"title": "设置"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)
            (base / "zh").mkdir()
            with open(base / "zh" / "settings.yaml", "w") as f:
                yaml.dump(ns_zh, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            i18n.load_namespace("settings")
            # "extra" exists in en namespace but not zh namespace
            assert i18n.t("settings:extra") == "Extra"

    def test_fallback_namespace_with_params(self):
        """Fallback namespace with template parameters should render correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"greeting": "Welcome {name:string}!"}
            zh = {"hello": "你好"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "account.yaml", "w") as f:
                yaml.dump(ns_en, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("account:greeting", name="Alice") == "Welcome Alice!"

    def test_fallback_namespace_cleared_on_set_locale(self):
        """set_locale should not affect fallback namespaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings"}
            zh = {"hello": "你好"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("settings:title") == "Settings"

            i18n.set_locale("en")
            # fallback still works after locale switch
            i18n.set_locale("zh")
            assert i18n.t("settings:title") == "Settings"

    def test_fallback_namespace_cleared_on_set_fallback(self):
        """set_fallback_locale should reload fallback namespaces."""
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            ns_en = {"title": "Settings EN"}
            zh = {"hello": "你好"}
            fr = {"hello": "Bonjour"}
            ns_fr = {"title": "Paramètres"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(base / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            with open(base / "fr.yaml", "w") as f:
                yaml.dump(fr, f)
            (base / "en").mkdir()
            with open(base / "en" / "settings.yaml", "w") as f:
                yaml.dump(ns_en, f)
            (base / "fr").mkdir()
            with open(base / "fr" / "settings.yaml", "w") as f:
                yaml.dump(ns_fr, f)

            i18n = I18n(tmpdir, "zh")
            i18n.set_fallback_locale("en")
            assert i18n.t("settings:title") == "Settings EN"

            i18n.set_fallback_locale("fr")
            assert i18n.t("settings:title") == "Paramètres"


# ---------------------------------------------------------------------------
# T6: Subcommands config consistency (covered by TestCLIConfigPrecedence)
# Additional edge cases
# ---------------------------------------------------------------------------


class TestCLIConfigEdgeCases:
    """Edge cases for CLI config integration."""

    def _run_cli(self, args: list[str], cwd: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-m", "typesafe_i18n.cli", *args],
            capture_output=True, text=True, cwd=cwd,
        )

    def test_validate_cli_dir_overrides_config(self):
        """--dir on validate should override config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config_trans"
            cli_dir = Path(tmpdir) / "cli_trans"
            config_dir.mkdir()
            cli_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(config_dir)}, f)

            with open(cli_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            result = self._run_cli(["validate", "-d", str(cli_dir)], cwd=tmpdir)
            assert result.returncode == 0

    def test_validate_cli_locale_overrides_config(self):
        """--locale on validate should override config baseLocale."""
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"baseLocale": "zh"}, f)

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)
            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)

            result = self._run_cli(
                ["validate", "-d", str(trans_dir), "-l", "en"],
                cwd=tmpdir,
            )
            assert result.returncode == 0

    def test_export_cli_dir_overrides_config(self):
        """--dir on export should override config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config_trans"
            cli_dir = Path(tmpdir) / "cli_trans"
            config_dir.mkdir()
            cli_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(config_dir)}, f)

            with open(cli_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            json_out = Path(tmpdir) / "out.json"
            result = self._run_cli(
                ["export", "-d", str(cli_dir), "-o", str(json_out)],
                cwd=tmpdir,
            )
            assert result.returncode == 0
            with open(json_out) as f:
                data = json.load(f)
            assert "en" in data

    def test_import_cli_dir_overrides_config(self):
        """--dir on import should override config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config_trans"
            cli_dir = Path(tmpdir) / "cli_trans"

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(config_dir)}, f)

            json_file = Path(tmpdir) / "data.json"
            with open(json_file, "w") as f:
                json.dump({"en": {"hello": "Hello"}}, f)

            result = self._run_cli(
                ["import", str(json_file), "-d", str(cli_dir)],
                cwd=tmpdir,
            )
            assert result.returncode == 0
            assert (cli_dir / "en.yaml").exists()

    def test_extract_cli_dir_overrides_config(self):
        """--dir on extract should override config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / "config_trans"
            cli_dir = Path(tmpdir) / "cli_trans"
            src_dir = Path(tmpdir) / "src"
            config_dir.mkdir()
            cli_dir.mkdir()
            src_dir.mkdir()

            with open(Path(tmpdir) / ".typesafe-i18n.json", "w") as f:
                json.dump({"translationsPath": str(config_dir)}, f)

            with open(cli_dir / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)
            with open(src_dir / "app.py", "w") as f:
                f.write('i18n.t("hello")\n')

            result = self._run_cli(
                ["extract", str(src_dir), "-d", str(cli_dir)],
                cwd=tmpdir,
            )
            assert result.returncode == 0


# ---------------------------------------------------------------------------
# T4: async_loader atomicity (TOCTOU)
# ---------------------------------------------------------------------------


class TestAsyncLoaderAtomicity:
    """Verify that async loader find+load is atomic (single thread call)."""

    @pytest.mark.asyncio
    async def test_load_locale_atomic_success(self):
        """Normal load should work correctly with atomic find+load."""
        from typesafe_i18n.async_loader import load_locale_async

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            data = await load_locale_async(tmpdir, "en")
            assert data["hello"] == "Hello"

    @pytest.mark.asyncio
    async def test_load_locale_atomic_missing(self):
        """Missing file should raise FileNotFoundError atomically."""
        from typesafe_i18n.async_loader import load_locale_async

        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(FileNotFoundError):
                await load_locale_async(tmpdir, "fr")

    @pytest.mark.asyncio
    async def test_load_namespace_atomic_success(self):
        """Normal namespace load should work correctly."""
        from typesafe_i18n.async_loader import load_namespace_async

        with tempfile.TemporaryDirectory() as tmpdir:
            en_dir = Path(tmpdir) / "en"
            en_dir.mkdir()
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)
            with open(en_dir / "settings.yaml", "w") as f:
                yaml.dump({"title": "Settings"}, f)

            data = await load_namespace_async(tmpdir, "en", "settings")
            assert data["title"] == "Settings"

    @pytest.mark.asyncio
    async def test_load_namespace_atomic_missing(self):
        """Missing namespace file should raise FileNotFoundError atomically."""
        from typesafe_i18n.async_loader import load_namespace_async

        with tempfile.TemporaryDirectory() as tmpdir:
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)

            with pytest.raises(FileNotFoundError):
                await load_namespace_async(tmpdir, "en", "nonexistent")

    @pytest.mark.asyncio
    async def test_concurrent_mixed_loads(self):
        """Concurrent locale and namespace loads should not interfere."""
        from typesafe_i18n.async_loader import load_locale_async, load_namespace_async

        with tempfile.TemporaryDirectory() as tmpdir:
            en_dir = Path(tmpdir) / "en"
            en_dir.mkdir()
            zh_dir = Path(tmpdir) / "zh"
            zh_dir.mkdir()

            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump({"hello": "Hello"}, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好"}, f)
            with open(en_dir / "settings.yaml", "w") as f:
                yaml.dump({"title": "Settings"}, f)
            with open(zh_dir / "settings.yaml", "w") as f:
                yaml.dump({"title": "设置"}, f)

            results = await asyncio.gather(
                load_locale_async(tmpdir, "en"),
                load_locale_async(tmpdir, "zh"),
                load_namespace_async(tmpdir, "en", "settings"),
                load_namespace_async(tmpdir, "zh", "settings"),
            )
            assert results[0]["hello"] == "Hello"
            assert results[1]["hello"] == "你好"
            assert results[2]["title"] == "Settings"
            assert results[3]["title"] == "设置"
