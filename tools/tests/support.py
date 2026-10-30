"""Shared helpers for the tools/ tests.

Test files start with `import support` so the code under test can be imported.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# The tools live in tools/, one folder above this file. `unittest discover`
# only puts tools/tests/ on the import path, so without this line
# `import compile` would fail. Adding tools/ here means the tests need no
# tools/tests/__init__.py and no install step.
TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

# Tests write only here, never to /tmp or the OS temp folder, so nothing
# lands outside the repo. .gitignore excludes it, so nothing is committed.
TMP_DIR = Path(__file__).resolve().parent / ".tmp"


def make_worktree(test, files=None):
    """Create a fake working copy for one test and return its root folder.

    `files` maps a relative path (e.g. "findings/F-001-x.md") to its text.
    The folder is removed when the test finishes, pass or fail.
    """
    TMP_DIR.mkdir(exist_ok=True)
    # mkdtemp picks a fresh name, so two tests never share or clash on a folder.
    # It never creates a .git folder, so the root passes the tools' .git check.
    root = Path(tempfile.mkdtemp(prefix="worktree-", dir=str(TMP_DIR)))
    test.addCleanup(remove_worktree, root)
    for relative_path, text in (files or {}).items():
        write_fake_file(root, relative_path, text)
    return root


def write_fake_file(root, relative_path, text):
    """Write one fake file under root, creating its folders."""
    path = (root / relative_path).resolve()
    # A typo such as "../x" must not let a test write outside its own folder.
    if root.resolve() not in path.parents:
        raise ValueError("fake file escapes the worktree: " + relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# templates/finding.md filled in by hand, so tests have one finding that should
# pass every check. Same sections and labels as the template, every marker
# replaced and every NOTE deleted. The Attack chain section is removed, as the
# template says to for a standalone finding: one default finding has no
# neighbours to link, and a chain naming made-up IDs would make the duplicate
# and index checks report findings that don't exist.
# Only {finding_id} and {title} are filled by .format(), so any literal brace
# added later must be doubled.
COMPLETE_FINDING = """\
### {finding_id}: {title}

- **Severity:** Critical
- **CVSS 3.1:** `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H` (9.8)
- **Why this severity:** We logged in to the admin portal over the network with the vendor default password and could change any account.
- **Likelihood:** Anyone on the guest network can reach the login page, and the default password is published in the vendor manual.
- **Affected assets:** web01 (10.0.0.1), http://10.0.0.1/login, admin
- **Discovered by / when:** alice, 2026-11-07 10:15
- **Status:** Exploited
- **References:** CWE-1392, ATT&CK T1078.001, https://example.invalid/advisories/default-credentials

#### Summary
The client-example admin portal still accepts the password it shipped with. Anyone who knows that password can take full control of the portal and every account in it.

#### Business impact
An outsider on the guest network could lock staff out of the portal, change prices and read customer details.

#### Technical detail
The portal's built-in admin account was never given a new password after installation, and the login page allows unlimited attempts.

#### Reproduction steps
Starting position: Unauthenticated, on the client-example guest network, with no credentials.

1. `curl -i http://10.0.0.1/login`
   Expected: HTTP/1.1 200 OK and the admin portal login form
2. `curl -i -c cookies.txt -d 'user=admin&pass=admin' http://10.0.0.1/login`
   Expected: HTTP/1.1 302 Found redirecting to /admin, with a session cookie saved
3. `curl -i -b cookies.txt http://10.0.0.1/admin`
   Expected: HTTP/1.1 200 OK and the admin dashboard listing all accounts

#### Evidence
- `evidence/{finding_id}-01.png`: the admin dashboard after logging in as admin
- Log excerpt (timestamps included):

```
2026-11-07 10:14:52 POST /login user=admin -> 302 Found
2026-11-07 10:14:53 GET /admin -> 200 OK
```

#### Remediation
- **Immediate:** Set a new, unique password on the admin account.
- **Longer term:** Require every installed product's default passwords to be changed before it goes live.
- **How to verify the fix:** Repeat step 2 and confirm the login is refused.
"""


def make_complete_finding(finding_id="F-001", title="Default admin password on web01"):
    """Return the text of a fully filled-in fake finding."""
    return COMPLETE_FINDING.format(finding_id=finding_id, title=title)


# A short fake findings-library entry, shaped like templates/finding.md: the
# general text is written, but the event-specific fields are still markers,
# as findings-library/README.md describes. Only {title}, {severity} and
# {technical_detail} are filled by .format().
LIBRARY_ENTRY = """\
### [[FINDING_ID]]: {title}

[[NOTE: Library text is general. Check every section against the real finding.]]

- **Severity:** {severity}
- **CVSS 3.1:** `[[CVSS_VECTOR]]` ([[CVSS_SCORE]])
- **Why this severity:** [[SEVERITY_RATIONALE]]
- **Likelihood:** [[LIKELIHOOD]]
- **Affected assets:** [[HOST]] ([[HOST_IP]]), [[ACCOUNT]]
- **Discovered by / when:** [[TESTER]], [[DATE]] [[TIME]]
- **Status:** [[CHOOSE: Confirmed / Exploited / Suspected]]
- **References:** CWE-[[CWE_ID]], https://example.invalid/library/example-entry

#### Summary
An example service on a fake host accepts an unsafe example setting, so an attacker could misuse it.

#### Technical detail
{technical_detail}

#### Reproduction steps
Starting position: [[STARTING_POSITION]]

[[REPRODUCTION_STEPS]]

#### Remediation
- **Immediate:** [[IMMEDIATE_FIX]]
- **Longer term:** Review the example setting on every host before it goes live.
"""


def make_library_entry(title="Example unsafe service setting", severity="High",
                       technical_detail="The example setting is on by default."):
    """Return the text of a fake findings-library entry."""
    return LIBRARY_ENTRY.format(title=title, severity=severity,
                                technical_detail=technical_detail)


# A fake terminal transcript, shaped like what scripts/logged-shell.sh saves
# with util-linux `script`, holding every control-code case the log viewer's
# cleaner must handle (BUILD-SPEC Logs). Logs can hold hostile HTML because
# we attack things, so the curl answer carries a <script> tag (Constraint 9).
# Kept here as text, not a committed .log file: .gitignore excludes *.log, and
# the bytes must be exact, which a text editor could quietly change.
HOSTILE_LOG = (
    # `script`'s own header and footer end in a plain LF.
    'Script started on 2026-11-07 10:15:00+00:00 [COMMAND="/bin/bash --rcfile fake-rc"]\n'
    # OSC window title ended by BEL, a `?` private-mode CSI, then the prompt.
    # A typo fixed with Backspace echoes BS then CSI "erase line" (ESC [ K),
    # so the code must be stripped before the backspace is applied.
    "\x1b]0;alice@kali: ~\x07\x1b[?2004h"
    "[2026-11-07 10:15:09 UTC] alice@kali:~$ curl -i http://10.0.0.1/inn\x08\x1b[Kdex.html\r\n"
    # A Windows-style answer reaches the transcript as CR CR LF; the empty
    # line between headers and body is one too.
    "HTTP/1.1 200 OK\r\r\n"
    "Server: fake-iis\r\r\n"
    "\r\r\n"
    '<script>alert("fake-xss")</script>\r\n'
    "[2026-11-07 10:15:30 UTC] alice@kali:~$ ./fake-download.sh\r\n"
    # A progress bar redrawn twice with lone CRs: only the last part stays.
    "fake-dl  10%\rfake-dl  55%\rfake-dl 100%\r\n"
    # Two-character escapes (ESC ( B, ESC ) 0, ESC =, ESC >), SGR colour
    # codes, and a CSI with an intermediate byte (ESC [ 0 space q).
    "\x1b(B\x1b)0\x1b=\x1b[01;31mERROR\x1b[0m: fake failure\x1b>\x1b[0 q\r\n"
    # An OSC 8 link ended by ESC backslash instead of BEL.
    "see \x1b]8;;http://10.0.0.1/\x1b\\the fake link\x1b]8;;\x1b\\ for details\r\n"
    "[2026-11-07 10:16:40 UTC] alice@kali:~$ exit\r\n"
    "exit\r\n"
    'Script done on 2026-11-07 10:16:40+00:00 [COMMAND_EXIT_CODE="0"]\n'
)

# HOSTILE_LOG after the spec's four cleaning steps, worked out by hand.
# NT6-01 checks the cleaner against it.
HOSTILE_LOG_CLEANED = (
    'Script started on 2026-11-07 10:15:00+00:00 [COMMAND="/bin/bash --rcfile fake-rc"]\n'
    "[2026-11-07 10:15:09 UTC] alice@kali:~$ curl -i http://10.0.0.1/index.html\n"
    "HTTP/1.1 200 OK\n"
    "Server: fake-iis\n"
    "\n"
    '<script>alert("fake-xss")</script>\n'
    "[2026-11-07 10:15:30 UTC] alice@kali:~$ ./fake-download.sh\n"
    "fake-dl 100%\n"
    "ERROR: fake failure\n"
    "see the fake link for details\n"
    "[2026-11-07 10:16:40 UTC] alice@kali:~$ exit\n"
    "exit\n"
    'Script done on 2026-11-07 10:16:40+00:00 [COMMAND_EXIT_CODE="0"]\n'
)

# The matching command index, in logged-shell.sh's line format:
# time (exit code) [directory] command. The cleaned transcript can mangle
# commands, so the viewer shows these exact lines beside it.
HOSTILE_CMDS = (
    "2026-11-07 10:15:12 UTC (exit 0) [/home/alice] curl -i http://10.0.0.1/index.html\n"
    "2026-11-07 10:16:38 UTC (exit 1) [/home/alice] ./fake-download.sh\n"
)


def make_hostile_logs(logdir, base="alice_20261107T101500Z", mtime=None):
    """Write HOSTILE_LOG and HOSTILE_CMDS into logdir as <base>.log and
    <base>.cmds.log, and return both paths.

    logdir must be inside tests/.tmp/ (e.g. a make_worktree() folder, so the
    logs are removed with it); it is created if needed. `mtime` (seconds)
    sets both files' modified time, so list tests can order several logs.
    """
    logdir = Path(logdir)
    # Like write_fake_file(): a wrong argument must not write outside .tmp/.
    if TMP_DIR.resolve() not in logdir.resolve().parents:
        raise ValueError("fake log folder is outside tests/.tmp: " + str(logdir))
    logdir.mkdir(parents=True, exist_ok=True)
    log_path = logdir / (base + ".log")
    cmds_path = logdir / (base + ".cmds.log")
    # Check both names before writing either, so a base such as "../x" or an
    # absolute path writes nothing at all.
    for path in (log_path, cmds_path):
        if path.resolve().parent != logdir.resolve():
            raise ValueError("fake log name leaves the log folder: " + base)
    for path, text in ((log_path, HOSTILE_LOG), (cmds_path, HOSTILE_CMDS)):
        # Bytes, so no newline translation touches the CRs. "xb" refuses an
        # existing file, so two calls with the same base fail loudly instead
        # of one silently replacing the other's log.
        with path.open("xb") as handle:
            handle.write(text.encode("utf-8"))
        if mtime is not None:
            os.utime(str(path), (mtime, mtime))
    return log_path, cmds_path


def remove_worktree(root):
    """Delete one test's folder, and refuse anything else.

    Deleting is allowed only for the tests' own folders inside .tmp/, so check
    the folder really sits directly in .tmp/ before removing it.
    """
    if root.resolve().parent != TMP_DIR.resolve():
        raise ValueError("refusing to delete a folder outside tests/.tmp: " + str(root))
    # rmtree removes a symlink itself and never follows it, so a test link
    # such as incoming/alice -> another folder can't make cleanup delete
    # anything outside this folder.
    shutil.rmtree(str(root))
