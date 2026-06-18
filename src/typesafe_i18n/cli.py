from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import yaml

from typesafe_i18n.generator import TranslationValidationError, generate
from typesafe_i18n.parser import validate_template
from typesafe_i18n.translation_files import collect_locales, flatten_translation_tree, iter_translation_files, load_locale_sections


def main() -> None:
    """CLI entry point for typesafe-i18n."""
    parser = argparse.ArgumentParser(
        prog="typesafe-i18n",
        description="Type-safe internationalization for Python",
    )
    subparsers = parser.add_subparsers(dest="command")

    gen_parser = subparsers.add_parser("generate", help="Generate type stubs from translations")
    gen_parser.add_argument("-d", "--dir", default="translations", help="Translations directory")
    gen_parser.add_argument("-o", "--output", default="_generated", help="Output directory")
    gen_parser.add_argument("-l", "--locale", default="en", help="Base locale")
    gen_parser.add_argument("--watch", action="store_true", help="Watch for changes and regenerate")
    gen_parser.add_argument("--no-check", action="store_true", help="Skip missing key checks")

    validate_parser = subparsers.add_parser("validate", help="Validate translations")
    validate_parser.add_argument("-d", "--dir", default="translations", help="Translations directory")
    validate_parser.add_argument("-l", "--locale", default="en", help="Base locale")

    extract_parser = subparsers.add_parser("extract", help="Extract translation keys from source")
    extract_parser.add_argument("source", help="Source directory to scan")
    extract_parser.add_argument("-d", "--dir", default="translations", help="Translations directory")
    extract_parser.add_argument("-l", "--locale", default="en", help="Base locale")

    export_parser = subparsers.add_parser("export", help="Export translations to JSON")
    export_parser.add_argument("-d", "--dir", default="translations", help="Translations directory")
    export_parser.add_argument("-o", "--output", default="translations.json", help="Output file")
    export_parser.add_argument("-l", "--locale", help="Export specific locale only")

    import_parser = subparsers.add_parser("import", help="Import translations from JSON")
    import_parser.add_argument("file", help="JSON file to import")
    import_parser.add_argument("-d", "--dir", default="translations", help="Translations directory")

    args = parser.parse_args()

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "validate":
        _cmd_validate(args)
    elif args.command == "extract":
        _cmd_extract(args)
    elif args.command == "export":
        _cmd_export(args)
    elif args.command == "import":
        _cmd_import(args)
    else:
        parser.print_help()
        sys.exit(1)


def _cmd_generate(args: argparse.Namespace) -> None:
    try:
        if args.watch:
            _watch_and_generate(args.dir, args.output, args.locale, not args.no_check)
        else:
            generate(args.dir, args.output, args.locale, check_missing=not args.no_check, fail_on_validation_error=True)
    except TranslationValidationError:
        sys.exit(1)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def _watch_and_generate(
    translations_dir: str,
    output_dir: str,
    base_locale: str,
    check_missing: bool,
) -> None:
    print(f"Watching {translations_dir} for changes...")
    last_modified = _get_last_modified(translations_dir)

    try:
        while True:
            time.sleep(0.5)
            current_modified = _get_last_modified(translations_dir)
            if current_modified != last_modified:
                print("\nChanges detected, regenerating...")
                try:
                    generate(translations_dir, output_dir, base_locale, check_missing=check_missing)
                except Exception as e:
                    print(f"Error: {e}", file=sys.stderr)
                last_modified = current_modified
    except KeyboardInterrupt:
        print("\nStopped watching.")


def _get_last_modified(directory: str) -> float:
    path = Path(directory)
    if not path.exists():
        return 0
    latest = 0.0
    for f in iter_translation_files(path):
        latest = max(latest, f.stat().st_mtime)
    return latest


def _cmd_validate(args: argparse.Namespace) -> None:
    translations_dir = Path(args.dir)
    if not translations_dir.exists():
        print(f"Error: Directory not found: {translations_dir}", file=sys.stderr)
        sys.exit(1)

    errors: list[str] = []
    warnings: list[str] = []

    base_sections = load_locale_sections(translations_dir, args.locale)
    if not base_sections:
        print(f"Error: Base locale file not found: {args.locale}", file=sys.stderr)
        sys.exit(1)

    base_flat_sections = {
        prefix: flatten_translation_tree(data, prefix=prefix) for prefix, data in base_sections.items()
    }

    for locale in collect_locales(translations_dir):
        locale_sections = load_locale_sections(translations_dir, locale)
        all_prefixes = sorted(set(base_flat_sections) | set(locale_sections))

        for prefix in all_prefixes:
            base_flat = base_flat_sections.get(prefix, {})
            current_flat = flatten_translation_tree(locale_sections.get(prefix, {}), prefix=prefix)

            missing = set(base_flat.keys()) - set(current_flat.keys())
            extra = set(current_flat.keys()) - set(base_flat.keys())

            for key in sorted(missing):
                warnings.append(f"[{locale}] Missing key: {key}")
            for key in sorted(extra):
                warnings.append(f"[{locale}] Extra key: {key}")

            for key, template in current_flat.items():
                errs = validate_template(template, f"{locale}.{key}")
                errors.extend(errs)

    if errors:
        print("Errors:")
        for e in errors:
            print(f"  {e}")
    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  {w}")
    if not errors and not warnings:
        print("All translations are valid!")

    sys.exit(1 if errors else 0)


def _cmd_extract(args: argparse.Namespace) -> None:
    source_dir = Path(args.source)
    translations_dir = Path(args.dir)

    if not source_dir.exists():
        print(f"Error: Source directory not found: {source_dir}", file=sys.stderr)
        sys.exit(1)

    import re
    t_call_re = re.compile(r'''(?:^|[^.\w])t\(\s*["']([^"']+)["']''')

    used_keys: set[str] = set()
    for py_file in source_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        for match in t_call_re.finditer(content):
            used_keys.add(match.group(1))

    base_sections = load_locale_sections(translations_dir, args.locale)
    defined_keys: set[str] = set()
    for prefix, data in base_sections.items():
        defined_keys.update(flatten_translation_tree(data, prefix=prefix).keys())

    unused = defined_keys - used_keys
    undefined = used_keys - defined_keys

    if undefined:
        print("Keys used in code but not defined:")
        for key in sorted(undefined):
            print(f"  {key}")
    if unused:
        print("\nKeys defined but not used in code:")
        for key in sorted(unused):
            print(f"  {key}")
    if not undefined and not unused:
        print("All keys are in sync!")


def _cmd_export(args: argparse.Namespace) -> None:
    translations_dir = Path(args.dir)
    if not translations_dir.exists():
        print(f"Error: Directory not found: {translations_dir}", file=sys.stderr)
        sys.exit(1)

    result: dict[str, dict[str, str]] = {}

    locales = [args.locale] if args.locale else collect_locales(translations_dir)
    for locale in locales:
        locale_sections = load_locale_sections(translations_dir, locale)
        flat: dict[str, str] = {}
        for prefix, data in locale_sections.items():
            flat.update(flatten_translation_tree(data, prefix=prefix))
        if flat:
            result[locale] = flat

    output_path = Path(args.output)
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(result, out, ensure_ascii=False, indent=2)

    print(f"Exported {len(result)} locale(s) to {args.output}")


def _cmd_import(args: argparse.Namespace) -> None:
    translations_dir = Path(args.dir)
    translations_dir.mkdir(parents=True, exist_ok=True)

    with open(args.file, encoding="utf-8") as f:
        data: dict[str, dict[str, str]] = json.load(f)

    for locale, translations in data.items():
        nested: dict[str, Any] = {}
        for key, value in translations.items():
            parts = key.split(".")
            obj = nested
            for part in parts[:-1]:
                obj = obj.setdefault(part, {})
            obj[parts[-1]] = value

        out_file = translations_dir / f"{locale}.yaml"
        with open(out_file, "w", encoding="utf-8") as f:
            yaml.dump(nested, f, allow_unicode=True, default_flow_style=False)
        print(f"Imported {len(translations)} keys to {out_file}")


if __name__ == "__main__":
    main()
