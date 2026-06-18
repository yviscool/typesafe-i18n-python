import tempfile
import threading
from pathlib import Path

import yaml

from typesafe_i18n.runtime import I18n


class TestThreadSafety:
    def test_concurrent_reads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {f"key{i}": f"Value {i}" for i in range(100)}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)

            i18n = I18n(tmpdir, "en")
            results: list[str] = []
            errors: list[Exception] = []

            def read_key(key: str) -> None:
                try:
                    result = i18n.t(key)
                    results.append(result)
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=read_key, args=(f"key{i}",)) for i in range(100)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
            assert len(results) == 100

    def test_concurrent_locale_switch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            en = {"hello": "Hello"}
            zh = {"hello": "你好"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(en, f)
            with open(Path(tmpdir) / "zh.yaml", "w", encoding="utf-8") as f:
                yaml.dump(zh, f)

            i18n = I18n(tmpdir, "en")
            errors: list[Exception] = []

            def switch_and_read() -> None:
                try:
                    for _ in range(10):
                        i18n.set_locale("en")
                        i18n.t("hello")
                        i18n.set_locale("zh")
                        i18n.t("hello")
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=switch_and_read) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0

    def test_concurrent_formatter_registration(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            data = {"hello": "Hello {name:string|upper}!"}
            with open(Path(tmpdir) / "en.yaml", "w", encoding="utf-8") as f:
                yaml.dump(data, f)

            i18n = I18n(tmpdir, "en")
            errors: list[Exception] = []

            def register_and_use() -> None:
                try:
                    for i in range(10):
                        i18n.set_formatters({"upper": lambda v: v.upper()})
                        i18n.t("hello", name="test")
                except Exception as e:
                    errors.append(e)

            threads = [threading.Thread(target=register_and_use) for _ in range(10)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0
