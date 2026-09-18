"""In-memory packaging and temporary-tree tests; never write project dist."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

spec = importlib.util.spec_from_file_location("pack_dist", Path(__file__).with_name("pack-dist.py"))
pack = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pack)


class PackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / "skill"
        for directory in ("references", "templates", "templates/charts"):
            (self.src / directory).mkdir(parents=True, exist_ok=True)
        for name in ("SKILL.md", "references/z.md", "references/a.md", "templates/a.md", "templates/charts/a.json"):
            (self.src / name).write_bytes((name + "\n").encode() * 200)
        for key, value in (("SRC", str(self.src)), ("EXPECTED", 5), ("OUT", str(self.root / "dist.zip"))):
            mocker = patch.object(pack, key, value)
            mocker.start()
            self.addCleanup(mocker.stop)

    def test_determinism_independent_of_mtime_mode_listing_and_platform(self):
        original = pack.build()
        for _, path in pack.collect():
            os.utime(path, (1000000000, 1000000000))
            os.chmod(path, 0o600)
        listdir = os.listdir
        with patch.object(pack.os, "listdir", side_effect=lambda p: list(reversed(listdir(p)))):
            self.assertEqual(original, pack.build())
        zip_info = zipfile.ZipInfo
        with zipfile.ZipFile(io.BytesIO(original)) as archive:
            self.assertEqual(len(archive.infolist()), 5)
            for info in archive.infolist():
                self.assertEqual(info.create_system, 3)
                self.assertEqual(info.date_time, pack.STAMP)
                self.assertEqual(info.external_attr, 0o644 << 16)
                self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
                self.assertTrue(info.filename.startswith(pack.PREFIX))
        # Simulate Windows defaults at construction without changing the class.
        init = zip_info.__init__
        def windows_init(info, *args, **kwargs):
            init(info, *args, **kwargs)
            info.create_system = 0
        with patch.object(zip_info, "__init__", windows_init):
            self.assertEqual(original, pack.build())

    def test_explicit_compression_preserves_historical_default_bytes(self):
        old = io.BytesIO()
        with zipfile.ZipFile(old, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for rel, path in pack.collect():
                info = zipfile.ZipInfo(pack.PREFIX + rel, date_time=pack.STAMP)
                info.create_system = 3
                info.external_attr = 0o644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, Path(path).read_bytes())
        self.assertEqual(pack.build(), old.getvalue())

    def test_missing_member_and_external_symlink_rejected(self):
        (self.src / "references/a.md").unlink()
        with self.assertRaises(ValueError):
            pack.build()
        outside = self.root / "outside.md"
        outside.write_text("outside")
        (self.src / "references/a.md").symlink_to(outside)
        with self.assertRaises(ValueError):
            pack.build()

    def test_checks_survive_optimized_python(self):
        script = (f"import runpy; m=runpy.run_path({str(Path(pack.__file__))!r}); "
                  f"m['build'].__globals__.update(SRC={str(self.src)!r}, EXPECTED=6); m['build']()")
        proc = subprocess.run([sys.executable, "-O", "-c", script], capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("expected 6 entries", proc.stderr)

    def test_check_is_read_only_for_missing_matching_and_stale_dist(self):
        for content, expected in ((None, 3), (pack.build(), 0), (b"stale", 3)):
            path = Path(pack.OUT)
            if content is not None:
                path.write_bytes(content)
            with patch.object(sys, "argv", ["pack-dist", "--check"]), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(pack.main(), expected)
            if content is None:
                self.assertFalse(path.exists())
            else:
                self.assertEqual(path.read_bytes(), content)


if __name__ == "__main__":
    unittest.main()
