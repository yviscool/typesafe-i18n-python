import tempfile
import time
from pathlib import Path

import yaml

from typesafe_i18n.runtime import I18n


def _create_large_translations(tmpdir: str, num_keys: int = 1000) -> None:
    data = {}
    for i in range(num_keys):
        data[f"key_{i}"] = f"Value {i} for {{name:string}}"
    with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
        yaml.dump(data, f)


class TestBenchmark:
    def test_load_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_large_translations(tmpdir)

            start = time.perf_counter()
            i18n = I18n(tmpdir, "en")
            elapsed = time.perf_counter() - start

            assert elapsed < 2.0, f"Load time {elapsed:.3f}s exceeds 2s limit"

    def test_translation_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_large_translations(tmpdir)
            i18n = I18n(tmpdir, "en")

            start = time.perf_counter()
            for i in range(1000):
                i18n.t(f"key_{i % 1000}", name="test")
            elapsed = time.perf_counter() - start

            assert elapsed < 1.0, f"1000 translations took {elapsed:.3f}s, exceeds 1s limit"

    def test_cached_translation_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            _create_large_translations(tmpdir)
            i18n = I18n(tmpdir, "en")

            for i in range(100):
                i18n.t(f"key_{i}", name="warmup")

            start = time.perf_counter()
            for i in range(1000):
                i18n.t(f"key_{i % 100}", name="test")
            elapsed = time.perf_counter() - start

            assert elapsed < 0.5, f"Cached translations took {elapsed:.3f}s, exceeds 0.5s limit"

    def test_locale_switch_time(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {f"key{i}": f"Value {i}" for i in range(100)}
            zh = {f"key{i}": f"值 {i}" for i in range(100)}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w", encoding="utf-8") as f:
                yaml.dump(zh, f)

            i18n = I18n(tmpdir, "en")

            start = time.perf_counter()
            for _ in range(100):
                i18n.set_locale("en")
                i18n.set_locale("zh")
            elapsed = time.perf_counter() - start

            assert elapsed < 5.0, f"200 locale switches took {elapsed:.3f}s, exceeds 5s limit"
