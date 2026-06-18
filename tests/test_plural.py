import pytest

from typesafe_i18n.plural import get_plural_form


class TestPluralRules:
    def test_english(self):
        assert get_plural_form("en", 0) == "other"
        assert get_plural_form("en", 1) == "one"
        assert get_plural_form("en", 2) == "other"
        assert get_plural_form("en", 5) == "other"
        assert get_plural_form("en", 100) == "other"

    def test_chinese(self):
        assert get_plural_form("zh", 0) == "other"
        assert get_plural_form("zh", 1) == "one"
        assert get_plural_form("zh", 100) == "other"

    def test_arabic(self):
        assert get_plural_form("ar", 0) == "zero"
        assert get_plural_form("ar", 1) == "one"
        assert get_plural_form("ar", 2) == "two"
        assert get_plural_form("ar", 5) == "few"
        assert get_plural_form("ar", 15) == "many"
        assert get_plural_form("ar", 100) == "other"
        assert get_plural_form("ar", 110) == "few"

    def test_polish(self):
        assert get_plural_form("pl", 1) == "one"
        assert get_plural_form("pl", 2) == "few"
        assert get_plural_form("pl", 5) == "many"
        assert get_plural_form("pl", 22) == "few"
        assert get_plural_form("pl", 12) == "many"

    def test_russian(self):
        assert get_plural_form("ru", 1) == "one"
        assert get_plural_form("ru", 2) == "few"
        assert get_plural_form("ru", 5) == "many"
        assert get_plural_form("ru", 21) == "one"
        assert get_plural_form("ru", 11) == "many"
        assert get_plural_form("ru", 111) == "many"

    def test_french(self):
        assert get_plural_form("fr", 0) == "one"
        assert get_plural_form("fr", 1) == "one"
        assert get_plural_form("fr", 2) == "other"
        assert get_plural_form("fr", 5) == "other"

    def test_spanish(self):
        assert get_plural_form("es", 1) == "one"
        assert get_plural_form("es", 2) == "other"
        assert get_plural_form("es", 0) == "other"

    def test_german(self):
        assert get_plural_form("de", 1) == "one"
        assert get_plural_form("de", 2) == "other"

    def test_japanese(self):
        assert get_plural_form("ja", 1) == "one"
        assert get_plural_form("ja", 0) == "other"
        assert get_plural_form("ja", 100) == "other"

    def test_czech(self):
        assert get_plural_form("cs", 1) == "one"
        assert get_plural_form("cs", 2) == "few"
        assert get_plural_form("cs", 5) == "other"

    def test_welsh(self):
        assert get_plural_form("cy", 0) == "zero"
        assert get_plural_form("cy", 1) == "one"
        assert get_plural_form("cy", 2) == "two"
        assert get_plural_form("cy", 3) == "few"
        assert get_plural_form("cy", 6) == "many"
        assert get_plural_form("cy", 10) == "other"

    def test_locale_with_region(self):
        assert get_plural_form("en-US", 1) == "one"
        assert get_plural_form("zh-CN", 1) == "one"
        assert get_plural_form("pt_BR", 1) == "one"
        assert get_plural_form("en-GB", 2) == "other"

    def test_unknown_locale_defaults(self):
        assert get_plural_form("xx", 1) == "one"
        assert get_plural_form("xx", 2) == "other"
