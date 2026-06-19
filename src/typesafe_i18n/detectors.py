from __future__ import annotations

import os
from typing import Callable, TypeAlias

LocaleDetector: TypeAlias = Callable[[], list[str]]


def detect_locale(fallback: str, available: list[str], *detectors: LocaleDetector) -> str:
    lower_available = [loc.lower() for loc in available]
    for detector in detectors:
        detected = detector()
        for locale in detected:
            lower = locale.lower()
            candidates = [lower, lower.split("-")[0]] if "-" in lower else [lower]
            for candidate in candidates:
                for i, avail in enumerate(lower_available):
                    if avail == candidate:
                        return available[i]
    return fallback


def init_accept_language_header_detector(header_value: str) -> LocaleDetector:
    def detector() -> list[str]:
        if not header_value:
            return []
        parts = [p.strip() for p in header_value.split(",")]
        weighted: list[tuple[str, float]] = []
        for part in parts:
            segments = [s.strip() for s in part.split(";")]
            locale = segments[0]
            if not locale or locale == "*":
                continue
            q = 1.0
            for seg in segments[1:]:
                if seg.startswith("q="):
                    try:
                        q = float(seg[2:])
                    except ValueError:
                        q = 0.0
            weighted.append((locale, q))
        weighted.sort(key=lambda x: x[1], reverse=True)
        return [loc for loc, _ in weighted]

    return detector


def init_cookie_detector(cookie_value: str, key: str = "lang") -> LocaleDetector:
    def detector() -> list[str]:
        if not cookie_value:
            return []
        for part in cookie_value.split(";"):
            part = part.strip()
            if part.startswith(key):
                value = part.split("=", 1)[1] if "=" in part else ""
                if value:
                    return [value]
        return []

    return detector


def init_env_detector(key: str = "LANG") -> LocaleDetector:
    def detector() -> list[str]:
        value = os.environ.get(key, "")
        return [value] if value else []

    return detector


def init_query_string_detector(query_string: str, key: str = "lang") -> LocaleDetector:
    def detector() -> list[str]:
        if not query_string:
            return []
        qs = query_string.lstrip("?")
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                if k == key and v:
                    return [v]
        return []

    return detector


def navigator_detector(navigator_languages: list[str]) -> LocaleDetector:
    def detector() -> list[str]:
        return list(navigator_languages)

    return detector
