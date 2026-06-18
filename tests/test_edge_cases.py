import tempfile
from pathlib import Path

import yaml

from typesafe_i18n.runtime import I18n
from typesafe_i18n.parser import validate_template


class TestYAMLSpecialChars:
    def test_exclamation_mark(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "Hello {name}!"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("hello", name="World") == "Hello World!"

    def test_colon_in_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"info": "Name: {name:string}"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("info", name="test") == "Name: test"

    def test_curly_braces_in_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"code": "Use {{braces}} for display"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert "braces" in i18n.t("code")

    def test_hash_in_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"comment": "This is # not a comment"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert "#" in i18n.t("comment")

    def test_percent_in_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"discount": "Save 50% today!"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert "50%" in i18n.t("discount")

    def test_quotes_in_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"quote": 'He said "hello"'}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert "hello" in i18n.t("quote")

    def test_multiline_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"long": "Line 1\nLine 2\nLine 3"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            result = i18n.t("long")
            assert "Line 1" in result


class TestEmptyTranslations:
    def test_empty_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data: dict = {}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("anything") == "anything"

    def test_empty_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"empty": ""}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("empty") == ""

    def test_none_value(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"null_val": None}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("null_val") == "null_val"


class TestEncoding:
    def test_utf8_chinese(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "你好 {name}！"}
            with open(Path(tmpdir) / "zh.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "zh")
            assert "你好" in i18n.t("hello", name="世界")

    def test_utf8_japanese(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "こんにちは {name}！"}
            with open(Path(tmpdir) / "ja.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "ja")
            assert "こんにちは" in i18n.t("hello", name="世界")

    def test_utf8_arabic(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "مرحبا {name}"}
            with open(Path(tmpdir) / "ar.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "ar")
            assert "مرحبا" in i18n.t("hello", name="test")

    def test_utf8_emoji(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"greeting": "Hello {name} 👋"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
            i18n = I18n(tmpdir, "en")
            assert "👋" in i18n.t("greeting", name="World")


class TestValidationEdgeCases:
    def test_valid_nested_braces(self):
        assert validate_template("{gender|{male:He,female:She}}", "test") == []

    def test_unmatched_open(self):
        errors = validate_template("Hello {name", "test")
        assert len(errors) == 1

    def test_unmatched_close(self):
        errors = validate_template("Hello name}!", "test")
        assert len(errors) == 1

    def test_empty_template(self):
        assert validate_template("", "test") == []

    def test_only_text(self):
        assert validate_template("Hello World", "test") == []
