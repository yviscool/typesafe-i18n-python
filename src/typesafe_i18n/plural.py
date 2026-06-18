from __future__ import annotations

from typing import Callable

_PluralRule = Callable[[int], str]


def get_plural_form(locale: str, count: int) -> str:
    """Get the CLDR plural category for a given locale and count.

    Returns one of: 'zero', 'one', 'two', 'few', 'many', 'other'
    """
    lang = locale.split("-")[0].split("_")[0].lower()
    rule = _PLURAL_RULES.get(lang, _plural_other)
    return rule(count)


def _plural_other(count: int) -> str:
    return "one" if count == 1 else "other"


def _plural_arabic(count: int) -> str:
    if count == 0:
        return "zero"
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    mod100 = count % 100
    if 3 <= mod100 <= 10:
        return "few"
    if 11 <= mod100 <= 99:
        return "many"
    return "other"


def _plural_polish(count: int) -> str:
    if count == 1:
        return "one"
    mod10 = count % 10
    mod100 = count % 100
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return "few"
    if mod10 == 0 or (5 <= mod10 <= 9) or (12 <= mod100 <= 14):
        return "many"
    return "other"


def _plural_russian(count: int) -> str:
    mod10 = count % 10
    mod100 = count % 100
    if mod10 == 1 and mod100 != 11:
        return "one"
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return "few"
    if mod10 == 0 or (5 <= mod10 <= 9) or (11 <= mod100 <= 14):
        return "many"
    return "other"


def _plural_czech(count: int) -> str:
    if count == 1:
        return "one"
    if 2 <= count <= 4:
        return "few"
    return "other"


def _plural_lithuanian(count: int) -> str:
    mod10 = count % 10
    mod100 = count % 100
    if mod10 == 1 and mod100 != 11:
        return "one"
    if 2 <= mod10 <= 9 and not 12 <= mod100 <= 19:
        return "few"
    return "other"


def _plural_latvian(count: int) -> str:
    if count == 0:
        return "zero"
    if count % 10 == 1 and count % 100 != 11:
        return "one"
    return "other"


def _plural_romanian(count: int) -> str:
    if count == 1:
        return "one"
    if count == 0 or (1 <= count % 100 <= 19):
        return "few"
    return "other"


def _plural_welsh(count: int) -> str:
    if count == 0:
        return "zero"
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    if count == 3:
        return "few"
    if count == 6:
        return "many"
    return "other"


def _plural_breton(count: int) -> str:
    if count == 1:
        return "one"
    if count == 2:
        return "two"
    if count == 3:
        return "few"
    if count == 6:
        return "many"
    return "other"


def _plural_french(count: int) -> str:
    if count == 0 or count == 1:
        return "one"
    return "other"


def _plural_spanish(count: int) -> str:
    if count == 1:
        return "one"
    return "other"


_plural_rules: dict[str, _PluralRule] = {
    "ar": _plural_arabic,
    "pl": _plural_polish,
    "ru": _plural_russian,
    "uk": _plural_russian,
    "cs": _plural_czech,
    "sk": _plural_czech,
    "lt": _plural_lithuanian,
    "lv": _plural_latvian,
    "ro": _plural_romanian,
    "cy": _plural_welsh,
    "br": _plural_breton,
    "fr": _plural_french,
    "es": _plural_spanish,
    "de": _plural_other,
    "it": _plural_spanish,
    "pt": _plural_spanish,
    "ja": _plural_other,
    "ko": _plural_other,
    "vi": _plural_other,
    "th": _plural_other,
    "tr": _plural_other,
    "nl": _plural_other,
    "sv": _plural_other,
    "da": _plural_other,
    "no": _plural_other,
    "fi": _plural_other,
    "hu": _plural_other,
    "el": _plural_other,
    "he": _plural_other,
    "hi": _plural_other,
    "id": _plural_other,
    "ms": _plural_other,
}

_PLURAL_RULES: dict[str, _PluralRule] = _plural_rules
