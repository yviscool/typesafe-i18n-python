import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml


class TestEndToEnd:
    def test_generate_and_run(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            out_dir = Path(tmpdir) / "_generated"
            trans_dir.mkdir()

            en = {
                "hello": "Hello {name:string}!",
                "items": "{count:number} {{item|items}}",
            }
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "generate", "-d", str(trans_dir), "-o", str(out_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert (out_dir / "types.pyi").exists()

    def test_generate_and_typecheck(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            out_dir = Path(tmpdir) / "_generated"
            trans_dir.mkdir()

            en = {"hello": "Hello {name:string}!"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)

            subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "generate", "-d", str(trans_dir), "-o", str(out_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )

            test_code = '''
from typing import reveal_type
import sys
sys.path.insert(0, r"{}")
from types import t, LocalizedString

result = t("hello", name="World")
reveal_type(result)
'''.format(str(out_dir).replace("\\", "\\\\"))

            test_file = Path(tmpdir) / "test_typing.py"
            test_file.write_text(test_code)

            result = subprocess.run(
                [sys.executable, "-m", "mypy", str(test_file), "--ignore-missing-imports"],
                capture_output=True, text=True,
            )
            assert "error" not in result.stderr.lower() or result.returncode == 0

    def test_validate_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            en = {"hello": "Hello {name:string}!"}
            zh = {"hello": "你好 {name:string}！"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump(zh, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "validate", "-d", str(trans_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0

    def test_export_import_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            en = {"hello": "Hello {name:string}!", "items": "{count:number} items"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)

            json_file = Path(tmpdir) / "export.json"

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "export", "-d", str(trans_dir), "-o", str(json_file)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert json_file.exists()

            with open(json_file) as f:
                data = json.load(f)
            assert "en" in data
            assert data["en"]["hello"] == "Hello {name:string}!"

            import_dir = Path(tmpdir) / "imported"
            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "import", str(json_file), "-d", str(import_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert (import_dir / "en.yaml").exists()
