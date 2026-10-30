"""compile.py: assemble everyone's findings into report-ready Markdown.

Reads the finding files in the working copy (yours and teammates' in
incoming/), writes report-ready tables and a combined findings file to build/,
and runs some of the checks from checklists/50-report-qa.md on the Markdown
files. The checklist's other items, and the search of the exported PDF/DOCX,
still apply.

Usage: python3 tools/compile.py [--root PATH] [--index PATH] [--final]

Python 3 standard library only. It never runs commands and never opens a
network connection; it only reads files in the working copy (Markdown and
the findings index CSV) and writes its generated files under build/.
"""

import argparse
import csv
import re
import shlex
import shutil
import sys
from pathlib import Path

# One template marker, complete from `[[` to `]]`. Read it aloud as:
#   \[\[            two opening brackets
#   [A-Z_]+         a name in capitals and underscores (HOST, NOTE, CHOOSE...)
#   (?:             then, optionally:
#     :             a colon,
#     (?:(?!\[\[).)*?  then any text, as little as possible, that never
#                    starts a new `[[`
#   )?
#   \]\]            two closing brackets
# Requiring a capital right after `[[` skips bash tests like `[[ -f x ]]`.
# DOTALL lets `.` match line breaks, so a NOTE spanning several lines is one
# marker. The "never starts a new `[[`" rule means a marker missing its `]]`
# stops matching at the next marker instead of swallowing it.
MARKER_RE = re.compile(r"\[\[[A-Z_]+(?::(?:(?!\[\[).)*?)?\]\]", re.DOTALL)

# The start of a leftover marker: `[[` followed by a capitalised name. This is
# the same pattern as the grep in checklists/50-report-qa.md, so the tool and
# the manual check agree. Why two regexes: MARKER_RE needs a whole marker so
# it can strip it; this one needs only the start, so it also reports a marker
# whose `]]` is missing (e.g. `[[NOTE: never closed`, or a bare `[[HOST`).
# Catching every unfinished marker is what lets a READY finding be trusted.
# A bash test like `[[ -f x ]]` has a space after `[[`, so it isn't reported.
LEFTOVER_RE = re.compile(r"\[\[[A-Z_]+")


def strip_markers(text):
    """Return text with every complete marker removed.

    Used before "does this field have a value?" checks, so an unfilled
    `[[SEVERITY_RATIONALE]]` doesn't count as text.
    """
    return MARKER_RE.sub("", text)


def scan_leftover_markers(file_name, text):
    """Return every leftover marker as (file_name, line_number, matched_text).

    Line numbers start at 1, as in an editor, so QA can print file:line.
    The number of hits is the "unresolved markers" count used for READY/DRAFT.
    """
    hits = []
    # Split on "\n" only, like grep -n. splitlines() would also break on rarer
    # characters (form feed, Unicode line separators) and shift the numbers.
    for line_number, line in enumerate(text.split("\n"), start=1):
        for match in LEFTOVER_RE.finditer(line):
            hits.append((file_name, line_number, match.group(0)))
    return hits


def expand_path(text):
    """Turn a command-line path into a Path, expanding a leading ~."""
    # The shell doesn't always expand ~ for us: a quoted value such as
    # --root "~/cptc-work" reaches Python as a literal "~", and so does a path
    # passed in by another program instead of typed at a shell.
    return Path(text).expanduser()


def parse_args(argv=None):
    """Read the command-line options. argv=None means use sys.argv."""
    parser = argparse.ArgumentParser(
        description="Assemble findings into report-ready Markdown and check them for QA problems.",
    )
    parser.add_argument(
        "--root",
        type=expand_path,
        # Default to the working copy, never the current folder: running from
        # inside the repo clone must not compile (or write build/ into) the clone.
        default=Path("~/cptc-work").expanduser(),
        help="the working copy to read from (default: ~/cptc-work)",
    )
    parser.add_argument(
        "--index",
        type=expand_path,
        default=None,
        help="the findings index CSV; a relative path is taken from the root (default: <root>/tracker/findings-index.csv)",
    )
    parser.add_argument(
        "--final",
        action="store_true",
        help="pre-submission check: QA problems become errors (a few, like older-style "
             "leftovers, stay warnings) and the exit code is 1 if there is any error",
    )
    return parser.parse_args(argv)


class RootError(Exception):
    """The --root folder can't be used. The message says why, for the user."""


def validate_root(root):
    """Return the root as a full resolved path, or raise RootError.

    Only checks; it never creates anything, so a refused root is left as found.
    """
    root = Path(root).resolve()
    if not root.exists():
        raise RootError("root folder not found: " + str(root))
    if not root.is_dir():
        raise RootError("root is not a folder: " + str(root))
    # The working copy has no .git; the repo clone does. Writing build/ or
    # reading event files inside the clone risks committing client data to
    # this public repo. exists() also catches a .git file (worktrees, submodules).
    if (root / ".git").exists():
        raise RootError(
            "this looks like the git clone (" + str(root) + " has .git); "
            "run on the working copy, e.g. ~/cptc-work"
        )
    return root


def resolve_in_root(root, path):
    """Return path as a full resolved path inside root, or raise RootError.

    A relative path is taken relative to root. Every error names the path the
    user gave; the outside-the-root error also says where it really points,
    so they can see which one is wrong.
    """
    # Check `..` as a whole path part, not as text: "a..b.md" is a fine
    # filename, but "../x" or "findings/../../x" climbs out of the folder.
    if ".." in Path(path).parts:
        raise RootError("path contains '..': " + str(path))
    root = Path(root).resolve()
    # resolve() follows symlinks, so a link is judged by where it really
    # points: a link to another place in the working copy is fine, but a link
    # (e.g. incoming/alice) to somewhere outside it is refused.
    # If path is absolute, `root / path` is just path (a pathlib rule), so an
    # absolute --index is checked by the same containment test below.
    resolved = (root / path).resolve()
    if resolved != root and root not in resolved.parents:
        raise RootError(
            "path is outside the root: " + str(path) + " -> " + str(resolved)
        )
    return resolved


def finding_folders(root):
    """Return the folders that hold findings, relative to root.

    These are findings/ and incoming/<name>/findings/ for each teammate.
    Every folder is checked with resolve_in_root() before anything inside it
    is listed, so a symlink pointing outside the root raises RootError even
    when the place it points to holds no findings.
    """
    folders = [Path("findings")]
    incoming = resolve_in_root(root, "incoming")
    if incoming.is_dir():
        for owner in incoming.iterdir():
            owner_folder = Path("incoming") / owner.name
            # Check where the entry points before asking if it is a folder:
            # is_dir() follows a symlink, so it would look outside first.
            if resolve_in_root(root, owner_folder).is_dir():
                folders.append(owner_folder / "findings")
    for folder in folders:
        resolve_in_root(root, folder)
    return folders


def discover_findings(root):
    """Return every finding file to compile, sorted by path.

    Looks in exactly two places: <root>/findings/F-*.md (your own findings)
    and <root>/incoming/*/findings/F-*.md (each teammate's mirror). Raises
    RootError if a folder or file there points outside the root.
    """
    root = Path(root).resolve()
    findings = []
    for folder in finding_folders(root):
        for path in (root / folder).glob("F-*.md"):
            # A single finding file can be a symlink too, so check it as well.
            resolve_in_root(root, folder / path.name)
            # Skip anything that isn't a plain file, e.g. a folder named F-x.md.
            if path.is_file():
                findings.append(path)
    # glob() and iterdir() return names in whatever order the disk lists
    # them. Sorting makes every run give the same order: findings/ sorts
    # before incoming/. This only lists names; incoming/ is never opened for
    # writing (R18).
    return sorted(findings)


# The finding's title line, e.g. `### F-001: Default admin password`. The ID
# is F- plus three digits, or the unfilled `[[FINDING_ID]]` marker of an early
# draft. Any number of `#` is accepted here so a wrong level can be reported
# instead of the title going missing.
HEADING_RE = re.compile(r"^(#+)[ \t]+(F-\d{3}|\[\[FINDING_ID\]\])[ \t]*:[ \t]*(.*)$")

# The ID at the start of a finding's filename, e.g. F-001 in F-001-web01.md.
# \b stops F-0012-x.md from reading as F-001.
FILENAME_ID_RE = re.compile(r"^F-\d{3}\b")


def find_title_heading(text):
    """Return (line_number, match) for the first title heading, or None."""
    # Split on "\n" only, so line numbers match grep -n (see above).
    for line_number, line in enumerate(text.split("\n"), start=1):
        # rstrip() also drops the "\r" a Windows line ending leaves behind.
        match = HEADING_RE.match(line.rstrip())
        if match:
            return line_number, match
    return None


def parse_finding_heading(file_name, text):
    """Return a finding's ID and title, read from its heading line.

    The result is a dict:
      id                the finding ID, or None if neither the heading nor
                        the filename has one
      title             the text after "ID:", as written, or None
      line              the heading's line number (from 1), or None
      diagnostics       (file_name, line_number, message) problems
    Heading problems (ID mismatch, wrong heading level, no heading, no
    title, no ID) are reported only here, so no other check repeats them.
    """
    match = FILENAME_ID_RE.match(Path(file_name).name)
    filename_id = match.group(0) if match else None
    result = {"id": filename_id, "title": None, "line": None, "diagnostics": []}
    found = find_title_heading(text)
    if found is None:
        result["diagnostics"].append(
            (file_name, 1, "no finding title heading like '### F-NNN: Title'"))
        return result

    line_number, heading = found
    hashes, heading_id, title = heading.groups()
    result["title"] = title
    result["line"] = line_number
    # Findings use ### for the title and #### for sections, so they nest
    # under the report's "## 5. Detailed Findings" without changes.
    if hashes != "###":
        result["diagnostics"].append(
            (file_name, line_number, "title is a " + hashes + " heading, not ###"))
    # A blank title has no marker, so the leftover check can't see it; this
    # warning is what reports it.
    if not title:
        result["diagnostics"].append((file_name, line_number, "heading has no title text"))
    if heading_id.startswith("F-"):
        # The heading is what goes into the report, so its ID wins; a
        # different filename ID is flagged so one of them gets fixed.
        result["id"] = heading_id
        if filename_id is not None and filename_id != heading_id:
            result["diagnostics"].append(
                (file_name, line_number,
                 "heading ID " + heading_id + " does not match filename ID " + filename_id))
    elif filename_id is None:
        # An unfilled [[FINDING_ID]] uses the filename's ID (set above); if
        # the filename has none either, report it.
        result["diagnostics"].append(
            (file_name, line_number, "no finding ID in the heading or the filename"))
    return result


# The labelled detail lines every finding must have, as in templates/finding.md.
FIELD_LABELS = ["Severity", "CVSS 3.1", "Why this severity",
                "Affected assets", "Status", "References"]

# A labelled list line, e.g. `- **Severity:** High`. Spaces around the dash,
# the label and the colon are allowed, so `-  ** Severity :**  High` still
# counts. Group 1 is the label, group 2 the rest of the line.
LABEL_LINE_RE = re.compile(r"^[ \t]*-[ \t]+\*\*[ \t]*([^*:]+?)[ \t]*:[ \t]*\*\*[ \t]*(.*?)[ \t]*$")

# On the CVSS 3.1 line, the vector is between backticks and the score is in
# parentheses: `CVSS:3.1/AV:N/...` (9.8).
CVSS_VECTOR_RE = re.compile(r"`([^`]*)`")
CVSS_SCORE_RE = re.compile(r"\(([^)]*)\)")


def parse_labelled_fields(file_name, text):
    """Return a finding's labelled details, read from its `- **Label:**` lines.

    The result is a dict:
      fields        label -> {"value": rest of the line as written, markers
                    included, "line": line number from 1}, for each label
                    in FIELD_LABELS that was found
      cvss_vector   the text between backticks on the CVSS 3.1 line, or None
      cvss_score    the text in parentheses on the CVSS 3.1 line, or None
      diagnostics   (file_name, label, message) for each missing label;
                    (file_name, line_number, message) for each duplicate
    A missing label is reported, never raised, so one bad file can't stop
    the whole compile.
    """
    fields = {}
    duplicates = []
    # Split on "\n" only, so line numbers match grep -n (see above).
    for line_number, line in enumerate(text.split("\n"), start=1):
        # rstrip() also drops the "\r" a Windows line ending leaves behind,
        # which would otherwise end up inside every value.
        match = LABEL_LINE_RE.match(line.rstrip())
        # Other labels (Likelihood, Immediate...) aren't needed by compile
        # and are ignored.
        if match and match.group(1) in FIELD_LABELS:
            label = match.group(1)
            if label not in fields:
                fields[label] = {"value": match.group(2), "line": line_number}
            else:
                # The first line wins; flag each extra one so a wrong value
                # can't slip into the report. Unlike a missing label it has a
                # real line, so it is (file_name, line_number, message).
                duplicates.append((file_name, line_number, "duplicate " + label
                                   + " line; line " + str(fields[label]["line"]) + " is used"))

    result = {"fields": fields, "cvss_vector": None, "cvss_score": None,
              "diagnostics": []}
    for label in FIELD_LABELS:
        if label not in fields:
            result["diagnostics"].append(
                (file_name, label, "missing labelled line '- **" + label + ":**'"))
    result["diagnostics"].extend(duplicates)

    if "CVSS 3.1" in fields:
        cvss = fields["CVSS 3.1"]["value"]
        vector = CVSS_VECTOR_RE.search(cvss)
        if vector:
            result["cvss_vector"] = vector.group(1)
            # Look for the score only outside the backticks, so brackets in
            # a mistyped vector can't be read as the score.
            cvss = cvss[:vector.start()] + cvss[vector.end():]
        score = CVSS_SCORE_RE.search(cvss)
        if score:
            result["cvss_score"] = score.group(1)
    return result


# Severity levels from most to least severe. The position in this list is the
# sort order; a finding with no severity sorts after all of them.
SEVERITIES = ["Critical", "High", "Medium", "Low", "Informational"]

# One level as a whole word. Case-sensitive on purpose: the template offers
# these exact words, so "high" or "HIGH" means the line wasn't filled in
# properly, and \b stops "Highest" from counting as High.
SEVERITY_RE = re.compile(r"\b(Critical|High|Medium|Low|Informational)\b")


def severity_value(file_name, fields):
    """Return (severity, diagnostics) for one finding.

    `fields` is the "fields" dict from parse_labelled_fields(). severity is
    the first level word on the Severity line, or None.
    """
    if "Severity" not in fields:
        # parse_labelled_fields() already reported the missing line, so
        # don't report the same problem twice.
        return None, []
    field = fields["Severity"]
    # Strip markers first: an unfilled [[CHOOSE: Critical / High / ...]]
    # contains every level word, and must not read as Critical.
    match = SEVERITY_RE.search(strip_markers(field["value"]))
    if match:
        return match.group(1), []
    return None, [(file_name, field["line"],
                   "no severity (Critical, High, Medium, Low or Informational); sorted last")]


def finding_sort_key(finding_id, severity):
    """Return the key that sorts findings Critical first, then by ID.

    A finding with no severity (None) sorts after Informational.
    """
    if severity in SEVERITIES:
        rank = SEVERITIES.index(severity)
    else:
        rank = len(SEVERITIES)
    # IDs are F- plus three digits, so sorting them as text sorts them by
    # number. A finding with no ID at all (None) uses "" so it still sorts.
    return (rank, finding_id or "")


# Where the findings index lives in the working copy when --index isn't given.
DEFAULT_INDEX = Path("tracker") / "findings-index.csv"


def index_location(root, index):
    """Return (path, shown) for the findings index.

    path is the full resolved path; shown is its name relative to the root,
    as every index problem names it. index None means DEFAULT_INDEX.
    Raises RootError if the index is outside the root.
    """
    if index is None:
        index = DEFAULT_INDEX
    # A relative --index is taken from the root, like every other path.
    path = resolve_in_root(root, index)
    return path, path.relative_to(Path(root).resolve()).as_posix()


def load_index_ids(root, index, final):
    """Return (ids, diagnostics) from the findings index CSV.

    ids maps each finding_id to its line in the file, or is None when the
    index can't be used, which turns off the missing/extra ID comparison.
    Each diagnostic is (level, file, line, message), level "warning" or
    "error". Line 0 means the problem is with the whole file, not one line.
    Raises RootError if the index is outside the root.
    """
    path, shown = index_location(root, index)
    if not path.exists():
        return None, [("warning", shown, 0,
                       "findings index not found; ID comparison skipped")]

    # A broken index is a QA problem, not a crash, so the other outputs are
    # still written: a warning while drafting, an error in --final.
    problem_level = "error" if final else "warning"
    try:
        # utf-8-sig drops the invisible marker spreadsheet programs put at
        # the start of a CSV, which would otherwise hide the finding_id name.
        # newline="" is what the csv module needs to read quoted line breaks.
        with path.open(encoding="utf-8-sig", newline="") as handle:
            # strict=True makes a badly quoted line an error instead of a guess.
            reader = csv.reader(handle, strict=True)
            header = next(reader, None)
            rows = [(reader.line_num, row) for row in reader]
    except (csv.Error, UnicodeDecodeError) as error:
        return None, [(problem_level, shown, 0,
                       "findings index is not a readable CSV (" + str(error) + "); ID comparison skipped")]

    if header is None:
        return None, [("warning", shown, 1,
                       "findings index is empty; ID comparison skipped")]
    # Spaces around a column name (e.g. "finding_id " typed in a
    # spreadsheet) don't hide the column.
    columns = [name.strip() for name in header]
    if "finding_id" not in columns:
        return None, [(problem_level, shown, 1,
                       "findings index has no finding_id column; ID comparison skipped")]
    column = columns.index("finding_id")
    ids = {}
    for line_number, row in rows:
        # A short row or a blank ID cell is skipped. An ID listed twice
        # keeps its first line; the repeat is not reported.
        if len(row) > column and row[column].strip():
            ids.setdefault(row[column].strip(), line_number)
    if not ids:
        # An empty index would flag every finding as "extra", so treat a
        # file with only the header row as absent.
        return None, [("warning", shown, 1,
                       "findings index has no rows; ID comparison skipped")]
    return ids, []


# Older-style placeholders from before the [[...]] markers, one regex each.
# They can appear legitimately (e.g. "TODO" in quoted output), so they are
# always warnings, even in --final.
OLDER_LEFTOVER_PATTERNS = [
    re.compile(r"<<"),
    re.compile(r"TODO"),
    re.compile(r"F-XXX"),
    re.compile(r"IR-XXX"),
    # \b on both sides: only a bare XX, not the XX in XXE or F-XXX.
    re.compile(r"\bXX\b"),
    re.compile(r"YYYY"),
    re.compile(r"HH:MM"),
]

# An inline code span, e.g. `cat << EOF` or ``a ` inside``. Read it as: a run
# of backticks (group 1), then as little text as possible, then the same run
# again. Code is copied output, not prose, so it isn't checked.
CODE_SPAN_RE = re.compile(r"(`+).*?\1")


def hide_todo_marker_words(text):
    """Return text with the word TODO blanked inside every [[TODO: ...]] marker."""
    # The leftover-marker check already reports these markers, so their TODO
    # isn't reported twice (OQ-02). Other words inside them still count.
    for marker in MARKER_RE.findall(text):
        if marker.startswith("[[TODO:"):
            # Spaces, not "", so nothing else on the line moves or joins.
            text = text.replace(marker, marker.replace("TODO", "    "))
    return text


def scan_older_leftovers(file_name, text):
    """Return every older-style leftover as (file_name, line_number, matched_text).

    Skips fenced code blocks and `code spans`. Inside markers, only the TODO
    of a [[TODO: ...]] marker is skipped; e.g. F-XXX inside a NOTE still counts.
    """
    # Done on the whole text, so a marker spanning lines is handled. Only the
    # letters TODO change, never line breaks, so line numbers stay the same.
    text = hide_todo_marker_words(text)
    hits = []
    fence = None  # the ``` or ~~~ that opened the code block we are in
    # Split on "\n" only, so line numbers match grep -n (see above).
    for line_number, line in enumerate(text.split("\n"), start=1):
        stripped = line.lstrip()
        if fence is None and (stripped.startswith("```") or stripped.startswith("~~~")):
            fence = stripped[:3]
            continue
        if fence is not None:
            # Only the same kind of fence closes the block.
            if stripped.startswith(fence):
                fence = None
            continue
        # A space, not "", so X`code`X can't become a bare XX.
        line = CODE_SPAN_RE.sub(" ", line)
        for pattern in OLDER_LEFTOVER_PATTERNS:
            for match in pattern.finditer(line):
                hits.append((file_name, line_number, match.group(0)))
    return hits


# The heading that starts a finding's reproduction steps, as in the template.
REPRODUCTION_HEADING_RE = re.compile(r"^####[ \t]+Reproduction steps[ \t]*$")

# A ### or #### heading, which ends the reproduction section. ##### and
# deeper don't match: after three or four #, a space or tab must follow.
SECTION_END_RE = re.compile(r"^#{3,4}[ \t]")

# A numbered step: optional indent, digits, a dot, then a space or tab, e.g.
# "1. " or "  12.\t". The space after the dot matters: pasted output often
# starts with an IP address (10.0.0.5 dc01), which must not count as a step.
STEP_RE = re.compile(r"^[ \t]*\d+\.[ \t]")


def reproduction_section(text):
    """Return (heading_line_number, section_text), or None if there is no section.

    The section is every line after `#### Reproduction steps` up to the next
    ### or #### heading (or the end of the file).
    """
    lines = text.split("\n")
    for index, line in enumerate(lines):
        # rstrip() also drops the "\r" a Windows line ending leaves behind.
        if REPRODUCTION_HEADING_RE.match(line.rstrip()):
            section = []
            for section_line in lines[index + 1:]:
                if SECTION_END_RE.match(section_line):
                    break
                section.append(section_line)
            return index + 1, "\n".join(section)
    return None


def remove_note_markers(text):
    """Return text with every complete [[NOTE: ...]] marker removed."""
    for marker in MARKER_RE.findall(text):
        if marker.startswith("[[NOTE:"):
            text = text.replace(marker, "")
    return text


def check_reproduction(file_name, text):
    """Return a list of reproduction-step problems; an empty list means it passes.

    Passes when the section has at least one numbered step and at least as
    many `Expected:` lines as steps. Each problem is (file_name, line_number,
    message), or (file_name, "Reproduction steps", message) if the section is
    missing, like a missing labelled line.
    """
    found = reproduction_section(text)
    if found is None:
        return [(file_name, "Reproduction steps",
                 "missing '#### Reproduction steps' section")]
    line_number, section = found
    # The template's NOTE holds an example step and an Expected: line. Remove
    # NOTEs first so an untouched template can't pass off that example.
    section = remove_note_markers(section)
    steps = 0
    expected = 0
    for line in section.split("\n"):
        if STEP_RE.match(line):
            steps += 1
        # lstrip(): the template indents Expected: under its step.
        if line.lstrip().startswith("Expected:"):
            expected += 1
    if steps >= 1 and expected >= steps:
        return []
    return [(file_name, line_number,
             "reproduction steps: " + str(steps) + " numbered steps, "
             + str(expected) + " Expected: lines; need at least 1 step and an Expected: line for each")]


def has_text(value):
    """Return True if value, with markers removed, has a letter or digit.

    Punctuation left over from the template, like the "()" of an unfilled
    `[[CVSS_VECTOR]]` ([[CVSS_SCORE]]), doesn't count as a value.
    """
    # isalnum() is True for any Unicode letter or digit, so a value written
    # in another alphabet (e.g. an accented name) still counts.
    for character in strip_markers(value):
        if character.isalnum():
            return True
    return False


def missing_required_fields(fields):
    """Return the labels a finding needs for READY but has no value for.

    `fields` is the "fields" dict from parse_labelled_fields(). The required
    labels are FIELD_LABELS, the same six it reads (OQ-14). Reproduction
    steps are not one of them; check_reproduction() checks those separately.
    """
    missing = []
    for label in FIELD_LABELS:
        if label not in fields or not has_text(fields[label]["value"]):
            missing.append(label)
    return missing


def check_references(file_name, fields):
    """Return a list of reference problems; an empty list means it passes.

    Passes when the References line has "http" in it. Only that labelled line
    is checked: a link elsewhere in the finding doesn't count. Each problem
    is (file_name, line_number, message).
    """
    if "References" not in fields:
        # parse_labelled_fields() already reported the missing line, so
        # don't report the same problem twice.
        return []
    field = fields["References"]
    # Strip markers first, so a link inside a NOTE's example isn't taken as
    # a real reference.
    if "http" in strip_markers(field["value"]):
        return []
    return [(file_name, field["line"], "References line has no http link")]


# A full CVSS 3.1 base vector (OQ-09): all eight metrics in the standard
# order, each with one of its allowed letters, and nothing extra. One shared
# constant, so the notebook's CVSS_VECTOR warning can use the same rule (N4-03).
FULL_CVSS31_VECTOR_RE = re.compile(
    r"^CVSS:3\.1/AV:[NALP]/AC:[LH]/PR:[NHL]/UI:[NR]/S:[UC]/C:[NLH]/I:[NLH]/A:[NLH]$")


def check_cvss_version(file_name, fields, cvss_vector):
    """Return a list of CVSS-vector problems; an empty list means it passes.

    `fields` and `cvss_vector` come from parse_labelled_fields(). The vector
    must be a full CVSS 3.1 vector unless it is still the [[CVSS_VECTOR]]
    placeholder. Each problem is (file_name, line_number, message).
    """
    if "CVSS 3.1" not in fields:
        # parse_labelled_fields() already reported the missing line.
        return []
    field = fields["CVSS 3.1"]
    vector = cvss_vector
    if vector is None:
        # No backticks on the line (e.g. just "9.8"): check the whole value,
        # so a score typed in place of the vector is still reported.
        vector = field["value"]
    # Only an unfilled [[CVSS_VECTOR]] placeholder is skipped (closed or not):
    # the leftover-marker check already reports it (OQ-05). Any other marker
    # doesn't hide a bad vector, and an empty vector is reported too.
    if "[[CVSS_VECTOR" in vector:
        return []
    if FULL_CVSS31_VECTOR_RE.match(vector):
        return []
    return [(file_name, field["line"],
             "CVSS vector is not a full CVSS 3.1 vector: " + vector)]


def finding_id_locations(headings):
    """Return (file_name, line_number, finding_id) for each finding with an ID.

    `headings` is a list of (file_name, heading) pairs, where heading is the
    dict from parse_finding_heading(), so the ID is the one the heading
    parser chose. A finding with no ID is left out: parse_finding_heading()
    already reports it.
    """
    locations = []
    for file_name, heading in headings:
        if heading["id"] is None:
            continue
        line_number = heading["line"]
        if line_number is None:
            # No title heading: parse_finding_heading() reports that at
            # line 1, so point there too.
            line_number = 1
        locations.append((file_name, line_number, heading["id"]))
    return locations


def check_duplicate_ids(locations):
    """Return one problem per finding ID used by more than one file.

    `locations` comes from finding_id_locations(). The problem is placed at
    the first file and its message names every file with that ID, so each
    copy can be found. Each problem is (file_name, line_number, message).
    """
    files_by_id = {}
    for file_name, line_number, finding_id in locations:
        files_by_id.setdefault(finding_id, []).append((file_name, line_number))
    problems = []
    for finding_id in sorted(files_by_id):
        places = files_by_id[finding_id]
        if len(places) > 1:
            names = [file_name for file_name, line_number in places]
            first_file, first_line = places[0]
            problems.append((first_file, first_line,
                             "duplicate finding ID " + finding_id + " in: " + ", ".join(names)))
    return problems


def check_index_membership(locations, index_ids, index_file):
    """Return problems for finding IDs missing from, or extra to, the index.

    `locations` comes from finding_id_locations(); `index_ids` comes from
    load_index_ids(), and `index_file` is the index's name to show. An ID in
    a finding file but not in the index is reported at the finding; an ID in
    the index but in no finding file is reported at its index line. Each
    problem is (file_name, line_number, message).
    """
    if index_ids is None:
        # The index is absent or unusable: load_index_ids() already warned,
        # and comparing against nothing would flag every finding as extra.
        return []
    problems = []
    file_ids = set()
    for file_name, line_number, finding_id in locations:
        file_ids.add(finding_id)
        if finding_id not in index_ids:
            problems.append((file_name, line_number,
                             finding_id + " is not in the findings index " + index_file))
    # index_ids keeps the file's row order, so these follow the index lines.
    for finding_id, line_number in index_ids.items():
        if finding_id not in file_ids:
            problems.append((index_file, line_number,
                             finding_id + " is in the findings index but no finding file has it"))
    return problems


def finding_readiness(leftover_hits, missing_fields, severity, title):
    """Return (status, summary) for one finding: READY or DRAFT.

    leftover_hits comes from scan_leftover_markers() on the whole file,
    missing_fields from missing_required_fields(), severity from
    severity_value() and title from parse_finding_heading(). READY needs no
    leftover markers, no missing required fields, a severity word and a
    title (DECISIONS 2026-10-20 C-15). summary is "READY", or "DRAFT: "
    with both counts plus any other reason, for the QA report.
    """
    # The heading's own markers are among the whole-file hits, so they
    # aren't counted separately.
    # A misspelled severity (e.g. "high") would leave a blank Severity cell
    # in the summary table (C-15 Q2). A blank title has no marker for the
    # leftover check to count (C-15 Q3); title is None when there is no
    # heading at all.
    if not leftover_hits and not missing_fields and severity is not None and title:
        return "READY", "READY"
    reasons = [str(len(leftover_hits)) + " unresolved markers",
               str(len(missing_fields)) + " missing fields"]
    if severity is None:
        reasons.append("no severity word")
    if not title:
        reasons.append("no title")
    return "DRAFT", "DRAFT: " + ", ".join(reasons)


def draft_banner(summary):
    """Return the line put before a draft in findings-combined.md.

    `summary` is the readiness line from finding_readiness(), shown as it
    is, so the banner says every reason the finding is a draft (DECISIONS
    2026-10-20 Chunk 4 CR-3), e.g.
    [[NOTE: DRAFT: 0 unresolved markers, 0 missing fields, no severity word]].
    It is itself a marker, so if a draft is pasted into report.md with its
    banner, the --final leftover check of report.md reports it.
    """
    return "[[NOTE: " + summary + "]]"


# The labelled fields that go into the summary table as written, so a "|"
# in them is checked (DECISIONS 2026-10-20 C-16). The title is checked
# separately; the ID is always F-NNN and Severity is a fixed word, so
# neither can hold a "|".
TABLE_TEXT_LABELS = ["Affected assets", "Status"]


def field_value(fields, label):
    """Return a labelled field's value as written, or "" if it is missing."""
    if label in fields:
        return fields[label]["value"]
    return ""


def summary_row(heading, fields, severity):
    """Return one finding's summary-table cells as a dict.

    `heading` comes from parse_finding_heading(), `fields` from
    parse_labelled_fields() and `severity` from severity_value(). Values are
    kept exactly as written; anything missing becomes a blank cell.
    """
    return {
        "id": heading["id"] or "",
        "title": heading["title"] or "",
        "severity": severity or "",
        "assets": field_value(fields, "Affected assets"),
        "status": field_value(fields, "Status"),
    }


def has_unescaped_pipe(text):
    """Return True if text holds a "|" that isn't written as "\\|"."""
    # "\|" is how Markdown writes a "|" inside a table cell, and it doesn't
    # break the table, so it is removed before looking (DECISIONS 2026-10-20
    # Chunk 4 CR-4). The text itself is never changed.
    return "|" in text.replace("\\|", "")


def check_table_pipes(file_name, heading, fields):
    """Return a warning for each summary cell whose text holds a "|".

    A "|" would split the cell and break the Markdown table, so it is
    reported, but the text is left as written. An escaped "\\|" is fine.
    Each problem is (file_name, line_number, message).
    """
    # Name the finding by ID when it has one, so a teammate's finding is
    # easy to find in the table.
    name = heading["id"] or file_name
    problems = []
    if heading["title"] and has_unescaped_pipe(heading["title"]):
        problems.append((file_name, heading["line"],
                         name + ": '|' in Title breaks the summary table"))
    for label in TABLE_TEXT_LABELS:
        if label in fields and has_unescaped_pipe(fields[label]["value"]):
            problems.append((file_name, fields[label]["line"],
                             name + ": '|' in " + label + " breaks the summary table"))
    return problems


def table_line(cells):
    """Return one Markdown table line from a list of cell texts."""
    return "| " + " | ".join(cells) + " |"


def summary_sort_key(row):
    """Return the sort key for one summary_row(): Critical first, then by ID."""
    # A blank Severity cell isn't a level, so it sorts last, like None.
    return finding_sort_key(row["id"], row["severity"])


def render_findings_summary(rows):
    """Return the text of build/findings-summary.md.

    `rows` is a list of summary_row() dicts. The findings table is sorted
    Critical first, then by ID, with no-severity findings last. The count
    table shows every level, zeros included, and Total counts every row.
    """
    rows = sorted(rows, key=summary_sort_key)
    lines = ["## Findings", "",
             table_line(["ID", "Title", "Severity", "Affected assets", "Status"]),
             table_line(["---"] * 5)]
    for row in rows:
        lines.append(table_line([row["id"], row["title"], row["severity"],
                                 row["assets"], row["status"]]))

    counts = []
    for level in SEVERITIES:
        level_rows = [row for row in rows if row["severity"] == level]
        counts.append(str(len(level_rows)))
    # Total is every row, so a finding with no severity is still counted.
    counts.append(str(len(rows)))
    lines += ["", "## Severity counts", "",
              table_line(SEVERITIES + ["Total"]),
              table_line(["---"] * 6),
              table_line(counts)]
    return "\n".join(lines) + "\n"


# The three timeline file types (OQ-11: no other type), by filename prefix:
# the Type column text, and the labelled line that holds the file's time.
TIMELINE_TYPES = {
    "IR": ("Incident", "Time reported"),
    "SU": ("Status update", "Time"),
    "INJ": ("Inject", "Sent"),
}

# A timeline time: a date and a time (OQ-01). Written this way, sorting the
# text also sorts by time.
TIMELINE_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")

# The file's top heading, e.g. `# Incident Report IR-001`: exactly one "#".
TOP_HEADING_RE = re.compile(r"^#[ \t]+(.*)$")


def child_folders(root, folder):
    """Return folder/<name> for each folder inside root/folder.

    Returns [] if root/folder doesn't exist, since a working copy may not
    have field-notes/ yet. Each entry is checked with resolve_in_root()
    before it is used, so a symlink pointing outside the root raises
    RootError instead of being followed.
    """
    path = resolve_in_root(root, folder)
    children = []
    if path.is_dir():
        for entry in path.iterdir():
            child = Path(folder) / entry.name
            # Check where the entry points before asking if it is a folder:
            # is_dir() follows a symlink, so it would look outside first.
            if resolve_in_root(root, child).is_dir():
                children.append(child)
    return children


def timeline_folders(root):
    """Return the folders that hold timeline files, relative to root.

    These are field-notes/<name>/ and incoming/<owner>/field-notes/<name>/.
    """
    folders = child_folders(root, "field-notes")
    for owner in child_folders(root, "incoming"):
        folders += child_folders(root, owner / "field-notes")
    return folders


def discover_timeline_files(root):
    """Return every IR-, SU- and INJ- file for the timeline, sorted by path.

    Raises RootError if a folder or file there points outside the root.
    NOTE- files aren't interactions, so they are never listed (OQ-11).
    """
    root = Path(root).resolve()
    files = []
    for folder in timeline_folders(root):
        for prefix in TIMELINE_TYPES:
            for path in (root / folder).glob(prefix + "-*.md"):
                # A single file can be a symlink too, so check it as well.
                resolve_in_root(root, folder / path.name)
                if path.is_file():
                    files.append(path)
    # Sorted so every run gives the same order, like discover_findings().
    return sorted(files)


def misplaced_timeline_files(root):
    """Return a problem for each IR-, SU- or INJ- file in a likely wrong spot.

    The spots are the root's top level and the top of field-notes/, and the
    same two inside each incoming/<owner>/. A file saved there by hand is
    left out of the timeline, and without this check nothing would say so
    (DECISIONS 2026-10-22 Chunk 7 CR-3). No other folder is searched. Each
    problem is (file_name, 0, message): line 0 means the whole file.
    """
    root = Path(root).resolve()
    spots = [Path("."), Path("field-notes")]
    for owner in child_folders(root, "incoming"):
        spots += [owner, owner / "field-notes"]
    names = []
    for spot in spots:
        if resolve_in_root(root, spot).is_dir():
            for prefix in TIMELINE_TYPES:
                for path in (root / spot).glob(prefix + "-*.md"):
                    # Check where a file points before asking if it is a file,
                    # as child_folders() does for folders.
                    if resolve_in_root(root, spot / path.name).is_file():
                        names.append((spot / path.name).as_posix())
    problems = []
    for name in sorted(names):
        problems.append((name, 0, "not in field-notes/<name>/, so it is not in the timeline"))
    return problems


def parse_timeline_entry(file_name, text):
    """Return one timeline file's row data and its problems.

    `file_name` must start with IR-, SU- or INJ-, as every file from
    discover_timeline_files() does. The result is a dict:
      type          Incident, Status update or Inject, from the prefix
      time          the labelled time as written, or "" if the line is missing
      time_ok       True only if time is YYYY-MM-DD HH:MM
      summary       the "# " heading's text as written, or ""
      reference     the filename without .md
      diagnostics   (file_name, line_number, message) problems, or
                    (file_name, label, message) for a missing time line
    A file whose time isn't valid is sorted last by the timeline.
    """
    name = Path(file_name).name
    entry_type, time_label = TIMELINE_TYPES[name.split("-", 1)[0]]
    result = {"type": entry_type, "time": "", "time_ok": False, "summary": "",
              "reference": Path(file_name).stem, "diagnostics": []}
    time_line = None
    heading_found = False
    # Split on "\n" only, so line numbers match grep -n (see above).
    for line_number, line in enumerate(text.split("\n"), start=1):
        # rstrip() also drops the "\r" a Windows line ending leaves behind.
        line = line.rstrip()
        heading = TOP_HEADING_RE.match(line)
        if heading and not heading_found:
            result["summary"] = heading.group(1)
            heading_found = True
            # A "|" would break the timeline table, like the summary table
            # (DECISIONS 2026-10-20 C-17B): warn, but keep the text as written.
            if has_unescaped_pipe(result["summary"]):
                result["diagnostics"].append(
                    (file_name, line_number,
                     result["reference"] + ": '|' in Summary breaks the timeline table"))
        label = LABEL_LINE_RE.match(line)
        if label and label.group(1) == time_label and time_line is None:
            result["time"] = label.group(2)
            time_line = line_number

    if not heading_found:
        result["diagnostics"].append((file_name, 1, "no '# ' heading; Summary left blank"))
    if time_line is None:
        result["diagnostics"].append(
            (file_name, time_label, "missing labelled line '- **" + time_label + ":**'; sorted last"))
    elif TIMELINE_TIME_RE.match(result["time"]):
        result["time_ok"] = True
    else:
        # This also catches an unfilled [[DATE]] [[TIME]] marker.
        result["diagnostics"].append(
            (file_name, time_line,
             time_label + " is not YYYY-MM-DD HH:MM: " + result["time"] + "; sorted last"))
    return result


def timeline_sort_key(entry):
    """Return the sort key for one parse_timeline_entry() result.

    Valid times sort first, as text (YYYY-MM-DD HH:MM text sorts by time).
    Invalid times sort after all of them. Ties go by reference, so every
    run gives the same order.
    """
    if entry["time_ok"]:
        return (0, entry["time"], entry["reference"])
    return (1, "", entry["reference"])


def render_timeline(entries):
    """Return the text of build/interactions-timeline.md.

    `entries` is a list of parse_timeline_entry() results; each one becomes
    one row, with its values as written.
    """
    lines = [table_line(["Time", "Type", "Summary", "Reference"]),
             table_line(["---"] * 4)]
    for entry in sorted(entries, key=timeline_sort_key):
        lines.append(table_line([entry["time"], entry["type"], entry["summary"],
                                 entry["reference"]]))
    return "\n".join(lines) + "\n"


def combined_sort_key(finding):
    """Return the sort key for one render_combined_findings() entry."""
    return finding_sort_key(finding["id"], finding["severity"])


def render_combined_findings(findings):
    """Return the text of build/findings-combined.md.

    `findings` is a list of dicts, one per finding file:
      id, severity    from parse_finding_heading() and severity_value()
      status          "READY" or "DRAFT", from finding_readiness()
      summary         the readiness line, also from finding_readiness()
      text            the file's full text
    Findings come in finding_sort_key() order, each one's text unchanged
    except that a missing final line break is added, so its ### and ####
    headings nest under the report's Section 5. A draft gets the
    draft_banner() line immediately before it.
    """
    parts = []
    # sorted() keeps the given order for equal keys, so two files with the
    # same ID stay in path order.
    for finding in sorted(findings, key=combined_sort_key):
        text = finding["text"]
        # Without a final line break, the next finding's heading would be
        # glued onto this finding's last line.
        if not text.endswith("\n"):
            text += "\n"
        if finding["status"] == "DRAFT":
            text = draft_banner(finding["summary"]) + "\n" + text
        parts.append(text)
    # A blank line between findings keeps each one a separate block.
    return "\n".join(parts)


# The QA checks, in the order qa-report.txt lists them. Each one shows PASS
# when it found no problems, otherwise FAIL.
QA_CHECKS = [
    "finding headings",
    "labelled lines",
    "severity",
    "required fields",
    "leftover markers",
    "older-style leftovers",
    "reproduction steps",
    "references",
    "CVSS version",
    "duplicate finding IDs",
    "findings index",
    "summary table",
    "interactions timeline",
]

# Older-style leftovers can appear legitimately (e.g. "TODO" in quoted
# output), so their problems stay warnings even in --final.
ALWAYS_WARNING_CHECKS = ["older-style leftovers"]


def check_required_fields(file_name, fields):
    """Return a problem for each required field whose line has no value.

    `fields` is the "fields" dict from parse_labelled_fields(). Uses the same
    rule as READY (missing_required_fields()), so every finding that is DRAFT
    for an empty field also has a QA problem, and --final can't pass it
    (DECISIONS 2026-10-21 C-19 Q2). Each problem is (file_name,
    line_number, message).
    """
    problems = []
    for label in missing_required_fields(fields):
        # A missing line has no value either, but parse_labelled_fields()
        # already reports it, so it isn't reported twice.
        if label in fields:
            problems.append((file_name, fields[label]["line"], label + " has no value"))
    return problems


def qa_level(check_name, final):
    """Return "warning" or "error" for a problem found by one check.

    Drafts are normal during the event, so in draft mode every problem is a
    warning. In --final every problem is an error, except for the checks in
    ALWAYS_WARNING_CHECKS.
    """
    if final and check_name not in ALWAYS_WARNING_CHECKS:
        return "error"
    return "warning"


def hit_diagnostics(hits, what):
    """Turn scanner hits into (file_name, line_number, message) diagnostics.

    `hits` come from scan_leftover_markers() or scan_older_leftovers(), as
    (file_name, line_number, matched_text). `what` names the kind of hit,
    e.g. "leftover marker", so the message reads "leftover marker [[HOST".
    """
    diagnostics = []
    for file_name, line_number, matched_text in hits:
        diagnostics.append((file_name, line_number, what + " " + matched_text))
    return diagnostics


def check_problems(check_name, diagnostics, final):
    """Return one check's diagnostics as (level, file_name, line_number, message).

    Each diagnostic is (file_name, line_number, message), or (file_name,
    label, message) when there is no line to point at (a missing labelled
    line or section); those get line_number None. The level comes from
    qa_level(). The findings index loader already gives its own levels, so
    its problems are added as they are, without this function.
    """
    level = qa_level(check_name, final)
    problems = []
    for file_name, place, message in diagnostics:
        # A label (text) isn't a line number, so that problem has no line.
        line_number = place if isinstance(place, int) else None
        problems.append((level, file_name, line_number, message))
    return problems


def problem_location(file_name, line_number):
    """Return "file:line", or just "file" for a problem with no line."""
    # None means there is no line to point at; the findings index loader
    # uses line 0 for a problem with the whole file.
    if line_number:
        return file_name + ":" + str(line_number)
    return file_name


def problem_line(problem):
    """Return one problem as "WARNING: file:line: message" (or "ERROR: ...")."""
    level, file_name, line_number, message = problem
    return level.upper() + ": " + problem_location(file_name, line_number) + ": " + message


def count_levels(problems):
    """Return (warnings, errors): how many problems have each level."""
    warnings = 0
    errors = 0
    for problem in problems:
        if problem[0] == "error":
            errors += 1
        else:
            warnings += 1
    return warnings, errors


def check_status(problems):
    """Return a check's result: "PASS", or "FAIL" with its problem counts."""
    if not problems:
        return "PASS"
    warnings, errors = count_levels(problems)
    return "FAIL (" + str(errors) + " errors, " + str(warnings) + " warnings)"


class InputError(Exception):
    """An input file can't be read as text. The message names the file."""


def read_markdown(path):
    """Return a Markdown file's text as it is on disk, minus a leading BOM.

    Raises InputError if the file isn't UTF-8 text.
    """
    try:
        # utf-8-sig drops the invisible BOM some Windows editors put first,
        # which would hide a "# " heading on line 1. newline="" keeps "\r\n"
        # line endings, so findings-combined.md copies the text unchanged.
        with Path(path).open(encoding="utf-8-sig", newline="") as handle:
            return handle.read()
    except UnicodeDecodeError as error:
        # Python's own message doesn't say which file, so add it.
        raise InputError(str(path) + " is not UTF-8 text (" + str(error) + ")")


# The hand-assembled report in the root. --final checks it; nothing ever
# writes it.
REPORT_FILE = "report.md"


def check_report(root, final):
    """Return the report.md result for the QA report, or None in draft mode.

    In --final the result is a dict:
      status    "report.md NOT FOUND: report not checked", or
                "report.md checked: N problems"
      checks    "leftover markers" and "older-style leftovers" mapped to
                their problems in report.md, as (level, file_name,
                line_number, message); empty when report.md is absent
    report.md is only read, for these two checks; it is never parsed or
    changed. Raises RootError if report.md points outside the root.
    """
    # Drafts are normal during the event and the report is assembled at the
    # midpoint, so draft mode doesn't even open report.md.
    if not final:
        return None
    path = resolve_in_root(root, REPORT_FILE)
    if not path.exists():
        # Not an error: the report may be finished in another tool. The
        # loud status line makes sure nobody thinks it was checked.
        return {"status": REPORT_FILE + " NOT FOUND: report not checked", "checks": {}}
    text = read_markdown(path)
    markers = hit_diagnostics(scan_leftover_markers(REPORT_FILE, text), "leftover marker")
    older = hit_diagnostics(scan_older_leftovers(REPORT_FILE, text), "older-style leftover")
    # check_problems() gives the levels: a leftover marker blocks --final,
    # an older-style leftover is only a warning.
    checks = {
        "leftover markers": check_problems("leftover markers", markers, final),
        "older-style leftovers": check_problems("older-style leftovers", older, final),
    }
    count = len(checks["leftover markers"]) + len(checks["older-style leftovers"])
    return {"status": REPORT_FILE + " checked: " + str(count) + " problems", "checks": checks}


def render_qa_report(final, readiness, checks, report):
    """Return the text of build/qa-report.txt.

    `readiness` is a list of (file_name, summary) pairs, one per finding,
    where summary is the readiness line from finding_readiness(), printed as
    it is. `checks` maps every name in QA_CHECKS to that check's problems, as
    (level, file_name, line_number, message); an empty list means the check
    ran and found nothing. Every check gets a PASS or FAIL line, then its
    problems. `report` is the check_report() result: None in draft mode, and
    in --final its own "report.md:" section. Raises ValueError if a check is
    missing or unknown, or if --final has no report.md result.
    """
    # Every check must be given, even with no problems, so a missing one
    # gets a readable error instead of a bare KeyError below. An unknown
    # (e.g. misspelt) name is refused: its problems would otherwise be left
    # out of the report and of the exit code, since both read only
    # QA_CHECKS names. An empty list is taken as "ran and found nothing";
    # this can't tell whether the check really ran.
    for name in QA_CHECKS:
        if name not in checks:
            raise ValueError("QA check not run: " + name)
    for name in checks:
        if name not in QA_CHECKS:
            raise ValueError("unknown QA check: " + name)
    # In --final, report.md must have been checked (or found absent), so a
    # forgotten check can't look like a clean report.
    if final and report is None:
        raise ValueError("--final QA report needs the report.md result")
    if final:
        lines = ["QA report (--final): any ERROR below fails the run"]
    else:
        lines = ["QA report (draft mode): problems are warnings"]

    lines += ["", "Findings:"]
    if not readiness:
        lines.append("  no finding files found")
    for file_name, summary in readiness:
        lines.append("  " + file_name + ": " + summary)

    lines += ["", "Checks:"]
    for name in QA_CHECKS:
        problems = checks[name]
        lines.append(check_status(problems) + " " + name)
        for problem in problems:
            lines.append("  " + problem_line(problem))

    # report.md gets its own section, apart from the findings' checks.
    if report is not None:
        lines += ["", REPORT_FILE + ":", report["status"]]
        for name, problems in report["checks"].items():
            lines.append(check_status(problems) + " " + name)
            for problem in problems:
                lines.append("  " + problem_line(problem))
    return "\n".join(lines) + "\n"


def check_finding(file_name, text, final):
    """Run every check that looks at one finding file on its own.

    Returns a dict:
      name, heading     the file name, and the parse_finding_heading() result
      status, summary   READY or DRAFT, and the readiness line
      row               its summary_row() for findings-summary.md
      combined          its render_combined_findings() entry
      checks            check name -> problems, as (level, file_name,
                        line_number, message), for the per-finding checks
    The checks across files (duplicate IDs, index, timeline) are run by
    collect_qa().
    """
    heading = parse_finding_heading(file_name, text)
    parsed = parse_labelled_fields(file_name, text)
    fields = parsed["fields"]
    severity, severity_diagnostics = severity_value(file_name, fields)
    hits = scan_leftover_markers(file_name, text)
    status, summary = finding_readiness(
        hits, missing_required_fields(fields), severity, heading["title"])
    older = scan_older_leftovers(file_name, text)
    diagnostics = {
        "finding headings": heading["diagnostics"],
        "labelled lines": parsed["diagnostics"],
        "severity": severity_diagnostics,
        "required fields": check_required_fields(file_name, fields),
        "leftover markers": hit_diagnostics(hits, "leftover marker"),
        "older-style leftovers": hit_diagnostics(older, "older-style leftover"),
        "reproduction steps": check_reproduction(file_name, text),
        "references": check_references(file_name, fields),
        "CVSS version": check_cvss_version(file_name, fields, parsed["cvss_vector"]),
        "summary table": check_table_pipes(file_name, heading, fields),
    }
    checks = {}
    for check_name, found in diagnostics.items():
        checks[check_name] = check_problems(check_name, found, final)
    return {
        "name": file_name,
        "heading": heading,
        "status": status,
        "summary": summary,
        "row": summary_row(heading, fields, severity),
        "combined": {"id": heading["id"], "severity": severity, "status": status,
                     "summary": summary, "text": text},
        "checks": checks,
    }


def collect_qa(root, index, final):
    """Read every input in the working copy and run every QA check.

    Returns a dict:
      findings    one check_finding() result per finding file, in path order
      timeline    one parse_timeline_entry() result per timeline file
      checks      every name in QA_CHECKS -> its problems
      report      the check_report() result (None in draft mode)
    File names are shown relative to the root, e.g. findings/F-001-x.md.
    Raises RootError if a path points outside the root.
    """
    root = Path(root).resolve()
    # Every check starts with no problems, so a check that finds nothing
    # (e.g. no timeline files) still shows PASS in the QA report.
    checks = {}
    for name in QA_CHECKS:
        checks[name] = []

    findings = []
    for path in discover_findings(root):
        finding = check_finding(path.relative_to(root).as_posix(), read_markdown(path), final)
        findings.append(finding)
        for check_name, problems in finding["checks"].items():
            checks[check_name] += problems

    headings = [(finding["name"], finding["heading"]) for finding in findings]
    locations = finding_id_locations(headings)
    checks["duplicate finding IDs"] = check_problems(
        "duplicate finding IDs", check_duplicate_ids(locations), final)
    # The loader gives its own levels, so its problems are added as they are.
    index_ids, index_problems = load_index_ids(root, index, final)
    # The same shown name as the loader's problems, so both name one file.
    shown_index = index_location(root, index)[1]
    membership = check_index_membership(locations, index_ids, shown_index)
    checks["findings index"] = index_problems + check_problems(
        "findings index", membership, final)

    timeline = []
    for path in discover_timeline_files(root):
        entry = parse_timeline_entry(path.relative_to(root).as_posix(), read_markdown(path))
        timeline.append(entry)
        checks["interactions timeline"] += check_problems(
            "interactions timeline", entry["diagnostics"], final)
    checks["interactions timeline"] += check_problems(
        "interactions timeline", misplaced_timeline_files(root), final)

    return {"findings": findings, "timeline": timeline, "checks": checks,
            "report": check_report(root, final)}


def all_problems(collected):
    """Return every QA problem in a collect_qa() result, report.md's included."""
    problems = []
    for name in QA_CHECKS:
        problems += collected["checks"][name]
    if collected["report"] is not None:
        for report_problems in collected["report"]["checks"].values():
            problems += report_problems
    return problems


def qa_summary_line(collected):
    """Return "QA: N findings; R READY; D DRAFT; W warnings; E errors"."""
    findings = collected["findings"]
    ready = len([finding for finding in findings if finding["status"] == "READY"])
    warnings, errors = count_levels(all_problems(collected))
    return ("QA: " + str(len(findings)) + " findings; " + str(ready) + " READY; "
            + str(len(findings) - ready) + " DRAFT; " + str(warnings) + " warnings; "
            + str(errors) + " errors")


# The four files every run writes, in build/ (in this order on screen).
BUILD_FOLDER = "build"
OUTPUT_FILES = ["findings-summary.md", "interactions-timeline.md",
                "findings-combined.md", "qa-report.txt"]


def build_path(root, relative_path):
    """Return root/relative_path for writing, or raise RootError.

    Writing follows links, so a link at build/ or at an output file could
    make the tool overwrite report.md or write into incoming/. Both kinds
    are refused: a symlink, and an existing file with another hard link.
    This is stricter than resolve_in_root(), which allows a symlink that
    stays inside the root (DECISIONS 2026-10-21 C-21 build/ links).
    """
    root = Path(root).resolve()
    path = resolve_in_root(root, relative_path)
    # A symlink resolves somewhere else, so the path must resolve to exactly
    # where it says.
    if path != root / relative_path:
        raise RootError("build output is a link; remove it: " + str(relative_path))
    # A hard link is the same file under two names (e.g. report.md), so
    # writing one would change the other. st_nlink counts the names; only
    # files are checked, since a folder always has more than one.
    if path.is_file() and path.stat().st_nlink > 1:
        raise RootError("build output has another hard link; remove it: " + str(relative_path))
    return path


def readiness_lines(collected):
    """Return (file_name, readiness summary) for each finding, for the QA report."""
    return [(finding["name"], finding["summary"]) for finding in collected["findings"]]


def write_outputs(root, collected, final):
    """Write the four build/ files and return the lines for the screen.

    `collected` comes from collect_qa(). Each file is rewritten from scratch,
    so nothing stale is left in it; report.md is never written. The lines are
    one "WROTE <path>" per file, one "WARNING: ..." or "ERROR: ..." per QA
    problem, the report.md status line (--final only), then the QA summary.
    """
    findings = collected["findings"]
    texts = {
        "findings-summary.md": render_findings_summary(
            [finding["row"] for finding in findings]),
        "interactions-timeline.md": render_timeline(collected["timeline"]),
        "findings-combined.md": render_combined_findings(
            [finding["combined"] for finding in findings]),
        "qa-report.txt": render_qa_report(
            final, readiness_lines(collected), collected["checks"], collected["report"]),
    }
    # Check build/ and all four paths before writing anything, so a refused
    # path leaves every file as it was instead of a half-updated build/.
    build = build_path(root, BUILD_FOLDER)
    paths = {}
    for file_name in OUTPUT_FILES:
        path = build_path(root, Path(BUILD_FOLDER) / file_name)
        # e.g. a folder named qa-report.txt, which can't be opened for writing.
        if path.exists() and not path.is_file():
            raise RootError("build output is not a file; remove it: "
                            + str(Path(BUILD_FOLDER) / file_name))
        paths[file_name] = path
    build.mkdir(exist_ok=True)
    lines = []
    for file_name in OUTPUT_FILES:
        # newline="" writes the text exactly, so a finding's "\r\n" line
        # endings reach findings-combined.md unchanged.
        with paths[file_name].open("w", encoding="utf-8", newline="") as handle:
            handle.write(texts[file_name])
        lines.append("WROTE " + str(paths[file_name]))
    for problem in all_problems(collected):
        lines.append(problem_line(problem))
    if collected["report"] is not None:
        lines.append(collected["report"]["status"])
    lines.append(qa_summary_line(collected))
    return lines


def pandoc_hint(root):
    """Return the pandoc command line hint, or None if pandoc isn't installed.

    The tool only shows the command; it never runs it (no command execution).
    """
    # which() only looks pandoc up on PATH; it runs nothing.
    if shutil.which("pandoc") is None:
        return None
    root = Path(root).resolve()
    # shlex.quote() keeps a path with spaces in it one argument when pasted.
    report = shlex.quote(str(root / REPORT_FILE))
    output = shlex.quote(str(root / BUILD_FOLDER / "report.docx"))
    return ("HINT: to convert the report, run: pandoc " + report + " -o " + output
            + " (or end it in report.pdf; PDF also needs a LaTeX engine)")


def run(root, index, final):
    """Compile the working copy and return (exit_code, qa_text, lines).

    qa_text is the text of build/qa-report.txt; lines are the screen lines.
    Nothing is printed, so the notebook's Compile button can call this too.
    Exit code 0: success, or draft mode with any number of warnings.
    1: --final found at least one error. 2: the tool couldn't run (bad
    root, a path outside the root, or a file it can't read or write).
    """
    try:
        root = validate_root(root)
        collected = collect_qa(root, index, final)
        lines = write_outputs(root, collected, final)
    except (RootError, InputError, OSError) as error:
        # A problem with the setup or the files, not a QA result: say what
        # it is instead of showing a Python traceback.
        return 2, "", ["compile failed: " + str(error)]
    qa_text = render_qa_report(final, readiness_lines(collected),
                               collected["checks"], collected["report"])
    hint = pandoc_hint(root)
    if hint is not None:
        lines.append(hint)
    # Draft mode has no errors (every problem is a warning), so it gives 0.
    errors = count_levels(all_problems(collected))[1]
    if final and errors > 0:
        return 1, qa_text, lines
    return 0, qa_text, lines


def main(argv=None):
    """Run from the command line: print the screen lines, return the exit code."""
    args = parse_args(argv)
    exit_code, qa_text, lines = run(args.root, args.index, args.final)
    for line in lines:
        print(line)
    return exit_code


# Only runs when started as `python3 tools/compile.py`, never on import, so
# the notebook and the tests can import this file without side effects.
if __name__ == "__main__":
    sys.exit(main())
