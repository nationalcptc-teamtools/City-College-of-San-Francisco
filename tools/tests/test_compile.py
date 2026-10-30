"""Tests for tools/compile.py."""

import support  # puts tools/ on the import path, so it must come first
import compile

import ast
import contextlib
import importlib.util
import io
import os
import re
import shlex
import unittest
from unittest import mock


class StripMarkersTests(unittest.TestCase):
    def test_named_marker(self):
        self.assertEqual(compile.strip_markers("Host: [[HOST]] up"), "Host:  up")

    def test_choose_marker(self):
        text = "- **Severity:** [[CHOOSE: Critical / High / Low]]"
        self.assertEqual(compile.strip_markers(text), "- **Severity:** ")

    def test_todo_marker(self):
        self.assertEqual(compile.strip_markers("a [[TODO: root cause]] b"), "a  b")

    def test_multiline_note(self):
        text = "before\n[[NOTE: line one\n1. `cmd`\n   Expected: x]]\nafter"
        self.assertEqual(compile.strip_markers(text), "before\n\nafter")

    def test_adjacent_markers(self):
        self.assertEqual(compile.strip_markers("[[DATE]][[TIME]]!"), "!")

    def test_marker_starting_inside_another(self):
        # The outer NOTE can't contain `[[`, so only the inner marker is a
        # complete match; the outer one is left for the leftover check to find.
        text = "[[NOTE: see [[HOST]] here]]"
        self.assertEqual(compile.strip_markers(text), "[[NOTE: see  here]]")

    def test_unclosed_marker_does_not_swallow_next(self):
        text = "[[HOST and [[PORT]] end"
        self.assertEqual(compile.strip_markers(text), "[[HOST and  end")

    def test_unclosed_note_does_not_swallow_next(self):
        text = "[[NOTE: never closed\n[[HOST]] end"
        self.assertEqual(compile.strip_markers(text), "[[NOTE: never closed\n end")

    def test_bash_test_is_not_a_marker(self):
        text = "if [[ -f x ]]; then echo yes; fi"
        self.assertEqual(compile.strip_markers(text), text)

    def test_real_finding_template(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        stripped = compile.strip_markers(path.read_text(encoding="utf-8"))
        self.assertIsNone(re.search(r"\[\[[A-Z]", stripped))
        # The example inside the Reproduction steps NOTE must not survive,
        # or it would look like real steps to the reproduction check.
        self.assertNotIn("nxc smb", stripped)
        self.assertNotIn("Expected:", stripped)


class ScanLeftoverMarkersTests(unittest.TestCase):
    def test_complete_todo_and_unclosed_markers_reported(self):
        text = "line one\n- **Host:** [[HOST]]\n[[TODO: text]]\n\n[[NOTE: never closed\n"
        hits = compile.scan_leftover_markers("findings/F-001-x.md", text)
        self.assertEqual(hits, [
            ("findings/F-001-x.md", 2, "[[HOST"),
            ("findings/F-001-x.md", 3, "[[TODO"),
            ("findings/F-001-x.md", 5, "[[NOTE"),
        ])

    def test_bare_name_reported_and_bash_test_not(self):
        # A bare `[[HOST` (no `:` or `]]`) is still an unfinished marker, so it
        # must count; a bash test has a space after `[[` and is not a marker.
        text = "if [[ -f x ]]; then\n[[HOST\n"
        self.assertEqual(compile.scan_leftover_markers("f.md", text), [("f.md", 2, "[[HOST")])

    def test_count_equals_regex_hits(self):
        text = "[[DATE]] [[TIME]]\n[[CHOOSE: a / b]] and [[ -f x ]]\n"
        hits = compile.scan_leftover_markers("f.md", text)
        self.assertEqual(len(hits), len(compile.LEFTOVER_RE.findall(text)))
        self.assertEqual([hit[1] for hit in hits], [1, 1, 2])


class ValidateRootTests(unittest.TestCase):
    def test_root_without_git_passes(self):
        root = support.make_worktree(self, {"findings/F-001-x.md": "x\n"})
        self.assertEqual(compile.validate_root(root), root.resolve())

    def test_root_with_git_is_refused_and_nothing_created(self):
        root = support.make_worktree(self, {".git/HEAD": "ref: refs/heads/main\n"})
        before = sorted(root.rglob("*"))
        with self.assertRaisesRegex(compile.RootError, "git clone"):
            compile.validate_root(root)
        self.assertFalse((root / "build").exists())
        self.assertEqual(sorted(root.rglob("*")), before)

    def test_git_file_is_refused(self):
        # A worktree or submodule has a .git file instead of a folder.
        root = support.make_worktree(self, {".git": "gitdir: elsewhere\n"})
        with self.assertRaises(compile.RootError):
            compile.validate_root(root)

    def test_missing_root_is_refused(self):
        root = support.make_worktree(self)
        with self.assertRaisesRegex(compile.RootError, "not found"):
            compile.validate_root(root / "no-such-folder")
        self.assertFalse((root / "no-such-folder").exists())

    def test_file_as_root_is_refused(self):
        root = support.make_worktree(self, {"report.md": "x\n"})
        with self.assertRaisesRegex(compile.RootError, "not a folder"):
            compile.validate_root(root / "report.md")


class ResolveInRootTests(unittest.TestCase):
    def setUp(self):
        self.root = support.make_worktree(self, {
            "findings/F-001-x.md": "x\n",
            "findings/a..b.md": "x\n",
        })
        # A second worktree stands in for "somewhere outside the root", so the
        # tests never point at anything outside tools/tests/.tmp/.
        self.outside = support.make_worktree(self, {"findings/F-009-y.md": "y\n"})

    def test_normal_child_passes(self):
        resolved = compile.resolve_in_root(self.root, "findings/F-001-x.md")
        self.assertEqual(resolved, self.root.resolve() / "findings" / "F-001-x.md")

    def test_double_dot_inside_a_filename_passes(self):
        resolved = compile.resolve_in_root(self.root, "findings/a..b.md")
        self.assertEqual(resolved.name, "a..b.md")

    def test_symlink_inside_root_passes(self):
        (self.root / "latest").symlink_to(self.root / "findings")
        resolved = compile.resolve_in_root(self.root, "latest/F-001-x.md")
        self.assertEqual(resolved, self.root.resolve() / "findings" / "F-001-x.md")

    def test_absolute_path_inside_root_passes(self):
        # A real `--index ~/cptc-work/tracker/findings-index.csv` is absolute
        # once ~ is expanded, and must be allowed when it is inside the root.
        index = self.root.resolve() / "tracker" / "findings-index.csv"
        self.assertEqual(compile.resolve_in_root(self.root, index), index)

    def test_dot_dot_part_is_refused(self):
        with self.assertRaisesRegex(compile.RootError, re.escape("../x")):
            compile.resolve_in_root(self.root, "../x")

    def test_absolute_outside_path_is_refused(self):
        target = str(self.outside / "findings")
        with self.assertRaisesRegex(compile.RootError, re.escape(target)):
            compile.resolve_in_root(self.root, target)

    def test_index_outside_root_is_refused(self):
        index = self.outside / "tracker" / "findings-index.csv"
        with self.assertRaisesRegex(compile.RootError, re.escape(str(index))):
            compile.resolve_in_root(self.root, index)

    def test_symlinked_incoming_folder_outside_root_is_refused(self):
        (self.root / "incoming").mkdir()
        (self.root / "incoming" / "alice").symlink_to(self.outside)
        with self.assertRaisesRegex(compile.RootError, re.escape("incoming/alice")):
            compile.resolve_in_root(self.root, "incoming/alice/findings/F-009-y.md")


class DiscoverFindingsTests(unittest.TestCase):
    def test_only_local_and_incoming_findings_returned_in_path_order(self):
        finding = support.make_complete_finding()
        root = support.make_worktree(self, {
            "incoming/bob/findings/F-001-sql-injection.md": finding,
            "incoming/alice/findings/F-001-default-password.md": finding,
            "findings/F-001-default-password.md": finding,
            # Each of these must be left out:
            "findings/G-001.md": "x\n",
            "findings/F-002-notes.txt": "x\n",
            "findings/drafts/F-003-nested.md": "x\n",
            "incoming/alice/notes/F-004-study.md": "x\n",
            "incoming/alice/field-notes/alice/NOTE-recon.md": "x\n",
            "notes/F-005-study.md": "x\n",
        })
        found = compile.discover_findings(root)
        relative = [path.relative_to(root.resolve()).as_posix() for path in found]
        self.assertEqual(relative, [
            "findings/F-001-default-password.md",
            "incoming/alice/findings/F-001-default-password.md",
            "incoming/bob/findings/F-001-sql-injection.md",
        ])

    def test_folder_named_like_a_finding_is_skipped(self):
        root = support.make_worktree(self, {"findings/F-001-x.md/inside.md": "x\n"})
        self.assertEqual(compile.discover_findings(root), [])

    def test_no_findings_folders_returns_empty_list(self):
        root = support.make_worktree(self)
        self.assertEqual(compile.discover_findings(root), [])

    def test_incoming_symlinked_outside_root_is_refused(self):
        root = support.make_worktree(self, {"findings/F-001-x.md": "x\n"})
        outside = support.make_worktree(self, {"findings/F-009-y.md": "y\n"})
        (root / "incoming").mkdir()
        (root / "incoming" / "alice").symlink_to(outside)
        with self.assertRaisesRegex(compile.RootError, re.escape("incoming/alice")):
            compile.discover_findings(root)

    def test_outside_symlink_with_no_findings_is_still_refused(self):
        # The link must be refused before its target is listed, not only
        # when a finding happens to be found there.
        root = support.make_worktree(self)
        outside = support.make_worktree(self, {"other/readme.md": "y\n"})
        (root / "incoming").mkdir()
        (root / "incoming" / "alice").symlink_to(outside)
        with self.assertRaisesRegex(compile.RootError, re.escape("incoming/alice")):
            compile.discover_findings(root)

    def test_incoming_entry_symlinked_to_outside_file_is_refused(self):
        root = support.make_worktree(self)
        outside = support.make_worktree(self, {"readme.md": "y\n"})
        (root / "incoming").mkdir()
        (root / "incoming" / "alice").symlink_to(outside / "readme.md")
        with self.assertRaisesRegex(compile.RootError, re.escape("incoming/alice")):
            compile.discover_findings(root)

    def test_findings_folder_symlinked_outside_root_is_refused(self):
        root = support.make_worktree(self)
        outside = support.make_worktree(self, {"F-009-y.md": "y\n"})
        (root / "findings").symlink_to(outside)
        with self.assertRaisesRegex(compile.RootError, re.escape("findings")):
            compile.discover_findings(root)

    def test_finding_file_symlinked_outside_root_is_refused(self):
        root = support.make_worktree(self, {"findings/F-001-x.md": "x\n"})
        outside = support.make_worktree(self, {"F-009-y.md": "y\n"})
        (root / "findings" / "F-009-y.md").symlink_to(outside / "F-009-y.md")
        with self.assertRaisesRegex(compile.RootError, re.escape("F-009-y.md")):
            compile.discover_findings(root)

    def test_symlink_inside_root_is_allowed(self):
        root = support.make_worktree(self, {"shared/findings/F-002-y.md": "y\n"})
        (root / "incoming").mkdir()
        (root / "incoming" / "bob").symlink_to(root / "shared")
        found = compile.discover_findings(root)
        self.assertEqual([path.name for path in found], ["F-002-y.md"])

    def test_incoming_is_not_changed(self):
        root = support.make_worktree(self, {
            "incoming/alice/findings/F-001-x.md": support.make_complete_finding(),
        })
        incoming = root / "incoming"
        before = [(path, path.stat().st_mtime_ns) for path in sorted(incoming.rglob("*"))]
        compile.discover_findings(root)
        after = [(path, path.stat().st_mtime_ns) for path in sorted(incoming.rglob("*"))]
        self.assertEqual(after, before)


class ParseFindingHeadingTests(unittest.TestCase):
    def test_filled_heading(self):
        text = support.make_complete_finding("F-001", "Default admin password on web01")
        result = compile.parse_finding_heading("findings/F-001-default-password.md", text)
        self.assertEqual(result, {
            "id": "F-001",
            "title": "Default admin password on web01",
            "line": 1,
            "diagnostics": [],
        })

    def test_marker_heading_uses_filename_id_and_counts_marker(self):
        text = "### [[FINDING_ID]]: SMB signing not required\n\n- **Severity:** High\n"
        result = compile.parse_finding_heading("incoming/alice/findings/F-007-smb.md", text)
        self.assertEqual(result["id"], "F-007")
        self.assertEqual(result["title"], "SMB signing not required")
        self.assertEqual(result["diagnostics"], [])
        # The marker is counted by the whole-file leftover scan, not here.
        hits = compile.scan_leftover_markers("f.md", text)
        self.assertEqual(hits, [("f.md", 1, "[[FINDING_ID")])

    def test_untouched_template_heading(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        text = path.read_text(encoding="utf-8")
        result = compile.parse_finding_heading("findings/F-003-x.md", text)
        self.assertEqual(result["id"], "F-003")
        self.assertEqual(result["title"], "[[FINDING_TITLE]]")
        hits = compile.scan_leftover_markers("f.md", text)
        self.assertEqual([hit[2] for hit in hits if hit[1] == result["line"]],
                         ["[[FINDING_ID", "[[FINDING_TITLE"])

    def test_heading_and_filename_mismatch(self):
        text = support.make_complete_finding("F-002")
        result = compile.parse_finding_heading("findings/F-001-x.md", text)
        self.assertEqual(result["id"], "F-002")
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", 1, "heading ID F-002 does not match filename ID F-001"),
        ])

    def test_two_hashes_instead_of_three(self):
        text = "Intro line\n## F-001: Default admin password\n"
        result = compile.parse_finding_heading("findings/F-001-x.md", text)
        self.assertEqual(result["id"], "F-001")
        self.assertEqual(result["line"], 2)
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", 2, "title is a ## heading, not ###"),
        ])

    def test_no_heading_falls_back_to_filename_id(self):
        result = compile.parse_finding_heading("findings/F-001-x.md", "Default admin password\n")
        self.assertEqual(result["id"], "F-001")
        self.assertIsNone(result["title"])
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", 1, "no finding title heading like '### F-NNN: Title'"),
        ])

    def test_blank_title_is_reported(self):
        result = compile.parse_finding_heading("findings/F-001-x.md", "### F-001:  \n")
        self.assertEqual(result["title"], "")
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", 1, "heading has no title text"),
        ])

    def test_marker_heading_without_filename_id(self):
        # A library entry such as L03-*.md has no F-NNN in its name.
        text = "### [[FINDING_ID]]: SMB signing not required\n"
        result = compile.parse_finding_heading("findings-library/L03-smb.md", text)
        self.assertIsNone(result["id"])
        self.assertEqual(result["diagnostics"], [
            ("findings-library/L03-smb.md", 1, "no finding ID in the heading or the filename"),
        ])

    def test_windows_line_ending_is_not_part_of_the_title(self):
        text = "### F-001: Default admin password\r\n- **Severity:** High\r\n"
        result = compile.parse_finding_heading("findings/F-001-x.md", text)
        self.assertEqual(result["title"], "Default admin password")
        self.assertEqual(result["diagnostics"], [])

    def test_four_digit_filename_is_not_read_as_three(self):
        text = "### [[FINDING_ID]]: x\n"
        result = compile.parse_finding_heading("findings/F-0012-x.md", text)
        self.assertIsNone(result["id"])


class ParseLabelledFieldsTests(unittest.TestCase):
    def test_complete_finding_returns_all_six_labels_and_cvss_parts(self):
        result = compile.parse_labelled_fields("findings/F-001-x.md", support.make_complete_finding())
        fields = result["fields"]
        self.assertEqual(sorted(fields), sorted(compile.FIELD_LABELS))
        self.assertEqual(fields["Severity"], {"value": "Critical", "line": 3})
        self.assertEqual(fields["CVSS 3.1"]["value"],
                         "`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)")
        self.assertTrue(fields["Why this severity"]["value"].startswith("We logged in"))
        self.assertEqual(fields["Affected assets"]["value"],
                         "web01 (10.0.0.1), http://10.0.0.1/login, admin")
        self.assertEqual(fields["Status"]["value"], "Exploited")
        self.assertIn("https://example.invalid/", fields["References"]["value"])
        self.assertEqual(result["cvss_vector"], "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H")
        self.assertEqual(result["cvss_score"], "9.8")
        self.assertEqual(result["diagnostics"], [])

    def test_missing_label_is_reported_not_raised(self):
        text = support.make_complete_finding().replace(
            "- **Status:** Exploited\n", "")
        result = compile.parse_labelled_fields("findings/F-001-x.md", text)
        self.assertNotIn("Status", result["fields"])
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", "Status", "missing labelled line '- **Status:**'"),
        ])

    def test_duplicate_label_is_reported_and_first_line_wins(self):
        text = support.make_complete_finding().replace(
            "- **Severity:** Critical\n",
            "- **Severity:** Critical\n- **Severity:** Low\n- **Severity:** High\n")
        result = compile.parse_labelled_fields("findings/F-001-x.md", text)
        self.assertEqual(result["fields"]["Severity"], {"value": "Critical", "line": 3})
        self.assertEqual(result["diagnostics"], [
            ("findings/F-001-x.md", 4, "duplicate Severity line; line 3 is used"),
            ("findings/F-001-x.md", 5, "duplicate Severity line; line 3 is used"),
        ])

    def test_extra_whitespace_is_tolerated(self):
        text = "  -   ** Severity :**   High  \n-\t**Status:**\tConfirmed\n"
        fields = compile.parse_labelled_fields("f.md", text)["fields"]
        self.assertEqual(fields["Severity"], {"value": "High", "line": 1})
        self.assertEqual(fields["Status"], {"value": "Confirmed", "line": 2})

    def test_windows_line_endings_leave_no_carriage_return(self):
        text = "- **Severity:** High\r\n- **Status:** Confirmed\r\n"
        fields = compile.parse_labelled_fields("f.md", text)["fields"]
        self.assertEqual(fields["Severity"], {"value": "High", "line": 1})
        self.assertEqual(fields["Status"], {"value": "Confirmed", "line": 2})

    def test_untouched_template_keeps_markers_as_written(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        result = compile.parse_labelled_fields("findings/F-001-x.md", path.read_text(encoding="utf-8"))
        self.assertEqual(result["diagnostics"], [])
        self.assertEqual(result["fields"]["Severity"]["value"],
                         "[[CHOOSE: Critical / High / Medium / Low / Informational]]")
        self.assertEqual(result["cvss_vector"], "[[CVSS_VECTOR]]")
        self.assertEqual(result["cvss_score"], "[[CVSS_SCORE]]")

    def test_cvss_without_backticks_or_parentheses(self):
        text = "- **CVSS 3.1:** 9.8\n"
        result = compile.parse_labelled_fields("f.md", text)
        self.assertIsNone(result["cvss_vector"])
        self.assertIsNone(result["cvss_score"])

    def test_score_is_not_read_from_inside_the_vector(self):
        text = "- **CVSS 3.1:** `CVSS:3.1/AV:N (typo)` (7.5)\n"
        result = compile.parse_labelled_fields("f.md", text)
        self.assertEqual(result["cvss_vector"], "CVSS:3.1/AV:N (typo)")
        self.assertEqual(result["cvss_score"], "7.5")

    def test_empty_file_reports_every_label(self):
        result = compile.parse_labelled_fields("f.md", "")
        self.assertEqual([d[1] for d in result["diagnostics"]], compile.FIELD_LABELS)


def severity_of(line):
    """Parse one Severity line the way compile does: label first, then level."""
    fields = compile.parse_labelled_fields("findings/F-001-x.md", line + "\n")["fields"]
    return compile.severity_value("findings/F-001-x.md", fields)


class SeverityValueTests(unittest.TestCase):
    def test_filled_level(self):
        self.assertEqual(severity_of("- **Severity:** High"), ("High", []))

    def test_unfilled_choose_yields_no_severity_and_warns(self):
        line = "- **Severity:** [[CHOOSE: Critical / High / Medium / Low / Informational]]"
        self.assertEqual(severity_of(line), (None, [
            ("findings/F-001-x.md", 1,
             "no severity (Critical, High, Medium, Low or Informational); sorted last"),
        ]))

    def test_lowercase_yields_no_severity(self):
        severity, diagnostics = severity_of("- **Severity:** high")
        self.assertIsNone(severity)
        self.assertEqual(len(diagnostics), 1)

    def test_part_of_a_word_does_not_count(self):
        self.assertIsNone(severity_of("- **Severity:** Highest")[0])

    def test_first_level_wins_and_markers_are_stripped(self):
        # The library's default Medium, with its NOTE still attached.
        line = "- **Severity:** Medium [[NOTE: Library default; High if exploited.]]"
        self.assertEqual(severity_of(line), ("Medium", []))
        self.assertEqual(severity_of("- **Severity:** Low (was High)")[0], "Low")

    def test_missing_line_is_not_reported_twice(self):
        # parse_labelled_fields() already reports the missing label.
        self.assertEqual(compile.severity_value("f.md", {}), (None, []))


class FindingSortKeyTests(unittest.TestCase):
    def test_severity_order_then_missing_then_id(self):
        findings = [
            ("F-009", None),
            ("F-004", "Informational"),
            ("F-002", "Low"),
            ("F-007", "Critical"),
            ("F-003", None),
            ("F-005", "High"),
            ("F-006", "Medium"),
            ("F-001", "High"),
        ]
        ordered = sorted(findings, key=lambda f: compile.finding_sort_key(*f))
        self.assertEqual(ordered, [
            ("F-007", "Critical"),
            ("F-001", "High"),
            ("F-005", "High"),
            ("F-006", "Medium"),
            ("F-002", "Low"),
            ("F-004", "Informational"),
            ("F-003", None),
            ("F-009", None),
        ])

    def test_missing_id_still_sorts(self):
        self.assertEqual(compile.finding_sort_key(None, None), (5, ""))


INDEX_HEADER = "finding_id,title,severity,cvss_score,owner,status,in_report\n"


class LoadIndexIdsTests(unittest.TestCase):
    def test_default_index_loads_an_f001_row(self):
        root = support.make_worktree(self, {
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,Default password,High,9.8,alice,done,yes\n",
        })
        self.assertEqual(compile.load_index_ids(root, None, False), ({"F-001": 2}, []))

    def test_explicit_in_root_index_wins(self):
        root = support.make_worktree(self, {
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,x,,,,,\n",
            "lead/index.csv": INDEX_HEADER + "F-002,y,,,,,\n",
        })
        self.assertEqual(compile.load_index_ids(root, "lead/index.csv", False), ({"F-002": 2}, []))
        absolute = root.resolve() / "lead" / "index.csv"
        self.assertEqual(compile.load_index_ids(root, absolute, True), ({"F-002": 2}, []))

    def test_explicit_index_outside_root_is_refused(self):
        root = support.make_worktree(self)
        outside = support.make_worktree(self, {"index.csv": INDEX_HEADER + "F-001,x,,,,,\n"})
        with self.assertRaises(compile.RootError):
            compile.load_index_ids(root, outside / "index.csv", False)

    def test_absent_index_warns_and_skips_comparison(self):
        root = support.make_worktree(self)
        for final in (False, True):
            self.assertEqual(compile.load_index_ids(root, None, final), (None, [
                ("warning", "tracker/findings-index.csv", 0,
                 "findings index not found; ID comparison skipped"),
            ]))

    def test_header_only_index_warns_and_skips_comparison(self):
        root = support.make_worktree(self, {"tracker/findings-index.csv": INDEX_HEADER + "\n"})
        for final in (False, True):
            self.assertEqual(compile.load_index_ids(root, None, final), (None, [
                ("warning", "tracker/findings-index.csv", 1,
                 "findings index has no rows; ID comparison skipped"),
            ]))

    def test_empty_file_warns_and_skips_comparison(self):
        root = support.make_worktree(self, {"tracker/findings-index.csv": ""})
        ids, diagnostics = compile.load_index_ids(root, None, True)
        self.assertIsNone(ids)
        self.assertEqual([d[0] for d in diagnostics], ["warning"])

    def test_malformed_csv_is_warning_in_draft_and_error_in_final(self):
        root = support.make_worktree(self, {
            "tracker/findings-index.csv": INDEX_HEADER + '"F-001"x,y\n',
        })
        for final, level in ((False, "warning"), (True, "error")):
            ids, diagnostics = compile.load_index_ids(root, None, final)
            self.assertIsNone(ids)
            self.assertEqual(len(diagnostics), 1)
            self.assertEqual(diagnostics[0][:3], (level, "tracker/findings-index.csv", 0))
            self.assertIn("not a readable CSV", diagnostics[0][3])

    def test_missing_finding_id_column_is_warning_in_draft_and_error_in_final(self):
        root = support.make_worktree(self, {
            "tracker/findings-index.csv": "title,severity\nDefault password,High\n",
        })
        for final, level in ((False, "warning"), (True, "error")):
            self.assertEqual(compile.load_index_ids(root, None, final), (None, [
                (level, "tracker/findings-index.csv", 1,
                 "findings index has no finding_id column; ID comparison skipped"),
            ]))

    def test_spreadsheet_bom_and_spaces_are_tolerated(self):
        # Excel saves "UTF-8 CSV" with an invisible marker before the header.
        root = support.make_worktree(self, {
            "tracker/findings-index.csv": "﻿title, finding_id\nx, F-003 \ny,\n",
        })
        self.assertEqual(compile.load_index_ids(root, None, False), ({"F-003": 2}, []))


class ScanOlderLeftoversTests(unittest.TestCase):
    def scan(self, text):
        return [hit[2] for hit in compile.scan_older_leftovers("f.md", text)]

    def test_each_pattern_found_in_prose_with_line(self):
        text = "a << b\nTODO fix\nsee F-XXX and IR-XXX\nport XX open\nYYYY at HH:MM\n"
        self.assertEqual(compile.scan_older_leftovers("f.md", text), [
            ("f.md", 1, "<<"), ("f.md", 2, "TODO"), ("f.md", 3, "F-XXX"),
            ("f.md", 3, "IR-XXX"), ("f.md", 4, "XX"), ("f.md", 5, "YYYY"),
            ("f.md", 5, "HH:MM"),
        ])

    def test_xxe_is_not_bare_xx(self):
        self.assertEqual(self.scan("XXE injection in XXXL form"), [])

    def test_fenced_and_inline_code_skipped(self):
        text = "```\ncat << EOF\nTODO XX\n```\nrun `echo TODO F-XXX` here\nafter TODO\n"
        self.assertEqual(compile.scan_older_leftovers("f.md", text), [("f.md", 6, "TODO")])

    def test_tilde_fence_skipped_and_fence_kinds_not_mixed(self):
        text = "~~~\nTODO\n```\nYYYY\n~~~\nafter TODO\n"
        self.assertEqual(compile.scan_older_leftovers("f.md", text), [("f.md", 6, "TODO")])

    def test_double_backtick_span_skipped(self):
        self.assertEqual(self.scan("run ``TODO ` F-XXX`` then YYYY"), ["YYYY"])

    def test_code_span_does_not_join_xs(self):
        self.assertEqual(self.scan("X`code`X"), [])

    def test_todo_inside_todo_marker_skipped(self):
        self.assertEqual(self.scan("[[TODO: root cause]] and [[TODO: a\nTODO b]]"), [])

    def test_other_patterns_inside_markers_still_reported(self):
        self.assertEqual(self.scan("[[NOTE: use F-XXX\nthen YYYY]]"), ["F-XXX", "YYYY"])
        self.assertEqual(self.scan("[[TODO: fill F-XXX]]"), ["F-XXX"])

    def test_todo_inside_other_marker_still_reported(self):
        self.assertEqual(self.scan("[[NOTE: TODO later]]"), ["TODO"])


class CheckReproductionTests(unittest.TestCase):
    def finding(self, steps):
        return "### F-001: T\n\n#### Reproduction steps\n" + steps + "\n#### Evidence\nx\n"

    def test_two_steps_two_indented_expected_pass(self):
        text = self.finding("1. `cmd one`\n   Expected: a\n2. `cmd two`\n   Expected: b\n")
        self.assertEqual(compile.check_reproduction("f.md", text), [])

    def test_one_expected_fails_two_steps(self):
        text = self.finding("1. `cmd one`\n   Expected: a\n2. `cmd two`\n")
        self.assertEqual(compile.check_reproduction("f.md", text), [
            ("f.md", 3, "reproduction steps: 2 numbered steps, 1 Expected: lines; "
                        "need at least 1 step and an Expected: line for each"),
        ])

    def test_ip_first_output_lines_are_not_steps(self):
        # Pasted output such as /etc/hosts starts lines with an IP address.
        text = self.finding("1. `cat /etc/hosts`\n   Expected: the host list\n"
                            "```\n10.0.0.5 dc01\n10.0.0.6 web01\n```\n")
        self.assertEqual(compile.check_reproduction("f.md", text), [])

    def test_no_steps_fails(self):
        problems = compile.check_reproduction("f.md", self.finding("Expected: a\n"))
        self.assertIn("0 numbered steps", problems[0][2])

    def test_untouched_template_fails_despite_note_example(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        text = path.read_text(encoding="utf-8")
        # The NOTE's example really is in the section, so this test means something.
        self.assertIn("Expected:", compile.reproduction_section(text)[1])
        problems = compile.check_reproduction("templates/finding.md", text)
        self.assertEqual(len(problems), 1)
        self.assertIn("0 numbered steps, 0 Expected: lines", problems[0][2])

    def test_complete_finding_passes(self):
        text = support.make_complete_finding()
        self.assertEqual(compile.check_reproduction("f.md", text), [])

    def test_steps_after_next_heading_not_counted(self):
        text = self.finding("1. `cmd`\n") + "   Expected: a\n"
        self.assertEqual(len(compile.check_reproduction("f.md", text)), 1)

    def test_deeper_heading_does_not_end_section(self):
        text = self.finding("1. `cmd`\n##### detail\n   Expected: a\n")
        self.assertEqual(compile.check_reproduction("f.md", text), [])

    def test_windows_line_endings(self):
        text = self.finding("1. `cmd`\n   Expected: a\n").replace("\n", "\r\n")
        self.assertEqual(compile.check_reproduction("f.md", text), [])

    def test_missing_section_reported(self):
        self.assertEqual(compile.check_reproduction("f.md", "### F-001: T\n"), [
            ("f.md", "Reproduction steps", "missing '#### Reproduction steps' section"),
        ])


class HasTextTests(unittest.TestCase):
    def test_punctuation_only_remnants_are_missing(self):
        # Untouched template values once their markers are stripped.
        self.assertFalse(compile.has_text("[[HOST]] ([[HOST_IP]]), [[URL]], [[ACCOUNT]]"))
        self.assertFalse(compile.has_text("() ,"))
        self.assertFalse(compile.has_text("`[[CVSS_VECTOR]]` ([[CVSS_SCORE]])"))
        self.assertFalse(compile.has_text("`` ()"))
        self.assertFalse(compile.has_text("[[SEVERITY_RATIONALE]] [[NOTE: One line.]]"))
        self.assertFalse(compile.has_text(""))

    def test_filled_values_pass(self):
        self.assertTrue(compile.has_text("web01 (10.0.0.1)"))
        self.assertTrue(compile.has_text("`` (9)"))
        self.assertTrue(compile.has_text("Café"))

    def test_untouched_template_fields_missing(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        fields = compile.parse_labelled_fields("t.md", path.read_text(encoding="utf-8"))["fields"]
        # References is not missing: see the next test (DECISIONS 2026-10-20 C-11).
        self.assertEqual(compile.missing_required_fields(fields), [
            "Severity", "CVSS 3.1", "Why this severity", "Affected assets", "Status"])

    def test_untouched_references_remnant_counts_as_present(self):
        # "CWE-, ATT&CK ," has letters, so it counts as text (user decision,
        # option A). Its leftover markers still keep the finding from READY,
        # and the reference check (C-12) still fails it for having no http link.
        value = "CWE-[[CWE_ID]], ATT&CK [[ATTACK_TECHNIQUE_ID]], [[REFERENCE_URL]]"
        self.assertTrue(compile.has_text(value))

    def test_complete_finding_has_no_missing_fields(self):
        fields = compile.parse_labelled_fields("f.md", support.make_complete_finding())["fields"]
        self.assertEqual(compile.missing_required_fields(fields), [])

    def test_absent_label_counts_as_missing(self):
        text = support.make_complete_finding().replace("- **Status:**", "- **State:**")
        fields = compile.parse_labelled_fields("f.md", text)["fields"]
        self.assertEqual(compile.missing_required_fields(fields), ["Status"])

    def test_one_blank_value_counted_once(self):
        lines = []
        for line in support.make_complete_finding().split("\n"):
            if line.startswith("- **Why this severity:**"):
                line = "- **Why this severity:** [[SEVERITY_RATIONALE]] ."
            lines.append(line)
        fields = compile.parse_labelled_fields("f.md", "\n".join(lines))["fields"]
        self.assertEqual(compile.missing_required_fields(fields), ["Why this severity"])

    def test_reproduction_does_not_affect_missing_fields(self):
        text = support.make_complete_finding()
        no_steps = text.split("#### Reproduction steps")[0]
        self.assertNotEqual(compile.check_reproduction("f.md", no_steps), [])
        fields = compile.parse_labelled_fields("f.md", no_steps)["fields"]
        self.assertEqual(compile.missing_required_fields(fields), [])


class CheckReferencesTests(unittest.TestCase):
    def check(self, text):
        fields = compile.parse_labelled_fields("f.md", text)["fields"]
        return compile.check_references("f.md", fields)

    def test_references_without_http_fails(self):
        self.assertEqual(self.check("- **References:** CWE-798, ATT&CK T1078\n"),
                         [("f.md", 1, "References line has no http link")])

    def test_https_link_passes(self):
        self.assertEqual(self.check("- **References:** CWE-798, https://example.invalid/advisory\n"), [])

    def test_link_outside_the_labelled_line_does_not_count(self):
        text = "- **References:** CWE-798\n\nSee https://example.invalid for more.\n"
        self.assertEqual(self.check(text), [("f.md", 1, "References line has no http link")])

    def test_link_inside_a_marker_does_not_count(self):
        text = "- **References:** [[REFERENCE_URL]] [[NOTE: e.g. https://example.invalid]]\n"
        self.assertEqual(len(self.check(text)), 1)

    def test_untouched_template_fails(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        self.assertEqual(len(self.check(path.read_text(encoding="utf-8"))), 1)

    def test_complete_finding_passes(self):
        self.assertEqual(self.check(support.make_complete_finding()), [])

    def test_missing_line_not_reported_twice(self):
        self.assertEqual(self.check("- **Severity:** High\n"), [])


class CheckCvssVersionTests(unittest.TestCase):
    def check(self, cvss_line):
        parsed = compile.parse_labelled_fields("f.md", "- **CVSS 3.1:** " + cvss_line + "\n")
        return compile.check_cvss_version("f.md", parsed["fields"], parsed["cvss_vector"])

    def test_cvss_31_vector_passes(self):
        self.assertEqual(self.check("`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)"), [])

    def test_cvss_30_vector_fails_with_line(self):
        self.assertEqual(self.check("`CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)"), [
            ("f.md", 1, "CVSS vector is not a full CVSS 3.1 vector: "
                        "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
        ])

    def test_bare_score_fails(self):
        self.assertEqual(self.check("9.8"),
                         [("f.md", 1, "CVSS vector is not a full CVSS 3.1 vector: 9.8")])
        self.assertEqual(len(self.check("`9.8`")), 1)

    def test_missing_metric_fails(self):
        self.assertEqual(len(self.check("`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H` (9.8)")), 1)

    def test_reordered_metrics_fail(self):
        self.assertEqual(len(self.check("`CVSS:3.1/AC:L/AV:N/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)")), 1)

    def test_extra_metric_fails(self):
        self.assertEqual(len(self.check("`CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:P` (9.8)")), 1)

    def test_unfilled_vector_marker_skipped(self):
        self.assertEqual(self.check("`[[CVSS_VECTOR]]` ([[CVSS_SCORE]])"), [])
        self.assertEqual(self.check("`[[CVSS_VECTOR` (9.8)"), [])

    def test_other_marker_does_not_hide_wrong_version(self):
        self.assertEqual(len(self.check("`CVSS:3.0/AV:N [[TODO: fix]]` (9.8)")), 1)

    def test_empty_vector_fails(self):
        self.assertEqual(self.check("`` (9.8)"),
                         [("f.md", 1, "CVSS vector is not a full CVSS 3.1 vector: ")])
        self.assertEqual(len(self.check("`` ()")), 1)

    def test_complete_finding_passes(self):
        parsed = compile.parse_labelled_fields("f.md", support.make_complete_finding())
        self.assertEqual(compile.check_cvss_version("f.md", parsed["fields"], parsed["cvss_vector"]), [])

    def test_missing_line_not_reported_twice(self):
        self.assertEqual(compile.check_cvss_version("f.md", {}, None), [])


def id_locations(root):
    """Discover and parse a fake root's findings the way the tool does."""
    headings = []
    for path in compile.discover_findings(root):
        name = path.relative_to(root.resolve()).as_posix()
        text = path.read_text(encoding="utf-8")
        headings.append((name, compile.parse_finding_heading(name, text)))
    return compile.finding_id_locations(headings)


class FindingIdLocationsTests(unittest.TestCase):
    def test_heading_id_and_line_are_used(self):
        root = support.make_worktree(self, {
            "findings/F-001-x.md": "\n" + support.make_complete_finding("F-002"),
        })
        self.assertEqual(id_locations(root), [("findings/F-001-x.md", 2, "F-002")])

    def test_unfilled_heading_uses_the_filename_id(self):
        root = support.make_worktree(self, {"findings/F-003-x.md": "### [[FINDING_ID]]: Draft\n"})
        self.assertEqual(id_locations(root), [("findings/F-003-x.md", 1, "F-003")])

    def test_no_heading_points_at_line_1(self):
        root = support.make_worktree(self, {"findings/F-004-x.md": "notes only\n"})
        self.assertEqual(id_locations(root), [("findings/F-004-x.md", 1, "F-004")])

    def test_finding_without_any_id_is_left_out(self):
        root = support.make_worktree(self, {"findings/F-draft.md": "### [[FINDING_ID]]: Draft\n"})
        self.assertEqual(id_locations(root), [])


class CheckDuplicateIdsTests(unittest.TestCase):
    def check(self, files):
        return compile.check_duplicate_ids(id_locations(support.make_worktree(self, files)))

    def test_duplicate_within_one_folder(self):
        self.assertEqual(self.check({
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "findings/F-001-b.md": support.make_complete_finding("F-001"),
        }), [("findings/F-001-a.md", 1,
              "duplicate finding ID F-001 in: findings/F-001-a.md, findings/F-001-b.md")])

    def test_duplicate_local_versus_incoming(self):
        self.assertEqual(self.check({
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "incoming/alice/findings/F-001-b.md": support.make_complete_finding("F-001"),
        }), [("findings/F-001-a.md", 1,
              "duplicate finding ID F-001 in: findings/F-001-a.md, "
              "incoming/alice/findings/F-001-b.md")])

    def test_duplicate_across_two_incoming_owners(self):
        self.assertEqual(self.check({
            "incoming/alice/findings/F-004-a.md": support.make_complete_finding("F-004"),
            "incoming/bob/findings/F-004-b.md": support.make_complete_finding("F-004"),
        }), [("incoming/alice/findings/F-004-a.md", 1,
              "duplicate finding ID F-004 in: incoming/alice/findings/F-004-a.md, "
              "incoming/bob/findings/F-004-b.md")])

    def test_three_copies_give_one_problem_naming_every_path(self):
        problems = self.check({
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "incoming/alice/findings/F-001-b.md": support.make_complete_finding("F-001"),
            "incoming/bob/findings/F-001-c.md": support.make_complete_finding("F-001"),
        })
        self.assertEqual(len(problems), 1)
        for name in ("findings/F-001-a.md", "incoming/alice/findings/F-001-b.md",
                     "incoming/bob/findings/F-001-c.md"):
            self.assertIn(name, problems[0][2])

    def test_unique_ids_pass(self):
        self.assertEqual(self.check({
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "incoming/alice/findings/F-002-b.md": support.make_complete_finding("F-002"),
        }), [])

    def test_compares_the_heading_id_and_leaves_the_mismatch_to_the_heading_check(self):
        # F-001-x.md has an F-002 heading, so it clashes with F-002-y.md. The
        # filename/heading mismatch itself is reported only by C-05.
        problems = self.check({
            "findings/F-001-x.md": support.make_complete_finding("F-002"),
            "findings/F-002-y.md": support.make_complete_finding("F-002"),
        })
        self.assertEqual(problems, [("findings/F-001-x.md", 1,
                                     "duplicate finding ID F-002 in: findings/F-001-x.md, "
                                     "findings/F-002-y.md")])

    def test_unfilled_heading_counts_by_its_filename_id(self):
        self.assertEqual(len(self.check({
            "findings/F-003-a.md": "### [[FINDING_ID]]: Draft\n",
            "incoming/alice/findings/F-003-b.md": support.make_complete_finding("F-003"),
        })), 1)


class CheckIndexMembershipTests(unittest.TestCase):
    def check(self, files):
        root = support.make_worktree(self, files)
        index_ids = compile.load_index_ids(root, None, True)[0]
        return compile.check_index_membership(id_locations(root), index_ids,
                                              "tracker/findings-index.csv")

    def test_missing_and_extra_ids_are_reported(self):
        self.assertEqual(self.check({
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,a,,,,,\nF-003,c,,,,,\n",
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "incoming/alice/findings/F-002-b.md": support.make_complete_finding("F-002"),
        }), [
            ("incoming/alice/findings/F-002-b.md", 1,
             "F-002 is not in the findings index tracker/findings-index.csv"),
            ("tracker/findings-index.csv", 3,
             "F-003 is in the findings index but no finding file has it"),
        ])

    def test_matching_index_passes(self):
        self.assertEqual(self.check({
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,a,,,,,\nF-002,b,,,,,\n",
            "findings/F-001-a.md": support.make_complete_finding("F-001"),
            "findings/F-002-b.md": support.make_complete_finding("F-002"),
        }), [])

    def test_absent_or_unusable_index_reports_neither(self):
        findings = {"findings/F-002-b.md": support.make_complete_finding("F-002")}
        for index_text in (None, INDEX_HEADER, '"F-001"x,y\n', "title,severity\nx,High\n"):
            files = dict(findings)
            if index_text is not None:
                files["tracker/findings-index.csv"] = index_text
            self.assertEqual(self.check(files), [], index_text)


def readiness_of(text):
    """Run one finding through the checks that decide READY or DRAFT."""
    heading = compile.parse_finding_heading("f.md", text)
    fields = compile.parse_labelled_fields("f.md", text)["fields"]
    severity = compile.severity_value("f.md", fields)[0]
    hits = compile.scan_leftover_markers("f.md", text)
    readiness = compile.finding_readiness(
        hits, compile.missing_required_fields(fields), severity, heading["title"])
    return readiness, compile.draft_banner(readiness[1])


class FindingReadinessTests(unittest.TestCase):
    def complete_with(self, old, new):
        text = support.make_complete_finding()
        self.assertIn(old, text)
        return text.replace(old, new)

    def test_complete_finding_is_ready(self):
        self.assertEqual(readiness_of(support.make_complete_finding())[0], ("READY", "READY"))

    def test_two_leftover_markers_give_draft_and_banner(self):
        text = self.complete_with("web01 (10.0.0.1)", "[[HOST]] ([[HOST_IP]])")
        self.assertEqual(readiness_of(text), (
            ("DRAFT", "DRAFT: 2 unresolved markers, 0 missing fields"),
            "[[NOTE: DRAFT: 2 unresolved markers, 0 missing fields]]",
        ))

    def test_heading_marker_is_counted_once(self):
        text = self.complete_with("### F-001:", "### [[FINDING_ID]]:")
        self.assertEqual(readiness_of(text)[0],
                         ("DRAFT", "DRAFT: 1 unresolved markers, 0 missing fields"))

    def test_punctuation_only_value_counts_one_missing_field(self):
        text = self.complete_with("- **Status:** Exploited", "- **Status:** ()")
        self.assertEqual(readiness_of(text)[0],
                         ("DRAFT", "DRAFT: 0 unresolved markers, 1 missing fields"))

    def test_lowercase_severity_is_draft(self):
        text = self.complete_with("- **Severity:** Critical", "- **Severity:** high")
        self.assertEqual(readiness_of(text), (
            ("DRAFT", "DRAFT: 0 unresolved markers, 0 missing fields, no severity word"),
            "[[NOTE: DRAFT: 0 unresolved markers, 0 missing fields, no severity word]]",
        ))

    def test_blank_title_is_draft(self):
        text = support.make_complete_finding(title="")
        self.assertEqual(readiness_of(text), (
            ("DRAFT", "DRAFT: 0 unresolved markers, 0 missing fields, no title"),
            "[[NOTE: DRAFT: 0 unresolved markers, 0 missing fields, no title]]",
        ))

    def test_no_heading_is_draft(self):
        text = self.complete_with("### F-001: Default admin password on web01\n", "")
        self.assertEqual(readiness_of(text)[0],
                         ("DRAFT", "DRAFT: 0 unresolved markers, 0 missing fields, no title"))

    def test_untouched_template_is_draft_with_every_reason(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        text = path.read_text(encoding="utf-8")
        count = len(compile.scan_leftover_markers("f.md", text))
        self.assertEqual(readiness_of(text), (
            ("DRAFT", "DRAFT: " + str(count) + " unresolved markers, 5 missing fields, "
                      "no severity word"),
            "[[NOTE: DRAFT: " + str(count) + " unresolved markers, 5 missing fields, "
            "no severity word]]",
        ))


def library_entries(folder):
    """Return every entry in a findings-library folder, leaving out its README."""
    return sorted(path for path in folder.glob("*.md") if path.name != "README.md")


def check_whole_finding(name, text):
    """Run every per-finding check on one file and return its readiness."""
    heading = compile.parse_finding_heading(name, text)
    parsed = compile.parse_labelled_fields(name, text)
    fields = parsed["fields"]
    severity = compile.severity_value(name, fields)[0]
    compile.check_duplicate_ids(compile.finding_id_locations([(name, heading)]))
    compile.scan_older_leftovers(name, text)
    compile.check_reproduction(name, text)
    compile.check_references(name, fields)
    compile.check_cvss_version(name, fields, parsed["cvss_vector"])
    hits = compile.scan_leftover_markers(name, text)
    return compile.finding_readiness(
        hits, compile.missing_required_fields(fields), severity, heading["title"])


class FindingsLibraryTests(unittest.TestCase):
    def test_every_real_library_entry_parses(self):
        folder = support.TOOLS_DIR.parent / "findings-library"
        # The README must be there, so an empty list below means the folder
        # really has no entries yet, not that the path is wrong.
        self.assertTrue((folder / "README.md").is_file())
        # Since the 2026-10-19 repo split the folder holds only README.md
        # until finished entries come back from Drive, so today this loop
        # runs 0 times. The fake entries below cover parsing until then.
        for path in library_entries(folder):
            with self.subTest(entry=path.name):
                check_whole_finding(path.name, path.read_text(encoding="utf-8"))

    def test_fake_library_entries_parse_and_are_draft(self):
        root = support.make_worktree(self, {
            "findings-library/README.md": "# Findings Library\n\nNo [[TODO: …]] markers may remain.\n",
            "findings-library/L01-example-finished.md": support.make_library_entry(),
            "findings-library/L02-example-todo.md": support.make_library_entry(
                technical_detail="[[TODO: explain the root cause\nand why it matters]]"),
            "findings-library/L03-example-choose.md": support.make_library_entry(
                severity="[[CHOOSE: Critical / High / Medium / Low / Informational]]"),
        })
        entries = library_entries(root / "findings-library")
        self.assertEqual([path.name for path in entries], [
            "L01-example-finished.md", "L02-example-todo.md", "L03-example-choose.md"])
        for path in entries:
            with self.subTest(entry=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(check_whole_finding(path.name, text)[0], "DRAFT")
                # DRAFT comes from the C-00A leftover markers.
                self.assertNotEqual(compile.scan_leftover_markers(path.name, text), [])


def summary_inputs(name, text):
    """Parse one finding into its summary row and its pipe warnings."""
    heading = compile.parse_finding_heading(name, text)
    fields = compile.parse_labelled_fields(name, text)["fields"]
    severity = compile.severity_value(name, fields)[0]
    return (compile.summary_row(heading, fields, severity),
            compile.check_table_pipes(name, heading, fields))


SUMMARY_GOLDEN = """\
## Findings

| ID | Title | Severity | Affected assets | Status |
| --- | --- | --- | --- | --- |
| F-002 | Default admin password on web01 | Critical | web01 (10.0.0.1), http://10.0.0.1/login, admin | Exploited |
| F-004 |  | High | web01 (10.0.0.1), http://10.0.0.1/login, admin | Exploited |
| F-001 | Admin | user portal | Low | web01 (10.0.0.1), http://10.0.0.1/login, admin | Exploited |
| F-003 | Default admin password on web01 |  | web01 (10.0.0.1), http://10.0.0.1/login, admin | Exploited |

## Severity counts

| Critical | High | Medium | Low | Informational | Total |
| --- | --- | --- | --- | --- | --- |
| 1 | 1 | 0 | 1 | 0 | 4 |
"""


class RenderFindingsSummaryTests(unittest.TestCase):
    def finding(self, finding_id, title="Default admin password on web01", severity="Critical"):
        text = support.make_complete_finding(finding_id, title)
        return text.replace("- **Severity:** Critical", "- **Severity:** " + severity)

    def test_golden_summary(self):
        # Given out of order: F-003's lowercase "high" is no severity word,
        # and F-004's blank title is DRAFT but still listed.
        inputs = [
            summary_inputs("findings/F-003-x.md", self.finding("F-003", severity="high")),
            summary_inputs("findings/F-001-x.md", self.finding("F-001", "Admin | user portal", "Low")),
            summary_inputs("incoming/alice/findings/F-004-x.md", self.finding("F-004", "", "High")),
            summary_inputs("findings/F-002-x.md", self.finding("F-002")),
        ]
        rows = [row for row, problems in inputs]
        self.assertEqual(compile.render_findings_summary(rows), SUMMARY_GOLDEN)
        problems = [problem for row, found in inputs for problem in found]
        self.assertEqual(problems, [
            ("findings/F-001-x.md", 1, "F-001: '|' in Title breaks the summary table"),
        ])

    def test_pipe_in_assets_or_status_warns_without_changing_text(self):
        text = self.finding("F-005").replace("- **Status:** Exploited", "- **Status:** Exploited | via web01")
        text = text.replace("admin\n", "admin | backup\n", 1)
        row, problems = summary_inputs("incoming/bob/findings/F-005-x.md", text)
        self.assertEqual(row["assets"], "web01 (10.0.0.1), http://10.0.0.1/login, admin | backup")
        self.assertEqual(row["status"], "Exploited | via web01")
        self.assertEqual([(line, message) for name, line, message in problems], [
            (7, "F-005: '|' in Affected assets breaks the summary table"),
            (9, "F-005: '|' in Status breaks the summary table"),
        ])

    def test_no_pipe_gives_no_warning(self):
        self.assertEqual(summary_inputs("f.md", self.finding("F-001"))[1], [])

    def test_missing_fields_give_blank_cells(self):
        row, problems = summary_inputs("findings/F-006-x.md", "### F-006: Notes only\n")
        self.assertEqual(row, {"id": "F-006", "title": "Notes only", "severity": "",
                               "assets": "", "status": ""})
        self.assertEqual(problems, [])

    def test_no_findings_shows_zero_counts(self):
        text = compile.render_findings_summary([])
        self.assertIn("| --- | --- | --- | --- | --- |\n\n## Severity counts", text)
        self.assertTrue(text.endswith("| 0 | 0 | 0 | 0 | 0 | 0 |\n"))

    def test_escaped_pipe_does_not_warn(self):
        # "\\|" is Markdown's way to write a "|" inside a table cell.
        text = self.finding("F-001", "Guest \\| staff portal").replace(
            "- **Status:** Exploited", "- **Status:** Exploited \\| confirmed")
        row, problems = summary_inputs("f.md", text)
        self.assertEqual(row["title"], "Guest \\| staff portal")
        self.assertEqual(problems, [])

    def test_unescaped_pipe_next_to_an_escaped_one_still_warns(self):
        row, problems = summary_inputs("f.md", self.finding("F-001", "Guest \\| staff | portal"))
        self.assertEqual(problems, [("f.md", 1, "F-001: '|' in Title breaks the summary table")])


def filled_template(name, replacements):
    """Return a real template from templates/ with some markers filled in."""
    text = (support.TOOLS_DIR.parent / "templates" / name).read_text(encoding="utf-8")
    for marker, value in replacements.items():
        text = text.replace(marker, value)
    return text


class DiscoverTimelineFilesTests(unittest.TestCase):
    def names(self, root):
        return [path.relative_to(root.resolve()).as_posix()
                for path in compile.discover_timeline_files(root)]

    def test_local_and_incoming_timeline_files_are_found(self):
        root = support.make_worktree(self, {
            "field-notes/alice/IR-001-lockout.md": "# Incident Report IR-001\n",
            "field-notes/alice/SU-midpoint.md": "# Client Status Update\n",
            "field-notes/alice/INJ-scope.md": "# Inject Response: Scope\n",
            "incoming/bob/field-notes/bob/IR-002-crash.md": "# Incident Report IR-002\n",
        })
        self.assertEqual(self.names(root), [
            "field-notes/alice/INJ-scope.md",
            "field-notes/alice/IR-001-lockout.md",
            "field-notes/alice/SU-midpoint.md",
            "incoming/bob/field-notes/bob/IR-002-crash.md",
        ])

    def test_other_files_are_left_out(self):
        root = support.make_worktree(self, {
            "field-notes/alice/NOTE-recon.md": "# Recon notes\n",
            "field-notes/alice/IR-001.txt": "not markdown\n",
            "field-notes/alice/old/IR-002-x.md": "# nested one level too deep\n",
            "field-notes/IR-003-x.md": "# not inside a person's folder\n",
            "incoming/bob/findings/F-001-x.md": support.make_complete_finding(),
            "incoming/bob/SU-x.md": "# not inside field-notes\n",
        })
        self.assertEqual(self.names(root), [])

    def test_no_field_notes_folder_gives_empty_list(self):
        self.assertEqual(self.names(support.make_worktree(self)), [])

    def assert_refused(self, root, link):
        with self.assertRaises(compile.RootError) as caught:
            compile.discover_timeline_files(root)
        self.assertIn(link, str(caught.exception))

    def test_person_folder_linked_outside_is_refused(self):
        outside = support.make_worktree(self, {"IR-009-x.md": "# outside\n"})
        root = support.make_worktree(self, {"field-notes/bob/SU-x.md": "# ok\n"})
        (root / "field-notes" / "alice").symlink_to(outside)
        self.assert_refused(root, "field-notes/alice")

    def test_incoming_field_notes_linked_outside_is_refused(self):
        outside = support.make_worktree(self, {"bob/IR-009-x.md": "# outside\n"})
        root = support.make_worktree(self, {"incoming/bob/findings/F-001-x.md": "x\n"})
        (root / "incoming" / "bob" / "field-notes").symlink_to(outside)
        self.assert_refused(root, "incoming/bob/field-notes")

    def test_one_file_linked_outside_is_refused(self):
        outside = support.make_worktree(self, {"IR-009-x.md": "# outside\n"})
        root = support.make_worktree(self, {"field-notes/alice/SU-x.md": "# ok\n"})
        (root / "field-notes" / "alice" / "IR-009-x.md").symlink_to(outside / "IR-009-x.md")
        self.assert_refused(root, "field-notes/alice/IR-009-x.md")

    def test_link_inside_the_root_is_allowed(self):
        root = support.make_worktree(self, {"shared/SU-x.md": "# ok\n"})
        (root / "field-notes").mkdir()
        (root / "field-notes" / "alice").symlink_to(root / "shared")
        self.assertEqual(self.names(root), ["field-notes/alice/SU-x.md"])


def incident_file(number):
    """Return a small IR- file with a valid time, so it has no timeline problems."""
    return "# Incident Report IR-" + number + "\n- **Time reported:** 2026-11-07 09:05\n"


MISPLACED = "not in field-notes/<name>/, so it is not in the timeline"


class MisplacedTimelineFilesTests(unittest.TestCase):
    def test_probe_warns_in_draft_and_blocks_final(self):
        # The Chunk 7 CR-3 probe: before C-23, only IR-003 reached the
        # timeline and the other two were dropped with no problem line.
        root = support.make_worktree(self, {
            "IR-001-x.md": incident_file("001"),
            "field-notes/IR-002-x.md": incident_file("002"),
            "field-notes/alice/IR-003-x.md": incident_file("003"),
        })
        exit_code, qa_text, lines = compile.run(root, None, False)
        timeline = (root / "build" / "interactions-timeline.md").read_text(encoding="utf-8")
        self.assertIn("IR-003-x", timeline)
        self.assertNotIn("IR-001", timeline)
        self.assertNotIn("IR-002", timeline)
        self.assertEqual(exit_code, 0)
        self.assertEqual([line for line in lines if MISPLACED in line], [
            "WARNING: IR-001-x.md: " + MISPLACED,
            "WARNING: field-notes/IR-002-x.md: " + MISPLACED,
        ])
        exit_code, qa_text, lines = compile.run(root, None, True)
        self.assertEqual(exit_code, 1)
        # These two are the only errors, so they alone make --final fail.
        self.assertEqual([line for line in lines if line.startswith("ERROR:")], [
            "ERROR: IR-001-x.md: " + MISPLACED,
            "ERROR: field-notes/IR-002-x.md: " + MISPLACED,
        ])

    def test_same_two_spots_inside_each_incoming_owner(self):
        root = support.make_worktree(self, {
            "incoming/bob/SU-x.md": "# Status\n",
            "incoming/bob/field-notes/INJ-y.md": "# Inject\n",
            "incoming/bob/field-notes/bob/IR-004-z.md": incident_file("004"),
        })
        self.assertEqual(compile.misplaced_timeline_files(root), [
            ("incoming/bob/SU-x.md", 0, MISPLACED),
            ("incoming/bob/field-notes/INJ-y.md", 0, MISPLACED),
        ])

    def test_other_places_and_files_give_no_line(self):
        root = support.make_worktree(self, {
            "field-notes/alice/IR-001-x.md": incident_file("001"),
            "field-notes/alice/old/IR-002-x.md": incident_file("002"),
            "findings/IR-003-x.md": incident_file("003"),
            "NOTE-recon.md": "# Recon\n",
            "field-notes/NOTE-x.md": "# Note\n",
            "IR-004.txt": "not markdown\n",
            "IR-005-folder.md/inside.md": "a folder named like a file\n",
        })
        self.assertEqual(compile.misplaced_timeline_files(root), [])

    def test_file_linked_outside_is_refused(self):
        outside = support.make_worktree(self, {"IR-009-x.md": incident_file("009")})
        root = support.make_worktree(self)
        (root / "IR-009-x.md").symlink_to(outside / "IR-009-x.md")
        with self.assertRaises(compile.RootError) as caught:
            compile.misplaced_timeline_files(root)
        self.assertIn("IR-009-x.md", str(caught.exception))


class ParseTimelineEntryTests(unittest.TestCase):
    def test_incident_report(self):
        text = filled_template("incident-report.md", {
            "[[IR_ID]]": "IR-001", "[[DATE_REPORTED]] [[TIME_REPORTED]]": "2026-11-07 09:05"})
        entry = compile.parse_timeline_entry("field-notes/alice/IR-001-lockout.md", text)
        self.assertEqual(entry, {
            "type": "Incident", "time": "2026-11-07 09:05", "time_ok": True,
            "summary": "Incident Report IR-001", "reference": "IR-001-lockout",
            "diagnostics": [],
        })

    def test_status_update(self):
        text = filled_template("status-update.md", {"[[DATE]] [[TIME]]": "2026-11-07 10:00"})
        entry = compile.parse_timeline_entry("incoming/bob/field-notes/bob/SU-midpoint.md", text)
        self.assertEqual((entry["type"], entry["time"], entry["time_ok"], entry["summary"],
                          entry["reference"], entry["diagnostics"]),
                         ("Status update", "2026-11-07 10:00", True, "Client Status Update",
                          "SU-midpoint", []))

    def test_inject_response(self):
        text = filled_template("inject-response.md", {
            "[[INJECT_TITLE]]": "Scope question", "[[DATE_SENT]] [[TIME_SENT]]": "2026-11-07 11:30"})
        entry = compile.parse_timeline_entry("field-notes/alice/INJ-scope.md", text)
        self.assertEqual((entry["type"], entry["time"], entry["time_ok"], entry["summary"],
                          entry["reference"], entry["diagnostics"]),
                         ("Inject", "2026-11-07 11:30", True, "Inject Response: Scope question",
                          "INJ-scope", []))

    def test_summary_keeps_an_unfilled_marker_as_written(self):
        text = filled_template("incident-report.md", {
            "[[DATE_REPORTED]] [[TIME_REPORTED]]": "2026-11-07 09:05"})
        entry = compile.parse_timeline_entry("IR-001-x.md", text)
        self.assertEqual(entry["summary"], "Incident Report [[IR_ID]]")

    def test_time_without_date_warns(self):
        text = filled_template("status-update.md", {"[[DATE]] [[TIME]]": "09:05"})
        entry = compile.parse_timeline_entry("SU-x.md", text)
        self.assertFalse(entry["time_ok"])
        self.assertEqual(entry["diagnostics"], [
            ("SU-x.md", 5, "Time is not YYYY-MM-DD HH:MM: 09:05; sorted last")])

    def test_malformed_time_warns(self):
        text = filled_template("inject-response.md", {"[[DATE_SENT]] [[TIME_SENT]]": "around nine"})
        entry = compile.parse_timeline_entry("INJ-x.md", text)
        self.assertFalse(entry["time_ok"])
        self.assertEqual(entry["diagnostics"], [
            ("INJ-x.md", 7, "Sent is not YYYY-MM-DD HH:MM: around nine; sorted last")])

    def test_unfilled_marker_time_warns(self):
        entry = compile.parse_timeline_entry("IR-001-x.md", filled_template("incident-report.md", {}))
        self.assertFalse(entry["time_ok"])
        self.assertEqual(entry["diagnostics"], [
            ("IR-001-x.md", 8, "Time reported is not YYYY-MM-DD HH:MM: "
                               "[[DATE_REPORTED]] [[TIME_REPORTED]]; sorted last")])

    def test_incident_uses_time_reported_not_time_detected(self):
        text = filled_template("incident-report.md", {
            "[[DATE_DETECTED]] [[TIME_DETECTED]]": "2026-11-07 08:50"})
        self.assertFalse(compile.parse_timeline_entry("IR-001-x.md", text)["time_ok"])

    def test_missing_time_line_warns(self):
        entry = compile.parse_timeline_entry("SU-x.md", "# Client Status Update\n")
        self.assertEqual((entry["time"], entry["time_ok"]), ("", False))
        self.assertEqual(entry["diagnostics"], [
            ("SU-x.md", "Time", "missing labelled line '- **Time:**'; sorted last")])

    def test_missing_heading_warns(self):
        entry = compile.parse_timeline_entry("SU-x.md", "## Not a top heading\n- **Time:** 2026-11-07 10:00\n")
        self.assertEqual(entry["summary"], "")
        self.assertEqual(entry["diagnostics"], [("SU-x.md", 1, "no '# ' heading; Summary left blank")])

    def test_windows_line_endings(self):
        text = "# Client Status Update\r\n- **Time:** 2026-11-07 10:00\r\n"
        entry = compile.parse_timeline_entry("SU-x.md", text)
        self.assertEqual((entry["summary"], entry["time"], entry["time_ok"]),
                         ("Client Status Update", "2026-11-07 10:00", True))


TIMELINE_GOLDEN = """\
| Time | Type | Summary | Reference |
| --- | --- | --- | --- |
| 2026-11-07 09:05 | Incident | Incident Report IR-001 | IR-001-lockout |
| 2026-11-07 10:00 | Incident | Incident Report IR-002 | IR-002-crash |
| 2026-11-07 10:00 | Status update | Client Status Update | SU-midpoint |
| [[DATE_SENT]] [[TIME_SENT]] | Inject | Inject Response: Scope | INJ-scope |
| 09:05 | Status update | Client Status Update | SU-early |
"""


class RenderTimelineTests(unittest.TestCase):
    def entry(self, file_name, heading, label, time):
        text = "# " + heading + "\n\n- **" + label + ":** " + time + "\n"
        return compile.parse_timeline_entry(file_name, text)

    def test_golden_timeline(self):
        # Given out of order. The two 10:00 entries tie on time, so they go
        # by reference; the two invalid times go last, by reference.
        entries = [
            self.entry("SU-midpoint.md", "Client Status Update", "Time", "2026-11-07 10:00"),
            self.entry("SU-early.md", "Client Status Update", "Time", "09:05"),
            self.entry("INJ-scope.md", "Inject Response: Scope", "Sent", "[[DATE_SENT]] [[TIME_SENT]]"),
            self.entry("IR-002-crash.md", "Incident Report IR-002", "Time reported", "2026-11-07 10:00"),
            self.entry("IR-001-lockout.md", "Incident Report IR-001", "Time reported", "2026-11-07 09:05"),
        ]
        text = compile.render_timeline(entries)
        self.assertEqual(text, TIMELINE_GOLDEN)
        # Header, separator, then one row per entry.
        self.assertEqual(len(text.splitlines()), 2 + len(entries))

    def test_no_entries_gives_header_only(self):
        self.assertEqual(compile.render_timeline([]),
                         "| Time | Type | Summary | Reference |\n| --- | --- | --- | --- |\n")

    def test_pipe_in_summary_warns_without_changing_text(self):
        entry = self.entry("SU-x.md", "Status | midpoint", "Time", "2026-11-07 10:00")
        self.assertEqual(entry["summary"], "Status | midpoint")
        self.assertEqual(entry["diagnostics"],
                         [("SU-x.md", 1, "SU-x: '|' in Summary breaks the timeline table")])
        self.assertIn("| Status | midpoint |", compile.render_timeline([entry]))

    def test_escaped_pipe_in_summary_does_not_warn(self):
        entry = self.entry("SU-x.md", "Status \\| midpoint", "Time", "2026-11-07 10:00")
        self.assertEqual(entry["summary"], "Status \\| midpoint")
        self.assertEqual(entry["diagnostics"], [])

    def test_unescaped_pipe_next_to_an_escaped_one_still_warns(self):
        entry = self.entry("SU-x.md", "Status \\| mid | point", "Time", "2026-11-07 10:00")
        self.assertEqual(entry["diagnostics"],
                         [("SU-x.md", 1, "SU-x: '|' in Summary breaks the timeline table")])


def combined_entry(name, text):
    """Parse one finding into a render_combined_findings() entry."""
    heading = compile.parse_finding_heading(name, text)
    fields = compile.parse_labelled_fields(name, text)["fields"]
    severity = compile.severity_value(name, fields)[0]
    hits = compile.scan_leftover_markers(name, text)
    status, summary = compile.finding_readiness(
        hits, compile.missing_required_fields(fields), severity, heading["title"])
    return {"id": heading["id"], "severity": severity, "status": status,
            "summary": summary, "text": text}


class RenderCombinedFindingsTests(unittest.TestCase):
    def setUp(self):
        complete = support.make_complete_finding
        self.high = complete("F-002", "Weak service password").replace(
            "- **Severity:** Critical", "- **Severity:** High")
        # One leftover marker makes F-001 a draft.
        self.low_draft = complete("F-001", "Verbose error page").replace(
            "- **Severity:** Critical", "- **Severity:** Low").replace(
            "admin\n", "[[ACCOUNT]]\n", 1)

    def combined(self):
        return compile.render_combined_findings([
            combined_entry("findings/F-001-x.md", self.low_draft),
            combined_entry("findings/F-002-x.md", self.high),
        ])

    def test_golden_order_and_banner(self):
        self.assertEqual(self.combined(), self.high + "\n"
                         + "[[NOTE: DRAFT: 1 unresolved markers, 0 missing fields]]\n"
                         + self.low_draft)

    def test_headings_are_byte_identical(self):
        def headings(text):
            return [line for line in text.split("\n") if line.startswith("#")]
        self.assertEqual(headings(self.combined()), headings(self.high) + headings(self.low_draft))

    def test_only_the_draft_has_one_banner(self):
        text = self.combined()
        self.assertEqual(text.count("[[NOTE: DRAFT:"), 1)
        self.assertIn("[[NOTE: DRAFT: 1 unresolved markers, 0 missing fields]]\n"
                      "### F-001: Verbose error page\n", text)

    def test_missing_severity_goes_last(self):
        no_severity = self.high.replace("### F-002", "### F-000").replace(
            "- **Severity:** High", "- **Severity:** high")
        text = compile.render_combined_findings([
            combined_entry("findings/F-000-x.md", no_severity),
            combined_entry("findings/F-001-x.md", self.low_draft),
        ])
        self.assertLess(text.index("### F-001"), text.index("### F-000"))
        # Its banner says why: only the severity word holds it back.
        self.assertIn("[[NOTE: DRAFT: 0 unresolved markers, 0 missing fields, "
                      "no severity word]]\n### F-000", text)

    def test_text_is_kept_exactly_and_a_missing_last_line_break_is_added(self):
        windows = self.high.replace("\n", "\r\n")
        no_break = self.low_draft.rstrip("\n")
        text = compile.render_combined_findings([
            combined_entry("findings/F-002-x.md", windows),
            combined_entry("findings/F-001-x.md", no_break),
        ])
        self.assertEqual(text, windows + "\n"
                         + "[[NOTE: DRAFT: 1 unresolved markers, 0 missing fields]]\n"
                         + no_break + "\n")

    def test_no_findings_gives_empty_text(self):
        self.assertEqual(compile.render_combined_findings([]), "")


def whole_report(test, files, final):
    """Return render_qa_report() for a list of (name, text) findings.

    Each finding goes through compile.check_finding(), and the duplicate-ID
    check runs across them. The fake findings have no index and no timeline
    files, so those two checks are given as run with nothing found; their
    own tests are below. report.md is checked in an empty fake root, so in
    --final it is absent.
    """
    checks = no_problems()
    findings = []
    for name, text in files:
        finding = compile.check_finding(name, text, final)
        findings.append(finding)
        for check_name, problems in finding["checks"].items():
            checks[check_name] += problems
    headings = [(finding["name"], finding["heading"]) for finding in findings]
    duplicates = compile.check_duplicate_ids(compile.finding_id_locations(headings))
    checks["duplicate finding IDs"] = compile.check_problems(
        "duplicate finding IDs", duplicates, final)
    readiness = [(finding["name"], finding["summary"]) for finding in findings]
    report = compile.check_report(support.make_worktree(test), final)
    return compile.render_qa_report(final, readiness, checks, report)


def no_problems():
    """Return a checks dict where every QA check ran and found nothing."""
    return {name: [] for name in compile.QA_CHECKS}


QA_GOLDEN = """\
QA report (draft mode): problems are warnings

Findings:
  findings/F-001-x.md: READY

Checks:
PASS finding headings
PASS labelled lines
PASS severity
PASS required fields
PASS leftover markers
PASS older-style leftovers
PASS reproduction steps
PASS references
PASS CVSS version
PASS duplicate finding IDs
PASS findings index
PASS summary table
PASS interactions timeline
"""


class RenderQaReportTests(unittest.TestCase):
    def setUp(self):
        self.complete = support.make_complete_finding()
        # Two leftover markers on line 7, a punctuation-only Status on line 9
        # and an older-style TODO on line 19.
        self.draft = support.make_complete_finding("F-002").replace(
            "web01 (10.0.0.1), http", "[[HOST]] ([[HOST_IP]]), http").replace(
            "- **Status:** Exploited", "- **Status:** ()").replace(
            "unlimited attempts.", "unlimited attempts. TODO check lockout.")

    def report(self, final):
        """Render the report for the complete finding and the draft."""
        return whole_report(self, [("findings/F-001-x.md", self.complete),
                             ("findings/F-002-x.md", self.draft)], final)

    def test_golden_complete_finding_passes_every_check(self):
        self.assertEqual(whole_report(self, [("findings/F-001-x.md", self.complete)], False),
                         QA_GOLDEN)

    def test_final_header(self):
        self.assertTrue(self.report(True).startswith(
            "QA report (--final): any ERROR below fails the run\n"))

    def test_same_marker_is_warning_in_draft_and_error_in_final(self):
        self.assertIn("\n  WARNING: findings/F-002-x.md:7: leftover marker [[HOST\n",
                      self.report(False))
        self.assertIn("\n  ERROR: findings/F-002-x.md:7: leftover marker [[HOST\n",
                      self.report(True))

    def test_older_todo_is_warning_in_both_modes(self):
        for final in (False, True):
            with self.subTest(final=final):
                self.assertIn("\nFAIL (0 errors, 1 warnings) older-style leftovers\n"
                              "  WARNING: findings/F-002-x.md:19: older-style leftover TODO\n",
                              self.report(final))

    def test_empty_field_of_a_draft_is_an_error_in_final(self):
        # The draft's "()" Status makes it DRAFT with 1 missing field; the
        # matching problem is what fails --final (DECISIONS 2026-10-21 C-19 Q2).
        self.assertIn("\nFAIL (1 errors, 0 warnings) required fields\n"
                      "  ERROR: findings/F-002-x.md:9: Status has no value\n",
                      self.report(True))

    def test_readiness_lines(self):
        text = self.report(False)
        self.assertIn("\n  findings/F-001-x.md: READY\n", text)
        self.assertIn("\n  findings/F-002-x.md: DRAFT: 2 unresolved markers, 1 missing fields\n",
                      text)

    def test_every_check_has_pass_or_fail(self):
        lines = self.report(True).split("\n")
        results = [line for line in lines if line.startswith(("PASS ", "FAIL "))]
        self.assertEqual(len(results), len(compile.QA_CHECKS))
        self.assertIn("FAIL (2 errors, 0 warnings) leftover markers", results)
        self.assertIn("PASS labelled lines", results)

    def test_no_findings(self):
        text = compile.render_qa_report(False, [], no_problems(), None)
        self.assertIn("\nFindings:\n  no finding files found\n", text)

    def test_unknown_check_name_is_refused(self):
        checks = no_problems()
        checks["leftover marker"] = []
        with self.assertRaisesRegex(ValueError, "unknown QA check: leftover marker"):
            compile.render_qa_report(False, [], checks, None)

    def test_missing_check_is_refused(self):
        checks = no_problems()
        del checks["references"]
        with self.assertRaisesRegex(ValueError, "QA check not run: references"):
            compile.render_qa_report(False, [], checks, None)

    def test_qa_level(self):
        self.assertEqual(compile.qa_level("leftover markers", False), "warning")
        self.assertEqual(compile.qa_level("leftover markers", True), "error")
        self.assertEqual(compile.qa_level("older-style leftovers", False), "warning")
        self.assertEqual(compile.qa_level("older-style leftovers", True), "warning")
        # Timeline problems are errors in --final like the others
        # (DECISIONS 2026-10-21 C-19 Q1).
        self.assertEqual(compile.qa_level("interactions timeline", True), "error")


class CheckRequiredFieldsTests(unittest.TestCase):
    def fields(self, text):
        return compile.parse_labelled_fields("f.md", text)["fields"]

    def test_complete_finding_passes(self):
        self.assertEqual(
            compile.check_required_fields("f.md", self.fields(support.make_complete_finding())), [])

    def test_unfilled_rationale_fails_why_this_severity(self):
        lines = support.make_complete_finding().split("\n")
        self.assertTrue(lines[4].startswith("- **Why this severity:** We logged"))
        lines[4] = "- **Why this severity:** [[SEVERITY_RATIONALE]]"
        self.assertEqual(compile.check_required_fields("f.md", self.fields("\n".join(lines))),
                         [("f.md", 5, "Why this severity has no value")])

    def test_each_empty_field_at_its_line(self):
        text = support.make_complete_finding().replace(
            "- **Status:** Exploited", "- **Status:** -").replace(
            "web01 (10.0.0.1), http://10.0.0.1/login, admin", "(), ,")
        self.assertEqual(compile.check_required_fields("f.md", self.fields(text)), [
            ("f.md", 7, "Affected assets has no value"),
            ("f.md", 9, "Status has no value"),
        ])

    def test_missing_line_is_not_reported_twice(self):
        text = support.make_complete_finding().replace("- **Status:** Exploited\n", "")
        self.assertEqual(compile.check_required_fields("f.md", self.fields(text)), [])

    def test_untouched_template_reports_its_five_empty_fields(self):
        path = support.TOOLS_DIR.parent / "templates" / "finding.md"
        fields = self.fields(path.read_text(encoding="utf-8"))
        problems = compile.check_required_fields("f.md", fields)
        self.assertEqual([message for file_name, line, message in problems], [
            "Severity has no value", "CVSS 3.1 has no value", "Why this severity has no value",
            "Affected assets has no value", "Status has no value"])


class QaProblemShapeTests(unittest.TestCase):
    """Every diagnostic shape prints as file:line, or as file when it has no line."""

    def printed(self, check_name, diagnostics):
        problems = compile.check_problems(check_name, diagnostics, True)
        return [compile.problem_line(problem) for problem in problems]

    def test_file_line_message(self):
        text = support.make_complete_finding().replace("### F-001:", "### F-002:")
        diagnostics = compile.parse_finding_heading("findings/F-001-x.md", text)["diagnostics"]
        self.assertEqual(self.printed("finding headings", diagnostics), [
            "ERROR: findings/F-001-x.md:1: heading ID F-002 does not match filename ID F-001"])

    def test_missing_label_has_no_line(self):
        text = support.make_complete_finding().replace("- **Status:** Exploited\n", "")
        diagnostics = compile.parse_labelled_fields("findings/F-001-x.md", text)["diagnostics"]
        self.assertEqual(self.printed("labelled lines", diagnostics), [
            "ERROR: findings/F-001-x.md: missing labelled line '- **Status:**'"])

    def test_missing_reproduction_section_has_no_line(self):
        diagnostics = compile.check_reproduction("findings/F-001-x.md", "### F-001: x\n")
        self.assertEqual(self.printed("reproduction steps", diagnostics), [
            "ERROR: findings/F-001-x.md: missing '#### Reproduction steps' section"])

    def test_missing_timeline_time_has_no_line(self):
        diagnostics = compile.parse_timeline_entry(
            "field-notes/alice/SU-x.md", "# Client Status Update\n")["diagnostics"]
        self.assertEqual(self.printed("interactions timeline", diagnostics), [
            "ERROR: field-notes/alice/SU-x.md: missing labelled line '- **Time:**'; sorted last"])

    def test_leftover_hits(self):
        hits = compile.scan_leftover_markers("findings/F-001-x.md", "a\n[[HOST]] b\n")
        diagnostics = compile.hit_diagnostics(hits, "leftover marker")
        self.assertEqual(self.printed("leftover markers", diagnostics), [
            "ERROR: findings/F-001-x.md:2: leftover marker [[HOST"])

    def test_index_loader_keeps_its_level_and_line_zero_has_no_line(self):
        root = support.make_worktree(self, {"findings/README.md": "fake\n"})
        problems = compile.load_index_ids(root, None, True)[1]
        # An absent index stays a warning in --final (C-08).
        self.assertEqual([compile.problem_line(problem) for problem in problems], [
            "WARNING: tracker/findings-index.csv: findings index not found; ID comparison skipped"])
        checks = no_problems()
        checks["findings index"] = problems
        text = compile.render_qa_report(True, [], checks, compile.check_report(root, True))
        self.assertIn("\nFAIL (0 errors, 1 warnings) findings index\n", text)

    def test_index_line_is_kept(self):
        root = support.make_worktree(self, {"tracker/findings-index.csv": "title,severity\n"})
        problems = compile.load_index_ids(root, None, True)[1]
        self.assertEqual([compile.problem_line(problem) for problem in problems], [
            "ERROR: tracker/findings-index.csv:1: findings index has no finding_id column; "
            "ID comparison skipped"])


class CheckReportTests(unittest.TestCase):
    def render(self, final, report):
        return compile.render_qa_report(final, [], no_problems(), report)

    def test_report_only_marker_is_ignored_in_draft_and_blocks_final(self):
        root = support.make_worktree(self, {"report.md": "# Report\n\nHost: [[HOST]]\n"})
        self.assertIsNone(compile.check_report(root, False))
        self.assertNotIn("report.md", self.render(False, None))

        report = compile.check_report(root, True)
        self.assertEqual(report["status"], "report.md checked: 1 problems")
        self.assertEqual(report["checks"]["leftover markers"],
                         [("error", "report.md", 3, "leftover marker [[HOST")])
        self.assertTrue(self.render(True, report).endswith(
            "\nreport.md:\n"
            "report.md checked: 1 problems\n"
            "FAIL (1 errors, 0 warnings) leftover markers\n"
            "  ERROR: report.md:3: leftover marker [[HOST\n"
            "PASS older-style leftovers\n"))

    def test_draft_mode_never_opens_report(self):
        root = support.make_worktree(self)
        # Bytes that aren't UTF-8 make any read fail, so draft mode passing
        # proves it never opened the file.
        (root / "report.md").write_bytes(b"\xff [[HOST]]\n")
        self.assertIsNone(compile.check_report(root, False))
        with self.assertRaisesRegex(compile.InputError, "report.md is not UTF-8"):
            compile.check_report(root, True)

    def test_older_leftover_is_only_a_warning(self):
        root = support.make_worktree(self, {"report.md": "# Report\nTODO add scope\n"})
        report = compile.check_report(root, True)
        self.assertEqual(report["status"], "report.md checked: 1 problems")
        self.assertEqual(report["checks"]["older-style leftovers"],
                         [("warning", "report.md", 2, "older-style leftover TODO")])
        self.assertEqual(report["checks"]["leftover markers"], [])

    def test_absent_report_is_the_loud_line_only(self):
        root = support.make_worktree(self)
        report = compile.check_report(root, True)
        self.assertEqual(report, {"status": "report.md NOT FOUND: report not checked",
                                  "checks": {}})
        text = self.render(True, report)
        self.assertTrue(text.endswith("\nreport.md:\nreport.md NOT FOUND: report not checked\n"))
        # Absent alone adds no problem, so nothing fails the run.
        self.assertNotIn("ERROR:", text)
        self.assertNotIn("WARNING:", text)

    def test_clean_report_passes_both_checks(self):
        root = support.make_worktree(self, {"report.md": "# Report\n\nAll filled in.\n"})
        report = compile.check_report(root, True)
        self.assertTrue(self.render(True, report).endswith(
            "\nreport.md:\n"
            "report.md checked: 0 problems\n"
            "PASS leftover markers\n"
            "PASS older-style leftovers\n"))

    def test_report_is_not_changed(self):
        root = support.make_worktree(self, {"report.md": "# Report\r\n[[HOST]] TODO\r\n"})
        before = (root / "report.md").read_bytes()
        compile.check_report(root, True)
        self.assertEqual((root / "report.md").read_bytes(), before)

    def test_report_linked_outside_root_is_refused(self):
        root = support.make_worktree(self)
        outside = support.make_worktree(self, {"report.md": "# Elsewhere\n"})
        (root / "report.md").symlink_to(outside / "report.md")
        with self.assertRaisesRegex(compile.RootError, "report.md"):
            compile.check_report(root, True)

    def test_final_without_report_result_is_refused(self):
        with self.assertRaisesRegex(ValueError, "report.md"):
            self.render(True, None)


class WriteOutputsTests(unittest.TestCase):
    DRAFT_NAME = "incoming/alice/findings/F-002-y.md"

    def setUp(self):
        # Two leftover markers on line 7 and an older-style TODO on line 19.
        self.draft = support.make_complete_finding("F-002", "Weak service password").replace(
            "web01 (10.0.0.1), http", "[[HOST]] ([[HOST_IP]]), http").replace(
            "unlimited attempts.", "unlimited attempts. TODO check lockout.")
        self.root = support.make_worktree(self, {
            "findings/F-001-x.md": support.make_complete_finding(),
            self.DRAFT_NAME: self.draft,
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,,,,,,\nF-002,,,,,,\n",
            "field-notes/bob/SU-mid.md": "# Client Status Update\n\n- **Time:** 2026-11-07 10:00\n",
            "report.md": "# Report\n\n[[EXEC_SUMMARY]]\n",
        })

    def run_outputs(self, final, index=None):
        collected = compile.collect_qa(self.root, index, final)
        return compile.write_outputs(self.root, collected, final), collected

    def wrote_lines(self):
        build = self.root.resolve() / "build"
        return ["WROTE " + str(build / name) for name in compile.OUTPUT_FILES]

    def test_draft_console_lines(self):
        lines = self.run_outputs(False)[0]
        self.assertEqual(lines, self.wrote_lines() + [
            "WARNING: " + self.DRAFT_NAME + ":7: leftover marker [[HOST",
            "WARNING: " + self.DRAFT_NAME + ":7: leftover marker [[HOST_IP",
            "WARNING: " + self.DRAFT_NAME + ":19: older-style leftover TODO",
            "QA: 2 findings; 1 READY; 1 DRAFT; 3 warnings; 0 errors",
        ])

    def test_final_console_lines(self):
        lines = self.run_outputs(True)[0]
        self.assertEqual(lines, self.wrote_lines() + [
            "ERROR: " + self.DRAFT_NAME + ":7: leftover marker [[HOST",
            "ERROR: " + self.DRAFT_NAME + ":7: leftover marker [[HOST_IP",
            "WARNING: " + self.DRAFT_NAME + ":19: older-style leftover TODO",
            "ERROR: report.md:3: leftover marker [[EXEC_SUMMARY",
            "report.md checked: 1 problems",
            "QA: 2 findings; 1 READY; 1 DRAFT; 1 warnings; 3 errors",
        ])

    def test_final_absent_report_status_line(self):
        (self.root / "report.md").unlink()
        lines = self.run_outputs(True)[0]
        self.assertEqual(lines[-2:], ["report.md NOT FOUND: report not checked",
                                      "QA: 2 findings; 1 READY; 1 DRAFT; 1 warnings; 2 errors"])

    def test_four_files_hold_the_rendered_text(self):
        lines, collected = self.run_outputs(False)
        build = self.root / "build"
        findings = collected["findings"]
        self.assertEqual(sorted(path.name for path in build.iterdir()),
                         sorted(compile.OUTPUT_FILES))
        self.assertEqual((build / "findings-summary.md").read_text(encoding="utf-8"),
                         compile.render_findings_summary([f["row"] for f in findings]))
        self.assertEqual((build / "interactions-timeline.md").read_text(encoding="utf-8"),
                         compile.render_timeline(collected["timeline"]))
        self.assertIn("| 2026-11-07 10:00 | Status update | Client Status Update | SU-mid |",
                      (build / "interactions-timeline.md").read_text(encoding="utf-8"))
        self.assertEqual((build / "findings-combined.md").read_text(encoding="utf-8"),
                         compile.render_combined_findings([f["combined"] for f in findings]))
        qa = (build / "qa-report.txt").read_text(encoding="utf-8")
        self.assertIn("\n  findings/F-001-x.md: READY\n"
                      "  " + self.DRAFT_NAME + ": DRAFT: 2 unresolved markers, 0 missing fields\n",
                      qa)

    def test_stale_content_disappears(self):
        build = self.root / "build"
        build.mkdir()
        for name in compile.OUTPUT_FILES:
            (build / name).write_text("STALE " * 1000, encoding="utf-8")
        self.run_outputs(False)
        for name in compile.OUTPUT_FILES:
            with self.subTest(file=name):
                self.assertNotIn("STALE", (build / name).read_text(encoding="utf-8"))

    def test_report_md_is_never_written(self):
        before = (self.root / "report.md").read_bytes()
        for final in (False, True):
            with self.subTest(final=final):
                lines = self.run_outputs(final)[0]
                self.assertEqual((self.root / "report.md").read_bytes(), before)
                self.assertFalse(any(line.startswith("WROTE") and line.endswith("report.md")
                                     for line in lines))

    def test_draft_has_no_report_status(self):
        lines = self.run_outputs(False)[0]
        self.assertFalse(any(line.startswith("report.md") for line in lines))

    def test_incoming_is_not_changed(self):
        path = self.root / self.DRAFT_NAME
        before = path.read_bytes()
        self.run_outputs(True)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in (self.root / "incoming").rglob("*")),
                         ["F-002-y.md", "alice", "findings"])

    def test_linked_build_folder_is_refused(self):
        outside = support.make_worktree(self)
        (self.root / "build").symlink_to(outside)
        with self.assertRaisesRegex(compile.RootError, "build"):
            self.run_outputs(False)
        self.assertEqual(list(outside.iterdir()), [])

    def stale_build(self):
        """Fill the first three outputs with STALE; return every file's bytes."""
        build = self.root / "build"
        build.mkdir()
        for name in compile.OUTPUT_FILES[:3]:
            (build / name).write_text("STALE\n", encoding="utf-8")
        return [(build / name).read_bytes() for name in compile.OUTPUT_FILES[:3]]

    def assert_unchanged(self, stale, report):
        """Assert the first three outputs and report.md kept their bytes."""
        build = self.root / "build"
        self.assertEqual([(build / name).read_bytes() for name in compile.OUTPUT_FILES[:3]],
                         stale)
        self.assertEqual((self.root / "report.md").read_bytes(), report)

    def test_output_linked_to_report_is_refused_before_any_write(self):
        report = (self.root / "report.md").read_bytes()
        stale = self.stale_build()
        (self.root / "build" / "qa-report.txt").symlink_to(self.root / "report.md")
        with self.assertRaisesRegex(compile.RootError, "qa-report.txt"):
            self.run_outputs(False)
        self.assert_unchanged(stale, report)

    def test_output_folder_is_refused_before_any_write(self):
        report = (self.root / "report.md").read_bytes()
        stale = self.stale_build()
        (self.root / "build" / "qa-report.txt").mkdir()
        with self.assertRaisesRegex(compile.RootError, "not a file.*qa-report.txt"):
            self.run_outputs(False)
        self.assert_unchanged(stale, report)

    def test_output_hard_linked_to_report_is_refused_before_any_write(self):
        report = (self.root / "report.md").read_bytes()
        stale = self.stale_build()
        os.link(self.root / "report.md", self.root / "build" / "qa-report.txt")
        with self.assertRaisesRegex(compile.RootError, "hard link.*qa-report.txt"):
            self.run_outputs(False)
        self.assert_unchanged(stale, report)

    def test_build_folder_linked_into_incoming_is_refused(self):
        (self.root / "build").symlink_to(self.root / "incoming" / "alice")
        with self.assertRaisesRegex(compile.RootError, "build"):
            self.run_outputs(False)
        self.assertEqual(sorted(p.name for p in (self.root / "incoming" / "alice").iterdir()),
                         ["findings"])

    def test_index_problems_name_the_same_file(self):
        support.write_fake_file(self.root, "lead/index.csv", INDEX_HEADER + "F-001,,,,,,\n")
        lines = self.run_outputs(False, index="lead/index.csv")[0]
        self.assertIn("WARNING: " + self.DRAFT_NAME + ":1: F-002 is not in the findings index "
                      "lead/index.csv", lines)

    def test_timeline_and_pipe_problems_are_collected(self):
        support.write_fake_file(self.root, "field-notes/bob/SU-mid.md",
                                "# Client Status Update\n\n- **Time:** 10:00\n")
        support.write_fake_file(self.root, "findings/F-003-z.md",
                                support.make_complete_finding("F-003", "Login | portal"))
        support.write_fake_file(self.root, "tracker/findings-index.csv",
                                INDEX_HEADER + "F-001,,,,,,\nF-002,,,,,,\nF-003,,,,,,\n")
        lines = self.run_outputs(True)[0]
        self.assertIn("ERROR: findings/F-003-z.md:1: F-003: '|' in Title breaks the summary table",
                      lines)
        self.assertIn("ERROR: field-notes/bob/SU-mid.md:3: Time is not YYYY-MM-DD HH:MM: 10:00; "
                      "sorted last", lines)

    def test_windows_line_endings_reach_combined_unchanged(self):
        windows = support.make_complete_finding().replace("\n", "\r\n")
        (self.root / "findings" / "F-001-x.md").write_bytes(windows.encode("utf-8"))
        self.run_outputs(False)
        combined = (self.root / "build" / "findings-combined.md").read_bytes()
        self.assertTrue(combined.startswith(windows.encode("utf-8")))

    def test_finding_with_bom_is_ready_and_bom_is_dropped(self):
        # Older Windows Notepad and PowerShell 5.1 save UTF-8 with a BOM.
        text = support.make_complete_finding()
        (self.root / "findings" / "F-001-x.md").write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
        lines, collected = self.run_outputs(True)
        self.assertEqual(collected["findings"][0]["status"], "READY")
        self.assertFalse([line for line in lines if "F-001-x.md" in line])
        combined = (self.root / "build" / "findings-combined.md").read_bytes()
        self.assertTrue(combined.startswith(text.encode("utf-8")))

    def test_timeline_file_with_bom_keeps_its_summary(self):
        (self.root / "field-notes" / "bob" / "SU-mid.md").write_bytes(
            b"\xef\xbb\xbf# Client Status Update\n\n- **Time:** 2026-11-07 10:00\n")
        self.run_outputs(False)
        self.assertIn("| 2026-11-07 10:00 | Status update | Client Status Update | SU-mid |",
                      (self.root / "build" / "interactions-timeline.md").read_text(encoding="utf-8"))

    def test_empty_working_copy(self):
        root = support.make_worktree(self)
        collected = compile.collect_qa(root, None, False)
        lines = compile.write_outputs(root, collected, False)
        self.assertEqual(lines[4:], [
            "WARNING: tracker/findings-index.csv: findings index not found; ID comparison skipped",
            "QA: 0 findings; 0 READY; 0 DRAFT; 1 warnings; 0 errors",
        ])


class RunTests(unittest.TestCase):
    def setUp(self):
        # One leftover marker makes F-002 a draft; F-001 is complete.
        self.draft = support.make_complete_finding("F-002", "Weak service password").replace(
            "web01 (10.0.0.1), http", "[[HOST]] (10.0.0.1), http")
        self.root = support.make_worktree(self, {
            "findings/F-001-x.md": support.make_complete_finding(),
            "findings/F-002-y.md": self.draft,
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,,,,,,\nF-002,,,,,,\n",
        })

    def run_quietly(self, root, index=None, final=False):
        """Call compile.run() and return its result plus anything it printed."""
        printed = io.StringIO()
        # which() is patched to None so a pandoc installed on this machine
        # doesn't add a hint line to every result.
        with contextlib.redirect_stdout(printed), mock.patch("shutil.which", return_value=None):
            result = compile.run(root, index, final)
        return result, printed.getvalue()

    def test_run_returns_data_and_prints_nothing(self):
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root)
        self.assertEqual(printed, "")
        self.assertEqual(exit_code, 0)
        self.assertEqual(qa_text, (self.root / "build" / "qa-report.txt").read_text(encoding="utf-8"))
        self.assertEqual(lines[-1], "QA: 2 findings; 1 READY; 1 DRAFT; 1 warnings; 0 errors")

    def test_draft_marker_is_exit_0_and_final_is_exit_1(self):
        self.assertEqual(self.run_quietly(self.root)[0][0], 0)
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root, final=True)
        self.assertEqual(exit_code, 1)
        self.assertIn("ERROR: findings/F-002-y.md:7: leftover marker [[HOST", lines)

    def test_final_with_only_warnings_is_exit_0(self):
        support.write_fake_file(self.root, "findings/F-002-y.md", self.draft.replace(
            "[[HOST]] (10.0.0.1)", "web01 (10.0.0.1) TODO"))
        support.write_fake_file(self.root, "report.md", "# Report\n")
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root, final=True)
        self.assertEqual(lines[-3:], [
            "WARNING: findings/F-002-y.md:7: older-style leftover TODO",
            "report.md checked: 0 problems",
            "QA: 2 findings; 2 READY; 0 DRAFT; 1 warnings; 0 errors",
        ])
        self.assertEqual(exit_code, 0)

    def test_final_absent_report_alone_is_exit_0(self):
        (self.root / "findings" / "F-002-y.md").unlink()
        support.write_fake_file(self.root, "tracker/findings-index.csv",
                                INDEX_HEADER + "F-001,,,,,,\n")
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root, final=True)
        self.assertEqual(lines[-2:], ["report.md NOT FOUND: report not checked",
                                      "QA: 1 findings; 1 READY; 0 DRAFT; 0 warnings; 0 errors"])
        self.assertEqual(exit_code, 0)

    def test_report_marker_only_blocks_final(self):
        support.write_fake_file(self.root, "findings/F-002-y.md", self.draft.replace(
            "[[HOST]] (10.0.0.1)", "web01 (10.0.0.1)"))
        support.write_fake_file(self.root, "report.md", "# Report\n[[EXEC_SUMMARY]]\n")
        self.assertEqual(self.run_quietly(self.root)[0][0], 0)
        self.assertEqual(self.run_quietly(self.root, final=True)[0][0], 1)

    def test_git_root_is_exit_2_and_writes_nothing(self):
        (self.root / ".git").mkdir()
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root)
        self.assertEqual(exit_code, 2)
        self.assertEqual(qa_text, "")
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("compile failed: this looks like the git clone"))
        self.assertFalse((self.root / "build").exists())

    def test_missing_root_is_exit_2(self):
        missing = self.root / "nope"
        (exit_code, qa_text, lines), printed = self.run_quietly(missing)
        self.assertEqual((exit_code, lines), (2, ["compile failed: root folder not found: "
                                                  + str(missing.resolve())]))

    def test_unreadable_finding_is_exit_2_naming_the_file(self):
        (self.root / "findings" / "F-002-y.md").write_bytes(b"\xff### F-002: x\n")
        (exit_code, qa_text, lines), printed = self.run_quietly(self.root)
        self.assertEqual(exit_code, 2)
        self.assertRegex(lines[0], r"^compile failed: .*F-002-y\.md is not UTF-8 text")

    def test_index_outside_root_is_exit_2(self):
        outside = support.make_worktree(self, {"index.csv": INDEX_HEADER})
        (exit_code, qa_text, lines), printed = self.run_quietly(
            self.root, index=outside / "index.csv")
        self.assertEqual(exit_code, 2)
        self.assertTrue(lines[0].startswith("compile failed: path is outside the root"))

    def test_index_name_matches_the_loader(self):
        # C-14 carry-forward: membership problems name the file the loader
        # names, here an explicit --index.
        support.write_fake_file(self.root, "lead/index.csv", INDEX_HEADER + "F-001,,,,,,\nf-002,,,,,,\n")
        lines = self.run_quietly(self.root, index="lead/index.csv")[0][2]
        # Exact text: f-002 matches nothing, so it is both missing and extra.
        self.assertIn("WARNING: findings/F-002-y.md:1: F-002 is not in the findings index "
                      "lead/index.csv", lines)
        self.assertIn("WARNING: lead/index.csv:3: f-002 is in the findings index but no "
                      "finding file has it", lines)

    def test_pandoc_present_adds_one_hint_last(self):
        with mock.patch("shutil.which", return_value="/usr/bin/pandoc") as which:
            exit_code, qa_text, lines = compile.run(self.root, None, False)
        which.assert_called_once_with("pandoc")
        root = self.root.resolve()
        self.assertEqual([line for line in lines if line.startswith("HINT:")], [lines[-1]])
        self.assertEqual(lines[-1], "HINT: to convert the report, run: pandoc "
                         + shlex.quote(str(root / "report.md")) + " -o "
                         + shlex.quote(str(root / "build" / "report.docx"))
                         + " (or end it in report.pdf; PDF also needs a LaTeX engine)")

    def test_pandoc_hint_quotes_a_path_with_spaces(self):
        root = support.make_worktree(self) / "my work"
        root.mkdir()
        with mock.patch("shutil.which", return_value="/usr/bin/pandoc"):
            hint = compile.pandoc_hint(root)
        self.assertIn("pandoc '" + str(root.resolve()) + "/report.md' -o '", hint)

    def test_pandoc_absent_adds_no_hint(self):
        lines = self.run_quietly(self.root)[0][2]
        self.assertFalse(any(line.startswith("HINT:") for line in lines))


class MainTests(unittest.TestCase):
    def test_main_prints_the_lines_and_returns_the_exit_code(self):
        root = support.make_worktree(self, {
            "findings/F-001-x.md": support.make_complete_finding().replace(
                "- **Status:** Exploited", "- **Status:** [[CHOOSE: Open / Exploited]]"),
        })
        for final, expected in ((False, 0), (True, 1)):
            with self.subTest(final=final):
                argv = ["--root", str(root)] + (["--final"] if final else [])
                printed = io.StringIO()
                with contextlib.redirect_stdout(printed), \
                        mock.patch("shutil.which", return_value=None):
                    exit_code = compile.main(argv)
                    lines = compile.run(root, None, final)[2]
                self.assertEqual(exit_code, expected)
                self.assertEqual(printed.getvalue(), "\n".join(lines) + "\n")

    def test_help_exits_0(self):
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                compile.main(["--help"])
        self.assertEqual(raised.exception.code, 0)


class ModuleSafetyTests(unittest.TestCase):
    PATH = support.TOOLS_DIR / "compile.py"

    def test_import_is_silent(self):
        # Load a fresh copy under another name, so the tests' own compile
        # module is untouched; importing it must print nothing.
        spec = importlib.util.spec_from_file_location("compile_import_check", str(self.PATH))
        module = importlib.util.module_from_spec(spec)
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), contextlib.redirect_stderr(printed):
            spec.loader.exec_module(module)
        self.assertEqual(printed.getvalue(), "")

    def test_only_safe_modules_are_imported(self):
        tree = ast.parse(self.PATH.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        # No subprocess or os (os.system, os.popen): the tool runs no commands.
        self.assertEqual(imported, {"argparse", "csv", "re", "shlex", "shutil", "sys", "pathlib"})

    def test_no_command_running_call_appears(self):
        tree = ast.parse(self.PATH.read_text(encoding="utf-8"))
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Name):
                names.add(node.id)
        for name in ("subprocess", "system", "popen", "Popen", "exec", "eval"):
            with self.subTest(name=name):
                self.assertNotIn(name, names)


class CompleteRunTests(unittest.TestCase):
    """CTX-01: a fully filled-in working copy passes every --final check."""

    def setUp(self):
        # The event's shape: the report writer's own finding, a teammate's
        # finding in incoming/, an index listing both, one status update,
        # and a report.md with a finished finding pasted in.
        self.report = ("# Penetration Test Report\n\n## 5. Detailed Findings\n\n"
                       + support.make_complete_finding())
        self.root = support.make_worktree(self, {
            "findings/F-001-default-admin-password.md": support.make_complete_finding(),
            "incoming/bob/findings/F-002-weak-service-password.md":
                support.make_complete_finding("F-002", "Weak service password"),
            "tracker/findings-index.csv": INDEX_HEADER + "F-001,,,,,,\nF-002,,,,,,\n",
            "field-notes/alice/SU-midpoint.md":
                "# Client Status Update\n\n- **Time:** 2026-11-07 12:00\n",
            "report.md": self.report,
        })

    def run_final(self):
        """Run compile.run() in --final with no pandoc hint."""
        with mock.patch("shutil.which", return_value=None):
            return compile.run(self.root, None, True)

    def test_final_run_has_no_problems_and_returns_0(self):
        exit_code, qa_text, lines = self.run_final()
        self.assertEqual(exit_code, 0)
        # Four WROTE lines, then no WARNING or ERROR line at all.
        self.assertEqual(lines[4:], [
            "report.md checked: 0 problems",
            "QA: 2 findings; 2 READY; 0 DRAFT; 0 warnings; 0 errors",
        ])

    def test_every_qa_check_is_pass(self):
        qa_text = self.run_final()[1]
        # Every named check must print its result line, so a check missing
        # from the report fails this test. (It shows each line is there,
        # not that the check behind it ran.)
        check_lines = [line for line in qa_text.splitlines()
                       if line.startswith("PASS ") or line.startswith("FAIL ")]
        self.assertEqual(check_lines, ["PASS " + name for name in compile.QA_CHECKS]
                         + ["PASS leftover markers", "PASS older-style leftovers"])
        # The checks the complete finding exists to pass: its rationale, its
        # indented Expected: lines and its https:// reference.
        for name in ("required fields", "reproduction steps", "references"):
            with self.subTest(name=name):
                self.assertIn(name, compile.QA_CHECKS)
        self.assertIn("  findings/F-001-default-admin-password.md: READY", qa_text)
        self.assertIn("  incoming/bob/findings/F-002-weak-service-password.md: READY", qa_text)

    def test_all_four_outputs_are_written(self):
        exit_code, qa_text, lines = self.run_final()
        build = self.root.resolve() / "build"
        self.assertEqual(lines[:4], ["WROTE " + str(build / name)
                                     for name in compile.OUTPUT_FILES])
        self.assertEqual((build / "qa-report.txt").read_text(encoding="utf-8"), qa_text)
        summary = (build / "findings-summary.md").read_text(encoding="utf-8")
        self.assertIn("| F-001 | Default admin password on web01 | Critical | "
                      "web01 (10.0.0.1), http://10.0.0.1/login, admin | Exploited |", summary)
        self.assertIn("| F-002 | Weak service password | Critical | ", summary)
        self.assertIn("| 2 | 0 | 0 | 0 | 0 | 2 |", summary)
        timeline = (build / "interactions-timeline.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-11-07 12:00 | Status update | Client Status Update | SU-midpoint |",
                      timeline)
        # Both findings unchanged, in ID order, with no DRAFT banner.
        combined = (build / "findings-combined.md").read_text(encoding="utf-8")
        self.assertEqual(combined, support.make_complete_finding() + "\n"
                         + support.make_complete_finding("F-002", "Weak service password"))
        # report.md is only read, never written.
        self.assertEqual((self.root / "report.md").read_text(encoding="utf-8"), self.report)


class DoneMatrixTests(unittest.TestCase):
    """CTX-02: the Definition-of-done draft/final matrix in one table."""

    COMPLETE = support.make_complete_finding()
    # One leftover marker and nothing else wrong: Affected assets still has
    # text, so no required field goes missing.
    MARKED = COMPLETE.replace("web01 (10.0.0.1), http", "[[HOST]] (10.0.0.1), http")
    REPORT_WITH_MARKER = "# Penetration Test Report\n\n[[EXEC_SUMMARY]]\n"

    # (case, finding text, report.md text or None for absent, draft exit,
    #  --final exit, the finding's readiness, the --final ERROR lines)
    MATRIX = [
        ("marker in a finding", MARKED, None, 0, 1, "DRAFT",
         ["ERROR: findings/F-001-default-admin-password.md:7: leftover marker [[HOST"]),
        ("marker only in report.md", COMPLETE, REPORT_WITH_MARKER, 0, 1, "READY",
         ["ERROR: report.md:3: leftover marker [[EXEC_SUMMARY"]),
        ("report.md absent", COMPLETE, None, 0, 0, "READY", []),
    ]

    def run_quietly(self, root, final):
        """Run compile.run() with no pandoc hint."""
        with mock.patch("shutil.which", return_value=None):
            return compile.run(root, None, final)

    def test_draft_and_final_matrix(self):
        for case, finding, report, draft_exit, final_exit, readiness, final_errors in self.MATRIX:
            with self.subTest(case=case):
                # A fresh root per row, so one row's build/ can't affect the next.
                files = {
                    "findings/F-001-default-admin-password.md": finding,
                    "tracker/findings-index.csv": INDEX_HEADER + "F-001,,,,,,\n",
                }
                if report is not None:
                    files["report.md"] = report
                root = support.make_worktree(self, files)

                exit_code, qa_text, lines = self.run_quietly(root, False)
                self.assertEqual(exit_code, draft_exit)
                self.assertIn("  findings/F-001-default-admin-password.md: " + readiness, qa_text)
                # Draft mode ignores report.md: no line mentions it (the
                # pandoc hint, which names it, is patched out) and no error.
                self.assertFalse(any("report.md" in line for line in lines))
                self.assertFalse(any(line.startswith("ERROR:") for line in lines))
                combined = (root / "build" / "findings-combined.md").read_text(encoding="utf-8")
                self.assertEqual("[[NOTE: DRAFT" in combined, readiness == "DRAFT")

                exit_code, qa_text, lines = self.run_quietly(root, True)
                self.assertEqual(exit_code, final_exit)
                # The exit code alone could come from any error, so check the cause.
                self.assertEqual([line for line in lines if line.startswith("ERROR:")],
                                 final_errors)
                if report is None:
                    self.assertIn("report.md NOT FOUND: report not checked", lines)


# Findings A and B from the 'event-scenario' canvas note (base corpus),
# copied exactly. All names and addresses are fake.
EVENT_F001 = """\
### F-001: Ticket records accessible across guest accounts

- **Severity:** High
- **CVSS 3.1:** `CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:L/A:N` (8.1)
- **Why this severity:** Alice read another fake guest record and changed only its display note.
- **Affected assets:** web01 (192.0.2.20), https://tickets.example.invalid, alice
- **Status:** Confirmed
- **References:** CWE-639, https://example.invalid/standards/access-control

#### Reproduction steps
Starting position: signed in as alice.

1. Request `GET /tickets/1001` from `https://tickets.example.invalid`.
   Expected: the response shows the alice sample record.
2. Change the path to `GET /tickets/1002`.
   Expected: the response shows the bob sample record.
"""

# One real step plus pasted output that starts with an IP address. A person
# reads one step; the output line must not count as a second one.
EVENT_F002 = """\
### F-002: SMB signing is not required on dc01

- **Severity:** Medium
- **CVSS 3.1:** `CVSS:3.1/AV:A/AC:H/PR:L/UI:R/S:U/C:H/I:H/A:N` (6.1)
- **Why this severity:** Bob confirmed relay exposure but did not relay or change a system.
- **Affected assets:** dc01 (10.0.0.5), smb://dc01.example.invalid, bob
- **Status:** Confirmed
- **References:** CWE-345, https://example.invalid/standards/smb-signing

#### Reproduction steps
Starting position: in-scope internal test box with no privileged session.

1. Run `nxc smb 10.0.0.5 --gen-relay-list relay.txt`.
   Expected: dc01 is written to the relay target list.

```text
10.0.0.5 dc01 signing:false
```
"""


class EventScenarioTests(unittest.TestCase):
    """CTX-03: the event-scenario note's proven traps in one fake root.

    Each trap that causes a problem (F-003, F-004) has a file of its own, so
    each problem line points at one trap. F-002 holds two traps that should
    cause no problem.
      F-001  saved with a UTF-8 BOM (Windows Notepad)      Chunk 5 CR-1
      F-002  CRLF line endings                             Chunk 2 card
             and an IP-first output line                   Chunk 3 CR-2
      F-003  F-001 with lowercase "high"                   C-15 Q2
      F-004  F-001 with a second Severity line             Chunk 2 fix (a49e6b7)
      SU     status update saved with a UTF-8 BOM          Chunk 5 CR-1
    """

    BOM = b"\xef\xbb\xbf"
    F002_CRLF = EVENT_F002.replace("\n", "\r\n").encode("utf-8")

    def setUp(self):
        lowercase = EVENT_F001.replace(
            "F-001: Ticket records accessible across guest accounts",
            "F-003: Ticket export open to guest accounts").replace(
            "- **Severity:** High", "- **Severity:** high")
        duplicate = EVENT_F001.replace(
            "F-001: Ticket records accessible across guest accounts",
            "F-004: Ticket history open to guest accounts").replace(
            "- **Severity:** High\n", "- **Severity:** High\n- **Severity:** Medium\n")
        # Bytes, not text: the BOM and the CRLF endings are the traps, so
        # they must reach the file exactly.
        self.sources = {
            "findings/F-001-ticket-record-access.md": self.BOM + EVENT_F001.encode("utf-8"),
            "incoming/bob/findings/F-002-smb-signing.md": self.F002_CRLF,
            "findings/F-003-ticket-export.md": lowercase.encode("utf-8"),
            "findings/F-004-ticket-history.md": duplicate.encode("utf-8"),
            "field-notes/alice/SU-midpoint.md":
                self.BOM + b"# Client Status Update\n\n- **Time:** 2026-11-07 14:00\n",
            # Lists all four, so the index check adds no problem of its own.
            "tracker/findings-index.csv":
                (INDEX_HEADER + "F-001,,,,,,\nF-002,,,,,,\nF-003,,,,,,\nF-004,,,,,,\n").encode("utf-8"),
        }
        self.root = support.make_worktree(self)
        for relative_path, data in self.sources.items():
            path = self.root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

    def run_quietly(self, final):
        """Run compile.run() with no pandoc hint."""
        with mock.patch("shutil.which", return_value=None):
            return compile.run(self.root, None, final)

    def problem_lines(self, lines):
        return [line for line in lines
                if line.startswith("WARNING:") or line.startswith("ERROR:")]

    def test_draft_returns_0_with_two_warnings(self):
        exit_code, qa_text, lines = self.run_quietly(False)
        self.assertEqual(exit_code, 0)
        self.assertEqual(self.problem_lines(lines), [
            "WARNING: findings/F-004-ticket-history.md:4: duplicate Severity line; line 3 is used",
            "WARNING: findings/F-003-ticket-export.md:3: no severity (Critical, High, Medium, "
            "Low or Informational); sorted last",
        ])
        self.assertEqual(lines[-1], "QA: 4 findings; 3 READY; 1 DRAFT; 2 warnings; 0 errors")

    def test_final_returns_1_with_the_same_two_as_errors(self):
        exit_code, qa_text, lines = self.run_quietly(True)
        self.assertEqual(exit_code, 1)
        self.assertEqual(self.problem_lines(lines), [
            "ERROR: findings/F-004-ticket-history.md:4: duplicate Severity line; line 3 is used",
            "ERROR: findings/F-003-ticket-export.md:3: no severity (Critical, High, Medium, "
            "Low or Informational); sorted last",
        ])
        self.assertEqual(lines[-1], "QA: 4 findings; 3 READY; 1 DRAFT; 0 warnings; 2 errors")

    def test_readiness_of_each_trap(self):
        for final in (False, True):
            with self.subTest(final=final):
                qa_text = self.run_quietly(final)[1]
                # Lowercase "high" is not a severity word, so F-003 is the
                # only DRAFT (C-15 Q2). F-004's duplicate label is reported
                # on its own: READY looks only at markers, missing fields,
                # the severity word and the title (C-15).
                for line in (
                        "  findings/F-001-ticket-record-access.md: READY",
                        "  findings/F-003-ticket-export.md: DRAFT: 0 unresolved markers, "
                        "0 missing fields, no severity word",
                        "  findings/F-004-ticket-history.md: READY",
                        "  incoming/bob/findings/F-002-smb-signing.md: READY"):
                    self.assertIn(line, qa_text)
        combined = (self.root / "build" / "findings-combined.md").read_text(encoding="utf-8")
        self.assertEqual(combined.count("[[NOTE: DRAFT"), 1)

    def test_bom_finding_and_status_update_read_as_without_bom(self):
        self.run_quietly(False)
        build = self.root / "build"
        summary = (build / "findings-summary.md").read_text(encoding="utf-8")
        self.assertIn("| F-001 | Ticket records accessible across guest accounts | High | ", summary)
        timeline = (build / "interactions-timeline.md").read_text(encoding="utf-8")
        self.assertIn("| 2026-11-07 14:00 | Status update | Client Status Update | SU-midpoint |",
                      timeline)
        self.assertNotIn(self.BOM, (build / "findings-combined.md").read_bytes())

    def test_crlf_finding_with_ip_output_passes_reproduction(self):
        qa_text = self.run_quietly(True)[1]
        self.assertIn("\nPASS reproduction steps\n", qa_text)
        # The CRLF finding reaches the combined file byte for byte.
        self.assertIn(self.F002_CRLF, (self.root / "build" / "findings-combined.md").read_bytes())

    def test_source_files_are_unchanged(self):
        self.run_quietly(False)
        self.run_quietly(True)
        for relative_path, data in self.sources.items():
            with self.subTest(path=relative_path):
                self.assertEqual((self.root / relative_path).read_bytes(), data)


if __name__ == "__main__":
    unittest.main()
