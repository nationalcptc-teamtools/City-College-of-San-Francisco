"""Tests for the shared test helpers in support.py."""

import re
import unittest

import support


def finding_structure(text):
    """Return the set of `####` headings and `- **Label:**` labels in a finding."""
    headings = re.findall(r"(?m)^#### .+$", text)
    labels = re.findall(r"(?m)^- \*\*[^*]+:\*\*", text)
    return set(headings + labels)


class MakeWorktreeTests(unittest.TestCase):
    def test_root_is_inside_tmp_without_git(self):
        root = support.make_worktree(self)
        self.assertEqual(root.parent, support.TMP_DIR.resolve())
        self.assertFalse((root / ".git").exists())

    def test_requested_files_are_written(self):
        files = {
            "findings/F-001-example.md": "### F-001: Example on 10.0.0.1\n",
            "field-notes/alice/NOTE-client-example.md": "client-example\n",
        }
        root = support.make_worktree(self, files)
        for relative_path, text in files.items():
            self.assertEqual((root / relative_path).read_text(encoding="utf-8"), text)

    def test_file_outside_root_is_refused(self):
        with self.assertRaises(ValueError):
            support.make_worktree(self, {"../escape.md": "x\n"})

    def test_folder_removed_after_cleanup(self):
        # A separate TestCase owns the worktree, so running its cleanups here
        # shows the folder is gone without waiting for this test to end.
        owner = unittest.TestCase()
        root = support.make_worktree(owner, {"findings/F-001-example.md": "x\n"})
        self.assertTrue(root.exists())
        owner.doCleanups()
        self.assertFalse(root.exists())
        self.assertTrue(support.TMP_DIR.exists())


class MakeCompleteFindingTests(unittest.TestCase):
    def test_default_finding_has_no_markers_and_f001_heading(self):
        text = support.make_complete_finding()
        self.assertNotIn("[[", text)
        self.assertTrue(text.startswith("### F-001: "))

    def test_rationale_and_reference_are_filled(self):
        text = support.make_complete_finding()
        # The label must be followed by real words, not just be present.
        self.assertRegex(text, r"(?m)^- \*\*Why this severity:\*\* \w")
        self.assertRegex(text, r"(?m)^- \*\*References:\*\* .*https://example\.invalid/")

    def test_reproduction_steps_have_indented_expected_lines(self):
        text = support.make_complete_finding()
        numbered = re.findall(r"(?m)^\d+\. `[^`]+`$", text)
        expected = re.findall(r"(?m)^ +Expected: \S", text)
        self.assertGreaterEqual(len(numbered), 1)
        self.assertGreaterEqual(len(expected), len(numbered))

    def test_matches_finding_template_structure(self):
        # The template is edited by hand, outside the build workflow, so this
        # is what notices when COMPLETE_FINDING goes stale. Attack chain is
        # left out on purpose: COMPLETE_FINDING drops it as a standalone finding.
        template_path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        template = finding_structure(template_path.read_text(encoding="utf-8"))
        template.discard("#### Attack chain")
        complete = finding_structure(support.COMPLETE_FINDING)
        self.assertEqual(sorted(template - complete), [], "missing from COMPLETE_FINDING")
        self.assertEqual(sorted(complete - template), [], "extra in COMPLETE_FINDING")

    def test_id_and_title_are_used(self):
        text = support.make_complete_finding("F-002", "Second example")
        self.assertTrue(text.startswith("### F-002: Second example\n"))
        self.assertIn("evidence/F-002-01.png", text)


if __name__ == "__main__":
    unittest.main()
