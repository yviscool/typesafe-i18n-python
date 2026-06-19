from __future__ import annotations

import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import yaml

from typesafe_i18n.contrib.django import TypesafeI18nMiddleware, get_i18n, t


def _make_translations(tmpdir: str) -> None:
    trans_dir = Path(tmpdir) / "translations"
    trans_dir.mkdir(exist_ok=True)
    with open(trans_dir / "en.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hello {name:string}!", "bye": "Bye!"}, f)
    with open(trans_dir / "de.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hallo {name:string}!", "bye": "Tschüss!"}, f)


def _make_request(accept_language: str = "", cookie: str = "") -> SimpleNamespace:
    meta: dict[str, str] = {}
    if accept_language:
        meta["HTTP_ACCEPT_LANGUAGE"] = accept_language
    if cookie:
        meta["HTTP_COOKIE"] = cookie
    request = SimpleNamespace(META=meta)
    return request


class TestTypesafeI18nMiddleware:
    def test_default_locale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(get_response, translations_dir=trans_dir)

            request = _make_request()
            result = middleware(request)

            assert result == "response"
            assert hasattr(request, "i18n")
            assert request.i18n.locale == "en"

    def test_accept_language_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(
                get_response,
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            request = _make_request(accept_language="de-CH,de;q=0.9,en;q=0.8")
            middleware(request)

            assert request.i18n.locale == "de"

    def test_cookie_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(
                get_response,
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            request = _make_request(cookie="session=abc;lang=de")
            middleware(request)

            assert request.i18n.locale == "de"

    def test_accept_language_takes_priority(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(
                get_response,
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            request = _make_request(
                accept_language="de",
                cookie="lang=en",
            )
            middleware(request)

            assert request.i18n.locale == "de"

    def test_unsupported_locale_falls_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(
                get_response,
                translations_dir=trans_dir,
                default_locale="en",
                available_locales=["en", "de"],
            )

            request = _make_request(accept_language="fr")
            middleware(request)

            assert request.i18n.locale == "en"

    def test_instance_caching(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(get_response, translations_dir=trans_dir)

            request1 = _make_request()
            middleware(request1)
            request2 = _make_request()
            middleware(request2)

            assert request1.i18n is request2.i18n


class TestGetI18n:
    def test_returns_i18n(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(get_response, translations_dir=trans_dir)

            request = _make_request()
            middleware(request)

            i18n = get_i18n(request)
            assert i18n is request.i18n

    def test_raises_without_middleware(self) -> None:
        request = SimpleNamespace()
        try:
            get_i18n(request)
            assert False, "Should have raised"
        except RuntimeError as e:
            assert "MIDDLEWARE" in str(e)


class TestTFunction:
    def test_translates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(get_response, translations_dir=trans_dir)

            request = _make_request()
            middleware(request)

            assert t(request, "hello", name="World") == "Hello World!"
            assert t(request, "bye") == "Bye!"

    def test_fallback_locale_translation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            get_response = MagicMock(return_value="response")
            middleware = TypesafeI18nMiddleware(
                get_response,
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            request = _make_request(accept_language="de")
            middleware(request)

            assert t(request, "hello", name="Welt") == "Hallo Welt!"
