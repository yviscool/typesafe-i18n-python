import json
import tempfile
from pathlib import Path

import pytest
import yaml

from typesafe_i18n.backends import JSONBackend, TOMLBackend, YAMLBackend, get_backend, get_backend_for_file


class TestYAMLBackend:
    def test_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as f:
            yaml.dump({"hello": "Hi"}, f)
            f.flush()
            backend = YAMLBackend()
            data = backend.load(Path(f.name))
            assert data == {"hello": "Hi"}

    def test_save(self):
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            backend = YAMLBackend()
            backend.save(Path(f.name), {"hello": "Hi"})
            with open(f.name, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            assert data == {"hello": "Hi"}

    def test_extensions(self):
        backend = YAMLBackend()
        assert ".yaml" in backend.extensions()
        assert ".yml" in backend.extensions()


class TestJSONBackend:
    def test_load(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"hello": "Hi"}, f)
            f.flush()
            backend = JSONBackend()
            data = backend.load(Path(f.name))
            assert data == {"hello": "Hi"}

    def test_save(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            backend = JSONBackend()
            backend.save(Path(f.name), {"hello": "Hi"})
            with open(f.name, encoding="utf-8") as fh:
                data = json.load(fh)
            assert data == {"hello": "Hi"}

    def test_extensions(self):
        backend = JSONBackend()
        assert ".json" in backend.extensions()

    def test_unicode(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            backend = JSONBackend()
            backend.save(Path(f.name), {"hello": "你好"})
            with open(f.name, encoding="utf-8") as fh:
                data = json.load(fh)
            assert data == {"hello": "你好"}


class TestGetBackend:
    def test_yaml(self):
        assert isinstance(get_backend("yaml"), YAMLBackend)

    def test_json(self):
        assert isinstance(get_backend("json"), JSONBackend)

    def test_unknown(self):
        with pytest.raises(ValueError):
            get_backend("unknown")


class TestGetBackendForFile:
    def test_yaml(self):
        backend = get_backend_for_file(Path("test.yaml"))
        assert isinstance(backend, YAMLBackend)

    def test_json(self):
        backend = get_backend_for_file(Path("test.json"))
        assert isinstance(backend, JSONBackend)

    def test_unknown(self):
        backend = get_backend_for_file(Path("test.txt"))
        assert backend is None


_toml_w_available = True
try:
    import tomli_w
except ImportError:
    _toml_w_available = False


@pytest.mark.skipif(not _toml_w_available, reason="tomli_w not installed")
class TestTOMLBackend:
    def test_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            backend = TOMLBackend()
            backend.save(Path(f.name), {"hello": "Hi"})
            data = backend.load(Path(f.name))
            assert data == {"hello": "Hi"}
