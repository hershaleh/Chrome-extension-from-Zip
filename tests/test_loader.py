import unittest
import zipfile
import tempfile
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from loader import extract_zip


class ZipTests(unittest.TestCase):
    def make_zip(self, nested=False):
        tmp = tempfile.TemporaryDirectory()
        p = Path(tmp.name) / "test.zip"
        root = "extension/" if nested else ""
        with zipfile.ZipFile(p, "w") as z:
            z.writestr(root + "manifest.json", json.dumps({"manifest_version": 3, "name": "Test"}))
            z.writestr(root + "background.js", " ")
        return tmp, p

    def test_root_manifest(self):
        t, p = self.make_zip()
        try:
            self.assertEqual(extract_zip(p)[1], "Test")
        finally:
            t.cleanup()

    def test_nested_manifest(self):
        t, p = self.make_zip(True)
        try:
            self.assertEqual(extract_zip(p)[1], "Test")
        finally:
            t.cleanup()

    def test_rejects_path_traversal(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            archive = Path(tmp.name) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("../outside.txt", "unsafe")
                z.writestr("manifest.json", json.dumps({"manifest_version": 3, "name": "Unsafe"}))
            with self.assertRaises(ValueError):
                extract_zip(archive)
        finally:
            tmp.cleanup()

    def test_rejects_missing_manifest(self):
        tmp = tempfile.TemporaryDirectory()
        try:
            archive = Path(tmp.name) / "missing.zip"
            with zipfile.ZipFile(archive, "w") as z:
                z.writestr("readme.txt", "not an extension")
            with self.assertRaises(ValueError):
                extract_zip(archive)
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
