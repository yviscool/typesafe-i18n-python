from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TextPart:
    """Plain text segment of a translation template."""
    text: str


@dataclass(frozen=True)
class SwitchCase:
    """Switch-case branch definition."""
    cases: dict[str, str]
    default: str = ""


@dataclass(frozen=True)
class ArgPart:
    """Parameter placeholder in a translation template."""
    name: str
    type: str | None = None
    optional: bool = False
    formatters: tuple[str, ...] = ()
    switch: SwitchCase | None = None


@dataclass(frozen=True)
class PluralPart:
    """Plural form block in a translation template."""
    forms: tuple[str, ...]


Part = TextPart | ArgPart | PluralPart

_PLURAL_RE = re.compile(r"\{\{([^}]+)\}\}")
_BASE_TYPES = frozenset({
    "string", "str", "number", "int", "float", "boolean", "bool",
    "Date", "date", "array", "object", "bigint", "undefined", "null",
})


def parse_translation(template: str) -> list[Part]:
    """Parse a translation template string into its constituent parts."""
    parts: list[Part] = []
    pos = 0

    for match in _PLURAL_RE.finditer(template):
        start, end = match.span()
        if start > pos:
            _parse_args(template[pos:start], parts)
        forms = tuple(f.strip() for f in match.group(1).split("|"))
        parts.append(PluralPart(forms=forms))
        pos = end

    if pos < len(template):
        _parse_args(template[pos:], parts)

    return parts


def _parse_args(text: str, parts: list[Part]) -> None:
    pos = 0
    while pos < len(text):
        if text[pos] == "{":
            end = _find_matching_brace(text, pos)
            if end == -1:
                parts.append(TextPart(text=text[pos]))
                pos += 1
                continue
            inner = text[pos + 1 : end].strip()
            if inner:
                part = _parse_arg(inner)
                parts.append(part)
            pos = end + 1
        else:
            next_brace = text.find("{", pos)
            if next_brace == -1:
                parts.append(TextPart(text=text[pos:]))
                break
            else:
                parts.append(TextPart(text=text[pos:next_brace]))
                pos = next_brace


def _find_matching_brace(text: str, start: int) -> int:
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return -1


def _parse_arg(inner: str) -> ArgPart:
    optional = False
    name = ""
    type_name: str | None = None
    formatters: tuple[str, ...] = ()
    switch: SwitchCase | None = None

    pipe_parts = _split_pipes(inner)
    name_and_type = pipe_parts[0]

    if "?" in name_and_type:
        name_part, rest = name_and_type.split("?", 1)
        optional = True
        name = name_part.strip()
        if rest.startswith(":"):
            type_name = rest[1:].strip()
    elif ":" in name_and_type:
        name_part, rest = name_and_type.split(":", 1)
        name = name_part.strip()
        type_name = rest.strip()
    else:
        name = name_and_type.strip()

    if len(pipe_parts) > 1:
        last = pipe_parts[-1].strip()
        if last.startswith("{") and last.endswith("}"):
            switch = _parse_switch(last[1:-1])
            if len(pipe_parts) > 2:
                formatters = tuple(f.strip() for f in pipe_parts[1:-1])
        else:
            formatters = tuple(f.strip() for f in pipe_parts[1:])

    if not name:
        name = "0"

    return ArgPart(
        name=name,
        type=type_name,
        optional=optional,
        formatters=formatters,
        switch=switch,
    )


def _split_pipes(s: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in s:
        if ch == "{":
            depth += 1
            current.append(ch)
        elif ch == "}":
            depth -= 1
            current.append(ch)
        elif ch == "|" and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current))
    return parts


def _parse_switch(content: str) -> SwitchCase:
    cases: dict[str, str] = {}
    default = ""

    depth = 0
    current_key = ""
    current_value = ""
    in_value = False

    for ch in content:
        if ch == "{":
            depth += 1
            if in_value:
                current_value += ch
            else:
                current_key += ch
        elif ch == "}":
            depth -= 1
            if in_value:
                current_value += ch
            else:
                current_key += ch
        elif ch == ":" and depth == 0 and not in_value:
            in_value = True
        elif ch == "," and depth == 0:
            key = current_key.strip()
            value = current_value.strip()
            if key == "*":
                default = value
            elif key:
                cases[key] = value
            current_key = ""
            current_value = ""
            in_value = False
        else:
            if in_value:
                current_value += ch
            else:
                current_key += ch

    key = current_key.strip()
    value = current_value.strip()
    if key == "*":
        default = value
    elif key:
        cases[key] = value

    return SwitchCase(cases=cases, default=default)


def extract_params(template: str) -> dict[str, str | None]:
    """Extract parameter names and their types from a translation template."""
    parts = parse_translation(template)
    params: dict[str, str | None] = {}
    for part in parts:
        if isinstance(part, ArgPart):
            params[part.name] = part.type
    return params


def has_plural(template: str) -> bool:
    """Check if a translation template contains plural forms."""
    return "{{" in template


def extract_custom_types(template: str) -> set[str]:
    """Extract custom type names that are not in the base types set."""
    params = extract_params(template)
    custom: set[str] = set()
    for type_name in params.values():
        if type_name and type_name not in _BASE_TYPES:
            custom.add(type_name)
    return custom


def validate_template(template: str, key: str) -> list[str]:
    """Validate a translation template and return list of errors."""
    errors: list[str] = []
    depth = 0
    for i, ch in enumerate(template):
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth < 0:
                errors.append(f"Key '{key}': unmatched '}}' at position {i}")
                depth = 0
    if depth > 0:
        errors.append(f"Key '{key}': unmatched '{{' - missing {depth} closing brace(s)")
    return errors
