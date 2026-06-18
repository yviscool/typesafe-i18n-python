from __future__ import annotations

from pathlib import Path
from typing import Any

from typesafe_i18n.backends import TranslationBackend, YAMLBackend
from typesafe_i18n.parser import (
    PluralPart,
    extract_custom_types,
    extract_params,
    has_plural,
    normalize_placeholder_name,
    parse_translation,
    validate_template,
)
from typesafe_i18n.translation_files import collect_locales, flatten_translation_tree, load_locale_sections


class TranslationValidationError(RuntimeError):
    """Raised when generated translations contain template validation errors."""

    def __init__(self, errors: list[str]) -> None:
        super().__init__("\n".join(errors))
        self.errors = errors


def generate(
    translations_dir: str | Path,
    output_dir: str | Path,
    base_locale: str = "en",
    check_missing: bool = True,
    backend: TranslationBackend | None = None,
    fail_on_validation_error: bool = False,
) -> list[str]:
    """Generate type stubs and utility files from translation files.

    Returns list of warnings (e.g., missing translations in other locales).
    """
    translations_dir = Path(translations_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _backend = backend or YAMLBackend()

    base_sections = load_locale_sections(translations_dir, base_locale, _backend)
    if not base_sections:
        raise FileNotFoundError(f"Base locale file not found for '{base_locale}' in {translations_dir}")

    all_flat = _flatten_sections(base_sections)

    validation_errors = _validate_translations(all_flat)
    for err in validation_errors:
        print(f"Error: {err}")

    custom_types = _collect_custom_types(all_flat)

    stub = _generate_stub(all_flat, custom_types)
    (output_dir / "types.pyi").write_text(stub, encoding="utf-8")

    base_types = _generate_base_types(all_flat)
    (output_dir / "base_types.pyi").write_text(base_types, encoding="utf-8")

    runtime = _generate_runtime()
    (output_dir / "util.py").write_text(runtime, encoding="utf-8")

    if custom_types:
        custom = _generate_custom_types(custom_types)
        (output_dir / "custom_types.py").write_text(custom, encoding="utf-8")

    init_content = _generate_init(custom_types)
    (output_dir / "__init__.py").write_text(init_content, encoding="utf-8")

    warnings: list[str] = []
    if check_missing:
        warnings = _check_missing_keys(translations_dir, base_locale, base_sections, _backend)

    for w in warnings:
        print(f"Warning: {w}")
    print(f"Generated type stubs in {output_dir}")

    if fail_on_validation_error and validation_errors:
        raise TranslationValidationError(validation_errors)

    return warnings + validation_errors


def _validate_translations(translations: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for key, template in translations.items():
        errors.extend(validate_template(template, key))
    return errors


def _collect_custom_types(translations: dict[str, str]) -> set[str]:
    custom: set[str] = set()
    for template in translations.values():
        custom.update(extract_custom_types(template))
    return custom


def _generate_stub(translations: dict[str, str], custom_types: set[str]) -> str:
    lines: list[str] = []
    lines.append("from typing import Literal, overload, NewType")
    lines.append("")
    if custom_types:
        lines.append("from .custom_types import " + ", ".join(sorted(custom_types)))
        lines.append("")
    lines.append('LocalizedString = NewType("LocalizedString", str)')
    lines.append("")

    for key, template in sorted(translations.items()):
        params = extract_params(template)
        plural = has_plural(template)

        if not params and not plural:
            lines.append("@overload")
            lines.append(f'def t(key: Literal["{key}"]) -> LocalizedString: ...')
            lines.append("")
        else:
            params_list: list[str] = []
            for name, type_name in sorted(params.items()):
                python_type = _map_type(type_name)
                params_list.append(f"{normalize_placeholder_name(name)}: {python_type}")

            if plural and not params:
                count_param = _guess_plural_param(template)
                if count_param not in params:
                    params_list.append(f"{count_param}: int")

            if params_list:
                args_str = "*, " + ", ".join(params_list)
            else:
                args_str = ""
            lines.append("@overload")
            lines.append(f'def t(key: Literal["{key}"], {args_str}) -> LocalizedString: ...')
            lines.append("")

    lines.append("@overload")
    lines.append("def t(key: str, **kwargs: object) -> str: ...")
    lines.append("")

    return "\n".join(lines)


def _generate_base_types(translations: dict[str, str]) -> str:
    lines: list[str] = []
    lines.append("from typing import Literal, overload, NewType")
    lines.append("")
    lines.append('LocalizedString = NewType("LocalizedString", str)')
    lines.append('BaseTranslation = dict[str, str | dict]')
    lines.append('Translation = dict[str, str | dict]')
    lines.append("")

    for key, template in sorted(translations.items()):
        params = extract_params(template)
        plural = has_plural(template)

        if not params and not plural:
            lines.append("@overload")
            lines.append(f'def t(key: Literal["{key}"]) -> LocalizedString: ...')
            lines.append("")
        else:
            params_list: list[str] = []
            for name, type_name in sorted(params.items()):
                python_type = _map_type(type_name)
                params_list.append(f"{normalize_placeholder_name(name)}: {python_type}")

            if plural and not params:
                count_param = _guess_plural_param(template)
                if count_param not in params:
                    params_list.append(f"{count_param}: int")

            if params_list:
                args_str = "*, " + ", ".join(params_list)
            else:
                args_str = ""
            lines.append("@overload")
            lines.append(f'def t(key: Literal["{key}"], {args_str}) -> LocalizedString: ...')
            lines.append("")

    lines.append("@overload")
    lines.append("def t(key: str, **kwargs: object) -> str: ...")
    lines.append("")

    return "\n".join(lines)


def _generate_runtime() -> str:
    return '''from __future__ import annotations

from pathlib import Path
from typesafe_i18n.runtime import I18n as _I18n

_instance: _I18n | None = None


def init(translations_dir: str | Path, locale: str) -> None:
    """Initialize the global i18n instance."""
    global _instance
    _instance = _I18n(translations_dir, locale)


def t(key: str, **kwargs: object) -> str:
    """Translate a key using the global i18n instance."""
    if _instance is None:
        raise RuntimeError("Call init() first")
    return _instance.t(key, **kwargs)


def set_locale(locale: str) -> None:
    """Switch the global i18n instance to a different locale."""
    if _instance is None:
        raise RuntimeError("Call init() first")
    _instance.set_locale(locale)
'''


def _generate_custom_types(custom_types: set[str]) -> str:
    lines: list[str] = []
    lines.append("from __future__ import annotations")
    lines.append("")
    lines.append("")
    for type_name in sorted(custom_types):
        lines.append(f"class {type_name}:")
        lines.append(f'    """Custom type: {type_name}"""')
        lines.append("")
        lines.append("    def __init__(self, **kwargs: object) -> None:")
        lines.append("        for k, v in kwargs.items():")
        lines.append("            setattr(self, k, v)")
        lines.append("")
        lines.append("    def __str__(self) -> str:")
        lines.append(f'        return f"{type_name}(...)"')
        lines.append("")
        lines.append("")
    return "\n".join(lines)


def _generate_init(custom_types: set[str]) -> str:
    lines: list[str] = []
    lines.append("from typesafe_i18n.runtime import I18n")
    lines.append("from typesafe_i18n.generator import generate")
    lines.append("")
    if custom_types:
        lines.append("from .custom_types import " + ", ".join(sorted(custom_types)))
    lines.append("")
    lines.append('__all__ = ["I18n", "generate"' + "".join(f', "{t}"' for t in sorted(custom_types)) + "]")
    lines.append("")
    return "\n".join(lines)


def _map_type(type_name: str | None) -> str:
    if type_name is None:
        return "object"
    mapping = {
        "string": "str",
        "str": "str",
        "number": "int | float",
        "int": "int",
        "float": "float",
        "boolean": "bool",
        "bool": "bool",
        "Date": "str",
        "date": "str",
        "array": "list",
        "object": "dict",
    }
    return mapping.get(type_name, type_name)


def _guess_plural_param(template: str) -> str:
    for part in parse_translation(template):
        if isinstance(part, PluralPart):
            normalized = normalize_placeholder_name(part.key)
            if normalized:
                return normalized
    params = extract_params(template)
    if params:
        return normalize_placeholder_name(next(iter(params)))
    return "count"


def _flatten_sections(sections: dict[str, dict[str, Any]]) -> dict[str, str]:
    flat: dict[str, str] = {}
    for prefix, section in sections.items():
        flat.update(flatten_translation_tree(section, prefix=prefix))
    return flat


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, str]:
    return flatten_translation_tree(d, prefix=prefix)


def _check_missing_keys(
    translations_dir: Path,
    base_locale: str,
    base_sections: dict[str, dict[str, Any]],
    backend: TranslationBackend,
) -> list[str]:
    warnings: list[str] = []
    base_flat_sections = {
        prefix: flatten_translation_tree(data, prefix=prefix) for prefix, data in base_sections.items()
    }

    for locale in collect_locales(translations_dir):
        if locale == base_locale:
            continue

        locale_sections = load_locale_sections(translations_dir, locale, backend)
        for prefix, base_flat in base_flat_sections.items():
            current_flat = flatten_translation_tree(locale_sections.get(prefix, {}), prefix=prefix)
            missing = set(base_flat.keys()) - set(current_flat.keys())
            if missing:
                for key in sorted(missing):
                    warnings.append(f"Locale '{locale}' missing key: {key}")

    return warnings
