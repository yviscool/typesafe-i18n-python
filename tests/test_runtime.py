import pytest
import tempfile
from pathlib import Path

import yaml

from typesafe_i18n.runtime import I18n


@pytest.fixture
def translations_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        en = {
            "hello": "Hello {name:string}!",
            "items": "{count:number} {{item|items}}",
            "simple": "Simple text",
            "age": "{name:string} is {age:number} years old",
            "greeting": "Good {time:string}",
            "optional": "Hello {name?}",
            "upper": "Hello {name:string|upper}!",
            "chain": "{name:string|trim|upper}",
            "switch": "{gender|{male:He,female:She,*:They}} replied",
            "fmt_switch": "{status:string|lower|{active:OK,inactive:Off}}",
        }
        zh = {
            "hello": "你好 {name:string}！",
            "items": "{count:number} 个项目",
            "simple": "简单文本",
            "age": "{name:string} 今年 {age:number} 岁",
            "greeting": "{time:string}好",
            "optional": "你好 {name?}",
        }
        with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
            yaml.dump(en, f, allow_unicode=True)
        with open(Path(tmpdir) / "zh.yaml", "w", encoding="utf-8") as f:
            yaml.dump(zh, f, allow_unicode=True)
        yield tmpdir


class TestI18nBasic:
    def test_simple_text(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("simple") == "Simple text"

    def test_named_arg(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("hello", name="World") == "Hello World!"

    def test_multiple_args(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("age", name="Alice", age=30) == "Alice is 30 years old"

    def test_missing_key(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("nonexistent") == "nonexistent"

    def test_missing_file(self, translations_dir):
        with pytest.raises(FileNotFoundError):
            I18n(translations_dir, "fr")

    def test_nested_key(self, translations_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"user": {"greeting": "Hello {name:string}!"}}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("user.greeting", name="World") == "Hello World!"

    def test_missing_nested_key(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("user.nonexistent") == "user.nonexistent"


class TestI18nPlural:
    def test_plural_one(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("items", count=1) == "1 item"

    def test_plural_other(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("items", count=5) == "5 items"

    def test_plural_zero(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("items", count=0) == "0 items"

    def test_plural_uses_matching_key(self, translations_dir):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {
                "message": "{other:number} {{count:item|items}}",
            }
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("message", count=1, other=2) == "2 item"


class TestI18nFormatters:
    def test_single_formatter(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        i18n.set_formatters({"upper": lambda v: v.upper()})
        assert i18n.t("upper", name="world") == "Hello WORLD!"

    def test_formatter_chain(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        i18n.set_formatters({
            "trim": lambda v: v.strip(),
            "upper": lambda v: v.upper(),
        })
        assert i18n.t("chain", name="  world  ") == "WORLD"

    def test_formatter_not_registered(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("upper", name="world") == "Hello world!"


class TestI18nSwitchCase:
    def test_switch_case_male(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("switch", gender="male") == "He replied"

    def test_switch_case_female(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("switch", gender="female") == "She replied"

    def test_switch_case_default(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("switch", gender="other") == "They replied"

    def test_formatter_then_switch(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        i18n.set_formatters({"lower": lambda v: v.lower()})
        assert i18n.t("fmt_switch", status="ACTIVE") == "OK"


class TestI18nLocale:
    def test_chinese_locale(self, translations_dir):
        i18n = I18n(translations_dir, "zh")
        assert "你好" in i18n.t("hello", name="World")

    def test_set_locale(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("simple") == "Simple text"
        i18n.set_locale("zh")
        assert i18n.t("simple") == "简单文本"

    def test_locale_property(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.locale == "en"
        i18n.set_locale("zh")
        assert i18n.locale == "zh"

    def test_yml_extension_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "Hi"}
            with open(Path(tmpdir) / "en.yml", "w") as f:
                yaml.dump(data, f)
            i18n = I18n(tmpdir, "en")
            assert i18n.t("hello") == "Hi"


class TestI18nOptional:
    def test_optional_present(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("optional", name="World") == "Hello World"

    def test_optional_missing(self, translations_dir):
        i18n = I18n(translations_dir, "en")
        assert i18n.t("optional") == "Hello "
