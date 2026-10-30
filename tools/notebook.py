"""notebook.py: a local web page for checklists, field notes and templates.

Each tester runs it on their own box. It reads and writes the same Markdown
files the repo already uses, in the working copy.

Usage: python3 tools/notebook.py --name alice [--root ~/cptc-work] [--port 8765]

Python 3 standard library only. It never runs commands, and it has no option
to serve on any address but 127.0.0.1. It uses compile.py's root check and
marker regex; compile.py imports nothing from here.
"""

import argparse
import datetime
import html
import json
import os
import re
import secrets
import shlex
import shutil
import stat
import sys
import tempfile
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import compile
# The same objects compile.py uses, so the fill-in view and the QA checks
# always agree on what a marker is (OQ-13).
from compile import MARKER_RE, strip_markers

# Any run of characters that aren't allowed in a slug.
NOT_SLUG_RE = re.compile(r"[^a-z0-9-]+")
# Two or more hyphens in a row.
REPEATED_HYPHENS_RE = re.compile(r"-{2,}")
SLUG_MAX_LENGTH = 40


def slugify(text):
    """Return text as a short filename part, e.g. "Admin Panel!" -> "admin-panel".

    Raises ValueError if nothing usable is left, e.g. for "!!!".
    """
    slug = text.lower()
    # Only a-z, 0-9 and "-" survive, so a title can't add "/", "..", spaces
    # or any other character that changes where a file is saved.
    slug = NOT_SLUG_RE.sub("-", slug)
    slug = REPEATED_HYPHENS_RE.sub("-", slug)
    # Trim before stripping the end hyphens, so a cut that lands just after
    # a "-" doesn't leave one at the end.
    slug = slug[:SLUG_MAX_LENGTH].strip("-")
    if not slug:
        raise ValueError("no letters or digits to make a file name from: " + repr(text))
    return slug


# The number in IR-NNN and F-NNN: exactly three ASCII digits. [0-9], not \d,
# because \d also matches other scripts' digits (e.g. Arabic-Indic), and
# fullmatch() is used because "$" would also accept a trailing newline.
NNN_RE = re.compile(r"[0-9]{3}")


def validate_nnn(text):
    """Return text if it is a three-digit number like 007, else raise ValueError.

    It only checks the format. The number itself is typed in by the user;
    this never picks or reserves one.
    """
    if not NNN_RE.fullmatch(text):
        raise ValueError("the number must be exactly three digits, e.g. 007: " + repr(text))
    return text


def is_inside(path, folder):
    """Return True if path is folder itself or anything below it."""
    return path == folder or folder in path.parents


def resolve_inside(root, path):
    """compile.resolve_in_root(), with a NUL byte refused as RootError too."""
    try:
        return compile.resolve_in_root(root, path)
    except ValueError as error:
        # Path.resolve() raises ValueError for a NUL byte, which a hand-typed
        # URL (%00) can carry. As a RootError it gets the same readable 403
        # as any other refused path, instead of a dropped connection.
        raise compile.RootError("path can't be used (" + str(error) + "): " + repr(str(path)))


def readable_path(root, path):
    """Return path, resolved, if it is inside the working copy; else raise RootError."""
    # One shared check (OQ-13): `..`, an absolute path outside the root, and a
    # symlink pointing outside are all refused by compile.py, with the path
    # named, while a symlink that stays inside the root is allowed (OQ-17).
    return resolve_inside(root, path)


def readable_log_path(logdir, path):
    """Return path, resolved, if it is inside the log folder; else raise RootError.

    The log folder is only ever read: there is no writable version of this.
    """
    # The same check as the working copy, with the log folder as the root.
    return resolve_inside(logdir, path)


def writable_path(root, logdir, path):
    """Return path, resolved, if the notebook may write it; else raise RootError.

    It must be inside the working copy, and not inside incoming/ or the
    log folder, which are read-only.
    """
    resolved = resolve_inside(root, path)
    # Both folders are resolved, so a symlink can't be used to write into them
    # through another name.
    incoming = (Path(root) / "incoming").resolve()
    if is_inside(resolved, incoming):
        # incoming/ holds teammates' copied files, which the tools only read
        # (R18); each person edits their own files on their own box.
        raise compile.RootError("incoming/ is read-only, not writing: " + str(path))
    if is_inside(resolved, Path(logdir).resolve()):
        # Logs are evidence: the notebook shows them but never changes them.
        raise compile.RootError("the log folder is read-only, not writing: " + str(path))
    return resolved


def name_option(text):
    """Turn --name into the slug used for field-notes/<name>/, e.g. "Alice Smith" -> "alice-smith"."""
    try:
        return slugify(text)
    except ValueError as error:
        # argparse shows this message with its usage line, instead of a traceback.
        raise argparse.ArgumentTypeError(str(error))


def make_token():
    """Return a new random token for this run (Constraint 8)."""
    # Put in the app's own page; other sites can't read that page, so they
    # can't learn it, and without it their POSTs are refused.
    return secrets.token_urlsafe(32)


def request_refusal(method, headers, port, token):
    """Return the 403 text if a request must be refused, or None to allow it.

    Every GET and POST needs Host exactly 127.0.0.1:<port>; a POST also
    needs the X-CPTC-Token header with this run's token.
    """
    refusal = "refused: use http://127.0.0.1:" + str(port)
    # A page on another site can make the browser send requests here. An
    # exact Host stops DNS rebinding, where an attacker's domain is pointed
    # at 127.0.0.1: the browser then sends that domain as the Host.
    # get_all() so a request can't sneak a second Host header past the check.
    if headers.get_all("Host") != ["127.0.0.1:" + str(port)]:
        return refusal
    if method == "POST":
        given = headers.get_all("X-CPTC-Token") or []
        # compare_digest() is built so its timing doesn't show how much of
        # the token matched. Bytes, because it raises an error on non-ASCII
        # text, which a header could contain.
        if len(given) != 1 or not secrets.compare_digest(given[0].encode("utf-8"),
                                                         token.encode("utf-8")):
            return refusal
    return None


def send_body(handler, status, content_type, body):
    """Send a response with the safety headers every response gets (Constraint 9)."""
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    # The browser must use the type above, not guess HTML from the content:
    # a log with "<script>" in it must never run as part of this page.
    handler.send_header("X-Content-Type-Options", "nosniff")
    # No other site may show the page inside a frame of its own.
    handler.send_header("X-Frame-Options", "DENY")
    # Deliberately no Access-Control-Allow-Origin (CORS) header, so other
    # sites' scripts can't read any response.
    handler.end_headers()
    # A HEAD response is headers only (HTTP says so); Content-Length still
    # gives the size the body would have, as the stdlib's own errors do.
    if handler.command != "HEAD":
        handler.wfile.write(body)


def send_text(handler, status, text):
    """Send a plain-text response: file and log content, and messages."""
    send_body(handler, status, "text/plain; charset=utf-8", text.encode("utf-8"))


def send_json(handler, status, data):
    """Send data (e.g. a file list) as JSON."""
    # ensure_ascii (the default) escapes non-ASCII text, so the body is plain ASCII.
    send_body(handler, status, "application/json", json.dumps(data).encode("ascii"))


def send_page(handler):
    """Send the app's one HTML page, with this run's token in it.

    Only "/" uses this; data is never HTML.
    """
    # The page's own script sends the token with every POST (Constraint 8).
    # token_urlsafe() uses only letters, digits, "-" and "_", so it can't end
    # the attribute it sits in; escape() makes sure of it anyway.
    page = APP_PAGE.replace(TOKEN_SLOT, html.escape(handler.server.token, quote=True))
    send_body(handler, 200, "text/html; charset=utf-8", page.encode("utf-8"))


# The checklists' folder in the working copy. Kept in this one place because
# where checklists 10-60 will live is still being decided.
CHECKLISTS_DIR = "checklists"


def list_checklists(root):
    """Return the checklists as paths relative to root, sorted, e.g. "checklists/10-ad.md".

    Only the .md files directly in checklists/; an empty list if it's missing.
    Raises compile.RootError if checklists/ is a symlink pointing outside the root.
    """
    # Checked before listing, so a linked folder outside the root is never
    # looked into: even its file names stay hidden.
    folder = readable_path(root, CHECKLISTS_DIR)
    # glob("*.md") doesn't look in subfolders, and is_file() leaves out a
    # folder named like "x.md". Sorted, because glob's order depends on the disk.
    return sorted(CHECKLISTS_DIR + "/" + path.name
                  for path in folder.glob("*.md") if path.is_file())


def read_checklist(root, path):
    """Return one listed checklist's text as it is on disk now.

    Raises compile.RootError if path is refused or isn't a listed checklist,
    and compile.InputError if the file isn't UTF-8 text.
    """
    # The shared path check first (OQ-13): `..`, an absolute path outside the
    # root and a symlink pointing outside are refused with the path named.
    resolved = readable_path(root, path)
    # Then only what the list shows, so this route reads checklists and
    # nothing else in the working copy (e.g. findings or subfolders).
    if path not in list_checklists(root):
        raise compile.RootError("not a checklist: " + str(path))
    # Read from disk on every request, never kept, so an edit to the file
    # shows on the next load. It is only read: the checklist never changes.
    return compile.read_markdown(resolved)


# A task line exactly as the checklists write it: "- [ ] text" or "- [x] text"
# at the start of the line. Anything else, e.g. "  - [ ] x" or "- [X] x", is
# shown as plain text.
TASK_RE = re.compile(r"- \[([ x])\] (.+)")
# A code-block fence line, as Markdown defines it: up to three spaces, then
# three or more ` or ~, then the rest of the line. Four spaces is indented
# code, not a fence.
FENCE_RE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


def task_key(path, text, occurrence):
    """Return the key a task's tick is saved under (OQ-08), as one string.

    E.g. '["checklists/10-ad.md", "Run the scan", 2]' for the second
    "Run the scan" task in that checklist.
    """
    # A JSON list, so no character in a path or task text can blur where
    # one part ends; JSON because the ticks are saved in a JSON file.
    return json.dumps([path, text, occurrence])


def checklist_records(path, text):
    """Split a checklist into records, in order, for the checklist view.

    path is the checklist's relative path, e.g. "checklists/10-ad.md". Each
    record is {"type": "task", "key", "text", "checked"} for a task line, or
    {"type": "text", "text"} for any other line, shown as-is (OQ-08).
    "checked" is the file's own mark ("- [x]").
    """
    records = []
    seen = {}
    fence = None
    # Split on "\n" only, like compile.py's line numbers; a "\r" is dropped so
    # a file saved with Windows line endings keeps the same keys.
    for line in text.split("\n"):
        line = line[:-1] if line.endswith("\r") else line
        fence_line = FENCE_RE.match(line)
        if fence_line:
            # Inside a code block every line is text, even one that looks
            # like a task. As in Markdown, only a run of the same character,
            # at least as long, with nothing after it, ends the block, so
            # "```" shown inside a "````" block doesn't end it.
            run, rest = fence_line.group(1), fence_line.group(2)
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                fence = None
        match = TASK_RE.fullmatch(line) if fence is None else None
        if match is None:
            records.append({"type": "text", "text": line})
            continue
        task = match.group(2)
        # Counts each exact text separately, so a repeated task gets its own
        # key, and editing one task's text never moves another task's key.
        seen[task] = seen.get(task, 0) + 1
        records.append({"type": "task", "key": task_key(path, task, seen[task]),
                        "text": task, "checked": match.group(1) == "x"})
    return records


class StateError(Exception):
    """The tick-state file can't be used. The message names the file."""


def state_path(name):
    """Return the tick-state file for this person, relative to the root."""
    return "field-notes/" + name + "/checklist-state.json"


def refuse_linked_state(root, name):
    """Raise RootError if the tick-state file itself is a symlink.

    DECISIONS 2026-10-28 Chunk N2 CR-1 (user, A): stricter than the usual
    "a link inside the root is fine" (OQ-17) for this one file the notebook
    writes, as compile.py is for its build files (C-21).
    """
    # Otherwise a save would write through the link into the file it points
    # to, e.g. another person's tick state or a checklist. islink() looks at
    # the file only, so a linked field-notes/<name> folder is still allowed.
    shown = state_path(name)
    if os.path.islink(os.path.join(str(root), shown)):
        raise compile.RootError("the tick-state file is a link, not a plain file: " + shown)


def check_state(state, shown):
    """Return state if it is {key: true/false}; else raise StateError naming `shown`."""
    # Anything else (a list, "yes", 1) would make ticks show wrongly, so it
    # is refused rather than guessed at.
    if not isinstance(state, dict):
        raise StateError(shown + " is not a {task: true/false} object")
    for key, value in state.items():
        # A loaded file always has text keys, but a state about to be saved
        # might not, and json.dumps() would quietly turn 1 into "1".
        if not isinstance(key, str):
            raise StateError(shown + ": a task key is not text: " + repr(key))
        # bool, not int: in Python True is also an int, but 1 isn't a tick.
        if not isinstance(value, bool):
            raise StateError(shown + ": the value for " + key + " is not true or false")
    return state


def load_checklist_state(root, name):
    """Return the saved ticks as {key: True/False}; {} if nothing is saved yet.

    Raises StateError if the file isn't valid tick state, and
    compile.RootError if its path is refused or the file is a symlink.
    """
    shown = state_path(name)
    path = readable_path(root, shown)
    refuse_linked_state(root, name)
    if not path.exists():
        return {}
    try:
        # Decoded like every other file the tools read (a BOM is dropped).
        with path.open(encoding="utf-8-sig") as handle:
            state = json.load(handle)
    except (ValueError, OSError) as error:
        # ValueError covers both bad JSON and text that isn't UTF-8.
        raise StateError(shown + " can't be read (" + str(error) + ")")
    return check_state(state, shown)


def save_checklist_state(root, logdir, name, state):
    """Write the ticks to field-notes/<name>/checklist-state.json, all at once.

    Raises StateError for a bad state and compile.RootError if the path is
    refused (outside the root, incoming/ or the log folder) or the file is a
    symlink.
    """
    shown = state_path(name)
    check_state(state, shown)
    path = writable_path(root, logdir, shown)
    refuse_linked_state(root, name)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(state, indent=2, sort_keys=True) + "\n"
    # Written to a new temp file beside it, then swapped in with one rename,
    # so a crash never leaves half a file. mkstemp only ever makes a new
    # file, so a symlink planted under the temp name can't be written through.
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".checklist-state-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as temp:
            temp.write(text)
        os.replace(temp_name, str(path))
    except BaseException:
        # Our own temp file only: a failed save leaves the old state as it was.
        os.unlink(temp_name)
        raise


def task_checked(record, state):
    """Return whether a task shows ticked: its saved tick, else the file's own mark."""
    # Once ticked or unticked in the notebook, the saved value wins; until
    # then "- [x]" in the file starts ticked (N2-02 Q1 A). An edited task has
    # a new key, so an old tick never carries over to it.
    return state.get(record["key"], record["checked"])


def own_folders(name):
    """Return the two folders that hold a person's own files, relative to the root.

    Their findings and their own field notes; never incoming/ (teammates'
    copies) or study notes/.
    """
    return ["findings", "field-notes/" + name]


def list_own_files(root, name):
    """Return (files, refused) for the left column.

    files: the .md files directly in the two own folders, as root-relative
    paths, sorted by filename so prefixes group (F-, INJ-, IR-, NOTE-, SU-).
    refused: one message per folder or file whose link points outside the
    root; it is never looked into or listed, but the rest still is.
    """
    files = []
    refused = []
    for folder in own_folders(name):
        try:
            # Checked before listing, so an outside folder's names stay hidden.
            resolved = readable_path(root, folder)
        except compile.RootError as error:
            refused.append(str(error))
            continue
        # glob("*.md") doesn't look in subfolders; a missing folder lists nothing.
        for path in resolved.glob("*.md"):
            relative = folder + "/" + path.name
            try:
                # is_file() after the check leaves out a folder named "x.md".
                if readable_path(root, relative).is_file():
                    files.append(relative)
            except compile.RootError as error:
                # One bad link must not hide the person's other files mid-event.
                refused.append(str(error))
    # By filename first, so both folders' files mix by prefix; the full path
    # breaks a tie, so the order never depends on the disk.
    files.sort(key=lambda path: (path.rsplit("/", 1)[1], path))
    refused.sort()
    return files, refused


def send_own_files(handler):
    """GET /files: the person's own files as JSON, with any refused links."""
    settings = handler.server.settings
    files, refused = list_own_files(settings["root"], settings["name"])
    send_json(handler, 200, {"files": files, "refused": refused})


def send_checklist_list(handler):
    """GET /checklists: the checklists' paths as JSON."""
    try:
        checklists = list_checklists(handler.server.settings["root"])
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    send_json(handler, 200, {"checklists": checklists})


def checklist_from_query(handler):
    """Return (path, text) for the ?path= checklist, or None after sending the error."""
    paths = parse_qs(urlsplit(handler.path).query).get("path", [])
    if len(paths) != 1:
        send_text(handler, 400, "give one checklist: ?path=checklists/<file>.md")
        return None
    try:
        return paths[0], read_checklist(handler.server.settings["root"], paths[0])
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
    except (compile.InputError, OSError) as error:
        # e.g. a checklist saved as Windows-1252, or deleted just now: a
        # readable message instead of a dropped connection.
        send_text(handler, 500, "can't read the checklist: " + str(error))
    return None


def send_checklist(handler):
    """GET /checklist?path=checklists/<file>.md: one checklist's Markdown as plain text."""
    checklist = checklist_from_query(handler)
    if checklist is not None:
        send_text(handler, 200, checklist[1])


def send_checklist_view(handler):
    """GET /checklist-view?path=...: the checklist's records as JSON, ticks filled in.

    Each task's "checked" is what it shows (task_checked()). If the saved
    ticks can't be read, the file's own marks show and "state_error" says why.
    """
    checklist = checklist_from_query(handler)
    if checklist is None:
        return
    path, text = checklist
    settings = handler.server.settings
    state_error = None
    try:
        state = load_checklist_state(settings["root"], settings["name"])
    except (StateError, compile.RootError) as error:
        # The checklist is still worth showing; saving a tick will refuse
        # with the same message, so a broken file is never overwritten.
        state, state_error = {}, str(error)
    records = []
    for record in checklist_records(path, text):
        if record["type"] == "task":
            record = dict(record, checked=task_checked(record, state))
        records.append(record)
    send_json(handler, 200, {"path": path, "records": records, "state_error": state_error})


# Far more than one tick needs ({"key": ..., "checked": ...}); a bigger body
# is refused before it is read.
MAX_TICK_BYTES = 64 * 1024


def read_tick(handler):
    """Return (key, checked) from a tick POST's JSON body, or None after sending a 400."""
    length = handler.headers.get("Content-Length", "")
    if not (length.isascii() and length.isdigit()) or int(length) > MAX_TICK_BYTES:
        send_text(handler, 400, "send one tick as JSON, at most " + str(MAX_TICK_BYTES) + " bytes")
        return None
    try:
        tick = json.loads(handler.rfile.read(int(length)).decode("utf-8"))
    except ValueError:
        tick = None
    # Exactly these two fields, so a typo like "check" is refused, not ignored.
    if (not isinstance(tick, dict) or set(tick) != {"key", "checked"}
            or not isinstance(tick["key"], str) or not isinstance(tick["checked"], bool)):
        send_text(handler, 400, 'send {"key": "<task key>", "checked": true or false}')
        return None
    return tick["key"], tick["checked"]


def save_tick(handler):
    """POST /checklist-state: save one task's tick, keeping every other saved tick."""
    tick = read_tick(handler)
    if tick is None:
        return
    key, checked = tick
    settings = handler.server.settings
    try:
        # Load first: if the saved ticks can't be read, refuse rather than
        # replace them with this one tick (N2-03, agreed with the adversary).
        state = load_checklist_state(settings["root"], settings["name"])
        state[key] = checked
        save_checklist_state(settings["root"], settings["logdir"], settings["name"], state)
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except (StateError, OSError) as error:
        send_text(handler, 500, "tick not saved: " + str(error))
        return
    send_json(handler, 200, {"key": key, "checked": checked})


# The New file table (BUILD-SPEC Tool 2, New file). The keys are the exact
# labels the New form shows.
# "path" is filled in later with str.format(): {name} is the slugged --name,
# {nnn} the checked three-digit number and {slug} the slugged title. The
# folders are written here, never taken from a request, so a new file can
# only go in field-notes/<name>/ or findings/.
# "template" is the file it starts from, relative to the root; None means a
# blank file. "library" is True only for a Finding, which may start from a
# findings-library/ entry instead.
NEW_FILE_TYPES = {
    "Note": {
        "path": "field-notes/{name}/NOTE-{slug}.md",
        "needs_nnn": False,
        "template": None,
        "library": False,
    },
    "Incident report": {
        "path": "field-notes/{name}/IR-{nnn}-{slug}.md",
        "needs_nnn": True,
        "template": "templates/incident-report.md",
        "library": False,
    },
    "Status update": {
        "path": "field-notes/{name}/SU-{slug}.md",
        "needs_nnn": False,
        "template": "templates/status-update.md",
        "library": False,
    },
    "Inject response": {
        "path": "field-notes/{name}/INJ-{slug}.md",
        "needs_nnn": False,
        "template": "templates/inject-response.md",
        "library": False,
    },
    "Finding": {
        "path": "findings/F-{nnn}-{slug}.md",
        "needs_nnn": True,
        "template": "templates/finding.md",
        "library": True,
    },
}


def new_file_type(type_name):
    """Return the New file table's entry for type_name, e.g. "Incident report".

    Raises ValueError for anything else, near misses such as "note" or
    " Note" included: only the form's exact labels are types.
    """
    # The isinstance check first: a list from a JSON body would make the
    # "in" test raise TypeError instead of this readable error.
    if not isinstance(type_name, str) or type_name not in NEW_FILE_TYPES:
        raise ValueError("unknown file type: " + repr(type_name)
                         + " (use one of: " + ", ".join(NEW_FILE_TYPES) + ")")
    # A copy, so a caller that changes it can't change the table.
    return dict(NEW_FILE_TYPES[type_name])


# The findings library: ready-written findings a new Finding can start from.
LIBRARY_DIR = "findings-library"
# Every library entry's first heading starts with this; the rest of that
# line is the entry's title (OQ-03).
LIBRARY_HEADING = "### [[FINDING_ID]]: "
# A Markdown heading: one or more "#", then a space or tab. "#1 priority"
# is prose, not a heading.
HEADING_LINE_RE = re.compile(r"#+[ \t]")


def library_paths(root):
    """Return the names directly in findings-library/ ending .md, as root-relative paths, sorted.

    Never its README.md; an empty list if the folder is missing. A name may
    still be a folder or a link: each is path-checked before it is read.
    Raises compile.RootError if findings-library/ is a symlink pointing
    outside the root.
    """
    # Checked before listing, so a linked folder outside the root is never
    # looked into: even its file names stay hidden.
    folder = readable_path(root, LIBRARY_DIR)
    # glob("*.md") doesn't look in subfolders. No is_file() here: it follows
    # a link, which must wait until the link has passed the path check.
    # Sorted, because glob's order depends on the disk.
    return sorted(LIBRARY_DIR + "/" + path.name for path in folder.glob("*.md")
                  if path.name != "README.md")


def read_library_entry(root, path):
    """Return one library entry's text as it is on disk now.

    Raises compile.RootError if path is refused or isn't a library entry,
    and compile.InputError if the file isn't UTF-8 text.
    """
    # The shared path check first (OQ-13): `..`, an absolute path outside the
    # root, a NUL byte and a symlink pointing outside are refused, path named.
    resolved = readable_path(root, path)
    # Then only what the list shows, so this reads library entries and
    # nothing else in the working copy. is_file() runs after the path check,
    # and leaves out a folder named like "x.md".
    if path not in library_paths(root) or not resolved.is_file():
        raise compile.RootError("not a findings-library entry: " + str(path))
    return compile.read_markdown(resolved)


def without_cr(line):
    """Return line without a final "\r", left by a Windows line ending."""
    return line[:-1] if line.endswith("\r") else line


def library_heading_index(path, lines):
    """Return the index of the entry's first heading in lines (the text split on "\n").

    Raises ValueError, naming path, if there is no heading or the first
    one doesn't start with "### [[FINDING_ID]]: ".
    """
    for index, line in enumerate(lines):
        line = without_cr(line)
        if not HEADING_LINE_RE.match(line):
            continue
        # Only the first heading counts; a later one is part of the entry.
        if not line.startswith(LIBRARY_HEADING):
            raise ValueError(path + ": first heading doesn't start with "
                             + repr(LIBRARY_HEADING) + ": " + repr(line))
        return index
    raise ValueError(path + ": no heading; a library entry starts with "
                     + repr(LIBRARY_HEADING + "<title>"))


def library_title(path, text):
    """Return the text after "### [[FINDING_ID]]: " on the entry's first heading.

    The title is returned exactly as written. Raises ValueError, naming
    path, if there is no heading or the first one doesn't start that way.
    """
    # Split on "\n" only, and drop a "\r", so a Windows line ending never
    # ends up in the title.
    lines = text.split("\n")
    heading = without_cr(lines[library_heading_index(path, lines)])
    return heading[len(LIBRARY_HEADING):]


def list_library(root):
    """Return (entries, refused) for the New form's library dropdown.

    entries: {"path", "title"} for each library entry, sorted by path.
    refused: one message per entry that can't be offered (a link pointing
    outside the root, not UTF-8, or the wrong first heading); the rest is
    still listed. If findings-library/ itself links outside the root, that
    is the one refusal and nothing is listed.
    """
    entries = []
    refused = []
    try:
        paths = library_paths(root)
    except compile.RootError as error:
        # Reported like any other bad link, so the New form still opens for
        # every other type (DECISIONS 2026-10-29 Chunk N3 D1).
        return entries, [str(error)]
    for path in paths:
        try:
            # Path check first; is_file() follows a link, so only after it.
            # A folder named like "x.md" isn't an entry, so it is skipped.
            if not readable_path(root, path).is_file():
                continue
            title = library_title(path, read_library_entry(root, path))
        except (compile.RootError, compile.InputError, ValueError, OSError) as error:
            # One bad entry must not hide the others mid-event (as the
            # own-file list, Chunk N2 D3); its reason is shown instead.
            refused.append(str(error))
            continue
        entries.append({"path": path, "title": title})
    refused.sort()
    return entries, refused


def checked_folder(root, folder, refused):
    """Return True if folder (root-relative) is a folder inside the root.

    A link pointing outside the root is added to refused, with its reason,
    and gives False, so the caller carries on with everything else.
    """
    try:
        # The path check first; is_dir() follows a link, so only after it.
        return readable_path(root, folder).is_dir()
    except compile.RootError as error:
        refused.append(str(error))
        return False


def subfolders(root, folder, refused):
    """Return folder/<name> for each folder directly inside folder, sorted.

    folder must already have passed the path check. A link pointing outside
    the root is added to refused instead.
    """
    names = sorted(entry.name for entry in readable_path(root, folder).iterdir())
    return [folder + "/" + name for name in names
            if checked_folder(root, folder + "/" + name, refused)]


def matching_files(root, folder, name_re, refused):
    """Return (path, match) for each .md file directly in folder whose name matches name_re.

    Sorted by path. A file link pointing outside the root is added to
    refused instead; a folder named like "x.md" is skipped.
    """
    found = []
    for entry in readable_path(root, folder).glob("*.md"):
        match = name_re.match(entry.name)
        if not match:
            continue
        path = folder + "/" + entry.name
        try:
            # The path check first; is_file() follows a link, so only after it.
            if readable_path(root, path).is_file():
                found.append((path, match))
        except compile.RootError as error:
            refused.append(str(error))
    return sorted(found, key=lambda item: item[0])


def finding_id_folders(root, refused):
    """Return the folders that hold findings: findings/ and incoming/<owner>/findings/.

    The same two places compile.py reads (Tool 1 Inputs). A link pointing
    outside the root, at any level, is added to refused; the rest is still
    scanned (DECISIONS 2026-10-29 Chunk N3 D1). A missing folder adds nothing.
    """
    folders = []
    if checked_folder(root, "findings", refused):
        folders.append("findings")
    if checked_folder(root, "incoming", refused):
        for owner in subfolders(root, "incoming", refused):
            if checked_folder(root, owner + "/findings", refused):
                folders.append(owner + "/findings")
    return folders


def ir_folders(root, refused):
    """Return the folders that hold IR files: field-notes/<name>/ and incoming/<owner>/field-notes/<name>/.

    The same places compile.py reads for the timeline, for every person, so
    no name is built in. A link pointing outside the root, at any level, is
    added to refused; the rest is still scanned (DECISIONS 2026-10-29
    Chunk N3 D1).
    """
    folders = []
    if checked_folder(root, "field-notes", refused):
        folders += subfolders(root, "field-notes", refused)
    if checked_folder(root, "incoming", refused):
        for owner in subfolders(root, "incoming", refused):
            if checked_folder(root, owner + "/field-notes", refused):
                folders += subfolders(root, owner + "/field-notes", refused)
    return folders


def finding_id_warnings(root, nnn):
    """Return (warnings, refused) for a new finding numbered nnn.

    warnings: one line per existing finding file with ID F-<nnn>, in
    findings/ or any incoming/<owner>/findings/, e.g.
    "F-007 already exists: findings/F-007-old.md". Only a warning: the user
    decides (the ID allocation rule R6 is the team's, not the tool's).
    refused: one message per link pointing outside the root; the rest is
    still checked. Raises ValueError if nnn isn't three digits.
    """
    finding_id = "F-" + validate_nnn(nnn)
    warnings = []
    refused = []
    for folder in finding_id_folders(root, refused):
        # compile.py's own file-name rule, so the notebook warns about the
        # same IDs compile's duplicate check will report (F-007-x.md and
        # F-007.md, but not F-0070 or F-007x).
        for path, match in matching_files(root, folder, compile.FILENAME_ID_RE, refused):
            if match.group(0) == finding_id:
                warnings.append(finding_id + " already exists: " + path)
    # Sorted, because a refused file link is found in glob's order,
    # which depends on the disk.
    refused.sort()
    return warnings, refused


# An IR file's number: "IR-", exactly three ASCII digits, then a non-word
# character, e.g. IR-004-x.md or IR-004.md, but not IR-0040 or IR-004x.
IR_NUMBER_RE = re.compile(r"IR-([0-9]{3})\b")
NO_IR_NUMBER_LEFT = ("IR-999 is in use, so there is no next three-digit IR number"
                     " to suggest: type one in.")


def suggest_ir_number(root):
    """Return (suggestion, refused): the highest IR number in use plus one, e.g. "005".

    "001" if there is no IR file yet. None if IR-999 is in use: then there
    is no three-digit number left to suggest (show NO_IR_NUMBER_LEFT).
    The suggestion is only shown in the form; it isn't reserved or written
    anywhere, and the user may type any other number (OQ-07).
    refused: one message per link pointing outside the root; the rest
    still counts.
    """
    refused = []
    highest = 0
    for folder in ir_folders(root, refused):
        for path, match in matching_files(root, folder, IR_NUMBER_RE, refused):
            # As a number, so IR-010 beats IR-009.
            highest = max(highest, int(match.group(1)))
    # Sorted, as in finding_id_warnings().
    refused.sort()
    if highest == 999:
        return None, refused
    return "%03d" % (highest + 1), refused


def ir_number_warnings(root, nnn):
    """Return (warnings, refused) for a new incident report numbered nnn.

    warnings: one line per existing IR file with that number, in any
    field-notes/<name>/ or incoming/<owner>/field-notes/<name>/, e.g.
    "IR-007 already exists: field-notes/alice/IR-007-old.md". Only a
    warning, as for findings. refused: one message per link pointing
    outside the root; the rest is still checked. Raises ValueError if nnn
    isn't three digits.
    """
    # DECISIONS 2026-10-29 Chunk N3 D2 (a spec departure: the spec warns for
    # finding IDs only). compile.py doesn't catch a duplicate IR ID, so
    # without this nothing would.
    ir_id = "IR-" + validate_nnn(nnn)
    warnings = []
    refused = []
    for folder in ir_folders(root, refused):
        # The same files suggest_ir_number() counts.
        for path, match in matching_files(root, folder, IR_NUMBER_RE, refused):
            if match.group(1) == nnn:
                warnings.append(ir_id + " already exists: " + path)
    # Sorted, as in finding_id_warnings().
    refused.sort()
    return warnings, refused


# The markers New fills in (templates/README.md): [[FINDING_ID]] -> F-NNN,
# [[IR_ID]] -> IR-NNN, [[FINDING_TITLE]] -> the title. Only these exact
# names; [[FINDING_ID_EXTRA]] or [[PREVIOUS_FINDING_ID]] are left alone.
NEW_FILE_MARKER_RE = re.compile(r"\[\[(FINDING_ID|FINDING_TITLE|IR_ID)\]\]")


def fill_new_file_markers(text, values):
    """Replace each exact marker named in values with its value, e.g. {"IR_ID": "IR-007"}.

    One pass over the text, so a value is never scanned again: a title
    containing "[[FINDING_ID]]" goes in exactly as typed. A marker not in
    values is left as it is.
    """
    return NEW_FILE_MARKER_RE.sub(
        lambda match: values.get(match.group(1), match.group(0)), text)


def checked_new_number(type_name, entry, nnn):
    """Return the checked three-digit number for this type, or None if it has none.

    Raises ValueError for a missing, wrong or unwanted number. The number is
    the one the user typed; the IR suggestion is never used here (OQ-07).
    """
    if not entry["needs_nnn"]:
        # Refused rather than ignored, so a mixed-up form is noticed.
        if nnn is not None:
            raise ValueError(type_name + " has no number: " + repr(nnn))
        return None
    # validate_nnn() expects text; anything else from a JSON body (null, a
    # number, a list) gets the same readable error.
    if not isinstance(nnn, str):
        raise ValueError("the number must be exactly three digits, e.g. 007: " + repr(nnn))
    return validate_nnn(nnn)


def read_template(root, path):
    """Return a template's text, e.g. path "templates/finding.md".

    Raises compile.RootError if path is refused, and compile.InputError if
    it isn't a file or isn't UTF-8 text.
    """
    resolved = readable_path(root, path)
    # After the path check, so a link pointing outside is never followed.
    if not resolved.is_file():
        raise compile.InputError("template not found: " + path)
    return compile.read_markdown(resolved)


def new_file_text(root, type_name, entry, title, nnn, library):
    """Return the new file's text: its template or library entry with the ID and title filled.

    Raises ValueError, compile.RootError or compile.InputError if the
    library entry or template can't be used.
    """
    values = {}
    if type_name == "Finding":
        values = {"FINDING_ID": "F-" + nnn, "FINDING_TITLE": title}
    elif type_name == "Incident report":
        values = {"IR_ID": "IR-" + nnn}
    if library is not None:
        if not entry["library"]:
            raise ValueError("only a Finding can start from the findings library, not a "
                             + type_name)
        if not isinstance(library, str):
            raise ValueError("the library entry must be a path: " + repr(library))
        text = read_library_entry(root, library)
        lines = text.split("\n")
        index = library_heading_index(library, lines)
        # Every line gets its markers filled, then the first heading is set
        # to the title as typed (OQ-03): an unchanged title gives the same
        # line, an edited one replaces only the text after the prefix.
        lines = [fill_new_file_markers(line, values) for line in lines]
        line_end = "\r" if lines[index].endswith("\r") else ""
        lines[index] = fill_new_file_markers(LIBRARY_HEADING, values) + title + line_end
        return "\n".join(lines)
    if entry["template"] is None:
        return ""
    return fill_new_file_markers(read_template(root, entry["template"]), values)


def check_new_file_path(root, logdir, path):
    """Return the full path to create path at, after checking every part of it.

    Raises compile.RootError if the path or a folder on the way leads
    outside the root, into incoming/ or the log folder, if a folder on the
    way isn't a folder, or if anything is already at path.
    """
    # Inside the root and not in incoming/ or the log folder, following any
    # linked folder on the way (OQ-17); the name itself must not exist yet.
    writable_path(root, logdir, path)
    full = os.path.join(str(root), path)
    # list() first: slicing Path.parents needs Python 3.10. The last parent
    # is "." (the root itself), which needs no check.
    for folder in reversed(list(Path(path).parents)[:-1]):
        folder_path = os.path.join(str(root), str(folder))
        # A file or a broken link where a folder should be would make mkdir
        # fail halfway; caught here instead, before anything is made.
        if os.path.lexists(folder_path) and not os.path.isdir(folder_path):
            raise compile.RootError("not a folder, so nothing can be saved in it: " + str(folder))
    # lexists() sees a link, a broken link, a folder or a hard-linked file
    # at the name itself, not only a plain file: a new file never replaces
    # or writes through anything already there (as Chunk N2 CR-1).
    if os.path.lexists(full):
        raise compile.RootError("already exists, choose a different title: " + path)
    return full


def create_new_file(root, logdir, name, type_name, title, nnn=None, library=None):
    """Create the New form's file and return (path, warnings, refused).

    path is root-relative, e.g. "field-notes/alice/IR-007-db-down.md".
    warnings and refused are finding_id_warnings()'s for a Finding and
    ir_number_warnings()'s for an Incident report; they never stop the file
    being created. Everything is checked before the
    first folder or file is made, so a refused call changes nothing.
    Raises ValueError, compile.RootError or compile.InputError (and OSError
    for an unreadable template) with a message naming what was refused.
    """
    entry = new_file_type(type_name)
    if not isinstance(title, str):
        raise ValueError("the title must be text: " + repr(title))
    # A line break would start a new line in the file, e.g. a second
    # "- **Severity:**" line that compile.py would then read (DECISIONS
    # 2026-10-29 Chunk N3 D5). The title isn't repeated in the message.
    if "\r" in title or "\n" in title:
        raise ValueError("the title must be one line, with no line breaks")
    # The file name only ever uses the slug: "/", "..", NUL and "%" can't
    # reach it.
    slug = slugify(title)
    nnn = checked_new_number(type_name, entry, nnn)
    text = new_file_text(root, type_name, entry, title, nnn, library)
    path = entry["path"].format(name=name, nnn=nnn, slug=slug)
    full = check_new_file_path(root, logdir, path)
    warnings, refused = [], []
    if type_name == "Finding":
        warnings, refused = finding_id_warnings(root, nnn)
    elif type_name == "Incident report":
        warnings, refused = ir_number_warnings(root, nnn)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    try:
        # "x" creates the file only if nothing is there, so a file that
        # appeared after the check above is never overwritten.
        # newline="" writes the template's own line endings unchanged.
        handle = open(full, "x", encoding="utf-8", newline="")
    except FileExistsError:
        raise compile.RootError("already exists, choose a different title: " + path)
    try:
        with handle:
            handle.write(text)
    except BaseException:
        # Our own new file only: a failed write leaves no half-made file.
        os.unlink(full)
        raise
    return path, warnings, refused


def send_new_data(handler):
    """GET /new-data: what the New form needs, as JSON.

    The types (with which need a number or may use the library), the
    library entries, the suggested IR number, and every refused reason. A
    folder linked outside the root, even a top-level one, is one of those
    reasons, so the form still opens (DECISIONS 2026-10-29 Chunk N3 D1).
    """
    settings = handler.server.settings
    try:
        library, library_refused = list_library(settings["root"])
        suggestion, ir_refused = suggest_ir_number(settings["root"])
    except OSError as error:
        send_text(handler, 500, "can't read the New form's data: " + str(error))
        return
    # The page builds its Type list and hides or shows fields from this, so
    # the script holds no list of types of its own.
    types = [{"name": name, "needs_nnn": entry["needs_nnn"], "library": entry["library"]}
             for name, entry in NEW_FILE_TYPES.items()]
    send_json(handler, 200, {
        "types": types,
        "library": library,
        "library_refused": library_refused,
        "ir_suggestion": suggestion,
        "ir_note": NO_IR_NUMBER_LEFT if suggestion is None else "",
        "ir_refused": ir_refused,
    })


MAX_NEW_FILE_BYTES = 64 * 1024
NEW_FILE_FIELDS = {"type", "title", "nnn", "library"}


def read_new_file_request(handler):
    """Return the New form's fields from a POST's JSON body, or None after sending a 400.

    Exactly {"type", "title", "nnn", "library"}: type and title text, nnn
    and library text or null. There is no field for a file name or path.
    """
    length = handler.headers.get("Content-Length", "")
    if not (length.isascii() and length.isdigit()) or int(length) > MAX_NEW_FILE_BYTES:
        send_text(handler, 400, "send one new file as JSON, at most "
                  + str(MAX_NEW_FILE_BYTES) + " bytes")
        return None
    try:
        fields = json.loads(handler.rfile.read(int(length)).decode("utf-8"))
    except (ValueError, OSError):
        # OSError: a body shorter than its Content-Length times out (see
        # NotebookHandler.timeout) instead of holding the server forever.
        send_text(handler, 400, "send one new file as JSON, at most "
                  + str(MAX_NEW_FILE_BYTES) + " bytes")
        return None
    # Exactly these fields, so a typo or a "path" field is refused, not ignored.
    if (not isinstance(fields, dict) or set(fields) != NEW_FILE_FIELDS
            or not isinstance(fields["type"], str) or not isinstance(fields["title"], str)
            or not isinstance(fields["nnn"], (str, type(None)))
            or not isinstance(fields["library"], (str, type(None)))):
        send_text(handler, 400, 'send {"type": text, "title": text, '
                  '"nnn": text or null, "library": text or null}')
        return None
    return fields


def save_new_file(handler):
    """POST /new-file: create the New form's file; answer {"path", "warnings", "refused"}."""
    fields = read_new_file_request(handler)
    if fields is None:
        return
    settings = handler.server.settings
    try:
        # create_new_file() checks every field and refuses a mixed-up form,
        # e.g. a number for a Note or a library entry for an incident report.
        path, warnings, refused = create_new_file(
            settings["root"], settings["logdir"], settings["name"], fields["type"],
            fields["title"], nnn=fields["nnn"], library=fields["library"])
    except ValueError as error:
        send_text(handler, 400, "not created: " + str(error))
        return
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except (compile.InputError, OSError) as error:
        send_text(handler, 500, "not created: " + str(error))
        return
    send_json(handler, 200, {"path": path, "warnings": warnings, "refused": refused})


def marker_parts(marker):
    """Split a marker's text into (name, body); body is None for a plain [[NAME]]."""
    # A name is capitals and "_" only, so the first colon ends it.
    name, colon, body = marker[2:-2].partition(":")
    return name, (body if colon else None)


def listed_matches(text):
    """Return the MARKER_RE matches the fill-in view lists, in the order they appear.

    A plain marker whose name was already seen is left out: one box fills
    every occurrence ("same name, same value", templates/README.md). A marker
    with a body is always listed: each one is handled by its own position.
    scan_markers() and marker_controls() both use this list, so they always
    agree on which markers there are.
    """
    matches = []
    seen_names = set()
    # MARKER_RE makes a NOTE spanning several lines one marker, and skips
    # bash tests like [[ -f x ]].
    for match in MARKER_RE.finditer(text):
        name, body = marker_parts(match.group(0))
        if body is None:
            if name in seen_names:
                continue
            seen_names.add(name)
        matches.append(match)
    return matches


def scan_markers(text):
    """Return a field for every marker listed_matches() keeps, in the order they appear.

    Each field is {"name", "body", "marker"}. "marker" is the exact marker
    text, e.g. "[[TODO: who ran it?]]". "name" is the part before any colon
    (HOST, CHOOSE, TODO, NOTE). "body" is everything after the colon exactly
    as written, or None for a plain [[NAME]] marker.
    """
    fields = []
    for match in listed_matches(text):
        name, body = marker_parts(match.group(0))
        fields.append({"name": name, "body": body, "marker": match.group(0)})
    return fields


def is_note(marker):
    """True for a [[NOTE: ...]] marker. A bare [[NOTE]] has no body, so it is a plain name."""
    return marker.startswith("[[NOTE:")


def blank_notes(text):
    """Return text with every NOTE marker turned into spaces, its line breaks kept.

    Every other character stays at the same position, so a marker's line can
    be read from this text by the marker's own offsets, with notes ignored
    (Box size: "Ignore NOTE markers when deciding").
    """
    pieces = []
    last = 0
    for match in MARKER_RE.finditer(text):
        if is_note(match.group(0)):
            pieces.append(text[last:match.start()])
            # Kept line breaks mean a marker after a multi-line note is still
            # on its own line.
            pieces.append(re.sub(r"[^\n]", " ", match.group(0)))
            last = match.end()
    pieces.append(text[last:])
    return "".join(pieces)


def needs_textarea(blanked, start, end):
    """True if the marker at blanked[start:end] gets a multi-line box (Box size).

    blanked is blank_notes()'s text. Multi-line when the marker is the only
    thing on its line, or when its line directly follows a heading line.
    A marker inside a heading line is always one line: a heading is one line.
    """
    line_start = blanked.rfind("\n", 0, start) + 1
    line_end = blanked.find("\n", end)
    if line_end == -1:
        line_end = len(blanked)
    if HEADING_LINE_RE.match(blanked[line_start:line_end]):
        return False
    rest = blanked[line_start:start] + blanked[end:line_end]
    # strip() also drops a "\r", so Windows line endings size the same.
    if not rest.strip():
        return True
    if line_start == 0:
        return False
    previous_start = blanked.rfind("\n", 0, line_start - 1) + 1
    return bool(HEADING_LINE_RE.match(blanked[previous_start:line_start - 1]))


def marker_controls(text):
    """Return scan_markers()'s fields, each with the control the fill-in view shows.

    Each field gains "control":
    - "note": a NOTE, shown as highlighted help, never editable. The app
      never removes a note; the writer deletes it in the textarea.
    - "dropdown": a CHOOSE, with "options", its body split on " / ".
    - "input" (one line) or "textarea" (multi-line), by needs_textarea(),
      for everything else. A TODO also gets "guidance", its body.
    A repeated plain name is sized by its first place, where its box shows.
    Bodies lose the space after the colon here, for display only.
    """
    blanked = blank_notes(text)
    controls = []
    for match in listed_matches(text):
        name, body = marker_parts(match.group(0))
        control = {"name": name, "body": body, "marker": match.group(0)}
        if is_note(match.group(0)):
            control["control"] = "note"
        elif body is not None and name == "CHOOSE":
            control["control"] = "dropdown"
            control["options"] = body.strip().split(" / ")
        else:
            big = needs_textarea(blanked, match.start(), match.end())
            control["control"] = "textarea" if big else "input"
            if body is not None and name == "TODO":
                control["guidance"] = body.strip()
        controls.append(control)
    return controls


def marker_status(text):
    """Return the fill-in status line: "n markers left (k of them notes)" or "complete".

    Counts what listed_matches() lists, so n is the number of boxes and
    notes the view shows: a repeated [[NAME]] counts once, as it has one box.
    """
    listed = listed_matches(text)
    if not listed:
        return "complete"
    notes = [match for match in listed if is_note(match.group(0))]
    return str(len(listed)) + " markers left (" + str(len(notes)) + " of them notes)"


# The fill-in view's format checks by marker name (Fill-in Warnings):
# (regex, warning). Each is used with fullmatch(), so trailing text or a
# trailing newline warns. Digits are [0-9], since \d also matches other
# scripts' digits (DECISIONS 2026-10-29 Chunk N4 D1, as Chunk N1 D1 for IDs).
FORMAT_RULES = {
    "FINDING_ID": (re.compile(r"F-[0-9]{3}"), "should look like F-001"),
    "IR_ID": (re.compile(r"IR-[0-9]{3}"), "should look like IR-001"),
    # compile.py's own regex, so a vector the notebook accepts also passes
    # the QA check (Chunk 3 CR-4).
    "CVSS_VECTOR": (compile.FULL_CVSS31_VECTOR_RE,
                    "should be a full CVSS 3.1 vector, all eight metrics in order,"
                    " e.g. CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"),
    "CVSS_SCORE": (re.compile(r"10\.0|[0-9]\.[0-9]"), "should be 0.0 to 10.0 with one decimal, e.g. 7.5"),
    "REFERENCE_URL": (re.compile(r"http.*", re.DOTALL), "should start with http"),
}
# For every name starting DATE or TIME, e.g. DATE_DETECTED, TIME_STARTED.
DATE_RULE = (re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}"), "should be a date as YYYY-MM-DD")
TIME_RULE = (re.compile(r"[0-9]{2}:[0-9]{2}"), "should be a time as HH:MM")
LEFTOVER_WARNING = "contains [[ and a capital letter, which QA will report as a leftover marker"


def format_rule(name):
    """Return the (regex, warning) that checks a marker name's value, or None for no check."""
    if name in FORMAT_RULES:
        return FORMAT_RULES[name]
    if name.startswith("DATE"):
        return DATE_RULE
    if name.startswith("TIME"):
        return TIME_RULE
    return None


def format_warnings(name, value):
    """Return the warnings for a value typed into marker name's box; [] if none.

    Only warnings: the caller still saves the value exactly as typed. An
    empty value gets none, since an empty box leaves its marker in place.
    """
    if value == "":
        return []
    warnings = []
    rule = format_rule(name)
    if rule is not None and not rule[0].fullmatch(value):
        warnings.append(rule[1])
    # compile.py's own leftover check (DECISIONS 2026-10-29 Chunk N4 D3), so
    # this warns exactly when QA would report it: a bash [[ -f x ]] gets none.
    if compile.LEFTOVER_RE.search(value):
        warnings.append(LEFTOVER_WARNING)
    return warnings


def marker_targets(text, fields):
    """Return ({start offset: value}, warnings): where each filled box's value goes in text.

    fields is the whole field list from the scan the boxes were made from,
    in its order, each with its "value". text is the current text, which the
    writer may have edited in the textarea since that scan.
    - An empty value changes nothing, so it is never checked.
    - A NOTE is never replaced (Fill-in: the app never removes a note).
    - A filled marker that is gone from text warns with the value as typed,
      since its box goes with the rescan (DECISIONS 2026-10-29 N5 F3b).
    - A plain [[NAME]] is keyed by name: its value goes at every copy.
    - A marker with a body is keyed by position: the k-th of the n identical
      copies in the scan goes at the k-th copy in text. If text no longer
      holds exactly n copies, the copies can't be matched up safely, so none
      of them is replaced and each filled one warns with its value: its box
      comes back empty with the rescan (DECISIONS 2026-10-29 N5 F3c).
    """
    now = {}
    for match in MARKER_RE.finditer(text):
        now.setdefault(match.group(0), []).append(match.start())
    scanned = {}
    for field in fields:
        scanned[field["marker"]] = scanned.get(field["marker"], 0) + 1
    targets = {}
    warnings = []
    seen = {}
    for field in fields:
        marker, value = field["marker"], field["value"]
        occurrence = seen.get(marker, 0)
        seen[marker] = occurrence + 1
        if value == "" or is_note(marker):
            continue
        starts = now.get(marker, [])
        if not starts:
            # The value, so the writer can copy it back in (N5 F3b).
            warnings.append(marker + " is no longer in the text: value not saved: " + value)
        elif field["body"] is None:
            for start in starts:
                targets[start] = value
        elif len(starts) != scanned[marker]:
            # The value too, as above (N5 F3c).
            warnings.append(marker + " is in the text " + str(len(starts)) + " times, not "
                            + str(scanned[marker]) + ", so it can't be told apart: value not saved: "
                            + value)
        else:
            targets[starts[occurrence]] = value
    return targets, warnings


def apply_marker_values(text, fields):
    """Return (new text, warnings) with each filled box's value in place of its marker.

    marker_targets() decides where each value goes. Each value goes in
    exactly as typed: no escaping, trimming or reformatting, and a value of
    only spaces still counts as filled. Everything else in text is kept as
    it is. One pass over text, so an inserted value is never scanned again:
    a value "[[PORT]]" stays as typed even when PORT also has a value.
    """
    targets, warnings = marker_targets(text, fields)
    pieces = []
    last = 0
    for match in MARKER_RE.finditer(text):
        if match.start() in targets:
            pieces.append(text[last:match.start()])
            pieces.append(targets[match.start()])
            last = match.end()
    pieces.append(text[last:])
    return "".join(pieces), warnings


def editable_path(root, name, path):
    """Return path if it is one of the person's own files; else raise RootError.

    Only what list_own_files() lists can be opened or saved: the .md files
    directly in findings/ and field-notes/<name>/. That leaves out notes/,
    templates/, checklists/, incoming/, the logs, other people's folders,
    subfolders, other file types, folders, missing files and links pointing
    outside. path is only compared, never used to look at the disk.
    """
    files, _ = list_own_files(root, name)
    if path not in files:
        raise compile.RootError("not one of your own files: " + repr(path))
    return path


def read_editable_file(root, name, path):
    """Return one of the person's own files' text, as compile.py reads it.

    DECISIONS 2026-10-29 N4-05 BOM (user, A): compile.read_markdown() drops
    a leading BOM, so the textarea never shows it and a save leaves it out.
    Raises compile.RootError if path is refused and compile.InputError if
    the file isn't UTF-8 text.
    """
    editable_path(root, name, path)
    return compile.read_markdown(readable_path(root, path))


def refuse_linked_save(root, path):
    """Raise RootError if any part of path is a link, or the file has another hard link.

    DECISIONS 2026-10-29 Chunk N4 D2: stricter than OQ-17's "a link inside
    the root is fine" for saves, as Chunk N2 CR-1 is for the tick-state file:
    writing through a link would change the file it points to, e.g. a
    template or a teammate's finding. Reading through an in-root link is
    still allowed, so the list and the open file match.
    """
    parts = path.split("/")
    for count in range(1, len(parts) + 1):
        shown = "/".join(parts[:count])
        if os.path.islink(os.path.join(str(root), shown)):
            raise compile.RootError("a link, not saving through it: " + shown)
    # A save renames a new file into place, so the other hard-linked name
    # would quietly keep the old text: the two copies would split apart.
    if os.stat(os.path.join(str(root), path)).st_nlink > 1:
        raise compile.RootError("the file has another hard link, not saving through it: " + path)


class StaleError(Exception):
    """The file on disk isn't the text the save started from."""


STALE_MESSAGE = "changed on disk since you opened it, reload"


def save_editable_file(root, logdir, name, path, text, base):
    """Write text to one of the person's own files, exactly, all at once; return the text written.

    base is the text GET /file gave when the file was opened (or the last
    save's answer). Raises compile.RootError if path is refused or any part
    of it is a link, StaleError if the file no longer holds base,
    compile.InputError if it is no longer UTF-8 text, and ValueError if text
    can't be written as UTF-8 (e.g. a lone surrogate from JSON's "\\ud800").
    Every check runs before anything is written. Leading BOMs are left out.
    """
    editable_path(root, name, path)
    full = writable_path(root, logdir, path)
    refuse_linked_save(root, path)
    # DECISIONS 2026-10-29 Chunk N4 D4: if the file was changed elsewhere
    # since it was opened (an editor, a pull), saving would silently throw
    # that change away. Read as GET /file reads it, so a BOM alone is no change.
    if compile.read_markdown(full) != base:
        raise StaleError(STALE_MESSAGE)
    # DECISIONS 2026-10-29 N4-05 BOM: a save writes no BOM, even one pasted at
    # the start. Then the text written is what GET /file reads back, so it
    # works as the next base (Chunk N4 re-review CR-1). All of them, since
    # read_markdown() drops only one.
    text = text.lstrip("\ufeff")
    # Encoded first, so text that can't be UTF-8 is refused before any write.
    # Bytes, not text mode, so "\r\n" and "\n" are written as they came.
    data = text.encode("utf-8")
    mode = os.stat(str(full)).st_mode & 0o777
    # As save_checklist_state(): a new temp file beside it, then one rename,
    # so a crash never leaves half a file. The rename replaces the name
    # itself, never writing through whatever is there.
    handle, temp_name = tempfile.mkstemp(dir=str(full.parent), prefix=".save-")
    try:
        with os.fdopen(handle, "wb") as temp:
            temp.write(data)
        # mkstemp makes the file private (0600); keep the file's own mode.
        os.chmod(temp_name, mode)
        os.replace(temp_name, str(full))
    except BaseException:
        os.unlink(temp_name)
        raise
    return text


def send_editable_file(handler):
    """GET /file?path=<own file>: {"path", "text", "fields", "status"}.

    fields is marker_controls()'s list, status is marker_status()'s line.

    text is also the "base" the first save sends back (Chunk N4 D4).
    """
    paths = parse_qs(urlsplit(handler.path).query).get("path", [])
    if len(paths) != 1:
        send_text(handler, 400, "give one file: ?path=findings/<file>.md or field-notes/<name>/<file>.md")
        return
    settings = handler.server.settings
    try:
        text = read_editable_file(settings["root"], settings["name"], paths[0])
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except (compile.InputError, OSError) as error:
        send_text(handler, 500, "can't read the file: " + str(error))
        return
    send_json(handler, 200, {"path": paths[0], "text": text, "fields": marker_controls(text),
                             "status": marker_status(text)})


# Big enough for a finding with pasted log output, small enough that one
# request can't fill the box's memory.
MAX_SAVE_BYTES = 4 * 1024 * 1024
SAVE_FIELDS = {"path", "text", "base", "fields"}
SAVE_HINT = ('send {"path": text, "text": text, "base": text, "fields": [{"name": text,'
             ' "marker": text, "body": text or null, "value": text}, ...]}')


def good_save_field(field):
    """True if field has the four keys apply_marker_values() and format_warnings() use."""
    # Other keys, e.g. "control" from GET /file, are allowed and not used.
    return (isinstance(field, dict)
            and all(key in field for key in ("name", "marker", "body", "value"))
            and isinstance(field["name"], str) and isinstance(field["marker"], str)
            and isinstance(field["body"], (str, type(None))) and isinstance(field["value"], str))


def read_save_request(handler):
    """Return a save's {"path", "text", "base", "fields"} from a POST's JSON, or None after a 400.

    base is the text the page started from (Chunk N4 D4). fields is the
    field list the boxes were made from, each with its "value"; an empty
    list saves the text alone (e.g. the textarea).
    """
    length = handler.headers.get("Content-Length", "")
    if not (length.isascii() and length.isdigit()) or int(length) > MAX_SAVE_BYTES:
        send_text(handler, 400, "send one save as JSON, at most " + str(MAX_SAVE_BYTES) + " bytes")
        return None
    try:
        save = json.loads(handler.rfile.read(int(length)).decode("utf-8"))
    except (ValueError, OSError):
        # OSError: a short body times out, as in read_new_file_request().
        send_text(handler, 400, "send one save as JSON, at most " + str(MAX_SAVE_BYTES) + " bytes")
        return None
    # Exactly these fields, so a typo is refused, not ignored.
    if (not isinstance(save, dict) or set(save) != SAVE_FIELDS
            or not isinstance(save["path"], str) or not isinstance(save["text"], str)
            or not isinstance(save["base"], str) or not isinstance(save["fields"], list)
            or not all(good_save_field(field) for field in save["fields"])):
        send_text(handler, 400, SAVE_HINT)
        return None
    return save


def save_file(handler):
    """POST /file: apply the boxes' values, save, rescan (Fill-in Save).

    Answers {"path", "text", "fields", "status", "warnings"}: the saved text,
    its new fields and status line, then apply_marker_values()'s warnings
    and each filled box's format warnings as "<name>: <warning>" (the page
    lists them under the status line). Warnings never stop the save.
    The saved text is the base for the next save. A file changed on disk
    since base was read gets 409 and nothing is written (Chunk N4 D4).
    """
    save = read_save_request(handler)
    if save is None:
        return
    text, warnings = apply_marker_values(save["text"], save["fields"])
    for field in save["fields"]:
        if field["value"] != "" and not is_note(field["marker"]):
            for warning in format_warnings(field["name"], field["value"]):
                warnings.append(field["name"] + ": " + warning)
    settings = handler.server.settings
    try:
        text = save_editable_file(settings["root"], settings["logdir"], settings["name"],
                                  save["path"], text, save["base"])
    except StaleError as error:
        send_text(handler, 409, str(error))
        return
    except compile.InputError as error:
        send_text(handler, 500, "not saved: " + str(error))
        return
    except ValueError as error:
        send_text(handler, 400, "not saved: " + str(error))
        return
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except OSError as error:
        send_text(handler, 500, "not saved: " + str(error))
        return
    send_json(handler, 200, {"path": save["path"], "text": text,
                             "fields": marker_controls(text), "status": marker_status(text),
                             "warnings": warnings})


def export_folders(name):
    """Return the folders the zip export takes, relative to the root.

    The person's own files, laid out like incoming/<name>/ on a teammate's
    box (R18): never incoming/ itself, other people's field notes, or
    anything else in the root.
    """
    return ["findings", "evidence", "field-notes/" + name, "tracker"]


def folder_id(path):
    """Return (device, inode) of the folder at path, following links, or None."""
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_dev, info.st_ino)


def add_export_entry(path, member, members, skipped, log_folder):
    """Add the file at path, or every file below the folder at path, to members.

    member is its name in the zip. A symlink is never followed or stored,
    wherever it points (OQ-12); it goes into skipped, as does anything that
    is neither a file nor a folder, or can't be read. log_folder is the log
    folder's folder_id(), or None: that folder is skipped too. A missing
    path adds nothing.
    """
    try:
        # lstat() looks at a link itself, not its target, so a broken link
        # or a link loop is skipped like any other link instead of hanging.
        info = os.lstat(path)
    except (FileNotFoundError, NotADirectoryError):
        # Gone since its folder was listed.
        return
    except OSError as error:
        skipped.append("not exported: can't read: " + member + " (" + str(error) + ")")
        return
    if stat.S_ISLNK(info.st_mode):
        skipped.append("not exported: symlink: " + member)
    elif stat.S_ISDIR(info.st_mode):
        if (info.st_dev, info.st_ino) == log_folder:
            # $LOGDIR kept inside e.g. evidence/: logs may hold secrets, so
            # they go in the zip only as logs/, and only when asked for.
            skipped.append("not exported: the log folder: " + member)
            return
        try:
            names = sorted(os.listdir(path))
        except OSError as error:
            # An unreadable folder must not stop the rest of the export.
            skipped.append("not exported: can't read: " + member + " (" + str(error) + ")")
            return
        for entry in names:
            add_export_entry(path / entry, member + "/" + entry, members, skipped, log_folder)
    elif stat.S_ISREG(info.st_mode):
        members.append((member, path))
    else:
        # A FIFO or device is never opened: reading a FIFO can block forever.
        skipped.append("not exported: not a regular file: " + member)


def export_folder_ok(path, member, skipped):
    """Return True if path is a real folder (not a link) to export from.

    Anything else in its place is added to skipped with the reason: in the
    zip a file there would not give the mirror layout. A missing folder
    just gives False.
    """
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return False
    except OSError as error:
        skipped.append("not exported: can't read: " + member + " (" + str(error) + ")")
        return False
    if stat.S_ISLNK(info.st_mode):
        skipped.append("not exported: symlink: " + member)
        return False
    if not stat.S_ISDIR(info.st_mode):
        skipped.append("not exported: not a folder: " + member)
        return False
    return True


def export_manifest(root, logdir, name, include_logs=False):
    """Return (members, skipped) for the zip export.

    members: (name in the zip, file path) for every regular file in the
    export folders, plus everything in the log folder under logs/ when
    include_logs is true. Ordered by folder, then by name, so it never
    depends on the disk.
    skipped: one "not exported: ..." line per symlink or other entry left
    out; the rest is still exported (DECISIONS 2026-10-30 Chunk N6 E1).
    """
    members = []
    skipped = []
    root = Path(root)
    log_folder = folder_id(logdir)
    for folder in export_folders(name):
        parent = folder.split("/")[0]
        # field-notes/ is checked before field-notes/<name>, so a link there
        # is never read through.
        if parent != folder and not export_folder_ok(root / parent, parent, skipped):
            continue
        if export_folder_ok(root / folder, folder, skipped):
            add_export_entry(root / folder, folder, members, skipped, log_folder)
    if include_logs and export_folder_ok(Path(logdir), "logs", skipped):
        # Every file in the log folder, with no size limit (DECISIONS
        # 2026-10-30 Chunk N6 E2). Named logs/..., never by its path on this box.
        add_export_entry(Path(logdir), "logs", members, skipped, None)
    return members, skipped


def export_file_name(name, now):
    """Return the zip's file name, e.g. cptc-export-alice-20261107T101500.zip.

    name is --name, already a slug (name_option()); now is a datetime.
    """
    return "cptc-export-" + name + "-" + now.strftime("%Y%m%dT%H%M%S") + ".zip"


def zip_name_problem(member):
    """Return why member can't be a name in the zip, or None if it can."""
    if "\\" in member:
        # Some unzip tools (Windows ones, Python's own there) take a
        # backslash as a folder separator, so the file could land outside
        # the mirror layout.
        return "name has a backslash"
    try:
        member.encode("utf-8")
    except UnicodeEncodeError:
        # A file name with bytes that aren't UTF-8 (possible on Linux):
        # zipfile can't store it.
        return "name isn't UTF-8"
    return None


# The first and last times a zip can hold (it keeps seconds in steps of 2).
ZIP_EARLIEST = (1980, 1, 1, 0, 0, 0)
ZIP_LATEST = (2107, 12, 31, 23, 59, 58)


def zip_time(seconds):
    """Return a file time as the zip's (year, month, day, hour, minute, second).

    A time the zip can't hold becomes its first or last one, so a file with
    a wrong date (e.g. copied with its times from a box with a bad clock)
    is still exported.
    """
    try:
        moment = datetime.datetime.fromtimestamp(seconds).timetuple()[:6]
    except (OverflowError, ValueError, OSError):
        # Beyond what this computer's clock functions handle (past year 9999).
        return ZIP_EARLIEST if seconds < 0 else ZIP_LATEST
    return min(max(moment, ZIP_EARLIEST), ZIP_LATEST)


def add_zip_file(archive, member, path, skipped):
    """Copy the file at path into archive as member, unless it changed into something else.

    The file was a plain file when export_manifest() looked; if it is a
    symlink or not a regular file by now, or can't be read, it is skipped
    and added to skipped instead.
    """
    try:
        # O_NOFOLLOW: a file swapped for a symlink since the manifest is
        # refused, not followed (OQ-12). O_NONBLOCK: one swapped for a FIFO
        # can't make open() wait forever; it changes nothing for a plain file.
        handle = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError as error:
        if os.path.islink(path):
            # Reported like the links the manifest found (E1).
            skipped.append("not exported: symlink: " + member)
        else:
            skipped.append("not exported: can't read: " + member + " (" + str(error) + ")")
        return
    # Checked on the open descriptor, before fdopen(), which raises its own
    # error for a folder and would leave the descriptor open (DECISIONS
    # 2026-10-30 Chunk N7 C-N6-01). Each early return closes it first.
    try:
        info = os.fstat(handle)
    except OSError as error:
        os.close(handle)
        skipped.append("not exported: can't read: " + member + " (" + str(error) + ")")
        return
    if not stat.S_ISREG(info.st_mode):
        os.close(handle)
        skipped.append("not exported: not a regular file: " + member)
        return
    with os.fdopen(handle, "rb") as source:
        entry = zipfile.ZipInfo(member, date_time=zip_time(info.st_mtime))
        entry.compress_type = zipfile.ZIP_DEFLATED
        # Copied in chunks, so a large log is never read into memory whole.
        # force_zip64: the large-file format (zip64) from the start, so a log
        # that grows past 2 GB while it is copied still fits; zipfile would
        # otherwise stop with an error. Info-ZIP unzip 6.0 reads zip64.
        with archive.open(entry, "w", force_zip64=True) as target:
            shutil.copyfileobj(source, target)


def write_export(root, logdir, name, include_logs=False, now=None):
    """Write the export zip to the root; return (its path, skipped).

    Members come from export_manifest(); skipped lists every file left out,
    with the reason. Raises FileExistsError if a file of that name is
    already there (never overwritten), compile.RootError if the root path
    is refused, and OSError if the zip can't be written. A failed write
    leaves no zip.
    """
    members, skipped = export_manifest(root, logdir, name, include_logs)
    file_name = export_file_name(name, now or datetime.datetime.now())
    # The same check as every other write: inside the root, not incoming/ or
    # the log folder.
    writable_path(root, logdir, file_name)
    # The name itself, not what writable_path() resolved it to: a link
    # already named like the export (even one to a file that doesn't exist
    # yet) must stop it, not send the zip to wherever the link points.
    path = Path(root) / file_name
    taken = "an export named " + file_name + " already exists; try again in a second"
    if os.path.lexists(str(path)):
        # Two exports in the same second: the first one is kept as it is.
        # Checked first, so a big zip isn't written only to be thrown away.
        raise FileExistsError(taken)
    # Written to a new temp file beside it, then given its name, so a
    # half-written zip never carries the export's name. The temp name doesn't
    # match cptc-export-*.zip, and the root itself is never exported.
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=".cptc-export-", suffix=".part")
    try:
        with os.fdopen(handle, "wb") as temp:
            with zipfile.ZipFile(temp, "w") as archive:
                # The four folders (and logs/) are always there, even empty,
                # so unzipping gives the whole mirror layout. A name ending
                # in "/" is stored as a folder.
                for folder in export_folders(name) + (["logs"] if include_logs else []):
                    archive.writestr(folder + "/", b"")
                for member, source in members:
                    problem = zip_name_problem(member)
                    if problem:
                        skipped.append("not exported: " + problem + ": " + member)
                    else:
                        add_zip_file(archive, member, source, skipped)
        # os.link() gives the zip its name but, unlike a rename, never
        # replaces a file: one that appeared under that name meanwhile is kept.
        os.link(temp_name, str(path))
    except FileExistsError:
        os.unlink(temp_name)
        raise FileExistsError(taken)
    except BaseException:
        # Our own temp file only.
        os.unlink(temp_name)
        raise
    # The zip has its name now; the temp name was a second name for it.
    os.unlink(temp_name)
    return path, skipped


MAX_EXPORT_BYTES = 1024


def read_export_request(handler):
    """Return include_logs from an export POST's JSON body, or None after sending a 400."""
    length = handler.headers.get("Content-Length", "")
    if not (length.isascii() and length.isdigit()) or int(length) > MAX_EXPORT_BYTES:
        send_text(handler, 400, "send the export choice as JSON, at most " + str(MAX_EXPORT_BYTES) + " bytes")
        return None
    try:
        request = json.loads(handler.rfile.read(int(length)).decode("utf-8"))
    except ValueError:
        request = None
    # Exactly this one field, and a real true or false: a missing or
    # misspelt field is refused, so logs are never put in by a guess.
    if (not isinstance(request, dict) or set(request) != {"include_logs"}
            or not isinstance(request["include_logs"], bool)):
        send_text(handler, 400, 'send {"include_logs": true or false}')
        return None
    return request["include_logs"]


def save_export(handler):
    """POST /export: write the export zip to the root; answer with its path and what was left out."""
    include_logs = read_export_request(handler)
    if include_logs is None:
        return
    settings = handler.server.settings
    try:
        path, skipped = write_export(settings["root"], settings["logdir"], settings["name"], include_logs)
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except FileExistsError as error:
        # Before OSError, which it is a kind of: the earlier zip is kept.
        send_text(handler, 409, "not exported: " + str(error))
        return
    except OSError as error:
        # write_export() has removed its temp file.
        send_text(handler, 500, "not exported: " + str(error))
        return
    send_json(handler, 200, {"path": str(path), "skipped": skipped})


# Logs: the terminal transcripts in $LOGDIR are cleaned for display only
# (BUILD-SPEC Logs); the log itself is never changed.

# A run of carriage returns ending in a line feed: \r\n, or \r\r\n from
# Windows output (evil-winrm, HTTP headers).
CR_RUN_LF_RE = re.compile(r"\r+\n")
# The escape codes the spec strips, in its order: CSI (colours, cursor
# moves, modes), OSC (window titles, links) ended by BEL or ESC backslash,
# a character-set choice such as ESC ( B, and keypad mode ESC = / ESC >.
ESCAPE_RES = (
    re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]"),
    re.compile(r"\x1b\][^\x07\x1b]*(\x07|\x1b\\)"),
    re.compile(r"\x1b[()][A-Za-z0-9]"),
    re.compile(r"\x1b[=>]"),
)


def last_redraw(line):
    """Return the text after a line's last carriage return (all of it if there is none)."""
    # A progress bar redraws itself with \r; the terminal showed only the
    # last drawing, so that is all the page shows.
    return line.split("\r")[-1]


def apply_backspaces(line):
    """Return one line with each backspace deleting the character before it."""
    kept = []
    for char in line:
        if char != "\x08":
            kept.append(char)
        elif kept:
            kept.pop()
        # A backspace with nothing before it on the line does nothing: it
        # never deletes the line break (DECISIONS 2026-10-30 Chunk N7 G1).
    return "".join(kept)


def clean_log_text(text):
    """Return a transcript's text as the page shows it, in the spec's four steps."""
    # 1. CR runs before a line feed become one \n first, or step 2 would
    #    keep the empty text after the last \r and blank every Windows line.
    text = CR_RUN_LF_RE.sub("\n", text)
    # 2. Split on \n only (like grep -n), so form feeds and Unicode line
    #    separators stay part of their line.
    text = "\n".join(last_redraw(line) for line in text.split("\n"))
    # 3. Codes go before backspaces, so a backspace never eats part of a code.
    for pattern in ESCAPE_RES:
        text = pattern.sub("", text)
    # 4. Line by line, so a backspace stops at the start of its line (G1).
    return "\n".join(apply_backspaces(line) for line in text.split("\n"))


# logged-shell.sh saves each session as <name>_<time>.log plus this command
# index beside it.
COMMANDS_SUFFIX = ".cmds.log"


def list_logs(logdir):
    """Return (logs, refused) for the Logs view.

    logs: the names of the regular files directly in the log folder, newest
    modified first (the same time: by name). A command index is left out:
    it is shown with its transcript (DECISIONS 2026-10-30 Chunk N7 G2).
    refused: one message per link pointing outside the log folder, or name
    the page couldn't send back.
    A missing log folder lists nothing and is not created.
    """
    try:
        names = os.listdir(str(logdir))
    except FileNotFoundError:
        # No logged shell has been started yet.
        return [], []
    found = []
    refused = []
    for name in names:
        if name.endswith(COMMANDS_SUFFIX):
            continue
        try:
            name.encode("utf-8")
        except UnicodeEncodeError:
            # A name with bytes that aren't UTF-8 (possible on Linux): the
            # page couldn't put it in a URL to open it.
            refused.append("name isn't UTF-8: " + repr(name))
            continue
        try:
            path = readable_log_path(logdir, name)
            info = os.stat(str(path))
        except compile.RootError as error:
            refused.append(str(error))
            continue
        except OSError:
            # Gone since the folder was listed, or a broken link.
            continue
        # Folders, FIFOs and devices aren't logs; a FIFO is never opened.
        if stat.S_ISREG(info.st_mode):
            found.append((-info.st_mtime, name))
    found.sort()
    refused.sort()
    return [name for _, name in found], refused


# The most of one log the page gets (DECISIONS 2026-10-30 Chunk N7 G4): an
# all-day transcript can be gigabytes, too much for the browser to show.
MAX_LOG_BYTES = 5 * 1024 * 1024


def open_regular_file(path):
    """Open a resolved path to read; return (descriptor, its os.stat_result).

    Raises RootError if it is not a regular file, and OSError if it can't
    be opened. The caller closes the descriptor.
    """
    # O_NONBLOCK: a FIFO can't make open() wait forever, and nothing is
    # ever read from it. O_NOFOLLOW: path is already resolved, so a link
    # here is one swapped in since the check; it is refused, not followed.
    handle = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    # Checked on the open descriptor, before fdopen(), which raises its own
    # error for a folder and would leave the descriptor open. Closed on
    # every way out of here that doesn't hand it back.
    try:
        info = os.fstat(handle)
    except OSError:
        os.close(handle)
        raise
    if not stat.S_ISREG(info.st_mode):
        os.close(handle)
        raise compile.RootError("not a regular file: " + str(path))
    return handle, info


def read_log_tail(path):
    """Return (text, cut) for a regular file: its last MAX_LOG_BYTES, decoded.

    cut is the number of bytes left out at the start. Raises RootError if
    path is not a regular file, and OSError if it can't be read.
    """
    handle, info = open_regular_file(path)
    with os.fdopen(handle, "rb") as source:
        # The size now is the snapshot (G5): text a live shell adds while
        # this reads is left for the next open.
        start = max(0, info.st_size - MAX_LOG_BYTES)
        source.seek(start)
        data = source.read(info.st_size - start)
    if start > 0:
        # Start after a line break, so the first line isn't half a line (or
        # half a character or escape code).
        first_line_end = data.find(b"\n") + 1
        data = data[first_line_end:]
        start += first_line_end
    # Decoding the bytes ourselves does no newline translation, which is
    # what the spec's newline="" is for: a lone \r reaches the cleaner.
    # Bytes that aren't UTF-8 show as U+FFFD (G3); the log is not changed.
    return data.decode("utf-8", errors="replace"), start


def commands_name(path):
    """Return the command index's name for a transcript path, or None."""
    if not path.endswith(".log") or path.endswith(COMMANDS_SUFFIX):
        return None
    return path[:-len(".log")] + COMMANDS_SUFFIX


def terminal_command(full_path):
    """Return the command that opens a log in a terminal: less -R <path>, quoted for the shell.

    Only text for the user to copy (BUILD-SPEC Logs): the notebook never
    opens a terminal or runs it (Constraint 3).
    """
    # shlex.quote() adds the quotes a path with spaces or quotes needs, so
    # no more quotes go around it.
    return "less -R " + shlex.quote(str(full_path))


def read_log(logdir, path):
    """Return what the Logs view shows for one log, as a dict.

    raw: the transcript as it is; clean: clean_log_text() of it; commands:
    the matching command index's text, or None; notes: plain lines the page
    shows (left-out text, a missing command index); command: terminal_command()
    for the log's full path, as checked. Never writes anything.
    Raises RootError for a refused path and OSError if it can't be read.
    """
    full_path = readable_log_path(logdir, path)
    raw, cut = read_log_tail(full_path)
    notes = []
    if cut:
        notes.append("Showing only the end of this log (at most 5 MB): the first "
                     + str(cut) + " bytes are left out. "
                     "To see the whole log, use the terminal command.")
    commands = None
    index = commands_name(path)
    if index is None:
        notes.append("No command index: this is a command index itself, or its name doesn't end in .log.")
    else:
        try:
            commands, commands_cut = read_log_tail(readable_log_path(logdir, index))
        except FileNotFoundError:
            notes.append("No command index: " + index + " isn't in the log folder.")
        except (compile.RootError, OSError) as error:
            # The transcript is still shown.
            notes.append("Command index not shown: " + str(error))
        else:
            if commands_cut:
                notes.append("Showing only the end of the command index (at most 5 MB): "
                             "the first " + str(commands_cut) + " bytes are left out.")
    return {"path": path, "raw": raw, "clean": clean_log_text(raw),
            "commands": commands, "notes": notes, "command": terminal_command(full_path)}


def send_log_list(handler):
    """GET /logs: the log names, newest first, with any refused ones, as JSON."""
    try:
        logs, refused = list_logs(handler.server.settings["logdir"])
    except OSError as error:
        # e.g. $LOGDIR is a file, or can't be read.
        send_text(handler, 500, "can't list the log folder: " + str(error))
        return
    send_json(handler, 200, {"logs": logs, "refused": refused})


def send_log(handler):
    """GET /log?path=<name>: one log's raw and clean text and commands, as JSON."""
    query = parse_qs(urlsplit(handler.path).query, keep_blank_values=True)
    if set(query) != {"path"} or len(query["path"]) != 1 or query["path"][0] == "":
        send_text(handler, 400, "give one log: ?path=<a name from the log list>")
        return
    path = query["path"][0]
    try:
        log = read_log(handler.server.settings["logdir"], path)
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except FileNotFoundError:
        send_text(handler, 404, "no such log: " + path)
        return
    except OSError as error:
        send_text(handler, 500, "can't read the log: " + str(error))
        return
    send_json(handler, 200, log)


# An evidence file name: letters, digits, ".", "_" and "-" only (BUILD-SPEC
# Logs), so it can't name a folder or leave evidence/. Used with fullmatch().
EVIDENCE_NAME_RE = re.compile(r"[A-Za-z0-9._-]+")
REDACT_WARNING = ("The copy is the whole log, unchanged. Logs can hold secrets such as "
                  "passwords and keys: redact them before any of it goes into a report.")
# Read in pieces of this size, so a big log is never in memory whole.
COPY_CHUNK_BYTES = 1024 * 1024


def check_evidence_name(name):
    """Return name if it can be an evidence file name; else raise ValueError."""
    # "." and ".." pass the pattern but are folders, not file names.
    if EVIDENCE_NAME_RE.fullmatch(name) is None or name in (".", ".."):
        raise ValueError("an evidence name may use only letters, digits, '.', '_' and '-' "
                         "(e.g. F-001-nmap.log): " + repr(name))
    return name


def evidence_folder(root, logdir):
    """Return the root's evidence/ folder, made if missing; raise RootError if it can't be used.

    DECISIONS 2026-10-30 Chunk N7 G7: refused if it is a symlink, even one
    inside the root, like the N4 D2 rule for saves: the copy must land in
    evidence/ itself, where the team looks for it.
    """
    folder = Path(root) / "evidence"
    if os.path.islink(str(folder)):
        raise compile.RootError("evidence is a link, not copying through it")
    # The same check as every other write: inside the root, not incoming/
    # or the log folder (e.g. $LOGDIR set to evidence/).
    writable_path(root, logdir, "evidence")
    try:
        folder.mkdir(exist_ok=True)
    except FileExistsError:
        # Something that isn't a folder is already named evidence.
        raise compile.RootError("evidence is not a folder, not copying into it")
    return folder


def copy_bytes(handle, target, size):
    """Copy size bytes (or up to the end, if the file got shorter) from handle to target."""
    left = size
    while left > 0:
        chunk = os.read(handle, min(left, COPY_CHUNK_BYTES))
        if not chunk:
            break
        target.write(chunk)
        left -= len(chunk)


def copy_log_to_evidence(root, logdir, path, name):
    """Copy a log, byte for byte, to evidence/<name>; return that path, root-relative.

    Raises ValueError for a bad name, RootError for a refused path, a
    non-regular log or a linked evidence/, FileExistsError if evidence/<name>
    exists (never overwritten), and OSError if the copy can't be made. A
    failed copy leaves nothing behind but a newly made evidence/ folder.
    """
    check_evidence_name(name)
    relative = "evidence/" + name
    handle, info = open_regular_file(readable_log_path(logdir, path))
    with os.fdopen(handle, "rb") as source:
        folder = evidence_folder(root, logdir)
        target = folder / name
        taken = relative + " already exists; not overwriting it, pick another name"
        # lexists: a link there, even a broken one, counts as taken too.
        # Checked first, so a big log isn't copied only to be thrown away.
        if os.path.lexists(str(target)):
            raise FileExistsError(taken)
        # Written to a new temp file beside it, then given its name, as the
        # export does, so a half-copied file never carries the name.
        temp_handle, temp_name = tempfile.mkstemp(dir=str(folder), prefix=".cptc-evidence-", suffix=".part")
        try:
            with os.fdopen(temp_handle, "wb") as temp:
                # The size when it was opened (DECISIONS 2026-10-30 Chunk N7
                # G8): text a live shell adds meanwhile is left out.
                copy_bytes(source.fileno(), temp, info.st_size)
            # os.link() never replaces a file, unlike a rename: one that
            # appeared under that name since the check above is kept.
            os.link(temp_name, str(target))
        except FileExistsError:
            os.unlink(temp_name)
            raise FileExistsError(taken)
        except BaseException:
            # Our own temp file only.
            os.unlink(temp_name)
            raise
        # The copy has its name now; the temp name was a second name for it.
        os.unlink(temp_name)
    return relative


MAX_EVIDENCE_BYTES = 4096
EVIDENCE_FIELDS = {"path", "name"}


def read_evidence_request(handler):
    """Return (log path, evidence name) from a copy POST's JSON body, or None after sending a 400."""
    length = handler.headers.get("Content-Length", "")
    if not (length.isascii() and length.isdigit()) or int(length) > MAX_EVIDENCE_BYTES:
        send_text(handler, 400, "send the copy request as JSON, at most " + str(MAX_EVIDENCE_BYTES) + " bytes")
        return None
    try:
        request = json.loads(handler.rfile.read(int(length)).decode("utf-8"))
    except ValueError:
        request = None
    # Exactly these two fields, both text, so nothing is copied by a guess.
    if (not isinstance(request, dict) or set(request) != EVIDENCE_FIELDS
            or not all(isinstance(request[field], str) for field in EVIDENCE_FIELDS)):
        send_text(handler, 400, 'send {"path": <log name>, "name": <evidence file name>}')
        return None
    return request["path"], request["name"]


def save_evidence(handler):
    """POST /evidence: copy a log unchanged into evidence/; answer with its path and the redact warning."""
    request = read_evidence_request(handler)
    if request is None:
        return
    path, name = request
    settings = handler.server.settings
    try:
        copied = copy_log_to_evidence(settings["root"], settings["logdir"], path, name)
    except ValueError as error:
        send_text(handler, 400, "not copied: " + str(error))
        return
    except compile.RootError as error:
        send_text(handler, 403, "refused: " + str(error))
        return
    except FileExistsError as error:
        # Before OSError, which it is a kind of: the existing file is kept.
        send_text(handler, 409, "not copied: " + str(error))
        return
    except FileNotFoundError:
        send_text(handler, 404, "no such log: " + path)
        return
    except OSError as error:
        send_text(handler, 500, "not copied: " + str(error))
        return
    send_json(handler, 200, {"path": copied, "warning": REDACT_WARNING})


# Where send_page() puts this run's token in the page.
TOKEN_SLOT = "CPTC_TOKEN_SLOT"

# The app page: a left column (nav) and a main pane. Inline CSS and JS only,
# no outside files (Constraint 1). Black on white, or white on black when the
# system is in dark mode; the button swaps them by hand. Plain styling only:
# one grey, spacing, borders and one button style, so messages stand out
# (DECISIONS 2026-10-30 LOOK-01). The script builds everything with textContent, never innerHTML, so
# text from a file (even "<script>") only ever shows as text.
APP_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="cptc-token" content="CPTC_TOKEN_SLOT">
<title>CPTC notebook</title>
<style>
/* Black and white (a soft dark grey in dark mode) plus one grey, for borders
   and disabled buttons (DECISIONS 2026-10-30 LOOK-01), and a red, a green and
   an amber for the left bar of error, OK and warning messages only (Chunk N7
   review F2). Each colour is readable on its background. */
:root { --text: black; --background: white; --grey: #707070; --error: #c62828; --ok: #2e7d32; --warning: #b26a00; }
/* Dark is a soft dark grey, not pure black (DECISIONS 2026-10-30 Chunk N7 review F1). */
@media (prefers-color-scheme: dark) {
  :root { --text: #e6e6e6; --background: #1e1e1e; --grey: #8f8f8f; --error: #ef5350; --ok: #66bb6a; --warning: #ffb74d; }
}
/* Set by the toggle button; these win over the system setting above. */
:root[data-theme="light"] { --text: black; --background: white; --grey: #707070; --error: #c62828; --ok: #2e7d32; --warning: #b26a00; }
:root[data-theme="dark"] { --text: #e6e6e6; --background: #1e1e1e; --grey: #8f8f8f; --error: #ef5350; --ok: #66bb6a; --warning: #ffb74d; }
body { margin: 0; color: var(--text); background: var(--background); font-family: sans-serif;
       line-height: 1.4; }
.columns { display: flex; gap: 2rem; padding: 1.5rem; max-width: 90rem; }
/* A line between the left column and the main pane. */
nav { width: 15rem; flex-shrink: 0; padding-right: 1.5rem; border-right: 1px solid var(--grey); }
/* min-width 0 lets long log lines wrap instead of widening the page. */
main { flex-grow: 1; min-width: 0; max-width: 65rem; }
h2 { margin: 0 0 1rem; font-size: 1.4rem; overflow-wrap: anywhere; }
h3 { margin: 1.5rem 0 0.5rem; font-size: 1.1rem; }
p { margin: 0.5rem 0; }
/* One button style; the page's own colours, not the system's grey ones. */
button { font: inherit; color: var(--text); background: var(--background);
         border: 1px solid var(--text); border-radius: 3px; padding: 0.25rem 0.75rem; cursor: pointer; }
button:disabled { color: var(--grey); border-color: var(--grey); cursor: default; }
/* A clear outline on whatever has the keyboard focus. */
:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; }
input[type="text"], select, textarea { font: inherit; color: var(--text); background: var(--background);
         border: 1px solid var(--grey); border-radius: 3px; padding: 0.25rem 0.4rem; }
/* Each box sits under its label, so the boxes line up. */
label > input[type="text"], label > select, label > textarea { display: block; margin-top: 0.25rem; }
input[type="text"] { width: 100%; max-width: 30rem; box-sizing: border-box; }
textarea { width: 100%; box-sizing: border-box; font-family: monospace; }
input[type="checkbox"] { margin-right: 0.5rem; }
nav button { display: block; width: 100%; margin-bottom: 0.5rem; text-align: left; }
/* One <pre> per checklist line; an empty line still takes up a line. */
pre { margin: 0; min-height: 1.2em; white-space: pre-wrap; overflow-wrap: anywhere; font-family: monospace; }
/* The file list: full paths wrap rather than widen the column. */
#file-list { margin: 1rem 0; padding: 0.75rem 0; border-top: 1px solid var(--grey);
             border-bottom: 1px solid var(--grey); }
#file-list div { margin-bottom: 0.25rem; overflow-wrap: anywhere; }
#file-list button { margin-bottom: 0; max-width: 100%; overflow-wrap: anywhere; }
/* The file just created, so it can be found in the list. */
#file-list .selected { font-weight: bold; }
form div, main > div { margin-bottom: 0.5rem; }
/* A NOTE in the fill-in view: bold, not the browser's yellow. */
mark { background: none; color: inherit; font-weight: bold; }
/* Status, warning and error lines: a block of their own, so they can't be
   missed. Hidden while empty. */
.message { margin: 0.75rem 0; padding: 0.5rem 0.75rem; border: 1px solid var(--grey);
           border-left: 4px solid var(--text); }
.message:empty { display: none; }
/* Only the bar is coloured; the words ("refused:", "Saved") say it too. */
.message.error { border-left-color: var(--error); }
.message.ok { border-left-color: var(--ok); }
.message.warning { border-left-color: var(--warning); }
.message p, .message pre { margin: 0.25rem 0; }
/* A log's text and its commands: framed, and scrolling inside the frame. */
.log-text { padding: 0.5rem; border: 1px solid var(--grey); max-height: 70vh; overflow: auto; }
</style>
</head>
<body>
<div class="columns">
<nav id="nav">
<button type="button" id="theme-toggle">Light / dark</button>
<div id="file-list"></div>
<button type="button" id="new-button">New</button>
<button type="button" id="checklists-button">Checklists</button>
<button type="button" id="logs-button">Logs</button>
<button type="button" id="export-button">Export</button>
</nav>
<main id="main"></main>
</div>
<script>
/* Swap light and dark, starting from whatever is showing now. */
document.getElementById("theme-toggle").addEventListener("click", function () {
  var root = document.documentElement;
  var dark = root.dataset.theme
    ? root.dataset.theme === "dark"
    : window.matchMedia("(prefers-color-scheme: dark)").matches;
  root.dataset.theme = dark ? "light" : "dark";
});

var TOKEN = document.querySelector('meta[name="cptc-token"]').content;
var main = document.getElementById("main");

/* A new element, with its text (if any) set as plain text. */
function element(tag, text) {
  var made = document.createElement(tag);
  if (text !== undefined) {
    made.textContent = text;
  }
  return made;
}

/* Mark a message block as an error, as done, or as a warning or note
   (DECISIONS 2026-10-30 Chunk N7 review F2): only its left bar changes colour.
   A status such as "3 markers left" stays plain. */
function markError(block) {
  block.className = "message error";
}

function markOk(block) {
  block.className = "message ok";
}

function markWarning(block) {
  block.className = "message warning";
}

/* Empty the main pane and show one message, e.g. the server's error text. */
function showMessage(text) {
  main.textContent = "";
  markError(main.appendChild(element("p", text)));
}

/* GET a JSON route and pass its data to show(); an error shows the server's text. */
function getJson(url, show) {
  fetch(url).then(function (response) {
    return response.ok ? response.json().then(show) : response.text().then(showMessage);
  }).catch(function (error) {
    showMessage("The notebook isn't answering: " + error);
  });
}

function showChecklistList(data) {
  main.textContent = "";
  main.appendChild(element("h2", "Checklists"));
  if (data.checklists.length === 0) {
    main.appendChild(element("p", "No checklists found."));
  }
  data.checklists.forEach(function (path) {
    var button = element("button", path);
    button.type = "button";
    button.addEventListener("click", function () {
      getJson("/checklist-view?path=" + encodeURIComponent(path), showChecklist);
    });
    main.appendChild(element("div")).appendChild(button);
  });
}

/* Each task gets a real checkbox; every other line is shown as it is. */
function showChecklist(data) {
  main.textContent = "";
  main.appendChild(element("h2", data.path));
  /* Saving problems show here; empty when all is well. */
  var status = main.appendChild(element("p", data.state_error || ""));
  /* It only ever holds a problem: a state error, or a tick not saved. */
  markError(status);
  data.records.forEach(function (record) {
    if (record.type === "text") {
      main.appendChild(element("pre", record.text));
      return;
    }
    var box = element("input");
    box.type = "checkbox";
    box.checked = record.checked;
    box.addEventListener("change", function () {
      saveTick(record.key, box, status);
    });
    var label = element("label");
    label.appendChild(box);
    label.appendChild(element("span", record.text));
    main.appendChild(element("div")).appendChild(label);
  });
}

/* Save one tick. If it isn't saved, the box goes back and the reason shows. */
function saveTick(key, box, status) {
  var wanted = box.checked;
  /* Locked until this save answers, so a quick second click can't be
     undone by the first click's answer arriving after it. */
  box.disabled = true;
  function saved() {
    box.disabled = false;
    status.textContent = "";
  }
  function notSaved(text) {
    box.checked = !wanted;
    box.disabled = false;
    status.textContent = text;
  }
  fetch("/checklist-state", {
    method: "POST",
    headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},
    body: JSON.stringify({key: key, checked: wanted})
  }).then(function (response) {
    if (response.ok) {
      saved();
      return;
    }
    return response.text().then(notSaved);
  }).catch(function (error) {
    notSaved("Tick not saved: " + error);
  });
}

var fileList = document.getElementById("file-list");

/* The person's own files, in the order /files gives them, which groups
   them by prefix. Clicking one opens it in the fill-in view. selected is a
   path to mark, e.g. the file just created. */
function showFiles(data, selected) {
  fileList.textContent = "";
  data.files.forEach(function (path) {
    var button = fileList.appendChild(element("div")).appendChild(element("button", path));
    button.type = "button";
    button.addEventListener("click", function () {
      goTo(function () {
        getJson("/file?path=" + encodeURIComponent(path), showFillIn);
      });
    });
    if (path === selected) {
      button.className = "selected";
    }
  });
  /* A link pointing outside isn't listed, but its reason always shows. */
  data.refused.forEach(function (reason) {
    markError(fileList.appendChild(element("p", "Not listed: " + reason)));
  });
}

function loadFiles(selected) {
  fetch("/files").then(function (response) {
    if (response.ok) {
      return response.json().then(function (data) {
        showFiles(data, selected);
      });
    }
    return response.text().then(showFileListError);
  }).catch(function (error) {
    showFileListError("The notebook isn't answering: " + error);
  });
}

/* Why the file list couldn't load, in place of the list. */
function showFileListError(text) {
  fileList.textContent = "";
  markError(fileList.appendChild(element("p", text)));
}

/* A labelled control in its own row; returns the row, to hide or add to. */
function addField(form, text, control) {
  var row = form.appendChild(element("div"));
  var label = row.appendChild(element("label", text + " "));
  label.appendChild(control);
  return row;
}

/* The New form. There is no file name or path field: the notebook builds
   the name from the type, the number and the title. */
function showNewForm(data) {
  main.textContent = "";
  main.appendChild(element("h2", "New file"));
  var form = main.appendChild(element("form"));
  /* One line, so a title can't split the heading it goes into. */
  var title = element("input");
  title.type = "text";
  addField(form, "Title", title);
  var typeList = element("select");
  data.types.forEach(function (kind) {
    var option = typeList.appendChild(element("option", kind.name));
    option.value = kind.name;
  });
  addField(form, "Type", typeList);
  var nnn = element("input");
  nnn.type = "text";
  var nnnRow = addField(form, "Number (NNN)", nnn);
  var nnnNote = nnnRow.appendChild(element("p", ""));
  /* Only ever "no number left" or "couldn't get one". */
  markError(nnnNote);
  data.ir_refused.forEach(function (reason) {
    markError(nnnRow.appendChild(element("p", "Not counted for the IR number: " + reason)));
  });
  var library = element("select");
  var blank = library.appendChild(element("option", "templates/finding.md (no library entry)"));
  blank.value = "";
  data.library.forEach(function (entry) {
    var option = library.appendChild(element("option", entry.title + " (" + entry.path + ")"));
    option.value = entry.path;
  });
  var libraryRow = addField(form, "Start from", library);
  data.library_refused.forEach(function (reason) {
    markError(libraryRow.appendChild(element("p", "Not offered: " + reason)));
  });
  var create = form.appendChild(element("div")).appendChild(element("button", "Create"));
  create.type = "button";
  var status = form.appendChild(element("div"));
  status.className = "message";

  function chosenType() {
    return data.types[typeList.selectedIndex];
  }

  /* Show only the fields this type uses. A hidden field's value is never
     sent, so an old value can't make the request a mixed-up one. */
  function typeChanged() {
    var kind = chosenType();
    nnnRow.hidden = !kind.needs_nnn;
    libraryRow.hidden = !kind.library;
    /* An incident report starts from the suggested number (OQ-07); a
       finding's number is the team's to pick (R6), so it starts empty. */
    var incident = kind.name === "Incident report";
    nnn.value = incident ? (data.ir_suggestion || "") : "";
    nnnNote.textContent = incident ? data.ir_note : "";
  }
  typeList.addEventListener("change", typeChanged);
  typeChanged();

  /* Ask the server again for the suggested IR number and show it. If that
     fails, the box is emptied with the reason, never left at a number that
     may now be taken. */
  function refreshSuggestion() {
    fetch("/new-data").then(function (response) {
      return response.ok ? response.json() : null;
    }).catch(function () {
      return null;
    }).then(function (fresh) {
      data.ir_suggestion = fresh ? fresh.ir_suggestion : null;
      data.ir_note = fresh ? fresh.ir_note : "Couldn't get the next IR number: type one in.";
      /* Only an incident report's number comes from the suggestion; any
         other type's fields stay as they are. */
      if (chosenType().name === "Incident report") {
        typeChanged();
      }
    });
  }

  /* Picking a library entry puts its title in the Title box, to keep or
     edit (OQ-03). */
  library.addEventListener("change", function () {
    var entry = data.library[library.selectedIndex - 1];
    if (entry) {
      title.value = entry.title;
    }
  });

  create.addEventListener("click", function () {
    var kind = chosenType();
    var request = {
      type: kind.name,
      title: title.value,
      nnn: kind.needs_nnn ? nnn.value : null,
      library: kind.library && library.value ? library.value : null
    };
    /* Locked until the answer, so one click makes at most one file. */
    create.disabled = true;
    status.textContent = "";
    function notCreated(text) {
      /* The form keeps its values, so the user can correct them. */
      create.disabled = false;
      markError(status);
      status.appendChild(element("p", text));
    }
    fetch("/new-file", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},
      body: JSON.stringify(request)
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(notCreated);
      }
      return response.json().then(function (result) {
        create.disabled = false;
        markOk(status);
        status.appendChild(element("p", "Created " + result.path));
        result.warnings.forEach(function (warning) {
          status.appendChild(element("p", "Warning: " + warning));
        });
        result.refused.forEach(function (reason) {
          status.appendChild(element("p", "Not checked for duplicates: " + reason));
        });
        /* Made, but with something to read: amber, not green (LOOK-02). */
        if (result.warnings.length > 0 || result.refused.length > 0) {
          markWarning(status);
        }
        loadFiles(result.path);
        refreshSuggestion();
      });
    }).catch(function (error) {
      notCreated("Not created: " + error);
    });
  });
}

/* The Export view (Export (a)): one zip of the person's own files, saved
   in the working copy, for a teammate to unzip in incoming/<name>/. */
function showExport() {
  main.textContent = "";
  main.appendChild(element("h2", "Export"));
  main.appendChild(element("p", "Makes one zip of your findings/, evidence/, tracker/ and " +
    "field-notes/<your name>/, saved in your working copy. A teammate unzips it " +
    "inside their incoming/<your name>/. Symlinks are never put in it."));
  var logs = element("input");
  logs.type = "checkbox";
  /* Off every time the view opens (Export (a)). */
  logs.checked = false;
  var label = element("label");
  label.appendChild(logs);
  label.appendChild(element("span", "Include logs"));
  main.appendChild(element("div")).appendChild(label);
  markWarning(main.appendChild(element("p", "Logs are large and may contain secrets such as " +
    "passwords and keys. Only include them when your team needs them.")));
  var make = element("button", "Make the zip");
  make.type = "button";
  main.appendChild(element("div")).appendChild(make);
  var status = main.appendChild(element("div"));
  status.className = "message";

  make.addEventListener("click", function () {
    /* Locked until the answer, so one click makes at most one zip. */
    make.disabled = true;
    status.textContent = "";
    function notMade(text) {
      make.disabled = false;
      markError(status);
      status.appendChild(element("p", text));
    }
    fetch("/export", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},
      body: JSON.stringify({include_logs: logs.checked})
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(notMade);
      }
      return response.json().then(function (result) {
        make.disabled = false;
        markOk(status);
        status.appendChild(element("p", "Saved " + result.path));
        /* The zip is still made without them (DECISIONS 2026-10-30 Chunk N6 E1). */
        if (result.skipped.length > 0) {
          /* Made, but not with everything: amber, not green (LOOK-02). */
          markWarning(status);
          status.appendChild(element("p", "Left out of the zip:"));
        }
        result.skipped.forEach(function (line) {
          status.appendChild(element("p", line));
        });
      });
    }).catch(function (error) {
      notMade("Not exported: " + error);
    });
  });
}

/* The Logs view: the log folder's files, newest first (GET /logs). */
function showLogList(data) {
  main.textContent = "";
  main.appendChild(element("h2", "Logs"));
  if (data.logs.length === 0) {
    main.appendChild(element("p", "No logs in the log folder."));
  }
  data.logs.forEach(function (name) {
    var button = element("button", name);
    button.type = "button";
    button.addEventListener("click", function () {
      getJson("/log?path=" + encodeURIComponent(name), showLog);
    });
    main.appendChild(element("div")).appendChild(button);
  });
  /* A link pointing outside isn't listed, but its reason always shows. */
  data.refused.forEach(function (reason) {
    markError(main.appendChild(element("p", "Not listed: " + reason)));
  });
}

/* The lines of text that contain wanted, ignoring case; all of it if
   wanted is empty (DECISIONS 2026-10-30 Chunk N7 G6). */
function matchingLines(text, wanted) {
  if (wanted === "") {
    return text;
  }
  var needle = wanted.toLowerCase();
  return text.split("\\n").filter(function (line) {
    return line.toLowerCase().indexOf(needle) !== -1;
  }).join("\\n");
}

/* One log (GET /log): its cleaned or raw text, searchable, with the exact
   commands from its .cmds.log below. Everything from the log goes in as
   textContent, so "<script>" in a log only ever shows as text. */
function showLog(data) {
  main.textContent = "";
  main.appendChild(element("h2", data.path));
  showTerminalCommand(data.command);
  markWarning(main.appendChild(element("p", "Shown cleaned: colour codes, carriage returns and " +
    "backspaces are taken out. Output that redraws the screen (progress bars, spinners, " +
    "full-screen tools such as vim) may still look messy here. For those, open the log " +
    "in a terminal with less -R and its full path, as checklists/40-evidence-and-logging.md " +
    "says (type / and a word to search, q to quit).")));
  /* e.g. only the last 5 MB is shown (G4), or there is no command index. */
  var notes = main.appendChild(element("div"));
  markWarning(notes);
  data.notes.forEach(function (note) {
    notes.appendChild(element("p", note));
  });
  var search = element("input");
  search.type = "text";
  addField(main, "Show only lines containing", search);
  var raw = element("input");
  raw.type = "checkbox";
  var rawLabel = element("label");
  rawLabel.appendChild(raw);
  rawLabel.appendChild(element("span", "Raw (the log as saved, control codes included)"));
  main.appendChild(element("div")).appendChild(rawLabel);
  var found = main.appendChild(element("p", ""));
  markWarning(found);
  var transcript = main.appendChild(element("pre", ""));
  transcript.className = "log-text";

  /* Search runs on whichever text is shown, clean or raw (G6). */
  function redraw() {
    var shown = matchingLines(raw.checked ? data.raw : data.clean, search.value);
    transcript.textContent = shown;
    found.textContent = search.value === "" ? "" :
      (shown === "" ? "No lines contain that text." : "Only lines containing that text are shown.");
  }
  search.addEventListener("input", redraw);
  raw.addEventListener("change", redraw);
  redraw();

  if (data.commands !== null) {
    main.appendChild(element("h3", "Commands (exact, from the .cmds.log)"));
    main.appendChild(element("pre", data.commands)).className = "log-text";
  }
  showEvidenceCopy(data.path);
}

/* The command that opens this log in a terminal, as selectable text, and a
   button that puts it on the clipboard. The page never runs it. */
function showTerminalCommand(command) {
  main.appendChild(element("p", "To open this log in a terminal, paste this command there:"));
  main.appendChild(element("pre", command));
  var copy = element("button", "Copy terminal command");
  copy.type = "button";
  main.appendChild(element("div")).appendChild(copy);
  var copied = main.appendChild(element("p", ""));
  copied.className = "message";
  copy.addEventListener("click", function () {
    /* Without clipboard access the command above can still be selected
       and copied by hand. */
    var cantCopy = "Couldn't copy it: select the command above and copy it by hand.";
    if (!navigator.clipboard) {
      markError(copied);
      copied.textContent = cantCopy;
      return;
    }
    navigator.clipboard.writeText(command).then(function () {
      markOk(copied);
      copied.textContent = "Copied.";
    }, function () {
      markError(copied);
      copied.textContent = cantCopy;
    });
  });
}

/* Copy the open log, unchanged, into evidence/ under a name the user types
   (POST /evidence). The server checks the name and never overwrites. */
function showEvidenceCopy(path) {
  main.appendChild(element("h3", "Copy into evidence/"));
  markWarning(main.appendChild(element("p", "The whole log is copied as it is saved, control codes " +
    "included. Logs can hold secrets such as passwords and keys: redact them before " +
    "any of it goes into a report.")));
  var name = element("input");
  name.type = "text";
  addField(main, "File name (letters, digits, . _ - only)", name);
  var copy = element("button", "Copy");
  copy.type = "button";
  main.appendChild(element("div")).appendChild(copy);
  var status = main.appendChild(element("div"));
  status.className = "message";

  copy.addEventListener("click", function () {
    /* Locked until the answer, so one click makes at most one copy. */
    copy.disabled = true;
    status.textContent = "";
    function notCopied(text) {
      /* The name stays in its box, so the user can correct it. */
      copy.disabled = false;
      markError(status);
      status.appendChild(element("p", text));
    }
    fetch("/evidence", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},
      body: JSON.stringify({path: path, name: name.value})
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(notCopied);
      }
      return response.json().then(function (result) {
        copy.disabled = false;
        markOk(status);
        status.appendChild(element("p", "Copied to " + result.path));
        /* The answer always carries the redact reminder, so a copy is
           amber, like any done block holding a warning (LOOK-02). */
        markWarning(status);
        status.appendChild(element("p", result.warning));
      });
    }).catch(function (error) {
      notCopied("Not copied: " + error);
    });
  });
}

/* The box for one marker that isn't a NOTE (Fill-in "What each marker
   becomes"); field.control comes from the server's marker_controls(). */
function markerBox(field) {
  if (field.control === "dropdown") {
    var list = element("select");
    /* An empty first choice, so an untouched dropdown leaves its marker in place. */
    var none = list.appendChild(element("option", "(not chosen)"));
    none.value = "";
    field.options.forEach(function (text) {
      var option = list.appendChild(element("option", text));
      option.value = text;
    });
    return list;
  }
  if (field.control === "textarea") {
    var big = element("textarea");
    big.rows = 4;
    big.cols = 60;
    return big;
  }
  var line = element("input");
  line.type = "text";
  return line;
}

/* Milliseconds after the last keystroke before the file autosaves (Fill-in textarea). */
var AUTOSAVE_DELAY = 2000;

/* The open file's {leave, holdsUnsaved}, or null (showFillIn()). Every
   move to another view goes through its leave(), so box values not saved
   get a warning and the file's unsaved text is saved first. */
var openView = null;

/* Show another view with next(), once the open file lets the page go. */
function goTo(next) {
  if (openView === null) {
    next();
    return;
  }
  openView.leave(function () {
    openView = null;
    next();
  });
}

/* Closing the tab, reloading or going to another site warns while boxes
   hold values (Fill-in textarea), or while the file's text can't be saved
   (DECISIONS 2026-10-29 N5 L6). Text that is only waiting for its autosave
   doesn't warn. The browser shows its own wording. */
window.addEventListener("beforeunload", function (event) {
  if (openView !== null && openView.holdsUnsaved()) {
    event.preventDefault();
    event.returnValue = "";
  }
});

/* The fill-in view: a box for every marker still in the file, in the order
   they appear, then the whole file in a textarea. The file's text only ever
   goes in through .value and every label, guidance and note through
   textContent, so "<script>" in a file shows as text and never runs.
   data is GET /file's answer. unsaved is text kept from before a Reload
   (N5 F1), shown in a read-only box of its own. */
function showFillIn(data, unsaved) {
  /* The text the next save starts from (Chunk N4 D4). The text as sent,
     not the textarea's .value: a browser turns "\\r\\n" into "\\n" there, so
     a Windows file would never match. */
  var base = data.text;
  /* Every field with its box; a NOTE has none. */
  var entries = [];
  /* The autosave waiting for typing to stop, if any. */
  var timer = null;
  /* True while a save is on its way: one at a time, so each starts from
     the base the one before it left. */
  var busy = false;
  /* Set by a "changed on disk" answer (N5 F1), or by leaving this view
     (Chunk N5 CR-1): no more autosaves. */
  var stopped = false;
  /* True while messages shows why a save failed. */
  var failureShown = false;
  /* False from a keystroke until a save of exactly that text works. */
  var textSaved = true;
  /* Runs once the save on its way has answered, e.g. to finish leaving. */
  var afterSave = null;
  /* True when the last Save came back with warnings, so leaving waits. */
  var warningsShown = false;
  var view = {leave: leave, holdsUnsaved: holdsUnsaved};
  openView = view;

  main.textContent = "";
  main.appendChild(element("h2", data.path));
  var statusLine = main.appendChild(element("p"));
  statusLine.className = "message";
  /* After a Save: that it saved, then each warning from the server (N5 F3),
     which starts with its box's name. Or why a save failed. */
  var messages = main.appendChild(element("div"));
  messages.className = "message";
  /* Why the page stays on this file, with a way to leave anyway. */
  var leaveRow = main.appendChild(element("div"));
  /* Only ever "this file's text isn't saved". */
  markError(leaveRow);
  if (unsaved !== undefined) {
    showUnsaved(unsaved);
  }
  var boxes = main.appendChild(element("form"));
  var save = element("button", "Save");
  save.type = "button";
  /* The "unsaved" indicator beside Save, shown while boxes hold values. */
  var unsavedMark = element("span", "");
  var fileText = element("textarea");
  fileText.rows = 30;
  fileText.cols = 100;
  fileText.value = data.text;
  addField(main, "The file", fileText);
  /* "saved at HH:MM:SS", or "not saved yet" after typing. */
  var savedLine = main.appendChild(element("p", ""));
  savedLine.className = "message";
  showBoxes(data);

  /* The status line and a box per marker, from a GET or a save's answer. */
  function showBoxes(answer) {
    statusLine.textContent = answer.status;
    boxes.textContent = "";
    entries = [];
    answer.fields.forEach(function (field) {
      if (field.control === "note") {
        /* Highlighted help, never a box: the writer deletes the note in the
           file below. A <pre>, so a note's example keeps its lines. */
        boxes.appendChild(element("pre")).appendChild(element("mark", "NOTE:" + field.body));
        entries.push({field: field, box: null});
        return;
      }
      var box = markerBox(field);
      entries.push({field: field, box: box});
      var row = addField(boxes, field.name, box);
      if (field.guidance !== undefined) {
        row.appendChild(element("p", field.guidance));
      }
    });
    var saveRow = boxes.appendChild(element("div"));
    saveRow.appendChild(save);
    saveRow.appendChild(unsavedMark);
    showUnsavedMark();
  }

  /* Lock or unlock every box, e.g. for a Save: its answer rebuilds them,
     so a value typed while it's on its way would be lost. */
  function lockBoxes(locked) {
    entries.forEach(function (entry) {
      if (entry.box !== null) {
        entry.box.disabled = locked;
      }
    });
  }

  /* A box value is unsaved until a Save puts it in the file and rebuilds
     the boxes empty; emptying a box again leaves nothing to save. */
  function showUnsavedMark() {
    unsavedMark.textContent = boxesHoldValues() ? " unsaved" : "";
  }

  /* True if any box holds a value. A Save puts them in the file and
     rebuilds the boxes empty, so a value in a box is not saved yet. */
  function boxesHoldValues() {
    return entries.some(function (entry) {
      return entry.box !== null && entry.box.value !== "";
    });
  }

  /* What a Reload would lose: the textarea's text, then each box value
     (not saved yet, since a Save empties the boxes), one line each, e.g.
     "HOST: dc01" (DECISIONS 2026-10-29 N5 F1d). */
  function unsavedText() {
    var text = fileText.value;
    entries.forEach(function (entry) {
      if (entry.box !== null && entry.box.value !== "") {
        /* Each value starts on a line of its own. */
        if (text !== "" && text.slice(-1) !== "\\n") {
          text += "\\n";
        }
        text += entry.field.name + ": " + entry.box.value + "\\n";
      }
    });
    return text;
  }

  /* The text from before a Reload, read-only, with a Copy button (N5 F1). */
  function showUnsaved(text) {
    var kept = element("textarea");
    kept.rows = 10;
    kept.cols = 100;
    kept.readOnly = true;
    kept.value = text;
    var row = addField(main, "Your unsaved text", kept);
    var copy = row.appendChild(element("button", "Copy"));
    copy.type = "button";
    var copied = row.appendChild(element("span", ""));
    copy.addEventListener("click", function () {
      navigator.clipboard.writeText(text).then(function () {
        copied.textContent = " Copied.";
      }, function (error) {
        copied.textContent = " Not copied (" + error + "): select the text and copy it by hand.";
      });
    });
  }

  /* After "changed on disk": stop autosaving and offer Reload. Reload
     shows the file as it is now and keeps this textarea's text (N5 F1). */
  function offerReload() {
    stopped = true;
    clearTimeout(timer);
    timer = null;
    var reload = messages.appendChild(element("button", "Reload"));
    reload.type = "button";
    reload.addEventListener("click", function () {
      var mine = unsavedText();
      fetch("/file?path=" + encodeURIComponent(data.path)).then(function (response) {
        if (response.ok) {
          return response.json().then(function (fresh) {
            /* Only if this view is still the one open: the user may have
               left it while the Reload was on its way (N4-09 round 3). */
            if (openView === view) {
              showFillIn(fresh, mine);
            }
          });
        }
        /* Not reloaded: the view stays, so the text is still here. */
        return response.text().then(function (text) {
          messages.appendChild(element("p", "Not reloaded: " + text));
        });
      }).catch(function (error) {
        messages.appendChild(element("p", "Not reloaded: " + error));
      });
    });
  }

  /* What the close-tab warning covers: box values, or text that can't be
     saved after a refusal, until a save works or Reload (N5 L6). */
  function holdsUnsaved() {
    return boxesHoldValues() || (!textSaved && (stopped || failureShown));
  }

  /* Leaving for another view (goTo()). A save on its way is waited for
     first: its answer decides whether the boxes still hold values, and a
     Save's warnings keep the page here so they are seen; the next click
     leaves (Chunk N5 CR-2). Then box values not saved get the one warning;
     staying keeps everything as it is, and leaving doesn't put them in the
     file. Then the text is saved (leaveText()). */
  function leave(next) {
    if (busy) {
      afterSave = function () {
        if (!warningsShown) {
          leave(next);
        }
      };
      return;
    }
    if (boxesHoldValues() && !window.confirm("Your box values aren't saved and will be lost. Leave anyway?")) {
      return;
    }
    leaveText(next);
  }

  /* Leave for good: this view sends nothing more, e.g. no autosave of
     text typed after its leave row showed (Chunk N5 CR-1). */
  function quit(next) {
    stopped = true;
    clearTimeout(timer);
    timer = null;
    next();
  }

  /* Unsaved text is saved first and the page moves on only once that
     works. Otherwise it stays here, where the text and the reason (and
     Reload, for "changed on disk") can be seen. No save is on its way
     here: leave() waited for it. */
  function leaveText(next) {
    clearTimeout(timer);
    timer = null;
    if (textSaved) {
      quit(next);
      return;
    }
    if (stopped || failureShown) {
      offerLeave(next);
      return;
    }
    afterSave = function () {
      leaveText(next);
    };
    post([], function () {}, function () {});
  }

  /* The text can't be saved: say so, and let the user leave anyway. */
  function offerLeave(next) {
    leaveRow.textContent = "";
    leaveRow.appendChild(element("p", "This file's text isn't saved, so the page stays here."));
    var away = leaveRow.appendChild(element("button", "Leave without saving"));
    away.type = "button";
    away.addEventListener("click", function () {
      quit(next);
    });
  }

  /* Run what was waiting for the save on its way, if anything. */
  function runAfterSave() {
    var waiting = afterSave;
    afterSave = null;
    if (waiting !== null) {
      waiting();
    }
  }

  /* POST one save of the textarea's text with these fields. saved(result,
     sent) runs after a save, failed() after a refusal. */
  function post(fields, saved, failed) {
    var sent = fileText.value;
    warningsShown = false;
    busy = true;
    save.disabled = true;
    function done() {
      busy = false;
      save.disabled = false;
    }
    function notSaved(status, text) {
      /* The boxes keep their values and base stays, so the user can retry. */
      done();
      failed();
      messages.textContent = "";
      markError(messages);
      messages.appendChild(element("p", "Not saved: " + text));
      failureShown = true;
      if (status === 409) {
        offerReload();
      }
      runAfterSave();
    }
    fetch("/file", {
      method: "POST",
      headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},
      body: JSON.stringify({path: data.path, text: sent, base: base, fields: fields})
    }).then(function (response) {
      if (!response.ok) {
        return response.text().then(function (text) {
          notSaved(response.status, text);
        });
      }
      return response.json().then(function (result) {
        done();
        /* The saved text is the next base. */
        base = result.text;
        /* Only if nothing was typed since: newer typing has its own autosave coming. */
        if (fileText.value === sent) {
          markOk(savedLine);
          savedLine.textContent = "saved at " + new Date().toTimeString().slice(0, 8);
          textSaved = true;
          leaveRow.textContent = "";
        }
        saved(result, sent);
        runAfterSave();
      });
    }).catch(function (error) {
      notSaved(0, "" + error);
    });
  }

  /* Autosave: the textarea's text alone, no box values (fields []). */
  function autosave() {
    timer = null;
    if (stopped) {
      return;
    }
    if (busy) {
      timer = setTimeout(autosave, AUTOSAVE_DELAY);
      return;
    }
    post([], function (result) {
      /* An old failure is no longer true once a save works. */
      if (failureShown) {
        messages.textContent = "";
        failureShown = false;
      }
      /* The boxes are rebuilt from the rescan only while none holds a
         value, so an autosave never wipes what the user typed in them. */
      if (!boxesHoldValues()) {
        showBoxes(result);
      }
    }, function () {});
  }

  /* Typing in a box, or picking from a dropdown. */
  boxes.addEventListener("input", showUnsavedMark);
  boxes.addEventListener("change", showUnsavedMark);

  fileText.addEventListener("input", function () {
    /* Not an error: an autosave is on its way. */
    savedLine.className = "message";
    savedLine.textContent = "not saved yet";
    textSaved = false;
    if (stopped) {
      return;
    }
    clearTimeout(timer);
    timer = setTimeout(autosave, AUTOSAVE_DELAY);
  });

  save.addEventListener("click", function () {
    /* This save sends the textarea's text too, so no autosave is needed. */
    clearTimeout(timer);
    timer = null;
    /* Every field in the scan's order, notes too, so the server can match
       repeated markers by position (marker_targets()). */
    var fields = entries.map(function (entry) {
      return {name: entry.field.name, marker: entry.field.marker, body: entry.field.body,
              value: entry.box ? entry.box.value : ""};
    });
    /* Read-only and locked until the answer, so nothing typed in the file
       or the boxes meanwhile is lost when the saved text replaces them. */
    fileText.readOnly = true;
    lockBoxes(true);
    post(fields, function (result) {
      fileText.value = result.text;
      fileText.readOnly = false;
      showBoxes(result);
      messages.textContent = "";
      failureShown = false;
      markOk(messages);
      messages.appendChild(element("p", "Saved."));
      /* A <pre>, so a value quoted in a warning keeps its lines and
         spaces when copied back (N5 F3b). */
      result.warnings.forEach(function (warning) {
        messages.appendChild(element("pre", "Warning: " + warning));
      });
      warningsShown = result.warnings.length > 0;
      /* Saved, but with warnings to read: amber, not green (LOOK-02). */
      if (warningsShown) {
        markWarning(messages);
      }
    }, function () {
      fileText.readOnly = false;
      lockBoxes(false);
    });
  });
}

document.getElementById("new-button").addEventListener("click", function () {
  goTo(function () {
    getJson("/new-data", showNewForm);
  });
});

document.getElementById("checklists-button").addEventListener("click", function () {
  goTo(function () {
    getJson("/checklists", showChecklistList);
  });
});

document.getElementById("logs-button").addEventListener("click", function () {
  goTo(function () {
    getJson("/logs", showLogList);
  });
});

document.getElementById("export-button").addEventListener("click", function () {
  goTo(showExport);
});

loadFiles();
</script>
</body>
</html>
"""

# The app's routes: path -> function(handler). The feature tasks add the rest.
# GET routes must never change anything (Constraint 8).
GET_ROUTES = {"/": send_page,
              "/checklists": send_checklist_list,
              "/checklist": send_checklist,
              "/checklist-view": send_checklist_view,
              "/files": send_own_files,
              "/new-data": send_new_data,
              "/file": send_editable_file,
              "/logs": send_log_list,
              "/log": send_log}
POST_ROUTES = {"/checklist-state": save_tick,
               "/new-file": save_new_file,
               "/file": save_file,
               "/export": save_export,
               "/evidence": save_evidence}


class NotebookHandler(BaseHTTPRequestHandler):
    """Answers each request; the server must have a `token` attribute."""

    # Seconds a connection may wait for more of its request. The server
    # answers one request at a time, so a body shorter than its
    # Content-Length would otherwise hold it forever. Short, because an idle
    # connection a browser opens early holds every other request this long
    # (DECISIONS 2026-10-29 N5 F2).
    timeout = 2

    def do_GET(self):
        self.answer("GET", GET_ROUTES)

    def do_POST(self):
        self.answer("POST", POST_ROUTES)

    def answer(self, method, routes):
        """Refuse a bad request before any route runs, else run its route."""
        # One request per connection, whatever protocol_version says. A refused
        # request's body is never read, so on a kept-open connection the
        # server would read it as a second request, which could pass the guard.
        self.close_connection = True
        port = self.server.server_address[1]
        refusal = request_refusal(method, self.headers, port, self.server.token)
        if refusal is not None:
            # Nothing has been read or changed yet, so a refused POST changes nothing.
            send_text(self, 403, refusal)
            return
        # Routes are found by the path alone; a route reads its own ?query.
        route = routes.get(urlsplit(self.path).path)
        if route is None:
            send_text(self, 404, "not found: " + self.path)
            return
        route(self)

    def send_error(self, code, message=None, explain=None):
        # The stdlib sends its own errors (e.g. 501 for a method other than
        # GET and POST, 431 for too many headers) as an HTML page without the
        # safety headers; send them as text instead.
        # Limit: for a request line it can't parse, the stdlib sends no status
        # line or headers at all (old HTTP/0.9 style), only this text.
        # Close the connection, as the stdlib's own version does: the body was
        # never read, and must not be read as a second request (see answer()).
        self.close_connection = True
        send_text(self, code, message or self.responses.get(code, ("error",))[0])

    def log_message(self, format, *args):
        """Don't print a line for every request; the terminal stays readable."""


def parse_args(argv=None):
    """Read the command-line options. argv=None means use sys.argv."""
    parser = argparse.ArgumentParser(
        description="A local notebook for checklists, field notes and templates.",
    )
    # Required, so every file the notebook makes lands in the right person's
    # field-notes/<name>/ folder instead of a guessed one. It is slugged like
    # a title, so it can only ever be one plain folder name.
    parser.add_argument("--name", required=True, type=name_option,
                        help="your name, e.g. alice")
    parser.add_argument(
        "--root",
        type=compile.expand_path,
        # The working copy, never the current folder, for the same reason as
        # compile.py: running from the repo clone must not write into it.
        default=Path("~/cptc-work").expanduser(),
        help="the working copy to work in (default: ~/cptc-work)",
    )
    parser.add_argument("--port", type=port_option, default=8765,
                        help="the port to listen on (default: 8765)")
    # There is deliberately no option for the address: the page is only ever
    # served on 127.0.0.1, so no setting can open it to the network.
    return parser.parse_args(argv)


def port_option(text):
    """Turn --port into a number from 1 to 65535, the range a port can be."""
    # isascii() too, because isdigit() also accepts other scripts' digits.
    if not (text.isascii() and text.isdigit()) or not 1 <= int(text) <= 65535:
        # argparse shows this message with its usage line, instead of a traceback.
        raise argparse.ArgumentTypeError("the port must be a number from 1 to 65535: " + repr(text))
    return int(text)


def log_dir():
    """Return the terminal log folder: $LOGDIR, or ~/cptc-logs if it isn't set."""
    # Same rule as scripts/logged-shell.sh (${LOGDIR:-$HOME/cptc-logs}), so the
    # notebook reads the folder the logs were written to; an empty value
    # counts as unset there too.
    return compile.expand_path(os.environ.get("LOGDIR") or "~/cptc-logs")


def load_settings(argv=None):
    """Return the startup settings as a dict, or raise compile.RootError.

    The keys are name, root (resolved), port and logdir.
    """
    args = parse_args(argv)
    return {
        "name": args.name,
        # Checked before the server exists, so a refused root (e.g. the git
        # clone) is never served from or written to.
        "root": compile.validate_root(args.root),
        "port": args.port,
        "logdir": log_dir(),
    }


def make_server(settings):
    """Return the server, listening on 127.0.0.1 only, with a new token for this run."""
    # The literal address, never "" or "0.0.0.0" (every network interface) or
    # "localhost" (a name the system looks up, which may not be 127.0.0.1), so
    # other boxes on the network can't reach the notebook (Constraint 2).
    server = HTTPServer(("127.0.0.1", settings["port"]), NotebookHandler)
    server.token = make_token()
    # For the routes the feature tasks add: they reach these as handler.server.settings.
    server.settings = settings
    return server


def main(argv=None):
    """Run from the command line and return the exit code."""
    try:
        settings = load_settings(argv)
    except compile.RootError as error:
        # A readable line instead of a traceback, with compile.py's exit code
        # for "couldn't run".
        print("notebook failed: " + str(error))
        return 2
    try:
        server = make_server(settings)
    except OSError as error:
        # Usually the port is already in use, e.g. by a second notebook.
        print("notebook failed: can't listen on 127.0.0.1:" + str(settings["port"])
              + ": " + str(error))
        return 2
    print("Notebook: http://127.0.0.1:" + str(server.server_address[1]))
    print("Local only: it listens on 127.0.0.1, so only this box can open it. Ctrl+C stops it.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl+C is the normal way to stop it, so no traceback.
        print("Notebook stopped.")
    finally:
        server.server_close()
    return 0


# Only runs when started as `python3 tools/notebook.py`, never on import, so
# the tests can import this file without side effects.
if __name__ == "__main__":
    sys.exit(main())
