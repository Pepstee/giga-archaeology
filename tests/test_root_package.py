"""Exercise the donor-derived package against an actual isolated installation."""
from __future__ import annotations

import base64
import configparser
import csv
import hashlib
import importlib.util
import io
import json
import sqlite3
import stat
import os
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import venv
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "modules/platform/packaging/giga_build_backend.py"
SPEC = importlib.util.spec_from_file_location("giga_build_backend_test", BACKEND)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RootPackageTests(unittest.TestCase):
    def test_wheel_record_metadata_and_reproducibility(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            one = Path(first) / MODULE.build_wheel(first)
            two = Path(second) / MODULE.build_wheel(second)
            self.assertEqual(one.read_bytes(), two.read_bytes())
            with zipfile.ZipFile(one) as archive:
                names = archive.namelist()
                expected = set(MODULE.SOURCE_FILES) | {
                    f"{MODULE.DIST_INFO}/{name}"
                    for name in ("METADATA", "WHEEL", "entry_points.txt", "RECORD")
                }
                self.assertEqual(set(names), expected)
                self.assertEqual(len(names), len(expected))
                records = list(csv.reader(io.StringIO(archive.read(f"{MODULE.DIST_INFO}/RECORD").decode())))
                self.assertEqual({row[0] for row in records}, expected)
                for name, digest, size in records:
                    if name.endswith("/RECORD"):
                        self.assertEqual((digest, size), ("", ""))
                        continue
                    content = archive.read(name)
                    hashed = base64.urlsafe_b64encode(hashlib.sha256(content).digest()).rstrip(b"=").decode()
                    self.assertEqual(digest, "sha256=" + hashed)
                    self.assertEqual(int(size), len(content))
                project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
                metadata = archive.read(f"{MODULE.DIST_INFO}/METADATA").decode()
                self.assertIn("Name: " + project["name"], metadata)
                self.assertIn("Requires-Python: " + project["requires-python"], metadata)
                self.assertNotIn("Requires-Dist:", metadata)
                self.assertNotIn("Provides-Extra:", metadata)
                config = configparser.ConfigParser()
                config.read_string(archive.read(f"{MODULE.DIST_INFO}/entry_points.txt").decode())
                self.assertEqual(dict(config["console_scripts"]), project["scripts"])

    def test_sdist_reproduces_wheel_and_installed_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            one, two, rebuilt = (directory / name for name in ("one", "two", "rebuilt"))
            for path in (one, two, rebuilt):
                path.mkdir()
            source = one / MODULE.build_sdist(str(one))
            second = two / MODULE.build_sdist(str(two))
            self.assertEqual(source.read_bytes(), second.read_bytes())
            with tarfile.open(source) as archive:
                prefix = f"{MODULE.NAME}-{MODULE.VERSION}"
                self.assertEqual(set(archive.getnames()), {
                    f"{prefix}/{name}" for name in (*MODULE.SOURCE_FILES,
                        "pyproject.toml", "PKG-INFO", "modules/platform/packaging/giga_build_backend.py")
                })
                self.assertTrue(all(member.isfile() for member in archive.getmembers()))
                archive.extractall(directory / "extracted", filter="data")
            extracted = directory / "extracted" / prefix
            environment = directory / "venv"
            venv.EnvBuilder(with_pip=True).create(environment)
            python = environment / "bin/python"
            env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
            env.update(PIP_NO_INDEX="1", PIP_DISABLE_PIP_VERSION_CHECK="1", PIP_NO_CACHE_DIR="1")
            # The PEP 517 frontend builds the unpacked sdist, with no checkout on sys.path.
            subprocess.run([str(python), "-m", "pip", "wheel", "--no-deps", "--no-build-isolation",
                            "--wheel-dir", str(rebuilt), str(extracted)], cwd=directory, env=env,
                           capture_output=True, text=True, check=True)
            direct = one / MODULE.build_wheel(str(one))
            wheel = rebuilt / direct.name
            self.assertEqual(wheel.read_bytes(), direct.read_bytes())
            subprocess.run([str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
                           cwd=directory, env=env, capture_output=True, text=True, check=True)
            for command in ("giga-twin", "giga-sovereignty", "giga-operator-status"):
                result = subprocess.run([str(environment / "bin" / command), "--help"],
                                        cwd=directory, env=env, capture_output=True, text=True, check=True)
                self.assertIn("usage:", result.stdout.lower())
            result = subprocess.run([str(python), "-I", "-c", "import twin_core; print(twin_core.__file__)"],
                                    cwd=directory, env=env, capture_output=True, text=True, check=True)
            self.assertTrue(Path(result.stdout.strip()).resolve().is_relative_to(environment.resolve()))
            database = directory / "synthetic-state" / "kernel.sqlite3"
            result = subprocess.run([str(environment / "bin/giga-twin"), "--database", str(database), "init"],
                                    cwd=directory, env=env, capture_output=True, text=True, check=True)
            payload = json.loads(result.stdout)
            self.assertEqual(Path(payload["database"]).resolve(), database.resolve())
            self.assertTrue(payload["counts"])
            self.assertTrue(all(count == 0 for count in payload["counts"].values()))
            self.assertEqual(stat.S_IMODE(database.stat().st_mode), 0o600)
            with sqlite3.connect(database) as connection:
                self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone()[0], "ok")

    def test_unlisted_content_is_not_read_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "twin_core").mkdir()
            (root / "twin_core/allowed.py").write_text("value = 1\n")
            # Even Python files outside the exact allowlist are excluded.
            (root / "twin_core/private.py").symlink_to(root / "missing-private-target")
            with patch.object(MODULE, "ROOT", root), patch.object(MODULE, "SOURCE_FILES", ("twin_core/allowed.py",)):
                self.assertEqual(list(MODULE._sources()), [("twin_core/allowed.py", b"value = 1\n")])
                (root / "twin_core/allowed.py").unlink()
                (root / "twin_core/allowed.py").symlink_to(root / "missing-private-target")
                with self.assertRaisesRegex(ValueError, "symlink source forbidden"):
                    list(MODULE._sources())
            (root / "linked").symlink_to(root / "twin_core", target_is_directory=True)
            with patch.object(MODULE, "ROOT", root), patch.object(MODULE, "SOURCE_FILES", ("linked/allowed.py",)):
                with self.assertRaisesRegex(ValueError, "symlink source forbidden"):
                    list(MODULE._sources())

    def test_build_requires_no_dependencies_and_missing_source_fails(self):
        self.assertEqual(MODULE.get_requires_for_build_wheel(), [])
        self.assertEqual(MODULE.get_requires_for_build_sdist(), [])
        with tempfile.TemporaryDirectory() as temporary, patch.object(MODULE, "ROOT", Path(temporary)):
            with self.assertRaises(FileNotFoundError):
                list(MODULE._sources())


if __name__ == "__main__":
    unittest.main()
