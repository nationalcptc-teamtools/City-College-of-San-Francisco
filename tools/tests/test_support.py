"""Tests for the shared test helpers in support.py."""

import re
import unittest
from pathlib import Path

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


class MakeHostileLogsTests(unittest.TestCase):
    def make_logdir(self):
        """Return a fake $LOGDIR inside a fresh make_worktree() folder."""
        return support.make_worktree(self) / "cptc-logs"

    def test_both_files_are_written_inside_logdir(self):
        logdir = self.make_logdir()
        log_path, cmds_path = support.make_hostile_logs(logdir, "alice_20261107T101500Z")
        self.assertEqual(log_path, logdir / "alice_20261107T101500Z.log")
        self.assertEqual(cmds_path, logdir / "alice_20261107T101500Z.cmds.log")
        for path in (log_path, cmds_path):
            self.assertEqual(path.resolve().parent, logdir.resolve())
            self.assertTrue(path.is_file())
        # Generated, never a committed fixture.
        fixtures = support.TOOLS_DIR / "tests" / "fixtures"
        self.assertNotIn(fixtures.resolve(), log_path.resolve().parents)

    def test_files_are_removed_with_the_worktree(self):
        # A separate TestCase owns the worktree, as in MakeWorktreeTests.
        owner = unittest.TestCase()
        logdir = support.make_worktree(owner) / "cptc-logs"
        log_path, cmds_path = support.make_hostile_logs(logdir)
        owner.doCleanups()
        self.assertFalse(log_path.exists())
        self.assertFalse(cmds_path.exists())
        self.assertFalse(logdir.exists())

    def test_logdir_outside_tmp_is_refused(self):
        outside = support.TMP_DIR.parent / "not-a-logdir"
        with self.assertRaises(ValueError):
            support.make_hostile_logs(outside)
        self.assertFalse(outside.exists())

    def test_base_leaving_logdir_is_refused(self):
        logdir = self.make_logdir()
        worktree = logdir.parent
        with self.assertRaises(ValueError):
            support.make_hostile_logs(logdir, "../escape")
        self.assertEqual(sorted(worktree.iterdir()), [logdir])
        self.assertEqual(list(logdir.iterdir()), [])

    def test_absolute_base_is_refused(self):
        logdir = self.make_logdir()
        # Absolute, but inside the worktree, so even a broken helper writes
        # nothing that outlives the test.
        target = logdir.parent.resolve() / "absolute-escape"
        self.assertTrue(target.is_absolute())
        with self.assertRaises(ValueError):
            support.make_hostile_logs(logdir, str(target))
        self.assertFalse(Path(str(target) + ".log").exists())
        self.assertFalse(Path(str(target) + ".cmds.log").exists())
        self.assertEqual(list(logdir.iterdir()), [])

    def test_transcript_bytes_are_exact(self):
        log_path, cmds_path = support.make_hostile_logs(self.make_logdir())
        self.assertEqual(log_path.read_bytes(), support.HOSTILE_LOG.encode("utf-8"))
        self.assertEqual(cmds_path.read_bytes(), support.HOSTILE_CMDS.encode("utf-8"))

    def test_transcript_holds_every_hostile_case(self):
        data = support.make_hostile_logs(self.make_logdir())[0].read_bytes()
        cases = {
            "script tag": b'<script>alert("fake-xss")</script>',
            "CR CR LF": b"OK\r\r\n",
            "backspace": b"inn\x08",
            "CSI colour": b"\x1b[01;31m",
            "CSI private mode": b"\x1b[?2004h",
            "CSI erase line": b"\x1b[K",
            "CSI intermediate byte": b"\x1b[0 q",
            "OSC ended by BEL": b"\x1b]0;alice@kali: ~\x07",
            "OSC ended by ESC backslash": b"\x1b]8;;http://10.0.0.1/\x1b\\",
            "ESC ( B": b"\x1b(B",
            "ESC ) 0": b"\x1b)0",
            "ESC =": b"\x1b=",
            "ESC >": b"\x1b>",
        }
        for label, piece in cases.items():
            with self.subTest(label):
                self.assertIn(piece, data)
        # A plain CR LF too, not only the CR LF inside each CR CR LF.
        self.assertIn(b"fake-dl 100%\r\n", data)
        self.assertNotIn(b"\r\r\r", data)

    def test_progress_line_redraws_more_than_once(self):
        data = support.make_hostile_logs(self.make_logdir())[0].read_bytes()
        line = [part for part in data.split(b"\n") if b"fake-dl" in part][0]
        # Two lone CRs before the line's own CR LF.
        self.assertEqual(line, b"fake-dl  10%\rfake-dl  55%\rfake-dl 100%\r")

    def test_command_index_is_fake_and_matches_transcript(self):
        cmds = support.HOSTILE_CMDS
        self.assertIn("curl -i http://10.0.0.1/index.html\n", cmds)
        self.assertIn("./fake-download.sh\n", cmds)
        self.assertEqual(cmds.count("\n"), 2)
        # Every command appears, as typed, in the cleaned transcript.
        for line in cmds.splitlines():
            command = line.split("] ", 1)[1]
            self.assertIn("$ " + command + "\n", support.HOSTILE_LOG_CLEANED)

    def test_cleaned_text_has_no_control_codes(self):
        cleaned = support.HOSTILE_LOG_CLEANED
        for control in ("\r", "\x1b", "\x08", "\x07"):
            self.assertNotIn(control, cleaned)
        self.assertIn('<script>alert("fake-xss")</script>\n', cleaned)
        # Same number of lines as the transcript: cleaning never drops one.
        self.assertEqual(cleaned.count("\n"), support.HOSTILE_LOG.count("\n"))

    def test_two_calls_do_not_collide(self):
        logdir = self.make_logdir()
        first = support.make_hostile_logs(logdir, "alice_20261107T101500Z", mtime=1000000000)
        second = support.make_hostile_logs(logdir, "alice_20261107T120000Z", mtime=1000000060)
        self.assertEqual(len(set(first + second)), 4)
        self.assertEqual(first[0].stat().st_mtime, 1000000000)
        self.assertEqual(first[1].stat().st_mtime, 1000000000)
        self.assertEqual(second[0].stat().st_mtime, 1000000060)
        self.assertEqual(second[1].stat().st_mtime, 1000000060)
        self.assertEqual(second[0].read_bytes(), first[0].read_bytes())

    def test_same_base_twice_is_refused(self):
        logdir = self.make_logdir()
        log_path, _ = support.make_hostile_logs(logdir, mtime=1000000000)
        with self.assertRaises(FileExistsError):
            support.make_hostile_logs(logdir, mtime=1000000060)
        self.assertEqual(log_path.stat().st_mtime, 1000000000)
        self.assertEqual(log_path.read_bytes(), support.HOSTILE_LOG.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
