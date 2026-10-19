"""Exercise regeneration safety against isolated copies, never the real outputs."""
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch
import copy
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))
import build_library as library


class GenerationSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory(prefix="atlas-test-fixture-")
        cls.addClassCleanup(cls.fixture.cleanup)
        cls.base = Path(cls.fixture.name)
        library.build(cls.base)
        hashes = {p.relative_to(cls.base).as_posix(): library.content_hash(p)
                  for p in cls.base.rglob("*") if p.is_file()}
        (cls.base / "assets/cottage.png").write_bytes((library.ROOT / "assets/cottage.png").read_bytes())
        manifest = {"version": 1, "hash_algorithm": "sha256-lf-text", "files": dict(sorted(hashes.items()))}
        (cls.base / "tools").mkdir()
        (cls.base / library.MANIFEST_PATH).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix="atlas-test-checkout-")
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name) / "checkout"
        shutil.copytree(self.base, self.root)
        self.root_patch = patch.object(library, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix():
                (hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_mtime_ns)
                for p in self.root.rglob("*") if p.is_file()}

    def call(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            result = library.main(list(arguments))
        return result, output.getvalue()

    def change_explanation(self):
        principles = copy.deepcopy(library.PRINCIPLES)
        principles["dissolve"]["noise"] = "Changed sample.。Updated explanation."
        return patch.object(library, "PRINCIPLES", principles)

    def test_check_leaves_all_bytes_and_timestamps_unchanged(self):
        before = self.snapshot()
        result, output = self.call("--check")
        self.assertEqual(result, 0, output)
        self.assertEqual(before, self.snapshot())

    def test_check_reports_derived_changes_without_writing(self):
        before = self.snapshot()
        with self.change_explanation():
            result, output = self.call("--check")
        self.assertEqual(result, 1, output)
        self.assertIn("effects/01_dissolve/01_noise/README.md", output)
        self.assertEqual(before, self.snapshot())

    def test_unchanged_build_does_not_touch_files(self):
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 0, output)
        self.assertIn("updated=0", output)
        self.assertEqual(before, self.snapshot())

    def test_hand_edit_blocks_entire_build_before_any_write(self):
        shader = self.root / "effects/01_dissolve/01_noise/effect.gdshader"
        shader.write_text(shader.read_text(encoding="utf-8") + "// handwritten change\n", encoding="utf-8")
        before = self.snapshot()
        with self.change_explanation():
            result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("locally modified", output)
        self.assertEqual(before, self.snapshot())

    def test_handwritten_readme_is_protected(self):
        readme = self.root / "effects/01_dissolve/01_noise/README.md"
        readme.write_text("My custom instructions\n", encoding="utf-8")
        before = self.snapshot()
        result, output = self.call("--check")
        self.assertEqual(result, 2, output)
        self.assertIn("Protected files", output)
        self.assertEqual(before, self.snapshot())

    def test_deleted_managed_file_is_not_silently_restored(self):
        (self.root / "effects/01_dissolve/01_noise/README.md").unlink()
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("deleted", output)
        self.assertEqual(before, self.snapshot())

    def test_binary_output_edit_is_protected(self):
        vat = self.root / "assets/vat.png"
        vat.write_bytes(vat.read_bytes() + b"manual")
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("assets/vat.png", output)
        self.assertEqual(before, self.snapshot())

    def test_new_output_cannot_overwrite_an_unmanaged_file(self):
        real_build = library.build

        def add_output(staged):
            result = real_build(staged)
            (staged / "new.txt").write_text("generated", encoding="utf-8")
            return result

        (self.root / "new.txt").write_text("handwritten", encoding="utf-8")
        before = self.snapshot()
        with patch.object(library, "build", add_output):
            result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("unmanaged file", output)
        self.assertEqual(before, self.snapshot())

    def test_missing_manifest_does_not_adopt_current_files(self):
        (self.root / library.MANIFEST_PATH).unlink()
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("restore", output)
        self.assertEqual(before, self.snapshot())

    def test_manifest_cannot_point_outside_the_project(self):
        path = self.root / library.MANIFEST_PATH
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["files"]["../outside.txt"] = "0" * 64
        path.write_text(json.dumps(manifest), encoding="utf-8")
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("Invalid generated path", output)
        self.assertEqual(before, self.snapshot())

    def test_invalid_manifest_format_is_rejected(self):
        (self.root / library.MANIFEST_PATH).write_text("[]", encoding="utf-8")
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertEqual(before, self.snapshot())

    def test_single_effect_only_updates_its_outputs_and_changed_indexes(self):
        before = self.snapshot()
        with self.change_explanation():
            result, output = self.call("--effect", "dissolve/noise")
        self.assertEqual(result, 0, output)
        after = self.snapshot()
        changed = {name for name in before if before[name] != after[name]}
        self.assertEqual(changed, {"effects/01_dissolve/01_noise/README.md",
                                   "effects/01_dissolve/01_noise/metadata.json",
                                   "catalog.json", library.MANIFEST_PATH})

    def test_single_effect_preserves_unrelated_hand_edit(self):
        unrelated = self.root / "effects/01_dissolve/02_direction/README.md"
        unrelated.write_text("Keep my unrelated change\n", encoding="utf-8")
        before = self.snapshot()["effects/01_dissolve/02_direction/README.md"]
        with self.change_explanation():
            result, output = self.call("--effect", "dissolve/noise")
        self.assertEqual(result, 0, output)
        self.assertEqual(before, self.snapshot()["effects/01_dissolve/02_direction/README.md"])

    def test_check_single_effect_is_read_only(self):
        before = self.snapshot()
        with self.change_explanation():
            result, output = self.call("--check", "--effect", "dissolve/noise")
        self.assertEqual(result, 1, output)
        self.assertNotIn("02_direction/", output)
        self.assertEqual(before, self.snapshot())

    def test_crlf_checkout_is_supported_without_rewriting_it(self):
        shader = self.root / "effects/01_dissolve/01_noise/effect.gdshader"
        shader.write_bytes(shader.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
        before = self.snapshot()
        result, output = self.call("--check")
        self.assertEqual(result, 0, output)
        self.assertEqual(before, self.snapshot())

    def test_unknown_effect_does_not_modify_files(self):
        before = self.snapshot()
        result, output = self.call("--effect", "../../outside")
        self.assertEqual(result, 2, output)
        self.assertIn("Unknown effect", output)
        self.assertEqual(before, self.snapshot())

    def test_missing_repository_asset_is_reported_without_changes(self):
        (self.root / "assets/cottage.png").unlink()
        before = self.snapshot()
        result, output = self.call()
        self.assertEqual(result, 2, output)
        self.assertIn("assets/cottage.png", output)
        self.assertEqual(before, self.snapshot())

    def test_rebuild_updates_manifest_and_then_checks_clean(self):
        with self.change_explanation():
            result, output = self.call()
            self.assertEqual(result, 0, output)
            result, output = self.call("--check")
        self.assertEqual(result, 0, output)

    def test_isolated_checkout_cli_needs_no_sibling_blender_project(self):
        for name in ["build_library.py", "effect_catalog.py", "plain_language.py"]:
            shutil.copy2(TOOLS / name, self.root / "tools" / name)
        self.assertFalse((self.root.parent / "blender-cottage-demo").exists())
        before = self.snapshot()
        result = subprocess.run([sys.executable, str(self.root / "tools/build_library.py"), "--check"],
                                cwd=self.scratch.name, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(before, self.snapshot())


if __name__ == "__main__":
    unittest.main()
