from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from typesafe_i18n.translation_files import (
    collect_locales,
    extend_dictionary,
    flatten_translation_tree,
    iter_locale_files,
    iter_translation_files,
    load_locale_sections,
    load_locale_with_fallback,
    locale_prefix,
)


class TestFlattenTranslationTree:
    def test_flat_dict(self):
        data = {"hello": "Hello", "bye": "Bye"}
        assert flatten_translation_tree(data) == {"hello": "Hello", "bye": "Bye"}

    def test_nested_dict(self):
        data = {"user": {"name": "Name", "age": "Age"}}
        result = flatten_translation_tree(data)
        assert result == {"user.name": "Name", "user.age": "Age"}

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": "value"}}}
        assert flatten_translation_tree(data) == {"a.b.c": "value"}

    def test_mixed_types(self):
        data = {"text": "hello", "nested": {"inner": "world"}, "number": 42}
        result = flatten_translation_tree(data)
        assert result == {"text": "hello", "nested.inner": "world"}

    def test_empty_dict(self):
        assert flatten_translation_tree({}) == {}


class TestIterTranslationFiles:
    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert iter_translation_files(Path(tmpdir)) == []

    def test_nonexistent_dir(self):
        assert iter_translation_files(Path("/nonexistent")) == []

    def test_finds_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.yaml").write_text("hello: Hi")
            files = iter_translation_files(Path(tmpdir))
            assert len(files) == 1
            assert files[0].suffix == ".yaml"

    def test_finds_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.json").write_text('{"hello": "Hi"}')
            files = iter_translation_files(Path(tmpdir))
            assert len(files) == 1

    def test_ignores_unsupported(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.txt").write_text("hello")
            (Path(tmpdir) / "en.yaml").write_text("hello: Hi")
            files = iter_translation_files(Path(tmpdir))
            assert len(files) == 1

    def test_sorted_output(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "zh.yaml").write_text("hello: 你好")
            (Path(tmpdir) / "en.yaml").write_text("hello: Hi")
            files = iter_translation_files(Path(tmpdir))
            assert files[0].stem == "en"
            assert files[1].stem == "zh"


class TestCollectLocales:
    def test_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert collect_locales(Path(tmpdir)) == []

    def test_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.yaml").write_text("hello: Hi")
            (Path(tmpdir) / "zh.yaml").write_text("hello: 你好")
            (Path(tmpdir) / "de.yaml").write_text("hello: Hallo")
            assert collect_locales(Path(tmpdir)) == ["de", "en", "zh"]


class TestIterLocaleFiles:
    def test_root_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.yaml").write_text("hello: Hi")
            files = iter_locale_files(Path(tmpdir), "en")
            assert len(files) == 1

    def test_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            locale_dir = Path(tmpdir) / "en"
            locale_dir.mkdir()
            (locale_dir / "en.yaml").write_text("hello: Hi")
            files = iter_locale_files(Path(tmpdir), "en")
            assert len(files) == 1

    def test_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert iter_locale_files(Path(tmpdir), "en") == []


class TestLocalePrefix:
    def test_root_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "en.yaml"
            assert locale_prefix(Path(tmpdir), "en", path) == ""

    def test_subdirectory_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            locale_dir = Path(tmpdir) / "en"
            locale_dir.mkdir()
            path = locale_dir / "en.yaml"
            assert locale_prefix(Path(tmpdir), "en", path) == ""

    def test_nested_subdirectory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = Path(tmpdir) / "en" / "auth"
            nested.mkdir(parents=True)
            path = nested / "en.yaml"
            assert locale_prefix(Path(tmpdir), "en", path) == "auth"


class TestLoadLocaleSections:
    def test_simple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "Hi", "bye": "Bye"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(data, f)
            sections = load_locale_sections(Path(tmpdir), "en")
            assert "" in sections
            assert sections[""] == {"hello": "Hi", "bye": "Bye"}

    def test_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            assert load_locale_sections(Path(tmpdir), "en") == {}


class TestExtendDictionary:
    def test_flat_merge(self):
        base = {"a": "1", "b": "2"}
        over = {"b": "3", "c": "4"}
        result = extend_dictionary(base, over)
        assert result == {"a": "1", "b": "3", "c": "4"}

    def test_nested_merge(self):
        base = {"user": {"name": "Alice", "age": "30"}}
        over = {"user": {"age": "31"}}
        result = extend_dictionary(base, over)
        assert result == {"user": {"name": "Alice", "age": "31"}}

    def test_deep_nested_merge(self):
        base = {"a": {"b": {"c": "1", "d": "2"}}}
        over = {"a": {"b": {"c": "3"}}}
        result = extend_dictionary(base, over)
        assert result == {"a": {"b": {"c": "3", "d": "2"}}}

    def test_override_dict_with_string(self):
        base = {"a": {"b": "1"}}
        over = {"a": "2"}
        result = extend_dictionary(base, over)
        assert result == {"a": "2"}

    def test_override_string_with_dict(self):
        base = {"a": "1"}
        over = {"a": {"b": "2"}}
        result = extend_dictionary(base, over)
        assert result == {"a": {"b": "2"}}

    def test_empty_base(self):
        assert extend_dictionary({}, {"a": "1"}) == {"a": "1"}

    def test_empty_overrides(self):
        assert extend_dictionary({"a": "1"}, {}) == {"a": "1"}

    def test_both_empty(self):
        assert extend_dictionary({}, {}) == {}

    def test_does_not_mutate_base(self):
        base = {"a": {"b": "1"}}
        over = {"a": {"b": "2"}}
        extend_dictionary(base, over)
        assert base["a"]["b"] == "1"


class TestLoadLocaleWithFallback:
    def test_fills_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello", "bye": "Bye"}
            zh = {"hello": "你好"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            result = load_locale_with_fallback(Path(tmpdir), "zh", "en")
            assert result["hello"] == "你好"
            assert result["bye"] == "Bye"

    def test_locale_overrides_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            zh = {"hello": "你好"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            result = load_locale_with_fallback(Path(tmpdir), "zh", "en")
            assert result["hello"] == "你好"

    def test_only_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            result = load_locale_with_fallback(Path(tmpdir), "zh", "en")
            assert result == {"hello": "Hello"}

    def test_nested_merge_with_fallback(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"user": {"name": "Alice", "age": "30"}}
            zh = {"user": {"name": "爱丽丝"}}
            with open(Path(tmpdir) / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w") as f:
                yaml.dump(zh, f)
            result = load_locale_with_fallback(Path(tmpdir), "zh", "en")
            assert result["user"]["name"] == "爱丽丝"
            assert result["user"]["age"] == "30"

    def test_both_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "en.yaml").write_text("{}")
            (Path(tmpdir) / "zh.yaml").write_text("{}")
            result = load_locale_with_fallback(Path(tmpdir), "zh", "en")
            assert result == {}
