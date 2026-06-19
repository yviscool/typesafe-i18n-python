from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import yaml

from typesafe_i18n.contrib.flask import TypesafeI18n


def _make_translations(tmpdir: str) -> None:
    trans_dir = Path(tmpdir) / "translations"
    trans_dir.mkdir(exist_ok=True)
    with open(trans_dir / "en.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hello {name:string}!", "bye": "Bye!"}, f)
    with open(trans_dir / "de.yaml", "w", encoding="utf-8") as f:
        yaml.dump({"hello": "Hallo {name:string}!", "bye": "Tschüss!"}, f)


def _create_mock_flask() -> MagicMock:
    flask_mod = MagicMock()
    flask_g = SimpleNamespace()
    flask_mod.g = flask_g
    flask_mod.request = MagicMock()
    flask_mod.request.headers = {}
    flask_mod.request.query_string = b""
    flask_mod.request.args = {}
    flask_mod.current_app = MagicMock()
    return flask_mod


class TestTypesafeI18n:
    def test_init_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            app = MagicMock()
            app.config = {
                "I18N_TRANSLATIONS_DIR": trans_dir,
                "I18N_DEFAULT_LOCALE": "en",
                "I18N_AVAILABLE_LOCALES": ["en", "de"],
            }
            app.extensions = {}

            ext = TypesafeI18n()
            ext.init_app(app)

            assert "typesafe_i18n" in app.extensions
            assert app.extensions["typesafe_i18n"] is ext
            app.before_request.assert_called_once()
            app.context_processor.assert_called_once()

    def test_constructor_with_app(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            app = MagicMock()
            app.config = {
                "I18N_TRANSLATIONS_DIR": trans_dir,
                "I18N_DEFAULT_LOCALE": "en",
            }
            app.extensions = {}

            ext = TypesafeI18n(app=app)

            assert "typesafe_i18n" in app.extensions

    def test_detect_locale_accept_language(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace()
            flask_mod.request.headers = {"Accept-Language": "de-CH,de;q=0.9,en;q=0.8"}
            flask_mod.request.query_string = b""

            sys.modules["flask"] = flask_mod
            try:
                ext._set_locale()
                assert flask_mod.g.i18n_locale == "de"
                assert flask_mod.g.i18n.t("hello", name="Welt") == "Hallo Welt!"
            finally:
                del sys.modules["flask"]

    def test_detect_locale_cookie(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace()
            flask_mod.request.headers = {"Cookie": "session=abc;lang=de"}
            flask_mod.request.query_string = b""

            sys.modules["flask"] = flask_mod
            try:
                ext._set_locale()
                assert flask_mod.g.i18n_locale == "de"
            finally:
                del sys.modules["flask"]

    def test_detect_locale_query_string(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(
                translations_dir=trans_dir,
                available_locales=["en", "de"],
            )

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace()
            flask_mod.request.headers = {}
            flask_mod.request.query_string = b"lang=de"

            sys.modules["flask"] = flask_mod
            try:
                ext._set_locale()
                assert flask_mod.g.i18n_locale == "de"
            finally:
                del sys.modules["flask"]

    def test_detect_locale_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(
                translations_dir=trans_dir,
                default_locale="en",
            )

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace()
            flask_mod.request.headers = {}
            flask_mod.request.query_string = b""

            sys.modules["flask"] = flask_mod
            try:
                ext._set_locale()
                assert flask_mod.g.i18n_locale == "en"
            finally:
                del sys.modules["flask"]

    def test_inject_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir)

            i18n = ext._get_instance("en")

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace(i18n=i18n)

            sys.modules["flask"] = flask_mod
            try:
                context = ext._inject_context()
                assert "i18n" in context
                assert "t" in context
                assert context["t"]("hello", name="World") == "Hello World!"
            finally:
                del sys.modules["flask"]

    def test_get_i18n_with_locale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir)
            i18n = ext.get_i18n(locale="en")
            assert i18n.locale == "en"

    def test_get_i18n_from_g(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir)
            i18n = ext._get_instance("en")

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace(i18n=i18n)

            sys.modules["flask"] = flask_mod
            try:
                result = ext.get_i18n()
                assert result.locale == "en"
            finally:
                del sys.modules["flask"]

    def test_get_i18n_from_g_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir, default_locale="en")

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace()

            sys.modules["flask"] = flask_mod
            try:
                result = ext.get_i18n()
                assert result.locale == "en"
            finally:
                del sys.modules["flask"]

    def test_instance_caching(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir)
            i18n1 = ext._get_instance("en")
            i18n2 = ext._get_instance("en")
            assert i18n1 is i18n2

    def test_fallback_for_missing_locale(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            ext = TypesafeI18n(translations_dir=trans_dir, default_locale="en")
            i18n = ext._get_instance("fr")
            assert i18n.locale == "en"


class TestTFunction:
    def test_translates(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            _make_translations(tmpdir)
            trans_dir = str(Path(tmpdir) / "translations")

            from typesafe_i18n.contrib.flask import t

            ext = TypesafeI18n(translations_dir=trans_dir)

            app = MagicMock()
            app.config = {"I18N_TRANSLATIONS_DIR": trans_dir, "I18N_DEFAULT_LOCALE": "en"}
            app.extensions = {}
            ext.init_app(app)

            i18n = ext._get_instance("en")

            flask_mod = _create_mock_flask()
            flask_mod.g = SimpleNamespace(i18n=i18n)
            flask_mod.current_app = MagicMock()
            flask_mod.current_app.extensions = {"typesafe_i18n": ext}

            sys.modules["flask"] = flask_mod
            try:
                result = t("hello", name="World")
                assert result == "Hello World!"
            finally:
                del sys.modules["flask"]
