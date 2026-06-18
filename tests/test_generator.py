import pytest
import tempfile
from pathlib import Path

import yaml

from typesafe_i18n.generator import _flatten, _map_type, generate


class TestFlatten:
    def test_flat_dict(self):
        assert _flatten({"a": "1", "b": "2"}) == {"a": "1", "b": "2"}

    def test_nested_dict(self):
        data = {"user": {"name": "User Name", "email": "Email"}}
        assert _flatten(data) == {"user.name": "User Name", "user.email": "Email"}

    def test_deeply_nested(self):
        assert _flatten({"a": {"b": {"c": "value"}}}) == {"a.b.c": "value"}

    def test_mixed_types(self):
        data = {"a": "text", "b": {"c": "nested"}, "d": 123}
        assert _flatten(data) == {"a": "text", "b.c": "nested"}

    def test_empty_dict(self):
        assert _flatten({}) == {}


class TestMapType:
    def test_string(self):
        assert _map_type("string") == "str"
        assert _map_type("str") == "str"

    def test_number(self):
        assert _map_type("number") == "int | float"

    def test_int_float(self):
        assert _map_type("int") == "int"
        assert _map_type("float") == "float"

    def test_boolean(self):
        assert _map_type("boolean") == "bool"

    def test_none_unknown(self):
        assert _map_type(None) == "object"

    def test_custom_type(self):
        assert _map_type("MyType") == "MyType"

    def test_date(self):
        assert _map_type("Date") == "str"


class TestGenerate:
    def test_generates_files(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {
                    "hello": "Hello {name:string}!",
                    "items": "{count:number} {{item|items}}",
                    "simple": "Simple text",
                }
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)

                warnings = generate(trans_dir, out_dir, "en")
                assert (Path(out_dir) / "types.pyi").exists()
                assert (Path(out_dir) / "base_types.pyi").exists()
                assert (Path(out_dir) / "util.py").exists()
                assert (Path(out_dir) / "__init__.py").exists()

    def test_types_content(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"hello": "Hello {name:string}!", "simple": "Simple text"}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)

                generate(trans_dir, out_dir, "en")
                content = (Path(out_dir) / "types.pyi").read_text()
                assert 'Literal["hello"]' in content
                assert 'Literal["simple"]' in content
                assert "name: str" in content

    def test_missing_base_locale(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                with pytest.raises(FileNotFoundError):
                    generate(trans_dir, out_dir, "en")

    def test_nested_translations(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"user": {"greeting": "Hello {name:string}!"}}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)

                generate(trans_dir, out_dir, "en")
                content = (Path(out_dir) / "types.pyi").read_text()
                assert 'Literal["user.greeting"]' in content

    def test_yml_extension(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"hello": "Hi"}
                with open(Path(trans_dir) / "en.yml", "w") as f:
                    yaml.dump(en, f)

                generate(trans_dir, out_dir, "en")
                assert (Path(out_dir) / "types.pyi").exists()

    def test_missing_key_detection(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"hello": "Hi", "bye": "Bye"}
                zh = {"hello": "你好"}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)
                with open(Path(trans_dir) / "zh.yaml", "w") as f:
                    yaml.dump(zh, f)

                warnings = generate(trans_dir, out_dir, "en", check_missing=True)
                assert any("zh" in w and "bye" in w for w in warnings)

    def test_no_missing_keys(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"hello": "Hi"}
                zh = {"hello": "你好"}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)
                with open(Path(trans_dir) / "zh.yaml", "w") as f:
                    yaml.dump(zh, f)

                warnings = generate(trans_dir, out_dir, "en", check_missing=True)
                assert not any("missing" in w.lower() for w in warnings)

    def test_namespace_discovery(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"hello": "Hi"}
                ns_dir = Path(trans_dir) / "en" / "settings"
                ns_dir.mkdir(parents=True)
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)
                with open(ns_dir / "en.yaml", "w") as f:
                    yaml.dump({"title": "Settings"}, f)

                generate(trans_dir, out_dir, "en", check_missing=False)
                content = (Path(out_dir) / "types.pyi").read_text()
                assert 'Literal["settings.title"]' in content

    def test_custom_type_generation(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"result": "Result: {0:Sum|calculate}"}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)

                generate(trans_dir, out_dir, "en", check_missing=False)
                assert (Path(out_dir) / "custom_types.py").exists()
                content = (Path(out_dir) / "custom_types.py").read_text()
                assert "class Sum:" in content

    def test_validation_errors(self):
        with tempfile.TemporaryDirectory() as trans_dir:
            with tempfile.TemporaryDirectory() as out_dir:
                en = {"bad": "Hello {name"}
                with open(Path(trans_dir) / "en.yaml", "w") as f:
                    yaml.dump(en, f)

                warnings = generate(trans_dir, out_dir, "en", check_missing=False)
                assert any("unmatched" in w.lower() for w in warnings)
