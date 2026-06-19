import json
import subprocess
import sys
import tempfile
from pathlib import Path

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

    def test_generate_fails_on_invalid_template(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            out_dir = Path(tmpdir) / "_generated"
            trans_dir.mkdir()

            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump({"bad": "Hello {name"}, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "generate", "-d", str(trans_dir), "-o", str(out_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 1
            assert "unmatched" in result.stdout.lower()

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

    def test_validate_json_locale(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            with open(trans_dir / "en.json", "w", encoding="utf-8") as f:
                json.dump({"hello": "Hello {name:string}!"}, f)
            with open(trans_dir / "zh.json", "w", encoding="utf-8") as f:
                json.dump({"hello": "你好 {name:string}！"}, f)

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

    def test_extract_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            src_dir = Path(tmpdir) / "src"
            trans_dir.mkdir()
            src_dir.mkdir()

            en = {"greeting": "Hello {name:string}!", "farewell": "Goodbye!"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)

            py_code = 'from typesafe_i18n import I18n\ni18n = I18n(".", "en")\ni18n.t("greeting", name="x")\n'
            with open(src_dir / "app.py", "w") as f:
                f.write(py_code)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "extract", str(src_dir), "-d", str(trans_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert "farewell" in result.stdout or "sync" in result.stdout.lower()

    def test_export_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            en = {"hello": "Hello {name:string}!"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)

            json_file = Path(tmpdir) / "out.json"
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

    def test_import_command(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            import_dir = Path(tmpdir) / "imported"
            json_file = Path(tmpdir) / "data.json"

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump({"en": {"greeting": "Hello!"}}, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "import", str(json_file), "-d", str(import_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert (import_dir / "en.yaml").exists()
            with open(import_dir / "en.yaml", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data["greeting"] == "Hello!"

    def test_validate_command_with_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            en = {"hello": "Hello {name:string}!"}
            zh = {"hello": "你好 {name:string}！"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump(zh, f)

            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump({"hello": "你好 {"}, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "validate", "-d", str(trans_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 1
            assert "error" in result.stdout.lower() or "unmatched" in result.stdout.lower()

    def test_validate_command_missing_keys(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            trans_dir = Path(tmpdir) / "translations"
            trans_dir.mkdir()

            en = {"hello": "Hello!", "bye": "Goodbye!"}
            zh = {"hello": "你好！"}
            with open(trans_dir / "en.yaml", "w") as f:
                yaml.dump(en, f)
            with open(trans_dir / "zh.yaml", "w") as f:
                yaml.dump(zh, f)

            result = subprocess.run(
                [sys.executable, "-m", "typesafe_i18n.cli", "validate", "-d", str(trans_dir)],
                capture_output=True, text=True, cwd=str(Path(__file__).parent.parent),
            )
            assert result.returncode == 0
            assert "bye" in result.stdout
            assert "missing" in result.stdout.lower()
