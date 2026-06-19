from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from typesafe_i18n.async_loader import load_locale_async, load_namespace_async
from typesafe_i18n.runtime import I18n


@pytest.fixture
def translations_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        en = {
            "hello": "Hello {name:string}!",
            "simple": "Simple text",
        }
        zh = {
            "hello": "你好 {name:string}！",
            "simple": "简单文本",
        }
        settings_en = {
            "title": "Settings",
            "save": "Save changes",
        }
        settings_zh = {
            "title": "设置",
            "save": "保存更改",
        }

        base = Path(tmpdir)
        with open(base / "en.yaml", "w", encoding="utf-8") as f:
            yaml.dump(en, f, allow_unicode=True)
        with open(base / "zh.yaml", "w", encoding="utf-8") as f:
            yaml.dump(zh, f, allow_unicode=True)

        en_dir = base / "en"
        en_dir.mkdir()
        with open(en_dir / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(settings_en, f, allow_unicode=True)

        zh_dir = base / "zh"
        zh_dir.mkdir()
        with open(zh_dir / "settings.yaml", "w", encoding="utf-8") as f:
            yaml.dump(settings_zh, f, allow_unicode=True)

        yield tmpdir


class TestLoadLocaleAsync:
    @pytest.mark.asyncio
    async def test_load_locale(self, translations_dir: str) -> None:
        data = await load_locale_async(translations_dir, "en")
        assert data["hello"] == "Hello {name:string}!"
        assert data["simple"] == "Simple text"

    @pytest.mark.asyncio
    async def test_load_locale_zh(self, translations_dir: str) -> None:
        data = await load_locale_async(translations_dir, "zh")
        assert "你好" in data["hello"]

    @pytest.mark.asyncio
    async def test_load_locale_missing(self, translations_dir: str) -> None:
        with pytest.raises(FileNotFoundError):
            await load_locale_async(translations_dir, "fr")

    @pytest.mark.asyncio
    async def test_load_locale_nonexistent_dir(self) -> None:
        with pytest.raises(FileNotFoundError):
            await load_locale_async("/nonexistent/path", "en")


class TestLoadNamespaceAsync:
    @pytest.mark.asyncio
    async def test_load_namespace(self, translations_dir: str) -> None:
        data = await load_namespace_async(translations_dir, "en", "settings")
        assert data["title"] == "Settings"
        assert data["save"] == "Save changes"

    @pytest.mark.asyncio
    async def test_load_namespace_zh(self, translations_dir: str) -> None:
        data = await load_namespace_async(translations_dir, "zh", "settings")
        assert data["title"] == "设置"

    @pytest.mark.asyncio
    async def test_load_namespace_missing(self, translations_dir: str) -> None:
        with pytest.raises(FileNotFoundError):
            await load_namespace_async(translations_dir, "en", "nonexistent")

    @pytest.mark.asyncio
    async def test_load_namespace_missing_locale_dir(self, translations_dir: str) -> None:
        with pytest.raises(FileNotFoundError):
            await load_namespace_async(translations_dir, "fr", "settings")


class TestI18nNamespace:
    def test_load_namespace_sync(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        i18n.load_namespace("settings")
        assert i18n.t("settings:title") == "Settings"
        assert i18n.t("settings:save") == "Save changes"

    def test_namespace_with_params(self, translations_dir: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            account = {"greeting": "Welcome {name:string}!"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(en, f)

            en_dir = base / "en"
            en_dir.mkdir()
            with open(en_dir / "account.yaml", "w", encoding="utf-8") as f:
                yaml.dump(account, f)

            i18n = I18n(tmpdir, "en")
            i18n.load_namespace("account")
            assert i18n.t("account:greeting", name="Alice") == "Welcome Alice!"

    def test_namespace_missing_key_returns_key(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        i18n.load_namespace("settings")
        assert i18n.t("settings:nonexistent") == "settings:nonexistent"

    def test_namespace_not_loaded_returns_key(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        assert i18n.t("settings:title") == "settings:title"

    def test_namespace_file_not_found(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        with pytest.raises(FileNotFoundError):
            i18n.load_namespace("nonexistent")

    @pytest.mark.asyncio
    async def test_load_namespace_async(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        await i18n.load_namespace_async("settings")
        assert i18n.t("settings:title") == "Settings"
        assert i18n.t("settings:save") == "Save changes"

    @pytest.mark.asyncio
    async def test_load_namespace_async_with_params(self, translations_dir: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            account = {"greeting": "Welcome {name:string}!"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(en, f)

            en_dir = base / "en"
            en_dir.mkdir()
            with open(en_dir / "account.yaml", "w", encoding="utf-8") as f:
                yaml.dump(account, f)

            i18n = I18n(tmpdir, "en")
            await i18n.load_namespace_async("account")
            assert i18n.t("account:greeting", name="Bob") == "Welcome Bob!"

    def test_namespace_and_regular_key_coexist(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        i18n.load_namespace("settings")
        assert i18n.t("hello", name="World") == "Hello World!"
        assert i18n.t("settings:title") == "Settings"

    def test_set_locale_clears_namespaces(self, translations_dir: str) -> None:
        i18n = I18n(translations_dir, "en")
        i18n.load_namespace("settings")
        assert i18n.t("settings:title") == "Settings"

        i18n.set_locale("zh")
        assert i18n.t("settings:title") == "settings:title"

        i18n.load_namespace("settings")
        assert i18n.t("settings:title") == "设置"

    def test_multiple_namespaces(self, translations_dir: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            settings = {"title": "Settings"}
            profile = {"name": "Profile"}

            base = Path(tmpdir)
            with open(base / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(en, f)

            en_dir = base / "en"
            en_dir.mkdir()
            with open(en_dir / "settings.yaml", "w", encoding="utf-8") as f:
                yaml.dump(settings, f)
            with open(en_dir / "profile.yaml", "w", encoding="utf-8") as f:
                yaml.dump(profile, f)

            i18n = I18n(tmpdir, "en")
            i18n.load_namespace("settings")
            i18n.load_namespace("profile")
            assert i18n.t("settings:title") == "Settings"
            assert i18n.t("profile:name") == "Profile"
            assert i18n.t("hello") == "Hello"


class TestAsyncLoaderConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_locale_loading(self, translations_dir: str) -> None:
        results = await asyncio.gather(
            load_locale_async(translations_dir, "en"),
            load_locale_async(translations_dir, "zh"),
        )
        assert results[0]["simple"] == "Simple text"
        assert "你好" in results[1]["hello"]

    @pytest.mark.asyncio
    async def test_concurrent_namespace_loading(self, translations_dir: str) -> None:
        en_data, zh_data = await asyncio.gather(
            load_namespace_async(translations_dir, "en", "settings"),
            load_namespace_async(translations_dir, "zh", "settings"),
        )
        assert en_data["title"] == "Settings"
        assert zh_data["title"] == "设置"

    @pytest.mark.asyncio
    async def test_concurrent_mixed_loading(self, translations_dir: str) -> None:
        locale_data, ns_data = await asyncio.gather(
            load_locale_async(translations_dir, "en"),
            load_namespace_async(translations_dir, "en", "settings"),
        )
        assert locale_data["hello"] == "Hello {name:string}!"
        assert ns_data["title"] == "Settings"
