from __future__ import annotations

import re
from datetime import date, datetime, time

import pytest

from typesafe_i18n.formatters import (
    currency,
    date as date_formatter,
    ignore,
    identity,
    lowercase,
    number,
    replace,
    time as time_formatter,
    uppercase,
)


class TestDate:
    def test_default_format(self):
        fmt = date_formatter("en")
        d = datetime(2024, 1, 15)
        assert fmt(d) == "2024-01-15"

    def test_with_weekday_long(self):
        fmt = date_formatter("en", {"weekday": "long"})
        d = datetime(2024, 1, 15)
        assert fmt(d) == "Monday"

    def test_with_weekday_short(self):
        fmt = date_formatter("en", {"weekday": "short"})
        d = datetime(2024, 1, 15)
        assert fmt(d) == "Mon"

    def test_with_year_numeric(self):
        fmt = date_formatter("en", {"year": "numeric", "month": "long", "day": "numeric"})
        d = datetime(2024, 1, 15)
        result = fmt(d)
        assert "2024" in result
        assert "January" in result
        assert "15" in result

    def test_with_month_short(self):
        fmt = date_formatter("en", {"month": "short", "day": "2-digit"})
        d = datetime(2024, 3, 5)
        result = fmt(d)
        assert "Mar" in result
        assert "05" in result

    def test_date_object(self):
        fmt = date_formatter("en")
        d = date(2024, 6, 20)
        assert fmt(d) == "2024-06-20"

    def test_iso_string(self):
        fmt = date_formatter("en")
        assert fmt("2024-03-10") == "2024-03-10"

    def test_timestamp(self):
        fmt = date_formatter("en")
        ts = datetime(2024, 1, 1).timestamp()
        assert fmt(ts) == "2024-01-01"

    def test_none_options(self):
        fmt = date_formatter("en", None)
        d = datetime(2024, 1, 15)
        assert fmt(d) == "2024-01-15"

    def test_custom_separator(self):
        fmt = date_formatter("en", {"year": "numeric", "month": "2-digit", "day": "2-digit", "separator": "-"})
        d = datetime(2024, 1, 15)
        assert fmt(d) == "2024-01-15"


class TestTime:
    def test_default_format(self):
        fmt = time_formatter("en")
        t = time(14, 30, 45)
        assert fmt(t) == "14:30:45"

    def test_hour_minute(self):
        fmt = time_formatter("en", {"hour": "numeric", "minute": "2-digit"})
        t = time(9, 5)
        result = fmt(t)
        assert "09" in result
        assert "05" in result

    def test_12hour(self):
        fmt = time_formatter("en", {"hour": "numeric", "hour12": True})
        t = time(14, 30)
        result = fmt(t)
        assert "02" in result
        assert "PM" in result

    def test_datetime_input(self):
        fmt = time_formatter("en")
        dt = datetime(2024, 1, 15, 8, 30, 0)
        assert fmt(dt) == "08:30:00"

    def test_timestamp_input(self):
        fmt = time_formatter("en")
        ts = datetime(2024, 1, 1, 12, 0, 0).timestamp()
        result = fmt(ts)
        assert "12:00:00" in result

    def test_none_options(self):
        fmt = time_formatter("en", None)
        t = time(10, 20, 30)
        assert fmt(t) == "10:20:30"


class TestNumber:
    def test_integer(self):
        fmt = number("en")
        result = fmt(1234)
        assert "1,234" in result

    def test_float(self):
        fmt = number("en")
        result = fmt(1234.56)
        assert "1,234.56" in result

    def test_with_max_digits(self):
        fmt = number("en", {"maximumFractionDigits": 2})
        result = fmt(1234.5678)
        assert "1,234.57" in result

    def test_zero(self):
        fmt = number("en")
        assert "0" in fmt(0)

    def test_negative(self):
        fmt = number("en")
        result = fmt(-42)
        assert "42" in result


class TestCurrency:
    def test_usd(self):
        fmt = currency("en", "USD")
        result = fmt(1234.5)
        assert result == "USD 1,234.50"

    def test_eur(self):
        fmt = currency("en", "EUR")
        result = fmt(99.99)
        assert result == "EUR 99.99"

    def test_integer_value(self):
        fmt = currency("en", "JPY")
        result = fmt(1000)
        assert result == "JPY 1,000.00"

    def test_negative(self):
        fmt = currency("en", "USD")
        result = fmt(-50.25)
        assert result == "USD -50.25"

    def test_zero(self):
        fmt = currency("en", "GBP")
        assert fmt(0) == "GBP 0.00"


class TestReplace:
    def test_simple_replace(self):
        fmt = replace(r"cat", "dog")
        assert fmt("I have a cat") == "I have a dog"

    def test_regex_replace(self):
        fmt = replace(r"\d+", "#")
        assert fmt("abc123def456") == "abc#def#"

    def test_no_match(self):
        fmt = replace(r"xyz", "abc")
        assert fmt("hello world") == "hello world"

    def test_with_groups(self):
        fmt = replace(r"(\w+) (\w+)", r"\2 \1")
        assert fmt("hello world") == "world hello"

    def test_non_string_input(self):
        fmt = replace(r"\d+", "N")
        assert fmt(123) == "N"


class TestIdentity:
    def test_string(self):
        assert identity("hello") == "hello"

    def test_number(self):
        assert identity(42) == "42"

    def test_none(self):
        assert identity(None) == "None"

    def test_bool(self):
        assert identity(True) == "True"


class TestIgnore:
    def test_string(self):
        assert ignore("hello") == ""

    def test_number(self):
        assert ignore(42) == ""

    def test_none(self):
        assert ignore(None) == ""


class TestUppercase:
    def test_lowercase(self):
        assert uppercase("hello") == "HELLO"

    def test_mixed(self):
        assert uppercase("Hello World") == "HELLO WORLD"

    def test_already_upper(self):
        assert uppercase("ABC") == "ABC"

    def test_number(self):
        assert uppercase(123) == "123"

    def test_empty(self):
        assert uppercase("") == ""


class TestLowercase:
    def test_uppercase(self):
        assert lowercase("HELLO") == "hello"

    def test_mixed(self):
        assert lowercase("Hello World") == "hello world"

    def test_already_lower(self):
        assert lowercase("abc") == "abc"

    def test_number(self):
        assert lowercase(123) == "123"

    def test_empty(self):
        assert lowercase("") == ""
