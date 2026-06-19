from __future__ import annotations

import locale as _locale
import re
import threading
from datetime import date as _date, datetime, time as _time
from typing import Any, Callable

_locale_lock = threading.Lock()


def date(locale: str, options: dict[str, Any] | None = None) -> Callable[[Any], str]:
    opts = options or {}

    def _format(value: Any) -> str:
        if isinstance(value, (int, float)):
            value = datetime.fromtimestamp(value)
        if isinstance(value, _date) and not isinstance(value, datetime):
            value = datetime(value.year, value.month, value.day)
        if not isinstance(value, datetime):
            value = datetime.fromisoformat(str(value))
        if opts:
            return str(value.strftime(_build_date_format(opts)))
        return str(value.strftime("%Y-%m-%d"))

    return _format


def time(locale: str, options: dict[str, Any] | None = None) -> Callable[[Any], str]:
    opts = options or {}

    def _format(value: Any) -> str:
        if isinstance(value, (int, float)):
            value = datetime.fromtimestamp(value).time()
        if isinstance(value, datetime):
            value = value.time()
        if isinstance(value, _time):
            if opts:
                return value.strftime(_build_time_format(opts))
            return value.strftime("%H:%M:%S")
        return str(value)

    return _format


def number(locale: str, options: dict[str, Any] | None = None) -> Callable[[Any], str]:
    opts = options or {}

    def _format(value: Any) -> str:
        with _locale_lock:
            saved = _locale.getlocale(_locale.LC_NUMERIC)
            try:
                _locale.setlocale(_locale.LC_NUMERIC, locale)
            except _locale.Error:
                pass
            try:
                digits = opts.get("maximumFractionDigits")
                if digits is not None:
                    return _locale.format_string(f"%.{int(digits)}f", float(value), grouping=True)
                v = float(value)
                if v == int(v):
                    return _locale.format_string("%d", int(v), grouping=True)
                return _locale.format_string("%.2f", v, grouping=True)
            finally:
                try:
                    _locale.setlocale(_locale.LC_NUMERIC, saved)
                except _locale.Error:
                    pass

    return _format


def currency(locale: str, currency_code: str) -> Callable[[Any], str]:
    def _format(value: Any) -> str:
        return f"{currency_code} {float(value):,.2f}"

    return _format


def replace(pattern: str, replacement: str) -> Callable[[Any], str]:
    _re = re.compile(pattern)

    def _format(value: Any) -> str:
        return _re.sub(replacement, str(value))

    return _format


def identity(value: Any) -> str:
    return str(value)


def ignore(value: Any) -> str:
    return ""


def uppercase(value: Any) -> str:
    return str(value).upper()


def lowercase(value: Any) -> str:
    return str(value).lower()


def _build_date_format(opts: dict[str, Any]) -> str:
    parts: list[str] = []
    weekday = opts.get("weekday")
    year = opts.get("year")
    month = opts.get("month")
    day = opts.get("day")

    if weekday == "long":
        parts.append("%A")
    elif weekday == "short":
        parts.append("%a")

    if year == "numeric":
        parts.append("%Y")
    elif year == "2-digit":
        parts.append("%y")

    if month == "numeric":
        parts.append("%m")
    elif month == "2-digit":
        parts.append("%m")
    elif month == "long":
        parts.append("%B")
    elif month == "short":
        parts.append("%b")

    if day == "numeric":
        parts.append("%d")
    elif day == "2-digit":
        parts.append("%d")

    if not parts:
        return "%Y-%m-%d"

    sep = str(opts.get("separator", " "))
    return sep.join(parts)


def _build_time_format(opts: dict[str, Any]) -> str:
    parts: list[str] = []
    hour = opts.get("hour")
    minute = opts.get("minute")
    second = opts.get("second")
    hour12 = opts.get("hour12", False)

    if hour is not None:
        if hour12:
            parts.append("%I")
        else:
            parts.append("%H")

    if minute is not None:
        parts.append("%M")

    if second is not None:
        parts.append("%S")

    if hour12:
        parts.append("%p")

    if not parts:
        return "%H:%M:%S"

    return ":".join(parts)
