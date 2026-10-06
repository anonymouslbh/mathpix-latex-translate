"""Filesystem tests for destructive cleanup boundaries; no real books are changed."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import cleanup_project as cleanup


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="codex-book-cleanup-test-")
        self.base = Path(self.temp.name).resolve()
        self.assertTrue(self.base.is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.root = self.base / "书籍工程"
        self.root.mkdir()
        self.write("project.json", json.dumps({"inputs": [{"path": "source/original.pdf"}]}))
        self.write("source/original.pdf", b"original input")
        self.write("source/images/figure.png", b"original figure")
        self.write("baseline/main.tex", b"English source")
        self.write("translation/main.tex", b"Chinese editable source")
        self.write("translation/covers/back.png", b"adopted cover")
        self.write("delivery/final.pdf", b"accepted delivery")
        self.write("build/current/main.pdf", b"current verified PDF")
        self.write("qa/latest-pages/page-1.png", b"latest page one")
        self.write("qa/latest-pages/page-2.png", b"latest page two")
        self.write("qa/old/page-1.png", b"old page one")
        self.write("qa/old/pair-1.png", b"old comparison pair")
        self.write("qa/old/issues/before.png", b"unresolved issue evidence")
        self.write("qa/old/covers/back.png", b"asset in nested copy")
        self.write("qa/old/acceptance.json", b"historical QA record")
        self.write("qa/old/main.log", b"historical compilation log")
        self.write("build/old/main.pdf", b"superseded reconstructible PDF")
        for base in ("qa/staging/project", "qa/verified-project"):
            self.write(base + "/translation/main.tex", b"identical editable copy")
            self.write(base + "/source/original.pdf", b"identical input copy")
            self.write(base + "/proof.json", b"identical preserved record")
        self.policy = {
            "current_pdf": "build/current/main.pdf", "current_pages": "qa/latest-pages",
            "keep": ["qa/old/issues"], "generated_roots": ["qa", "build"],
            "image_roots": ["qa/old", "qa/latest-pages"],
            "obsolete_pdfs": ["build/old/main.pdf"],
            "duplicate_copies": [{"path": "qa/staging/project", "keep": "qa/verified-project"}]
        }

    def tearDown(self):
        self.assertTrue(self.base.is_relative_to(Path(tempfile.gettempdir()).resolve()))
        self.temp.cleanup()

    def write(self, rel, contents):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(contents.encode("utf-8") if isinstance(contents, str) else contents)
        return path

    def assert_originals(self):
        for rel in ("source/original.pdf", "source/images/figure.png", "baseline/main.tex",
                    "translation/main.tex", "translation/covers/back.png", "delivery/final.pdf",
                    "build/current/main.pdf", "qa/latest-pages/page-1.png", "qa/latest-pages/page-2.png",
                    "qa/old/issues/before.png", "qa/old/covers/back.png", "qa/old/acceptance.json",
                    "qa/old/main.log", "qa/verified-project/translation/main.tex"):
            self.assertTrue((self.root / rel).is_file(), rel)

    def test_preview_and_actual_cleanup_preserve_required_material(self):
        evidence = cleanup.plan(self.root, self.policy)
        self.assertEqual(evidence["candidate_files"], 6)
        self.assertTrue((self.root / "qa/old/page-1.png").exists())
        result = cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assertEqual(result["deleted_files"], 6)
        self.assertEqual(result["deleted_file_bytes"], evidence["estimated_file_bytes"])
        for row in evidence["candidates"]:
            self.assertFalse((self.root / row["path"]).exists())
        self.assert_originals()
        records = [json.loads(line) for line in (self.base / "cleanup.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(row["event"] == "deleted" for row in records), 6)
        self.assertEqual(records[-1]["event"], "complete")

    def test_changed_candidate_rejects_entire_batch_before_deletion(self):
        evidence = cleanup.plan(self.root, self.policy)
        self.write("qa/old/pair-1.png", b"new render appeared")
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assertTrue((self.root / "qa/old/page-1.png").exists())
        self.assertTrue((self.root / "build/old/main.pdf").exists())
        self.assertFalse((self.base / "cleanup.jsonl").exists())

    def test_current_version_change_or_new_page_invalidates_plan(self):
        evidence = cleanup.plan(self.root, self.policy)
        self.write("build/current/main.pdf", b"new current PDF")
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        evidence = cleanup.plan(self.root, self.policy)
        self.write("qa/latest-pages/page-3.png", b"new page")
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assertTrue((self.root / "qa/old/page-1.png").exists())

    def test_content_change_with_unchanged_size_and_timestamp_is_refused(self):
        evidence = cleanup.plan(self.root, self.policy)
        path = self.root / "qa/old/pair-1.png"
        before = path.stat()
        path.write_bytes(b"X" * before.st_size)
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assertTrue((self.root / "qa/old/page-1.png").exists())

    def test_declared_original_input_outside_source_is_protected(self):
        self.write("qa/original-input.pdf", b"original stored in an unusual directory")
        self.write("project.json", json.dumps({"inputs": [{"path": "qa/original-input.pdf"}]}))
        policy = copy.deepcopy(self.policy)
        policy["obsolete_pdfs"] = ["qa/original-input.pdf"]
        with self.assertRaises(cleanup.CleanupError):
            cleanup.plan(self.root, policy)
        self.assertTrue((self.root / "qa/original-input.pdf").exists())

    def test_path_escape_and_core_directory_selection_are_refused(self):
        for changes in ({"image_roots": ["../another-book"]},
                        {"generated_roots": ["source"]},
                        {"obsolete_pdfs": ["source/original.pdf"]},
                        {"obsolete_pdfs": ["build/current/main.pdf"]},
                        {"obsolete_pdfs": ["qa/.. /source/original.pdf"]},
                        {"image_roots": ["C:\\another-book\\pages"]}):
            policy = copy.deepcopy(self.policy)
            policy.update(changes)
            with self.subTest(changes=changes), self.assertRaises(cleanup.CleanupError):
                cleanup.plan(self.root, policy)
        self.assert_originals()

    def test_different_copies_and_keeper_inside_copy_are_refused(self):
        self.write("qa/staging/project/translation/main.tex", b"different revision")
        with self.assertRaises(cleanup.CleanupError):
            cleanup.plan(self.root, self.policy)
        policy = copy.deepcopy(self.policy)
        policy["duplicate_copies"] = [{"path": "qa/staging/project", "keep": "qa/staging/project/source"}]
        with self.assertRaises(cleanup.CleanupError):
            cleanup.plan(self.root, policy)
        self.assertTrue((self.root / "qa/staging/project/translation/main.tex").exists())

    def test_modified_plan_cannot_delete_source_text(self):
        evidence = cleanup.plan(self.root, self.policy)
        row = cleanup.snapshot(self.root, "translation/main.tex")
        row["kind"] = "old-page-image"
        evidence["candidates"].append(row)
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assert_originals()

    def test_writer_attestation_and_existing_journal_required(self):
        evidence = cleanup.plan(self.root, self.policy)
        with self.assertRaises(cleanup.CleanupError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", False)
        (self.base / "cleanup.jsonl").write_text("previous run", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            cleanup.apply(self.root, evidence, self.base / "cleanup.jsonl", True)
        self.assertTrue((self.root / "qa/old/page-1.png").exists())

    def test_directory_link_is_refused_without_touching_target(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "page.png").write_bytes(b"another project")
        link = self.root / "qa/old/linked"
        junction = False
        try:
            if os.name == "nt":
                quote = lambda path: "'" + str(path).replace("'", "''") + "'"
                created = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                    "New-Item -ItemType Junction -Path " + quote(link) + " -Target " + quote(outside) + " | Out-Null"],
                    capture_output=True)
                if created.returncode:
                    self.skipTest("Cannot create a test junction in this environment.")
                junction = True
            else:
                link.symlink_to(outside, target_is_directory=True)
            with self.assertRaises(cleanup.CleanupError):
                cleanup.plan(self.root, self.policy)
            self.assertEqual((outside / "page.png").read_bytes(), b"another project")
        finally:
            if link.exists() or link.is_symlink():
                self.assertTrue(link.parent.resolve().is_relative_to(self.base))
                if junction:
                    link.rmdir()
                else:
                    link.unlink()

    def test_cli_preview_is_nondestructive(self):
        policy = self.base / "policy.json"
        policy.write_text(json.dumps(self.policy), encoding="utf-8")
        result = subprocess.run([sys.executable, str(Path(cleanup.__file__)), "plan", str(self.root),
            "--policy", str(policy), "--output", str(self.base / "plan.json")], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        self.assertTrue((self.root / "qa/old/page-1.png").exists())
        self.assertEqual(json.loads(result.stdout)["files_deleted"], 0)


if __name__ == "__main__":
    unittest.main()
