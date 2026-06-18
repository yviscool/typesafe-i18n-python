from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from typesafe_i18n.parser import extract_custom_types, extract_params, has_plural, validate_template


def generate(
    translations_dir: str | Path,
    output_dir: str | Path,
    base_locale: str = "en",
    check_missing: bool = True,
) -> list[str]:
    """Generate type stubs and utility files from translation YAML files.

    Returns list of warnings (e.g., missing translations in other locales).
    """
    translations_dir = Path(translations_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    base_file = _find_locale_file(translations_dir, base_locale)
    if not base_file:
        raise FileNotFoundError(f"Base locale file not found for '{base_locale}' in {translations_dir}")

    with open(base_file, encoding="utf-8") as f:
        base_translations: dict[str, Any] = yaml.safe_load(f) or {}

    flat_base = _flatten(base_translations)
    namespaces = _discover_namespaces(translations_dir, base_locale)

    all_flat: dict[str, str] = {}
    all_flat.update(flat_base)
    for ns_name, ns_translations in namespaces.items():
        ns_flat = _flatten(ns_translations, prefix=ns_name)
        all_flat.update(ns_flat)

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
        warnings = _check_missing_keys(translations_dir, base_locale, all_flat)

    for w in warnings:
        print(f"Warning: {w}")
    print(f"Generated type stubs in {output_dir}")

    return warnings + validation_errors


def _find_locale_file(translations_dir: Path, locale: str) -> Path | None:
    for ext in (".yaml", ".yml"):
        path = translations_dir / f"{locale}{ext}"
        if path.exists():
            return path
    return None


def _discover_namespaces(translations_dir: Path, locale: str) -> dict[str, dict[str, Any]]:
    locale_dir = translations_dir / locale
    namespaces: dict[str, dict[str, Any]] = {}
    if not locale_dir.is_dir():
        return namespaces
    for child in sorted(locale_dir.iterdir()):
        if child.is_dir():
            ns_file = _find_locale_file(child, locale)
            if ns_file:
                with open(ns_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                namespaces[child.name] = data
    return namespaces


def _flatten(d: dict[str, Any], prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for k, v in d.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            result.update(_flatten(v, key))
        elif isinstance(v, str):
            result[key] = v
    return result


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
                params_list.append(f"{name}: {python_type}")

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
                params_list.append(f"{name}: {python_type}")

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
    params = extract_params(template)
    if params:
        return next(iter(params))
    return "count"


def _check_missing_keys(
    translations_dir: Path,
    base_locale: str,
    base_keys: dict[str, str],
) -> list[str]:
    warnings: list[str] = []
    for f in translations_dir.iterdir():
        if f.is_dir():
            continue
        locale = f.stem
        if locale == base_locale:
            continue
        if f.suffix not in (".yaml", ".yml"):
            continue

        with open(f, encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}

        flat = _flatten(data)
        missing = set(base_keys.keys()) - set(flat.keys())
        if missing:
            for key in sorted(missing):
                warnings.append(f"Locale '{locale}' missing key: {key}")

    return warnings
