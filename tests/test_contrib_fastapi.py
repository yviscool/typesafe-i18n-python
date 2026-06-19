from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import yaml

from typesafe_i18n.contrib.fastapi import (
    I18nConfig,
    TypesafeI18nMiddleware,
    configure,
    create_dependency,
    get_i18n,
    t,
)


def _make_translations(tmpdir: str) -> None:
    trans_dir = Path(tmpdir) / "translations"
    trans_dir.mkdir(exist_ok=True)
    with open(trans_dir / "en.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hello {name:string}!", "bye": "Bye!"}, f)
    with open(trans_dir / "de.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hallo {name:string}!", "bye": "Tschüss!"}, f)


def _make_scope(
    accept_language: str = "",
    cookie: str = "",
    query_string: str = "",
) -> dict:
    headers: list[tuple[bytes, bytes]] = []
    if accept_language:
        headers.append((b"accept-language", accept_language.encode()))
    if cookie:
        headers.append((b"cookie", cookie.encode()))
    return {
        "type": "http",
        "headers": headers,
        "query_string": query_string.encode() if query_string else b"",
    }


class TestI18nConfig:
    def test_default_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir)
            assert config.default_locale == "en"
            assert config.available_locales == ["en"]

    def test_detect_locale_accept_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )
            locale = config.detect_locale(accept_language="de-CH,de;q=0.9,en;q=0.8")
            assert locale == "de"

    def test_detect_locale_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )
            locale = config.detect_locale(cookie="session=abc;lang=de")
            assert locale == "de"

    def test_detect_locale_query_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )
            locale = config.detect_locale(query_string="?lang=de")
            assert locale == "de"

    def test_detect_locale_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir)
            locale = config.detect_locale()
            assert locale == "en"

    def test_get_instance(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir)
            i18n = config.get_instance("en")
            assert i18n.locale == "en"

    def test_get_instance_caching(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir)
            i18n1 = config.get_instance("en")
            i18n2 = config.get_instance("en")
            assert i18n1 is i18n2

    def test_get_instance_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir, default_locale="en")
            i18n = config.get_instance("fr")
            assert i18n.locale == "en"


class TestTypesafeI18nMiddleware:
    def test_sets_scope_i18n(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(translations_dir=trans_dir)
            app = AsyncMock()
            middleware = TypesafeI18nMiddleware(app, config=config)

            scope = _make_scope(accept_language="en")
            receive = AsyncMock()
            send = AsyncMock()

            asyncio.run(middleware(scope, receive, send))

            assert "i18n" in scope
            assert scope["i18n"].locale == "en"

    def test_detects_accept_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            config = I18nConfig(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )
            app = AsyncMock()
            middleware = TypesafeI18nMiddleware(app, config=config)

            scope = _make_scope(accept_language="de;q=0.9,en;q=0.8")
            receive = AsyncMock()
            send = AsyncMock()

            asyncio.run(middleware(scope, receive, send))

            assert scope["i18n"].locale == "de"

    def test_non_http_passthrough(self) -> None:
        config = I18nConfig()
        app = AsyncMock()
        middleware = TypesafeI18nMiddleware(app, config=config)

        scope = {"type": "lifespan"}
        receive = AsyncMock()
        send = AsyncMock()

        asyncio.run(middleware(scope, receive, send))

        app.assert_called_once_with(scope, receive, send)


class TestGetI18nFunction:
    def test_with_locale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            configure(translations_dir=trans_dir)
            i18n = get_i18n(locale="en")
            assert i18n.locale == "en"

    def test_with_accept_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            configure(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )
            i18n = get_i18n(accept_language="de-CH,de;q=0.9,en;q=0.8")
            assert i18n.locale == "de"


class TestCreateDependency:
    def test_returns_callable(self) -> None:
        dep = create_dependency()
        assert callable(dep)


class TestTFunction:
    def test_translates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            configure(translations_dir=trans_dir)
            result = t("hello", name="World")
            assert result == "Hello World!"
