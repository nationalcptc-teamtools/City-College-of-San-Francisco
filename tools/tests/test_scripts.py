"""Tests for the team Bash scripts in scripts/.

Each test runs a script with bash in a fake HOME under tests/.tmp/. PATH holds
only a stub folder: fake ssh, ssh-keygen, ssh-copy-id, rsync and git that
record their arguments (the make-workcopy tests' fake git clone also copies a
fake repo from the fake HOME), plus links to the few real commands the
scripts need (bash itself is the real one, run by its path). So no test
reaches the network or a real ~/.ssh, and every file a test writes is inside
the repo.
"""

import support  # sets up tests/.tmp/, so it must come first

import os
import re
import shutil
import subprocess
import unittest

SCRIPTS_DIR = support.TOOLS_DIR.parent / "scripts"
PULL = SCRIPTS_DIR / "pull.sh"
MAKE_WORKCOPY = SCRIPTS_DIR / "make-workcopy.sh"
LOGGED_SHELL = SCRIPTS_DIR / "logged-shell.sh"
# Found once on the real PATH, before any test swaps PATH for the stub folder.
BASH = shutil.which("bash")

# The network and git commands the scripts may call. Each stub appends one
# line to calls.log in the fake HOME and exits 0. The line is the command name
# then each argument in brackets, so an empty argument (-N "") shows as [].
STUBBED_COMMANDS = ["ssh", "ssh-keygen", "ssh-copy-id", "rsync", "git"]
STUB = """#!/bin/sh
line="${0##*/}"
for arg in "$@"; do line="$line [$arg]"; done
printf '%s\\n' "$line" >> "$HOME/calls.log"
"""
# Real commands pull.sh is allowed to use. Anything not listed here or
# stubbed is "command not found", so a test also fails if a script starts
# calling something new. make-workcopy.sh needs two more (MakeWorkcopyTests).
REAL_COMMANDS = ["cat", "mkdir", "mktemp", "mv"]
WORKCOPY_REAL_COMMANDS = ["cp", "rm"]

TWO_TEAMMATES = "2\nalice\nkali\n10.0.0.5\nbob\nkali\n10.0.0.6\n"
TWO_TEAMMATES_FILE = "alice\tkali\t10.0.0.5\nbob\tkali\t10.0.0.6\n"


def make_stub_path(home):
    """Create home/bin with the stubs and real-command links; return it."""
    bin_dir = home / "bin"
    bin_dir.mkdir()
    for name in STUBBED_COMMANDS:
        stub = bin_dir / name
        stub.write_text(STUB, encoding="utf-8")
        stub.chmod(0o755)
    link_real_commands(bin_dir, REAL_COMMANDS)
    return bin_dir


def link_real_commands(bin_dir, names):
    for name in names:
        # A link only lets the script run the real command; nothing is
        # written outside the repo by making it.
        (bin_dir / name).symlink_to(shutil.which(name))


@unittest.skipIf(BASH is None, "bash is not installed")
class ScriptTestCase(unittest.TestCase):
    """Gives each test a fake HOME with ~/cptc-work and the stub PATH."""

    def setUp(self):
        self.home = support.make_worktree(self)
        self.bin_dir = make_stub_path(self.home)
        self.workdir = self.home / "cptc-work"
        self.workdir.mkdir()
        self.config = self.workdir / "teammates.txt"

    def run_script(self, script, args=(), answers="", locale=None, encoding="utf-8",
                   extra_env=None):
        # Only HOME and PATH are passed (plus LC_ALL or extra_env when a test
        # asks), so nothing from the real environment (a real HOME, SSH agent,
        # proxy) reaches the script.
        env = {"HOME": str(self.home), "PATH": str(self.bin_dir)}
        if locale:
            env["LC_ALL"] = locale
        env.update(extra_env or {})
        return subprocess.run(
            [BASH, str(script)] + list(args), input=answers, env=env,
            cwd=str(self.home), capture_output=True, encoding=encoding, timeout=20)

    def stub_calls(self):
        log = self.home / "calls.log"
        if not log.exists():
            return []
        # "replace": a test may pass a Latin-1 byte through a stub; it then
        # shows as a mismatch, not a decoding crash.
        return log.read_text(encoding="utf-8", errors="replace").splitlines()

    def workdir_names(self):
        return sorted(path.name for path in self.workdir.iterdir())

    def fail_stub(self, name, when):
        """Replace a stub with one that records its call, then fails if its
        arguments contain `when`."""
        stub = self.bin_dir / name
        stub.write_text(STUB + 'case "$*" in *' + when + '*) exit 1 ;; esac\n',
                        encoding="utf-8")


class PullSetupTests(ScriptTestCase):
    def test_setup_asks_each_question_once_and_writes_the_list(self):
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (
            "How many teammates will you pull from? "
            "Teammate 1 name: Teammate 1 login: Teammate 1 IP: "
            "Teammate 2 name: Teammate 2 login: Teammate 2 IP: "
            "Saved 2 teammate(s) to " + str(self.config) + "\n"
            "Creating the pull key " + str(self.home / ".ssh/cptc_ed25519") + "\n"
            "Copying the pull key to alice (kali@10.0.0.5). Type alice's password when asked.\n"
            "Copying the pull key to bob (kali@10.0.0.6). Type bob's password when asked.\n"
            "Setup done. Pulls can now log in without a password.\n"))
        self.assertEqual(self.config.read_bytes(), TWO_TEAMMATES_FILE.encode())
        # The list holds engagement IPs, so only its owner may read it.
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        # The temp file was renamed, not left behind.
        self.assertEqual(self.workdir_names(), ["teammates.txt"])
        # Setup makes the key and copies it, but never pulls or uses git.
        self.assertEqual([call.split()[0] for call in self.stub_calls()],
                         ["ssh-keygen", "ssh-copy-id", "ssh-copy-id"])

    def test_spaces_around_an_answer_are_dropped(self):
        result = self.run_script(PULL, ["--setup"], " 1 \n  alice \n kali\n10.0.0.5  \n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.config.read_bytes(), b"alice\tkali\t10.0.0.5\n")

    def test_no_working_copy_is_refused(self):
        self.workdir.rmdir()
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: no working copy at " + str(self.workdir)
                         + ". Create it first with make-workcopy.sh.\n")
        self.assertFalse(self.workdir.exists())

    def test_answers_running_out_stops_without_writing(self):
        result = self.run_script(PULL, ["--setup"], "1\nalice\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr,
                         'pull: setup stopped: no answer to "Teammate 1 login: "\n')
        self.assertEqual(self.workdir_names(), [])


class PullSetupRefusalTests(ScriptTestCase):
    """Each bad answer stops setup before anything is written."""

    def assert_refused(self, answers, message):
        result = self.run_script(PULL, ["--setup"], answers)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: " + message + "\n")
        self.assertEqual(self.workdir_names(), [])

    def test_unsafe_names_are_refused(self):
        # Each of these could leave incoming/<name>/ or confuse a later command.
        # One fresh fake HOME per name, so one case can't affect the next.
        for name in ["..", ".", "../x", "a/b", "/abs", "-rf", "Alice", "a b", "a\tb", "~x", ""]:
            with self.subTest(name=name):
                self.setUp()
                self.assert_refused(
                    "1\n" + name + "\nkali\n10.0.0.5\n",
                    'Name "' + name + '" is not allowed. Use lowercase letters, '
                    'digits and -, starting with a letter or digit.')

    def test_accented_letters_are_refused_in_a_latin1_locale(self):
        # In a Latin-1 locale "\xe9" is one byte that [a-z] matches, unless the
        # script pins LC_ALL=C. The answers are sent as Latin-1 bytes to match.
        # Where the locale isn't installed, bash may print a setlocale warning
        # first, so only the end of stderr is compared.
        cases = [
            ("1\ncaf\xe9\nkali\n10.0.0.5\n",
             'Name "caf\xe9" is not allowed. Use lowercase letters, '
             'digits and -, starting with a letter or digit.'),
            ("1\nalice\njos\xe9\n10.0.0.5\n",
             'Login "jos\xe9" is not allowed. Use the Linux login, e.g. kali.'),
        ]
        for answers, message in cases:
            with self.subTest(answers=answers):
                self.setUp()
                result = self.run_script(PULL, ["--setup"], answers,
                                         locale="en_US.ISO8859-1", encoding="latin-1")
                self.assertEqual(result.returncode, 1)
                self.assertTrue(result.stderr.endswith("pull: " + message + "\n"), result.stderr)
                self.assertEqual(self.workdir_names(), [])

    def test_accented_letters_are_refused_in_utf8(self):
        for answers in ["1\ncaf\xe9\nkali\n10.0.0.5\n", "1\nalice\njos\xe9\n10.0.0.5\n"]:
            with self.subTest(answers=answers):
                self.setUp()
                result = self.run_script(PULL, ["--setup"], answers)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(self.workdir_names(), [])

    def test_duplicate_name_is_refused(self):
        self.assert_refused("2\nalice\nkali\n10.0.0.5\nalice\n",
                            'name "alice" is already used by another teammate.')

    def test_bad_logins_are_refused(self):
        # "-oproxycommand" uses only allowed letters, so only the leading "-"
        # rule refuses it: ssh would read it as an option.
        for login in ["-oproxycommand", "-oProxyCommand=x", "root@x", "Kali", "a b", ""]:
            with self.subTest(login=login):
                self.setUp()
                self.assert_refused(
                    "1\nalice\n" + login + "\n10.0.0.5\n",
                    'Login "' + login + '" is not allowed. Use the Linux login, e.g. kali.')

    def test_bad_ips_are_refused(self):
        for ip in ["10.0.0", "10.0.0.5.6", "kali-box", "-oX", "10.0.0.5 x", ""]:
            with self.subTest(ip=ip):
                self.setUp()
                self.assert_refused(
                    "1\nalice\nkali\n" + ip + "\n",
                    'IP "' + ip + '" is not allowed. Use a dotted IPv4 address, e.g. 10.0.0.5.')

    def test_bad_counts_are_refused(self):
        for count in ["0", "two", "-1", "01", ""]:
            with self.subTest(count=count):
                self.setUp()
                self.assert_refused(
                    count + "\n",
                    'Teammate count "' + count + '" is not allowed. Type a whole number, 1 or more.')


class PullSetupRerunTests(ScriptTestCase):
    """--setup when teammates.txt already exists (SQ-08)."""
    OLD_FILE = b"carol\tkali\t10.0.0.9\ndave\tkali\t10.0.0.10\n"
    PROMPT = "Replace it? Type yes to replace it, or anything else to keep it and redo the key step: "

    def setUp(self):
        super().setUp()
        self.config.write_bytes(self.OLD_FILE)
        self.key = self.home / ".ssh" / "cptc_ed25519"

    def shown_list(self):
        return ("A teammate list already exists: " + str(self.config) + "\n"
                "carol\tkali\t10.0.0.9\ndave\tkali\t10.0.0.10\n" + self.PROMPT)

    def copy_id_call(self, login_at_ip):
        return "ssh-copy-id [-i] [" + str(self.key) + ".pub] [" + login_at_ip + "]"

    def test_anything_but_yes_keeps_the_list_and_redoes_the_key_step(self):
        # One teammate's key copy failed: rerun setup without retyping anyone.
        for reply in ["no", "", "YES", "y"]:
            with self.subTest(reply=reply):
                self.setUp()
                result = self.run_script(PULL, ["--setup"], reply + "\n")
                self.assertEqual(result.returncode, 0, result.stderr)
                # No teammate questions: the kept list is used as it is.
                self.assertEqual(result.stdout, (
                    self.shown_list() + "Kept " + str(self.config) + "\n"
                    "Creating the pull key " + str(self.key) + "\n"
                    "Copying the pull key to carol (kali@10.0.0.9). Type carol's password when asked.\n"
                    "Copying the pull key to dave (kali@10.0.0.10). Type dave's password when asked.\n"
                    "Setup done. Pulls can now log in without a password.\n"))
                self.assertEqual([call.split()[0] for call in self.stub_calls()],
                                 ["ssh-keygen", "ssh-copy-id", "ssh-copy-id"])
                self.assertEqual(self.stub_calls()[1:], [self.copy_id_call("kali@10.0.0.9"),
                                                         self.copy_id_call("kali@10.0.0.10")])
                self.assertEqual(self.config.read_bytes(), self.OLD_FILE)
                self.assertEqual(self.workdir_names(), ["teammates.txt"])

    def test_keeping_the_list_reuses_an_existing_key(self):
        self.key.parent.mkdir()
        self.key.write_bytes(b"fake private key\n")
        (self.key.parent / "cptc_ed25519.pub").write_bytes(b"fake public key\n")
        result = self.run_script(PULL, ["--setup"], "no\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls(), [self.copy_id_call("kali@10.0.0.9"),
                                             self.copy_id_call("kali@10.0.0.10")])

    def test_a_kept_last_line_without_a_newline_still_gets_the_key(self):
        # A hand-edited list can lose its final newline; check_list keeps that
        # line, so the key copy must reach that teammate too (Chunk S CR-1).
        self.config.write_bytes(self.OLD_FILE.rstrip(b"\n"))
        result = self.run_script(PULL, ["--setup"], "no\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls()[1:], [self.copy_id_call("kali@10.0.0.9"),
                                                 self.copy_id_call("kali@10.0.0.10")])

    def test_keeping_the_list_still_names_a_failed_copy(self):
        self.fail_stub("ssh-copy-id", "10.0.0.9")
        result = self.run_script(PULL, ["--setup"], "no\n")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.endswith(
            "pull: the key is not on: carol. Check their ssh server is running and the "
            "password is right, then run setup again and keep the list.\n"), result.stderr)
        self.assertEqual(self.config.read_bytes(), self.OLD_FILE)

    def test_a_bad_kept_list_stops_before_any_ssh(self):
        # Hand-edited since setup: each bad line is named, and nothing runs.
        cases = [
            (b"carol\tkali\t10.0.0.9\n../x\tkali\t10.0.0.10\n",
             'line 2: name "../x" is not allowed.'),
            (b"carol\tkali\t10.0.0.9\ncarol\tkali\t10.0.0.10\n",
             'line 2: name "carol" is already used by another teammate.'),
            (b"carol\t-oX\t10.0.0.9\n", 'line 1: login "-oX" is not allowed.'),
            (b"carol\tkali\t10.0.0\n", 'line 1: IP "10.0.0" is not allowed.'),
        ]
        for listed, message in cases:
            with self.subTest(message=message):
                self.setUp()
                self.config.write_bytes(listed)
                result = self.run_script(PULL, ["--setup"], "no\n")
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, "pull: " + str(self.config) + " " + message
                                 + " Fix it or run " + str(PULL) + " --setup again.\n")
                self.assertNotIn("Kept", result.stdout)
                self.assertEqual(self.stub_calls(), [])
                self.assertFalse(self.key.parent.exists())
                self.assertEqual(self.config.read_bytes(), listed)

    def test_yes_replaces_the_list_then_sets_up_the_new_teammates(self):
        result = self.run_script(PULL, ["--setup"], "yes\n" + TWO_TEAMMATES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith(
            self.shown_list() + "How many teammates will you pull from? "), result.stdout)
        self.assertEqual(self.config.read_bytes(), TWO_TEAMMATES_FILE.encode())
        self.assertEqual(self.stub_calls()[1:], [self.copy_id_call("kali@10.0.0.5"),
                                                 self.copy_id_call("kali@10.0.0.6")])
        self.assertEqual(self.workdir_names(), ["teammates.txt"])

    def test_rerun_with_a_bad_answer_keeps_the_old_list(self):
        result = self.run_script(PULL, ["--setup"], "yes\n1\n../x\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(self.config.read_bytes(), self.OLD_FILE)
        self.assertEqual(self.workdir_names(), ["teammates.txt"])
        self.assertEqual(self.stub_calls(), [])


class PullKeySetupTests(ScriptTestCase):
    """Setup's SSH steps: the pull key and one ssh-copy-id per teammate."""

    def setUp(self):
        super().setUp()
        self.ssh_dir = self.home / ".ssh"
        self.key = self.ssh_dir / "cptc_ed25519"

    def copy_id_call(self, login_at_ip):
        return "ssh-copy-id [-i] [" + str(self.key) + ".pub] [" + login_at_ip + "]"

    def make_existing_key(self):
        self.ssh_dir.mkdir(mode=0o755)
        self.key.write_bytes(b"fake private key\n")
        (self.ssh_dir / "cptc_ed25519.pub").write_bytes(b"fake public key\n")

    def test_missing_key_is_created_then_copied_to_each_teammate(self):
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls(), [
            "ssh-keygen [-q] [-t] [ed25519] [-N] [] [-C] [cptc-pull] [-f] [" + str(self.key) + "]",
            self.copy_id_call("kali@10.0.0.5"),
            self.copy_id_call("kali@10.0.0.6"),
        ])
        # ssh-keygen needs the folder; ssh expects it private.
        self.assertEqual(self.ssh_dir.stat().st_mode & 0o777, 0o700)

    def test_existing_key_is_reused_untouched(self):
        self.make_existing_key()
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Using the existing pull key " + str(self.key) + "\n", result.stdout)
        # No ssh-keygen call, and the key and folder are left as they were.
        self.assertEqual(self.stub_calls(), [
            self.copy_id_call("kali@10.0.0.5"),
            self.copy_id_call("kali@10.0.0.6"),
        ])
        self.assertEqual(self.key.read_bytes(), b"fake private key\n")
        self.assertEqual(self.ssh_dir.stat().st_mode & 0o777, 0o755)

    def test_logins_and_ips_go_to_the_right_teammate(self):
        answers = "2\nalice\nkali\n10.0.0.5\nbob\nbob_k\n10.0.0.77\n"
        result = self.run_script(PULL, ["--setup"], answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls()[1:], [
            self.copy_id_call("kali@10.0.0.5"),
            self.copy_id_call("bob_k@10.0.0.77"),
        ])

    def test_half_a_key_is_refused_without_ssh(self):
        for present in ["cptc_ed25519", "cptc_ed25519.pub"]:
            with self.subTest(present=present):
                self.setUp()
                self.ssh_dir.mkdir()
                (self.ssh_dir / present).write_bytes(b"fake\n")
                self.assert_key_refused()
                self.assertEqual(sorted(p.name for p in self.ssh_dir.iterdir()), [present])

    def test_broken_key_links_are_refused_without_ssh(self):
        # A broken symlink isn't a key, but ssh-keygen would write through it
        # and create the file it points to.
        for links in [["cptc_ed25519"], ["cptc_ed25519.pub"], ["cptc_ed25519", "cptc_ed25519.pub"]]:
            with self.subTest(links=links):
                self.setUp()
                self.ssh_dir.mkdir()
                target = self.home / "link-target"
                for name in links:
                    (self.ssh_dir / name).symlink_to(target)
                self.assert_key_refused()
                self.assertFalse(target.exists())
                self.assertEqual(sorted(p.name for p in self.ssh_dir.iterdir()), links)

    def assert_key_refused(self):
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, (
            "pull: the pull key is incomplete or a broken link (" + str(self.key) + ", "
            + str(self.key) + ".pub). Delete both and run setup again.\n"))
        self.assertEqual(self.stub_calls(), [])

    def test_ssh_keygen_failure_stops_before_copying(self):
        self.fail_stub("ssh-keygen", "ed25519")
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: ssh-keygen could not create " + str(self.key) + ".\n")
        self.assertEqual([call.split()[0] for call in self.stub_calls()], ["ssh-keygen"])

    def test_one_failed_copy_is_named_and_the_rest_still_run(self):
        self.fail_stub("ssh-copy-id", "10.0.0.5")
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, (
            "pull: could not copy the key to alice (kali@10.0.0.5).\n"
            "pull: the key is not on: alice. Check their ssh server is running "
            "and the password is right, then run setup again and keep the list.\n"))
        # bob was still tried after alice failed, and the list was kept.
        self.assertEqual(self.stub_calls()[1:], [
            self.copy_id_call("kali@10.0.0.5"),
            self.copy_id_call("kali@10.0.0.6"),
        ])
        self.assertNotIn("Setup done", result.stdout)
        self.assertEqual(self.config.read_bytes(), TWO_TEAMMATES_FILE.encode())

    def test_every_failed_copy_is_named(self):
        self.fail_stub("ssh-copy-id", "kali@")
        result = self.run_script(PULL, ["--setup"], TWO_TEAMMATES)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.endswith(
            "pull: the key is not on: alice bob. Check their ssh server is running "
            "and the password is right, then run setup again and keep the list.\n"), result.stderr)

    def test_script_never_uses_sudo(self):
        # The stub PATH has no sudo, so a call would already fail; this also
        # catches one on a path the tests don't run.
        self.assertNotIn("sudo", PULL.read_text(encoding="utf-8"))


class PullTests(ScriptTestCase):
    """Normal pulls: which teammates, and the exact rsync call for each."""

    def setUp(self):
        super().setUp()
        self.config.write_bytes(TWO_TEAMMATES_FILE.encode())
        self.key = self.home / ".ssh" / "cptc_ed25519"
        self.key.parent.mkdir()
        self.key.write_bytes(b"fake private key\n")
        (self.key.parent / "cptc_ed25519.pub").write_bytes(b"fake public key\n")
        self.incoming = self.workdir / "incoming"

    def rsync_call(self, login_at_ip, name):
        args = ["-a", "--delete", "--delete-excluded",
                "-e", "ssh -i '" + str(self.key) + "' -o IdentitiesOnly=yes -o BatchMode=yes",
                "--include=/findings/***", "--include=/evidence/***",
                "--include=/field-notes/***", "--include=/tracker/***", "--exclude=*",
                login_at_ip + ":cptc-work/", str(self.incoming / name) + "/"]
        return "rsync" + "".join(" [" + arg + "]" for arg in args)

    def pulling_line(self, name, login_at_ip):
        return "Pulling " + name + " (" + login_at_ip + ") into " + str(self.incoming / name) + "/\n"

    def test_no_name_pulls_every_teammate_once(self):
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (
            self.pulling_line("alice", "kali@10.0.0.5")
            + self.pulling_line("bob", "kali@10.0.0.6")
            + "Pulled 2 teammate(s).\n"))
        # One rsync (one connection) per teammate, and nothing else runs.
        self.assertEqual(self.stub_calls(), [
            self.rsync_call("kali@10.0.0.5", "alice"),
            self.rsync_call("kali@10.0.0.6", "bob"),
        ])
        self.assertEqual(sorted(p.name for p in self.incoming.iterdir()), ["alice", "bob"])

    def test_a_name_pulls_only_that_teammate(self):
        result = self.run_script(PULL, ["bob"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls(), [self.rsync_call("kali@10.0.0.6", "bob")])
        self.assertEqual(sorted(p.name for p in self.incoming.iterdir()), ["bob"])

    def test_unknown_or_inexact_name_pulls_nobody(self):
        for wanted in ["carol", "ali", "Alice", "alice "]:
            with self.subTest(wanted=wanted):
                self.setUp()
                result = self.run_script(PULL, [wanted])
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, 'pull: no teammate named "' + wanted
                                 + '" in ' + str(self.config) + ".\n")
                self.assertEqual(self.stub_calls(), [])
                self.assertFalse(self.incoming.exists())

    def test_empty_name_is_refused_not_read_as_everyone(self):
        result = self.run_script(PULL, [""])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: the name is empty. Use: " + str(PULL)
                         + " [--setup | <name>]\n")
        self.assertEqual(self.stub_calls(), [])

    def test_a_failed_teammate_is_named_and_the_rest_still_pull(self):
        self.fail_stub("rsync", "10.0.0.5")
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, (
            "pull: alice failed.\n"
            "pull: not pulled: alice. Check their box is on and ssh is running, then pull again.\n"))
        self.assertTrue(result.stdout.endswith("Pulled 1 teammate(s).\n"), result.stdout)
        self.assertEqual(self.stub_calls(), [
            self.rsync_call("kali@10.0.0.5", "alice"),
            self.rsync_call("kali@10.0.0.6", "bob"),
        ])

    def test_one_named_teammate_failing_exits_nonzero(self):
        self.fail_stub("rsync", "10.0.0.5")
        result = self.run_script(PULL, ["alice"])
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.endswith("pull: not pulled: alice. Check their box "
                                               "is on and ssh is running, then pull again.\n"))
        self.assertEqual(len(self.stub_calls()), 1)

    def test_missing_pull_key_is_refused(self):
        self.key.unlink()
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: no pull key at " + str(self.key)
                         + ". Run setup first: " + str(PULL) + " --setup\n")
        self.assertEqual(self.stub_calls(), [])

    def test_symlinked_incoming_is_refused(self):
        target = self.home / "elsewhere"
        target.mkdir()
        self.incoming.symlink_to(target)
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: " + str(self.incoming)
                         + " is a symlink. Nothing was pulled.\n")
        self.assertEqual(self.stub_calls(), [])
        self.assertEqual(list(target.iterdir()), [])

    def test_symlinked_teammate_folder_is_refused_and_others_pull(self):
        target = self.home / "elsewhere"
        target.mkdir()
        self.incoming.mkdir()
        (self.incoming / "alice").symlink_to(target)
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith(
            "pull: " + str(self.incoming / "alice") + " is a symlink, so alice was not pulled.\n"
            "pull: alice failed.\n"), result.stderr)
        self.assertEqual(self.stub_calls(), [self.rsync_call("kali@10.0.0.6", "bob")])
        self.assertEqual(list(target.iterdir()), [])

    def test_bad_line_in_a_hand_edited_list_stops_every_pull(self):
        self.config.write_bytes(b"alice\tkali\t10.0.0.5\n../x\tkali\t10.0.0.6\n")
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: " + str(self.config) + ' line 2: name "../x" '
                         "is not allowed. Fix it or run " + str(PULL) + " --setup again.\n")
        self.assertEqual(self.stub_calls(), [])
        self.assertFalse(self.incoming.exists())

    def test_repeated_name_in_a_hand_edited_list_stops_every_pull(self):
        # Two rows for one name would both mirror into incoming/alice/.
        self.config.write_bytes(b"alice\tkali\t10.0.0.5\nalice\tkali\t10.0.0.6\n")
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: " + str(self.config) + ' line 2: name "alice" '
                         "is already used by another teammate. Fix it or run " + str(PULL)
                         + " --setup again.\n")
        self.assertEqual(self.stub_calls(), [])
        self.assertFalse(self.incoming.exists())

    def test_last_line_without_a_newline_is_still_pulled(self):
        self.config.write_bytes(TWO_TEAMMATES_FILE.encode().rstrip(b"\n"))
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self.stub_calls()), 2)

    def test_empty_list_says_to_run_setup(self):
        self.config.write_bytes(b"")
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: " + str(self.config)
                         + " lists no teammates. Run setup again: " + str(PULL) + " --setup\n")

    def test_too_many_arguments_is_refused(self):
        result = self.run_script(PULL, ["alice", "bob"])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "pull: too many arguments. Use: " + str(PULL)
                         + " [--setup | <name>]\n")
        self.assertEqual(self.stub_calls(), [])


@unittest.skipIf(shutil.which("rsync") is None, "rsync is not installed")
class PullRealRsyncTests(ScriptTestCase):
    """Replay pull.sh's recorded rsync arguments through the real rsync, with
    a local folder as the teammate's cptc-work/ (no ssh, no network), to check
    the filter and delete flags really mirror only the four folders."""

    def test_recorded_flags_mirror_only_the_four_folders(self):
        self.config.write_bytes(b"alice\tkali\t10.0.0.5\n")
        ssh_dir = self.home / ".ssh"
        ssh_dir.mkdir()
        (ssh_dir / "cptc_ed25519").write_bytes(b"fake\n")
        result = self.run_script(PULL)
        self.assertEqual(result.returncode, 0, result.stderr)
        args = re.findall(r"\[(.*?)\]", self.stub_calls()[0])
        # Swap the remote source for a local fake teammate folder and drop
        # "-e <ssh command>", so the real rsync copies locally only.
        source = self.home / "teammate-cptc-work"
        self.assertEqual(args[-2], "kali@10.0.0.5:cptc-work/")
        args[-2] = str(source) + "/"
        dash_e = args.index("-e")
        del args[dash_e:dash_e + 2]
        for relative_path in ["findings/F-001-a.md", "findings/sub/x.md", "evidence/e.png",
                              "field-notes/alice/NOTE-a.md", "tracker/findings-index.csv",
                              "notes/private.md", "build/report.md", "top.txt",
                              "incoming/bob/findings/F-009-b.md"]:
            support.write_fake_file(source, relative_path, "fake\n")
        dest = self.workdir / "incoming" / "alice"
        # Stale copies: one the teammate deleted, and files outside the four folders.
        for relative_path in ["findings/F-000-deleted.md", "notes/old.md", "junk.txt"]:
            support.write_fake_file(dest, relative_path, "stale\n")
        real = subprocess.run([shutil.which("rsync")] + args, capture_output=True,
                              text=True, timeout=20)
        self.assertEqual(real.returncode, 0, real.stderr)
        copied = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
        self.assertEqual(copied, ["evidence/e.png", "field-notes/alice/NOTE-a.md",
                                  "findings/F-001-a.md", "findings/sub/x.md",
                                  "tracker/findings-index.csv"])


# A fake `git clone`: records the call like every stub, then copies
# $HOME/fake-repo (a made-up team repo with its own .git) to the last
# argument, as a real clone would. No network, no real repo.
FAKE_GIT_CLONE = STUB + """if [ "$1" = clone ]; then
  for last; do :; done
  cp -R "$HOME/fake-repo" "$last"
fi
"""
FAKE_REPO_FILES = {
    ".git/HEAD": "ref: refs/heads/main\n",
    "README.md": "fake team readme\n",
    "templates/tracker/findings-index.csv": "finding_id,title\n",
    "templates/tracker/hosts.csv": "host,ip\n",
    "tools/compile.py": "# fake tool\n",
}


class MakeWorkcopyTests(ScriptTestCase):
    def setUp(self):
        super().setUp()
        # make-workcopy.sh creates ~/cptc-work itself, so start without it.
        self.workdir.rmdir()
        # It (and the fake git clone) also use cp and rm.
        link_real_commands(self.bin_dir, WORKCOPY_REAL_COMMANDS)
        self.repo = self.home / "fake-repo"
        for relative_path, text in FAKE_REPO_FILES.items():
            support.write_fake_file(self.repo, relative_path, text)
        (self.bin_dir / "git").write_text(FAKE_GIT_CLONE, encoding="utf-8")

    def git_clone_call(self, source):
        return "git [clone] [--] [" + source + "] [" + str(self.workdir) + "]"

    def all_paths(self):
        return sorted(str(p.relative_to(self.workdir)) for p in self.workdir.rglob("*"))

    def test_makes_the_working_copy_layout(self):
        result = self.run_script(MAKE_WORKCOPY, ["alice", str(self.repo)])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, (
            "Made " + str(self.workdir) + " for alice.\n"
            "Work only in " + str(self.workdir) + " from now on, and open every terminal there.\n"))
        self.assertEqual(self.stub_calls(), [self.git_clone_call(str(self.repo))])
        # The clone's .git is gone; the team files and the new parts are there.
        self.assertEqual(self.all_paths(), [
            ".cptc-name", "README.md", "exclude.txt", "field-notes", "field-notes/alice",
            "incoming", "templates", "templates/tracker",
            "templates/tracker/findings-index.csv", "templates/tracker/hosts.csv",
            "tools", "tools/compile.py", "tracker", "tracker/findings-index.csv",
            "tracker/hosts.csv"])
        self.assertEqual((self.workdir / ".cptc-name").read_bytes(), b"alice\n")
        self.assertEqual((self.workdir / "exclude.txt").read_bytes(), b"")
        for name in ["findings-index.csv", "hosts.csv"]:
            self.assertEqual((self.workdir / "tracker" / name).read_bytes(),
                             (self.repo / "templates/tracker" / name).read_bytes())
        # The source clone keeps its own .git.
        self.assertTrue((self.repo / ".git/HEAD").exists())

    def test_a_git_url_is_passed_to_git_as_is(self):
        url = "https://example.invalid/team/cptc.git"
        result = self.run_script(MAKE_WORKCOPY, ["alice", url])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.stub_calls(), [self.git_clone_call(url)])

    def test_a_source_starting_with_dash_stays_after_double_dash(self):
        result = self.run_script(MAKE_WORKCOPY, ["alice", "--upload-pack=x"])
        self.assertEqual(self.stub_calls(), [self.git_clone_call("--upload-pack=x")])
        self.assertEqual(result.returncode, 0, result.stderr)

    def assert_refused_before_git(self, args, message):
        result = self.run_script(MAKE_WORKCOPY, args)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "make-workcopy: " + message + "\n")
        self.assertEqual(self.stub_calls(), [])

    def test_existing_folder_is_refused_unchanged(self):
        support.write_fake_file(self.workdir, "findings/F-001-mine.md", "event work\n")
        self.assert_refused_before_git(["alice", str(self.repo)], str(self.workdir)
                                       + " already exists, so nothing was changed.")
        self.assertEqual(self.all_paths(), ["findings", "findings/F-001-mine.md"])
        self.assertEqual((self.workdir / "findings/F-001-mine.md").read_bytes(), b"event work\n")

    def test_existing_file_is_refused(self):
        self.workdir.write_bytes(b"not a folder\n")
        self.assert_refused_before_git(["alice", str(self.repo)], str(self.workdir)
                                       + " already exists, so nothing was changed.")
        self.assertEqual(self.workdir.read_bytes(), b"not a folder\n")

    def test_symlinks_are_refused_and_their_targets_untouched(self):
        for dangling in [False, True]:
            with self.subTest(dangling=dangling):
                self.setUp()
                target = self.home / "elsewhere"
                if not dangling:
                    target.mkdir()
                self.workdir.symlink_to(target)
                self.assert_refused_before_git(["alice", str(self.repo)], str(self.workdir)
                                               + " already exists, so nothing was changed.")
                if dangling:
                    self.assertFalse(target.exists())
                else:
                    self.assertEqual(list(target.iterdir()), [])

    def test_unsafe_names_are_refused_before_git(self):
        for name in ["..", "../x", "a/b", "Alice", "-x", "a b", "caf\xe9", ""]:
            with self.subTest(name=name):
                self.setUp()
                self.assert_refused_before_git(
                    [name, str(self.repo)],
                    'name "' + name + '" is not allowed. Use lowercase letters, digits '
                    'and -, starting with a letter or digit.')
                self.assertFalse(self.workdir.exists())

    def test_accented_name_is_refused_in_a_latin1_locale(self):
        # Same reason as the pull.sh test: in Latin-1, b"\xe9" is one byte that
        # [a-z] matches unless the script pins LC_ALL=C. The name goes in as
        # Latin-1 bytes; only the end of stderr is compared, in case bash
        # prints a setlocale warning where the locale isn't installed.
        result = self.run_script(MAKE_WORKCOPY, [b"caf\xe9", str(self.repo)],
                                 locale="en_US.ISO8859-1", encoding="latin-1")
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.endswith(
            'make-workcopy: name "caf\xe9" is not allowed. Use lowercase letters, digits '
            'and -, starting with a letter or digit.\n'), result.stderr)
        self.assertEqual(self.stub_calls(), [])
        self.assertFalse(self.workdir.exists())

    def test_wrong_argument_count_is_refused(self):
        for args in [[], ["alice"], ["alice", str(self.repo), "extra"]]:
            with self.subTest(args=args):
                self.assert_refused_before_git(
                    args, "Use: " + str(MAKE_WORKCOPY) + " <yourname> <clone-folder-or-git-url>")
                self.assertFalse(self.workdir.exists())

    def test_empty_source_is_refused(self):
        self.assert_refused_before_git(
            ["alice", ""], "the source is empty. Give the team repo's folder or Git URL.")

    def test_failed_clone_stops_before_any_later_step(self):
        self.fail_stub("git", "clone")
        result = self.run_script(MAKE_WORKCOPY, ["alice", str(self.repo)])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "make-workcopy: git clone of " + str(self.repo)
                         + " failed.\n")
        self.assertEqual(len(self.stub_calls()), 1)
        self.assertFalse(self.workdir.exists())

    def assert_partial_refusal(self, message):
        result = self.run_script(MAKE_WORKCOPY, ["alice", str(self.repo)])
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "make-workcopy: " + message + " " + str(self.workdir)
                         + " is incomplete: delete it, then run this again.\n")
        # Stopped before adding anything: no folders, tracker copy or name file
        # beyond what the source itself brought.
        for made in ["field-notes", "incoming", ".cptc-name"]:
            if not os.path.lexists(str(self.repo / made)):
                self.assertFalse(os.path.lexists(str(self.workdir / made)), made)
        self.assertFalse((self.workdir / ".git").exists())

    def test_source_without_tracker_templates_stops(self):
        shutil.rmtree(str(self.repo / "templates"))
        self.assert_partial_refusal(str(self.repo) + " has no templates/tracker/: is it the team repo?")

    def test_source_with_its_own_tracker_or_exclude_list_stops(self):
        for existing in ["tracker/hosts.csv", "exclude.txt"]:
            with self.subTest(existing=existing):
                self.setUp()
                support.write_fake_file(self.repo, existing, "from the repo\n")
                top = existing.split("/")[0]
                self.assert_partial_refusal(str(self.workdir / top) + " already came with the source.")
                self.assertEqual((self.workdir / existing).read_bytes(), b"from the repo\n")

    def assert_link_refused(self, link, target, message):
        """Make `link` in the fake repo point at `target`, run, and check the
        refusal left the target alone and added nothing to the copy."""
        before = sorted(str(p) for p in target.rglob("*")) if target.exists() else None
        (self.repo / link).symlink_to(target)
        self.assert_partial_refusal(message)
        after = sorted(str(p) for p in target.rglob("*")) if target.exists() else None
        self.assertEqual(after, before)
        self.assertTrue((self.workdir / link).is_symlink())
        for made in ["exclude.txt", "tracker"]:
            if made != link:
                self.assertFalse(os.path.lexists(str(self.workdir / made)), made)

    def test_symlinked_folders_from_the_source_are_refused(self):
        # Each of these is written into or copied from; a link could send the
        # write outside ~/cptc-work. The target is a real folder outside.
        for link in ["templates", "templates/tracker", "field-notes", "field-notes/alice", "incoming"]:
            with self.subTest(link=link):
                self.setUp()
                target = self.home / "outside"
                support.write_fake_file(target, "tracker/hosts.csv", "outside\n")
                if link.startswith("templates"):
                    shutil.rmtree(str(self.repo / link))
                else:
                    (self.repo / link).parent.mkdir(parents=True, exist_ok=True)
                self.assert_link_refused(link, target, str(self.workdir / link)
                                         + " is a symlink in the source.")

    def test_broken_links_where_files_are_made_are_refused(self):
        for link in ["tracker", "exclude.txt", ".cptc-name"]:
            with self.subTest(link=link):
                self.setUp()
                target = self.home / "never-made"
                self.assert_link_refused(link, target, str(self.workdir / link)
                                         + " already came with the source.")
                self.assertFalse(os.path.lexists(str(target)))

    def test_source_with_its_own_name_file_stops(self):
        support.write_fake_file(self.repo, ".cptc-name", "bob\n")
        self.assert_partial_refusal(str(self.workdir / ".cptc-name") + " already came with the source.")
        self.assertEqual((self.workdir / ".cptc-name").read_bytes(), b"bob\n")

    def test_script_never_uses_sudo(self):
        self.assertNotIn("sudo", MAKE_WORKCOPY.read_text(encoding="utf-8"))


# A fake util-linux `script`: records its call like every stub, plus the
# LC_ALL it was started with, and never starts a recorder or a shell.
FAKE_SCRIPT = STUB + """printf 'LC_ALL=%s\\n' "${LC_ALL-unset}" >> "$HOME/script-env.log"
"""
# A fake whoami: the shared login the event boxes may all use.
FAKE_WHOAMI = "#!/bin/sh\necho kali\n"


class LoggedShellNameTests(ScriptTestCase):
    """Which name logged-shell.sh gives the logs (SQ-06)."""

    def setUp(self):
        super().setUp()
        link_real_commands(self.bin_dir, ["date", "rm"])
        (self.bin_dir / "script").write_text(FAKE_SCRIPT, encoding="utf-8")
        (self.bin_dir / "script").chmod(0o755)
        (self.bin_dir / "whoami").write_text(FAKE_WHOAMI, encoding="utf-8")
        (self.bin_dir / "whoami").chmod(0o755)
        self.logdir = self.home / "logs"
        # mktemp writes its startup file to $TMPDIR; keep it inside the repo.
        self.tmpdir = self.home / "tmp"
        self.tmpdir.mkdir()
        self.name_file = self.workdir / ".cptc-name"

    def run_logged_shell(self, args=(), locale=None, encoding="utf-8", extra_env=None):
        env = {"LOGDIR": str(self.logdir), "TMPDIR": str(self.tmpdir)}
        env.update(extra_env or {})
        result = self.run_script(LOGGED_SHELL, args, locale=locale, encoding=encoding,
                                 extra_env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def log_name(self, result):
        """The name in the transcript path given to the fake `script`."""
        calls = [call for call in self.stub_calls() if call.startswith("script ")]
        self.assertEqual(len(calls), 1)
        log_path = re.findall(r"\[(.*?)\]", calls[0])[-1]
        match = re.fullmatch(re.escape(str(self.logdir)) + r"/(.*)_\d{8}T\d{6}Z\.log", log_path)
        self.assertIsNotNone(match, log_path)
        self.assertTrue(result.stdout.startswith("Logging to " + log_path + "\n"), result.stdout)
        # The startup file was made in TMPDIR and removed again.
        self.assertEqual(list(self.tmpdir.iterdir()), [])
        return match.group(1)

    def warning(self):
        return ("logged-shell: no valid name in " + str(self.name_file) + ", so these logs are "
                "named after your login (kali). Next time: " + str(LOGGED_SHELL) + " <yourname>\n")

    def test_an_explicit_name_wins_over_the_saved_one(self):
        self.name_file.write_bytes(b"bob\n")
        result = self.run_logged_shell(["alice"])
        self.assertEqual(self.log_name(result), "alice")
        self.assertEqual(result.stderr, "")

    def assert_typed_name_refused(self, name, locale=None, encoding="utf-8"):
        """A bad typed name stops the script before any log or log folder."""
        env = {"LOGDIR": str(self.logdir), "TMPDIR": str(self.tmpdir)}
        result = self.run_script(LOGGED_SHELL, [name], locale=locale, encoding=encoding,
                                 extra_env=env)
        self.assertEqual(result.returncode, 1)
        shown = name.decode("latin-1") if isinstance(name, bytes) else name
        # A line of its own: where the locale is missing, bash warns before AND after it.
        self.assertIn('logged-shell: name "' + shown + '" is not allowed. Use lowercase letters, '
                      'digits and -, starting with a letter or digit.', result.stderr.splitlines())
        self.assertEqual(result.stdout, "")
        self.assertEqual(self.stub_calls(), [])
        self.assertFalse(self.logdir.exists())
        self.assertEqual(list(self.tmpdir.iterdir()), [])
        return result

    def test_a_typed_name_breaking_the_rule_is_refused(self):
        # "/" and ".." would put logs outside LOGDIR; the rest break the same
        # rule as a saved name. A valid saved name doesn't rescue a bad typed one.
        for name in ["../x", "a/b", "..", "/tmp", "-n", "-e", "Alice", "a b", "caf\xe9", "a\\nb"]:
            with self.subTest(name=name):
                self.setUp()
                self.name_file.write_bytes(b"bob\n")
                result = self.assert_typed_name_refused(name)
                # Exactly the one line: no fallback warning, no bash error.
                self.assertEqual(result.stderr.count("\n"), 1)

    def test_an_accented_typed_name_is_refused_in_a_latin1_locale(self):
        # As for the saved name: in Latin-1 b"\xe9" is one byte that [a-z]
        # matches unless the check runs with LC_ALL=C.
        self.assert_typed_name_refused(b"caf\xe9", locale="en_US.ISO8859-1", encoding="latin-1")

    def test_the_saved_name_is_used_without_a_warning(self):
        for saved in [b"bob\n", b"bob", b"team-2\n"]:
            with self.subTest(saved=saved):
                self.setUp()
                self.name_file.write_bytes(saved)
                result = self.run_logged_shell()
                self.assertEqual(self.log_name(result), saved.decode().strip())
                self.assertEqual(result.stderr, "")

    def test_no_saved_name_warns_once_and_uses_the_login(self):
        result = self.run_logged_shell()
        self.assertEqual(self.log_name(result), "kali")
        self.assertEqual(result.stderr, self.warning())

    def test_no_working_copy_warns_and_uses_the_login(self):
        self.workdir.rmdir()
        result = self.run_logged_shell()
        self.assertEqual(self.log_name(result), "kali")
        self.assertEqual(result.stderr, self.warning())

    def test_an_invalid_saved_name_warns_and_uses_the_login(self):
        # Each is not one valid name: wrong letters, a path, two lines, blank.
        for saved in [b"Bob\n", b"../x\n", b"a/b\n", b" bob\n", b"-x\n", b"bob\nalice\n",
                      b"bob\nalice", b"bob\n\n", b"bob\n\nalice\n", b"\n", b"",
                      "caf\xe9\n".encode("utf-8")]:
            with self.subTest(saved=saved):
                self.setUp()
                self.name_file.write_bytes(saved)
                result = self.run_logged_shell()
                self.assertEqual(self.log_name(result), "kali")
                self.assertEqual(result.stderr, self.warning())

    @unittest.skipIf(os.geteuid() == 0, "root can read any file")
    def test_an_unreadable_name_file_gives_only_the_warning(self):
        self.name_file.write_bytes(b"bob\n")
        self.name_file.chmod(0)
        result = self.run_logged_shell()
        self.assertEqual(self.log_name(result), "kali")
        # Only our one-line warning: no "Permission denied" from bash.
        self.assertEqual(result.stderr, self.warning())

    def test_a_folder_in_place_of_the_name_file_warns(self):
        self.name_file.mkdir()
        result = self.run_logged_shell()
        self.assertEqual(self.log_name(result), "kali")
        self.assertEqual(result.stderr, self.warning())

    def test_an_accented_saved_name_is_refused_in_a_latin1_locale(self):
        # As in the pull.sh test: in Latin-1 b"\xe9" is one byte [a-z] matches
        # unless the check runs with LC_ALL=C. Only the end of stderr is
        # compared, in case bash prints a setlocale warning first.
        self.name_file.write_bytes(b"caf\xe9\n")
        result = self.run_logged_shell(locale="en_US.ISO8859-1", encoding="latin-1")
        self.assertEqual(self.log_name(result), "kali")
        self.assertTrue(result.stderr.endswith(self.warning()), result.stderr)

    def test_the_logged_session_keeps_your_locale(self):
        # LC_ALL=C is only for the name check; the recorded shell must get
        # whatever the user had, set or not.
        self.name_file.write_bytes(b"bob\n")
        for given, seen in [(None, "unset"), ("en_US.UTF-8", "en_US.UTF-8")]:
            with self.subTest(given=given):
                env_log = self.home / "script-env.log"
                if env_log.exists():
                    env_log.unlink()
                self.run_logged_shell(locale=given)
                self.assertEqual(env_log.read_text(encoding="utf-8"), "LC_ALL=" + seen + "\n")

    def test_logs_go_to_logdir_with_the_command_index_beside_them(self):
        self.name_file.write_bytes(b"bob\n")
        result = self.run_logged_shell()
        self.assertEqual(self.log_name(result), "bob")
        lines = result.stdout.splitlines()
        self.assertEqual(lines[1], "Command index: " + lines[0][len("Logging to "):-len(".log")]
                         + ".cmds.log  (type 'exit' to stop)")
        self.assertTrue(self.logdir.is_dir())


class PullMissingConfigTests(ScriptTestCase):
    def test_pull_without_a_list_says_how_to_run_setup(self):
        # Both pull forms need the list; neither may touch the network.
        for args in [[], ["alice"]]:
            with self.subTest(args=args):
                result = self.run_script(PULL, args)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertEqual(result.stderr, "pull: no teammate list at " + str(self.config)
                                 + ". Run setup first: " + str(PULL) + " --setup\n")
                self.assertEqual(self.stub_calls(), [])
                self.assertEqual(self.workdir_names(), [])


if __name__ == "__main__":
    unittest.main()
