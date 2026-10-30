"""Tests for tools/notebook.py."""

import support  # puts tools/ on the import path, so it must come first
import notebook
import compile

import ast
import contextlib
import datetime
import http.client
import io
import json
import os
import re
import shutil
import socket
import stat
import string
import tempfile
import threading
import unittest
import zipfile
from html.parser import HTMLParser
from http.server import HTTPServer
from unittest import mock
from pathlib import Path
from urllib.parse import quote


class StartupTests(unittest.TestCase):
    def test_git_root_exits_before_anything_is_created(self):
        root = support.make_worktree(self, {".git/HEAD": "ref: refs/heads/main\n"})
        before = sorted(root.rglob("*"))
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), \
                mock.patch.object(notebook, "HTTPServer") as server_class:
            exit_code = notebook.main(["--name", "alice", "--root", str(root)])
        self.assertEqual(exit_code, 2)
        self.assertTrue(printed.getvalue().startswith(
            "notebook failed: this looks like the git clone"))
        # Nothing was created: no server, no field-notes/alice/, no state file.
        server_class.assert_not_called()
        self.assertEqual(sorted(root.rglob("*")), before)

    def test_parser_has_no_bind_address_option(self):
        # The server always binds to 127.0.0.1 (Constraint 2), so there must
        # be no option that could expose it to the network.
        for option in ["--host", "--bind", "--address", "--listen"]:
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    notebook.parse_args(["--name", "alice", option, "0.0.0.0"])

    def test_port_must_be_a_real_port_number(self):
        self.assertEqual(notebook.parse_args(["--name", "alice", "--port", "9000"]).port, 9000)
        for port in ["0", "65536", "-1", "abc", "\u0663"]:
            with self.subTest(port=port), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    notebook.parse_args(["--name", "alice", "--port", port])


class ServeTests(unittest.TestCase):
    def setUp(self):
        self.root = support.make_worktree(self, {"findings/F-001-x.md": "x\n"})

    def run_main(self, port):
        """Run main() with the server faked; Ctrl+C stops it at once."""
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed), \
                mock.patch.object(notebook, "HTTPServer") as server_class:
            server = server_class.return_value
            server.server_address = ("127.0.0.1", port)
            server.serve_forever.side_effect = KeyboardInterrupt
            exit_code = notebook.main(["--name", "alice", "--root", str(self.root),
                                       "--port", str(port)])
        return exit_code, printed.getvalue(), server_class

    def test_serves_on_literal_loopback_and_prints_the_url(self):
        exit_code, printed, server_class = self.run_main(9123)
        self.assertEqual(exit_code, 0)
        server_class.assert_called_once_with(("127.0.0.1", 9123), notebook.NotebookHandler)
        server = server_class.return_value
        self.assertGreaterEqual(len(server.token), 43)
        self.assertEqual(server.settings["name"], "alice")
        self.assertIn("http://127.0.0.1:9123\n", printed)
        self.assertIn("Local only", printed)
        server.server_close.assert_called_once_with()

    def test_real_server_listens_on_127_0_0_1_with_a_token(self):
        server = notebook.make_server({"port": 0})
        self.addCleanup(server.server_close)
        self.assertEqual(server.server_address[0], "127.0.0.1")
        self.assertEqual(server.RequestHandlerClass, notebook.NotebookHandler)
        second = notebook.make_server({"port": 0})
        self.addCleanup(second.server_close)
        self.assertNotEqual(server.token, second.token)

    def test_port_in_use_exits_readably(self):
        taken = HTTPServer(("127.0.0.1", 0), notebook.NotebookHandler)
        self.addCleanup(taken.server_close)
        port = taken.server_address[1]
        printed = io.StringIO()
        # If main() ever got a server anyway, Ctrl+C stops it instead of the
        # test hanging forever.
        with contextlib.redirect_stdout(printed), \
                mock.patch.object(HTTPServer, "serve_forever", side_effect=KeyboardInterrupt):
            exit_code = notebook.main(["--name", "alice", "--root", str(self.root),
                                       "--port", str(port)])
        self.assertEqual(exit_code, 2)
        self.assertTrue(printed.getvalue().startswith(
            "notebook failed: can't listen on 127.0.0.1:" + str(port)))

    def test_page_needs_no_network_address(self):
        # Constraint 1: no CDN or other outside file; the page works offline.
        self.assertNotIn("http", notebook.APP_PAGE)
        self.assertNotIn("//", notebook.APP_PAGE)


class ModuleSafetyTests(unittest.TestCase):
    """Constraint 3, tested the same way as compile.py's (Chunk N1 D2)."""

    TREE = ast.parse((support.TOOLS_DIR / "notebook.py").read_text(encoding="utf-8"))

    def test_only_safe_modules_are_imported(self):
        imported = set()
        for node in ast.walk(self.TREE):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        # No subprocess. os is for $LOGDIR, the safe writes and the export's
        # walk that never follows a link (N5-01), and stat reads the file types
        # that walk sees; the test below checks os.system and os.popen never appear.
        # shutil only copies a file into the zip, and zipfile only writes one
        # (N5-02; ExportZipTests checks nothing extracts).
        self.assertEqual(imported, {"argparse", "datetime", "html", "json", "os", "re", "secrets",
                                    "shutil", "stat", "sys", "tempfile", "zipfile",
                                    "http.server", "pathlib", "urllib.parse", "compile"})

    def test_no_command_running_call_appears(self):
        names = set()
        for node in ast.walk(self.TREE):
            if isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.alias):
                # Imported names too, so "from os import popen" is caught.
                names.add(node.name)
        for name in ("subprocess", "system", "popen", "Popen", "exec", "eval"):
            with self.subTest(name=name):
                self.assertNotIn(name, names)


class SlugifyTests(unittest.TestCase):
    def test_spec_example(self):
        self.assertEqual(notebook.slugify(" ../A  B!! "), "a-b")

    def test_leading_trailing_and_repeated_hyphens_disappear(self):
        self.assertEqual(notebook.slugify("--smb---signing--"), "smb-signing")

    def test_length_is_at_most_40_with_no_hyphen_at_the_cut(self):
        # The 40th character is a space, which becomes "-" and is then stripped.
        slug = notebook.slugify("a" * 39 + " bcd")
        self.assertEqual(slug, "a" * 39)
        self.assertLessEqual(len(notebook.slugify("x" * 100)), 40)

    def test_punctuation_only_is_refused(self):
        with self.assertRaises(ValueError):
            notebook.slugify("!!! ../ ---")


class ValidateNnnTests(unittest.TestCase):
    def test_three_digits_pass(self):
        self.assertEqual(notebook.validate_nnn("000"), "000")
        self.assertEqual(notebook.validate_nnn("999"), "999")

    def test_other_values_fail(self):
        # "123\n" and Arabic-Indic digits would pass a plain re.match(r"^\d{3}$").
        for text in ["1", "01", "1000", "abc", "123\n", "١٢٣"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                notebook.validate_nnn(text)


class NameOptionTests(unittest.TestCase):
    def test_name_is_slugged(self):
        self.assertEqual(notebook.parse_args(["--name", "Alice Smith"]).name, "alice-smith")

    def test_name_with_nothing_usable_is_refused(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            notebook.parse_args(["--name", "../"])


class PathWrapperTests(unittest.TestCase):
    def setUp(self):
        self.root = support.make_worktree(self, {
            "findings/F-001-x.md": "x\n",
            "incoming/bob/findings/F-002-y.md": "y\n",
        })
        self.logdir = support.make_worktree(self, {"alice_20261107T0900Z.log": "log\n"})
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {"secret.md": "s\n"})

    def assert_refused(self, call, named):
        with self.assertRaises(compile.RootError) as caught:
            call()
        self.assertIn(named, str(caught.exception))

    def test_root_child_read_and_write_pass(self):
        expected = self.root.resolve() / "findings" / "F-001-x.md"
        self.assertEqual(notebook.readable_path(self.root, "findings/F-001-x.md"), expected)
        self.assertEqual(notebook.writable_path(self.root, self.logdir, "findings/F-001-x.md"),
                         expected)

    def test_log_read_passes(self):
        resolved = notebook.readable_log_path(self.logdir, "alice_20261107T0900Z.log")
        self.assertEqual(resolved, self.logdir.resolve() / "alice_20261107T0900Z.log")

    def test_log_write_outside_root_fails(self):
        log = self.logdir / "alice_20261107T0900Z.log"
        self.assert_refused(lambda: notebook.writable_path(self.root, self.logdir, log), str(log))

    def test_log_write_inside_root_fails(self):
        # $LOGDIR may point into the working copy; it is still read-only.
        logdir = self.root / "logs"
        self.assert_refused(
            lambda: notebook.writable_path(self.root, logdir, "logs/alice.log"), "logs/alice.log")

    def test_incoming_write_fails_but_read_passes(self):
        path = "incoming/bob/findings/F-002-y.md"
        self.assertEqual(notebook.readable_path(self.root, path), self.root.resolve() / path)
        self.assert_refused(lambda: notebook.writable_path(self.root, self.logdir, path), path)

    def test_write_through_link_into_incoming_fails(self):
        (self.root / "bob-link").symlink_to(self.root / "incoming" / "bob")
        path = "bob-link/findings/F-002-y.md"
        self.assert_refused(lambda: notebook.writable_path(self.root, self.logdir, path), path)

    def test_write_where_linked_incoming_points_fails(self):
        # incoming/ is itself a link, so its files really live in shared/.
        root = support.make_worktree(self, {"shared/bob/findings/F-002-y.md": "y\n"})
        (root / "incoming").symlink_to(root / "shared")
        path = "shared/bob/findings/F-002-y.md"
        self.assert_refused(lambda: notebook.writable_path(root, self.logdir, path), path)

    def test_write_where_linked_logdir_points_fails(self):
        # $LOGDIR is a link to logs/ inside the root.
        (self.root / "logs").mkdir()
        (self.root / "loglink").symlink_to(self.root / "logs")
        self.assert_refused(
            lambda: notebook.writable_path(self.root, self.root / "loglink", "logs/a.log"),
            "logs/a.log")

    def test_dot_dot_fails(self):
        self.assert_refused(lambda: notebook.readable_path(self.root, "../x.md"), "../x.md")

    def test_absolute_outside_fails(self):
        target = str(self.outside / "secret.md")
        self.assert_refused(lambda: notebook.writable_path(self.root, self.logdir, target), target)

    def test_symlink_resolving_outside_fails(self):
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(self.outside)
        self.assert_refused(
            lambda: notebook.readable_path(self.root, "field-notes/alice/secret.md"),
            "field-notes/alice/secret.md")

    # Path.resolve() raises ValueError for a NUL byte; each wrapper turns it
    # into the same RootError as any other refused path, naming it.
    NUL_PATH = "findings/F-001\x00.md"

    def test_nul_byte_read_is_refused(self):
        self.assert_refused(lambda: notebook.readable_path(self.root, self.NUL_PATH),
                            "F-001\\x00.md")

    def test_nul_byte_log_read_is_refused(self):
        self.assert_refused(lambda: notebook.readable_log_path(self.logdir, self.NUL_PATH),
                            "F-001\\x00.md")

    def test_nul_byte_write_is_refused(self):
        self.assert_refused(
            lambda: notebook.writable_path(self.root, self.logdir, self.NUL_PATH),
            "F-001\\x00.md")

    def test_symlink_inside_root_passes(self):
        (self.root / "latest").symlink_to(self.root / "findings")
        expected = self.root.resolve() / "findings" / "F-001-x.md"
        self.assertEqual(notebook.readable_path(self.root, "latest/F-001-x.md"), expected)
        self.assertEqual(notebook.writable_path(self.root, self.logdir, "latest/F-001-x.md"),
                         expected)


def file_bytes(root):
    """Return every file under root as {relative path: bytes}, to spot any change."""
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*")) if path.is_file()}


class ServerTestCase(unittest.TestCase):
    """Starts a real notebook server on 127.0.0.1 for each test; no tests of its own."""

    def setUp(self):
        self.root = support.make_worktree(self, {"findings/F-001-x.md": "original\n"})
        # Fake routes stand in for the real ones the feature tasks add: the
        # POST one changes a file, so a refused POST must leave it unchanged.
        self.calls = []
        routes = {"/test-read": self.fake_get}
        posts = {"/test-write": self.fake_post}
        for patcher in [mock.patch.dict(notebook.GET_ROUTES, routes),
                        mock.patch.dict(notebook.POST_ROUTES, posts)]:
            patcher.start()
            self.addCleanup(patcher.stop)
        # Port 0 lets the OS pick a free port; the address is always 127.0.0.1.
        self.server = HTTPServer(("127.0.0.1", 0), notebook.NotebookHandler)
        self.server.token = notebook.make_token()
        # Resolved, as load_settings() does for a real run.
        self.logdir = support.make_worktree(self)
        self.server.settings = {"root": self.root.resolve(), "name": "alice",
                                "logdir": self.logdir.resolve()}
        self.port = self.server.server_address[1]
        # A short poll interval keeps shutdown() quick at the end of each test.
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.before = file_bytes(self.root)

    def fake_get(self, handler):
        self.calls.append("GET")
        notebook.send_text(handler, 200, "ok")

    def fake_post(self, handler):
        self.calls.append("POST")
        (self.root / "findings" / "F-001-x.md").write_text("changed\n", encoding="utf-8")
        notebook.send_text(handler, 200, "ok")

    def send_full(self, method, path, host, token=None):
        """Send one request with exactly these headers; return (response, body text).

        `host` is one Host value, or a list to send the header more than once.
        """
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest(method, path, skip_host=True)
        for value in host if isinstance(host, list) else [host]:
            connection.putheader("Host", value)
        if token is not None:
            connection.putheader("X-CPTC-Token", token)
        connection.putheader("Content-Length", "0")
        connection.endheaders()
        response = connection.getresponse()
        return response, response.read().decode("utf-8")

    def send(self, method, path, host, token=None):
        """Like send_full(), but return (status, body text)."""
        response, body = self.send_full(method, path, host, token)
        return response.status, body

    def assert_refused(self, method, host, token=None):
        path = "/test-read" if method == "GET" else "/test-write"
        status, body = self.send(method, path, host, token)
        self.assertEqual((status, body), (403, "refused: use http://127.0.0.1:" + str(self.port)))
        self.assertEqual(self.calls, [])
        self.assertEqual(file_bytes(self.root), self.before)

    def good_host(self):
        return "127.0.0.1:" + str(self.port)

    def assert_safe_headers(self, response):
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
        cors = [name for name, _ in response.getheaders()
                if name.lower().startswith("access-control-")]
        self.assertEqual(cors, [])


class RequestGuardTests(ServerTestCase):
    def test_wrong_host_get_is_refused(self):
        self.assert_refused("GET", "evil.example:" + str(self.port))

    def test_localhost_name_is_refused(self):
        self.assert_refused("GET", "localhost:" + str(self.port))

    def test_host_without_port_is_refused(self):
        self.assert_refused("GET", "127.0.0.1")

    def test_second_host_header_is_refused(self):
        self.assert_refused("GET", [self.good_host(), "evil.example:" + str(self.port)])

    def test_wrong_host_post_with_token_is_refused(self):
        self.assert_refused("POST", "evil.example:" + str(self.port), self.server.token)

    def test_post_without_token_is_refused(self):
        self.assert_refused("POST", self.good_host())

    def test_post_with_wrong_token_is_refused(self):
        self.assert_refused("POST", self.good_host(), "not-the-token")

    def test_non_ascii_token_is_refused_not_crashed(self):
        self.assert_refused("POST", self.good_host(), "t\u00e9st")

    def test_exact_host_get_and_token_post_succeed(self):
        self.assertEqual(self.send("GET", "/test-read", self.good_host()), (200, "ok"))
        self.assertEqual(self.send("POST", "/test-write", self.good_host(), self.server.token),
                         (200, "ok"))
        self.assertEqual(self.calls, ["GET", "POST"])
        self.assertEqual(file_bytes(self.root)["findings/F-001-x.md"], b"changed\n")

    def test_other_methods_get_a_plain_501(self):
        # Only GET and POST have routes (Chunk N1 D3): any other method gets
        # the server's 501 as plain text with the safety headers, whatever
        # the Host. That its connection closes is tested below.
        for method in ["PUT", "OPTIONS", "HEAD", "BREW"]:
            for host in [self.good_host(), "evil.example:" + str(self.port)]:
                with self.subTest(method=method, host=host):
                    response, body = self.send_full(method, "/test-write", host,
                                                    self.server.token)
                    self.assertEqual(response.status, 501)
                    self.assertEqual(response.getheader("Content-Type"),
                                     "text/plain; charset=utf-8")
                    self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
                    self.assertEqual(response.getheader("X-Frame-Options"), "DENY")
                    # http.client never reads a HEAD response's body; the
                    # raw-socket test below checks it is empty.
                    if method != "HEAD":
                        self.assertEqual(body, "Unsupported method ('" + method + "')")
        self.assertEqual(self.calls, [])
        self.assertEqual(file_bytes(self.root), self.before)

    def test_head_501_has_no_body(self):
        # HTTP says a HEAD response has headers only.
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall(("HEAD / HTTP/1.0\r\nHost: " + self.good_host()
                          + "\r\n\r\n").encode("ascii"))
            reply = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply += chunk
        head, separator, body = reply.partition(b"\r\n\r\n")
        self.assertTrue(head.startswith(b"HTTP/1.0 501"), head)
        self.assertEqual(separator, b"\r\n\r\n")
        self.assertEqual(body, b"")

    def send_with_smuggled_get(self, method):
        """Send `method` with a wrong Host whose unread body is a whole GET
        with the right Host, on an HTTP/1.1 (kept-open) server; return the
        raw reply. If the connection stayed open, the server would answer
        that GET too, past the Host check."""
        smuggled = ("GET /test-read HTTP/1.1\r\nHost: " + self.good_host()
                    + "\r\n\r\n").encode("ascii")
        request = (method + " /test-write HTTP/1.1\r\nHost: evil.example:" + str(self.port)
                   + "\r\nContent-Length: " + str(len(smuggled)) + "\r\n\r\n").encode("ascii")
        reply = b""
        with mock.patch.object(notebook.NotebookHandler, "protocol_version", "HTTP/1.1"), \
                socket.create_connection(("127.0.0.1", self.port), timeout=2) as sock:
            sock.sendall(request + smuggled)
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    reply += chunk
            except socket.timeout:
                # If the connection stays open, the read ends here instead
                # of at a close.
                pass
        return reply

    def test_refused_request_body_is_never_read_as_a_second_request(self):
        reply = self.send_with_smuggled_get("POST")
        self.assertEqual(reply.count(b"HTTP/1.1 "), 1)
        self.assertTrue(reply.startswith(b"HTTP/1.1 403"))
        self.assertEqual(self.calls, [])

    def test_501_body_is_never_read_as_a_second_request(self):
        for method in ["PUT", "OPTIONS", "HEAD", "BREW"]:
            with self.subTest(method=method):
                reply = self.send_with_smuggled_get(method)
                self.assertEqual(reply.count(b"HTTP/1.1 "), 1)
                self.assertTrue(reply.startswith(b"HTTP/1.1 501"))
        self.assertEqual(self.calls, [])

    def test_tokens_differ_each_run(self):
        self.assertNotEqual(notebook.make_token(), notebook.make_token())
        self.assertGreaterEqual(len(notebook.make_token()), 43)


class ResponseHeaderTests(ServerTestCase):
    DATA_TYPES = ["application/json", "text/plain; charset=utf-8"]

    def fake_json(self, handler):
        notebook.send_json(handler, 200, {"files": ["findings/F-001-x.md"]})

    def fake_log(self, handler):
        notebook.send_text(handler, 200, "<script>alert(1)</script>\n")

    def test_every_built_route_only_slash_is_html(self):
        # The real route tables, not the fake routes: every route a feature
        # task adds is checked here automatically.
        routes = [(method, path)
                  for method, table in [("GET", notebook.GET_ROUTES), ("POST", notebook.POST_ROUTES)]
                  for path in table if not path.startswith("/test-")]
        self.assertIn(("GET", "/"), routes)
        for method, path in routes:
            with self.subTest(method=method, path=path):
                response, _ = self.send_full(method, path, self.good_host(), self.server.token)
                self.assert_safe_headers(response)
                content_type = response.getheader("Content-Type")
                if path == "/":
                    self.assertEqual(content_type, "text/html; charset=utf-8")
                else:
                    self.assertIn(content_type, self.DATA_TYPES)

    def test_helpers_send_data_types_never_html(self):
        with mock.patch.dict(notebook.GET_ROUTES, {"/test-json": self.fake_json,
                                                   "/test-log": self.fake_log}):
            response, body = self.send_full("GET", "/test-json", self.good_host())
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            self.assertEqual(json.loads(body), {"files": ["findings/F-001-x.md"]})
            self.assert_safe_headers(response)
            # A <script> in a log goes out as plain text, so it never runs.
            response, body = self.send_full("GET", "/test-log", self.good_host())
            self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
            self.assertEqual(body, "<script>alert(1)</script>\n")
            self.assert_safe_headers(response)

    def test_refusals_and_errors_have_the_headers(self):
        wrong_host = "evil.example:" + str(self.port)
        for method, path, host, status in [("GET", "/test-read", wrong_host, 403),
                                           ("POST", "/test-write", self.good_host(), 403),
                                           ("GET", "/nothing-here", self.good_host(), 404),
                                           ("PUT", "/", self.good_host(), 501)]:
            with self.subTest(method=method, path=path):
                response, _ = self.send_full(method, path, host)
                self.assertEqual(response.status, status)
                self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
                self.assert_safe_headers(response)

    def test_stdlib_error_is_text_with_the_headers(self):
        # Over 100 headers gets the server's own 431, which would otherwise
        # be an HTML page without the safety headers.
        with socket.create_connection(("127.0.0.1", self.port), timeout=5) as sock:
            sock.sendall(b"GET / HTTP/1.0\r\n" + b"X-Filler: x\r\n" * 101 + b"\r\n")
            reply = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                reply += chunk
        head, _, body = reply.decode("utf-8").partition("\r\n\r\n")
        lines = head.split("\r\n")
        self.assertTrue(lines[0].startswith("HTTP/1.0 431"), lines[0])
        headers = dict(line.split(": ", 1) for line in lines[1:])
        self.assertEqual(headers["Content-Type"], "text/plain; charset=utf-8")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual([name for name in headers if name.lower().startswith("access-control-")], [])
        self.assertNotIn("<", body)


class ChecklistTests(ServerTestCase):
    """N2-01: checklists are listed and read live from disk, read only."""

    FIRST = "# AD checklist\n\n- [ ] Run the fake scan\n<script>alert(1)</script>\r\n"

    def setUp(self):
        super().setUp()
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {"secret.md": "outside secret\n"})

    def write(self, relative_path, text):
        support.write_fake_file(self.root, relative_path, text)

    def get_list(self):
        response, body = self.send_full("GET", "/checklists", self.good_host())
        self.assertEqual(response.status, 200)
        self.assertEqual(response.getheader("Content-Type"), "application/json")
        self.assert_safe_headers(response)
        return json.loads(body)["checklists"]

    def get_checklist(self, path):
        """GET one checklist; return (response, body text)."""
        return self.send_full("GET", "/checklist?path=" + quote(path), self.good_host())

    def assert_read(self, path, text):
        response, body = self.get_checklist(path)
        self.assertEqual((response.status, body), (200, text))
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        self.assert_safe_headers(response)

    def assert_read_refused(self, path, named):
        response, body = self.get_checklist(path)
        self.assertEqual(response.status, 403)
        self.assertTrue(body.startswith("refused: "), body)
        self.assertIn(named, body)
        self.assertNotIn("outside secret", body)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        self.assert_safe_headers(response)

    def test_checklists_sort_by_name(self):
        # Created in reverse order, so the list can't just follow the disk.
        self.write("checklists/20-web.md", "web\n")
        self.write("checklists/10-ad.md", "ad\n")
        expected = ["checklists/10-ad.md", "checklists/20-web.md"]
        self.assertEqual(notebook.list_checklists(self.root), expected)
        self.assertEqual(self.get_list(), expected)

    def test_missing_folder_is_an_empty_list(self):
        self.assertEqual(notebook.list_checklists(self.root), [])
        self.assertEqual(self.get_list(), [])

    def test_only_md_files_directly_in_the_folder_are_listed(self):
        self.write("checklists/10-ad.md", "ad\n")
        self.write("checklists/notes.txt", "not markdown\n")
        self.write("checklists/old/90-old.md", "in a subfolder\n")
        (self.root / "checklists" / "folder.md").mkdir()
        self.assertEqual(self.get_list(), ["checklists/10-ad.md"])

    def test_subfolder_checklist_is_not_read(self):
        self.write("checklists/old/90-old.md", "in a subfolder\n")
        self.assert_read_refused("checklists/old/90-old.md", "not a checklist: checklists/old/90-old.md")

    def test_other_file_in_the_root_is_not_read(self):
        self.assert_read_refused("findings/F-001-x.md", "not a checklist: findings/F-001-x.md")

    def test_listed_checklist_reads_its_exact_text(self):
        self.write("checklists/10-ad.md", self.FIRST)
        self.assert_read("checklists/10-ad.md", self.FIRST)

    def test_edit_on_disk_shows_on_the_next_read(self):
        self.write("checklists/10-ad.md", self.FIRST)
        self.assert_read("checklists/10-ad.md", self.FIRST)
        self.write("checklists/10-ad.md", "- [ ] A new task\n")
        self.assert_read("checklists/10-ad.md", "- [ ] A new task\n")

    def test_listing_and_reading_change_no_bytes(self):
        self.write("checklists/10-ad.md", self.FIRST)
        before = file_bytes(self.root)
        self.get_list()
        self.assert_read("checklists/10-ad.md", self.FIRST)
        self.assert_read("checklists/10-ad.md", self.FIRST)
        self.assertEqual(file_bytes(self.root), before)

    def test_symlink_inside_root_is_read_live(self):
        self.write("shared/10-ad.md", "first\n")
        (self.root / "checklists").mkdir()
        (self.root / "checklists" / "10-ad.md").symlink_to(self.root / "shared" / "10-ad.md")
        self.assertEqual(self.get_list(), ["checklists/10-ad.md"])
        self.assert_read("checklists/10-ad.md", "first\n")
        self.write("shared/10-ad.md", "second\n")
        self.assert_read("checklists/10-ad.md", "second\n")

    def test_linked_folder_inside_root_lists_and_reads(self):
        self.write("shared/10-ad.md", "ad\n")
        (self.root / "checklists").symlink_to(self.root / "shared")
        self.assertEqual(self.get_list(), ["checklists/10-ad.md"])
        self.assert_read("checklists/10-ad.md", "ad\n")

    def test_linked_folder_outside_root_is_refused_without_its_names(self):
        (self.root / "checklists").symlink_to(self.outside)
        response, body = self.send_full("GET", "/checklists", self.good_host())
        self.assertEqual(response.status, 403)
        self.assertTrue(body.startswith("refused: path is outside the root: checklists -> "), body)
        self.assertNotIn("secret.md", body)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        self.assert_safe_headers(response)
        self.assert_read_refused("checklists/secret.md", "outside the root: checklists/secret.md")

    def test_symlink_pointing_outside_is_refused(self):
        (self.root / "checklists").mkdir()
        (self.root / "checklists" / "10-ad.md").symlink_to(self.outside / "secret.md")
        self.assert_read_refused("checklists/10-ad.md", "outside the root: checklists/10-ad.md")

    def test_dot_dot_is_refused(self):
        self.write("checklists/10-ad.md", "ad\n")
        self.assert_read_refused("checklists/../../secret.md", "'..': checklists/../../secret.md")

    def test_absolute_outside_path_is_refused(self):
        target = str(self.outside / "secret.md")
        self.assert_read_refused(target, "outside the root: " + target)

    def test_missing_or_repeated_path_gets_a_400(self):
        self.write("checklists/10-ad.md", "ad\n")
        for path in ["/checklist", "/checklist?path=",
                     "/checklist?path=checklists/10-ad.md&path=checklists/10-ad.md"]:
            with self.subTest(path=path):
                response, body = self.send_full("GET", path, self.good_host())
                self.assertEqual(response.status, 400)
                self.assertIn("give one checklist", body)
                self.assert_safe_headers(response)

    def test_nul_byte_in_the_path_is_refused_not_dropped(self):
        # Only a hand-typed URL can carry one; the answer must still be text.
        for route in ["/checklist", "/checklist-view"]:
            with self.subTest(route=route):
                response, body = self.send_full("GET", route + "?path=checklists/%00.md",
                                                self.good_host())
                self.assertEqual(response.status, 403)
                self.assertTrue(body.startswith("refused: "), body)
                self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
                self.assert_safe_headers(response)

    def test_bom_is_dropped_and_crlf_kept(self):
        # A checklist saved by Windows Notepad starts with a BOM.
        (self.root / "checklists").mkdir()
        (self.root / "checklists" / "10-ad.md").write_bytes(b"\xef\xbb\xbf# AD\r\n- [ ] Scan\r\n")
        self.assert_read("checklists/10-ad.md", "# AD\r\n- [ ] Scan\r\n")

    def test_windows_1252_file_gets_a_readable_error(self):
        (self.root / "checklists").mkdir()
        (self.root / "checklists" / "10-ad.md").write_bytes("- [ ] Café\n".encode("cp1252"))
        response, body = self.get_checklist("checklists/10-ad.md")
        self.assertEqual(response.status, 500)
        self.assertTrue(body.startswith("can't read the checklist: "), body)
        self.assertIn("10-ad.md is not UTF-8 text", body)
        self.assert_safe_headers(response)


class ChecklistRecordTests(unittest.TestCase):
    """N2-02: task lines become keyed records, every other line stays text (OQ-08)."""

    PATH = "checklists/10-ad.md"

    def records(self, text, path=PATH):
        return notebook.checklist_records(path, text)

    def tasks(self, text, path=PATH):
        return [record for record in self.records(text, path) if record["type"] == "task"]

    def keys(self, text, path=PATH):
        return [record["key"] for record in self.tasks(text, path)]

    def key(self, text, occurrence, path=PATH):
        return notebook.task_key(path, text, occurrence)

    def test_unticked_task_line(self):
        self.assertEqual(self.records("- [ ] Run the fake scan"), [
            {"type": "task", "key": '["checklists/10-ad.md", "Run the fake scan", 1]',
             "text": "Run the fake scan", "checked": False}])

    def test_ticked_task_line(self):
        self.assertEqual(self.records("- [x] Run the fake scan"), [
            {"type": "task", "key": '["checklists/10-ad.md", "Run the fake scan", 1]',
             "text": "Run the fake scan", "checked": True}])

    def test_repeated_text_gets_the_next_occurrence(self):
        text = "- [ ] Save evidence\n- [ ] Other task\nSome prose\n- [ ] Save evidence\n"
        self.assertEqual(self.keys(text), [self.key("Save evidence", 1),
                                           self.key("Other task", 1),
                                           self.key("Save evidence", 2)])

    def test_each_text_and_each_checklist_counts_from_one(self):
        text = "- [ ] A\n- [ ] B\n- [ ] A\n- [ ] B\n"
        self.assertEqual(self.keys(text), [self.key("A", 1), self.key("B", 1),
                                           self.key("A", 2), self.key("B", 2)])
        other = "checklists/20-web.md"
        self.assertEqual(self.keys("- [ ] A\n", other), [self.key("A", 1, other)])

    def test_same_text_in_two_checklists_gets_two_keys(self):
        first = self.keys("- [ ] Save evidence\n", "checklists/10-ad.md")
        second = self.keys("- [ ] Save evidence\n", "checklists/20-web.md")
        self.assertNotEqual(first, second)

    def test_unchanged_task_keeps_its_key_when_other_lines_change(self):
        before = self.keys("# AD\n- [ ] Run the scan\n- [ ] Save evidence\n")
        after = self.keys("# AD (edited)\n\nNew prose\n- [ ] Run the scan\n"
                          "- [ ] A new task\n- [ ] Save evidence\n")
        self.assertIn(before[0], after)
        self.assertIn(before[1], after)

    def test_edited_task_gets_a_new_unticked_key(self):
        old_keys = set(self.keys("- [ ] Run the scan\n"))
        # Any change to the text, even a space or a full stop, is a new task.
        for edited in ["- [ ] Run the scan.", "- [ ] Run  the scan", "- [ ] run the scan"]:
            with self.subTest(edited=edited):
                (task,) = self.tasks(edited)
                self.assertNotIn(task["key"], old_keys)
                self.assertFalse(task["checked"])

    def test_other_lines_stay_text_in_order(self):
        lines = ["# AD checklist", "", "Some **bold** prose", "> a quote",
                 "| a | b |", "- a plain bullet", "1. a numbered step"]
        self.assertEqual(self.records("\n".join(lines)),
                         [{"type": "text", "text": line} for line in lines])

    def test_task_inside_a_code_block_stays_text(self):
        lines = ["```", "- [ ] not a task", "```", "~~~", "- [x] not a task",
                 "```", "- [ ] still not a task", "~~~", "- [ ] A real task"]
        records = self.records("\n".join(lines))
        self.assertEqual([record["type"] for record in records], ["text"] * 8 + ["task"])

    def test_shorter_fence_inside_a_longer_one_doesnt_end_it(self):
        lines = ["````", "```", "- [ ] not a task", "````", "- [ ] A real task"]
        records = self.records("\n".join(lines))
        self.assertEqual([record["type"] for record in records], ["text"] * 4 + ["task"])

    def test_fence_with_text_after_it_doesnt_end_a_block(self):
        lines = ["```", "```python", "- [ ] not a task", "```", "- [ ] A real task"]
        records = self.records("\n".join(lines))
        self.assertEqual([record["type"] for record in records], ["text"] * 4 + ["task"])

    def test_four_space_indented_fence_starts_no_block(self):
        # Four spaces make an indented code line, not a fence; three still fence.
        records = self.records("    ```\n- [ ] A real task\n   ```\n- [ ] not a task\n")
        self.assertEqual([record["type"] for record in records],
                         ["text", "task", "text", "text", "text"])

    def test_near_misses_stay_text(self):
        for line in ["  - [ ] indented", "* [ ] star bullet", "- [X] capital X",
                     "- [] no space", "- [ ]no space after", "- [ ] ", "- [ ]",
                     "-  [ ] two spaces", "- [y] other mark"]:
            with self.subTest(line=line):
                self.assertEqual(self.records(line), [{"type": "text", "text": line}])

    def test_windows_line_endings_keep_the_same_keys(self):
        lf = "# AD\n- [ ] Run the scan\n- [x] Save evidence\n"
        self.assertEqual(self.records(lf.replace("\n", "\r\n")), self.records(lf))

    def test_reading_and_parsing_change_no_bytes(self):
        root = support.make_worktree(self)
        path = root / "checklists" / "10-ad.md"
        path.parent.mkdir()
        path.write_bytes(b"# AD\r\n- [ ] Run the scan\r\n- [x] Save evidence\r\n")
        before = file_bytes(root)
        tasks = self.tasks(notebook.read_checklist(root, self.PATH))
        self.assertEqual([task["text"] for task in tasks], ["Run the scan", "Save evidence"])
        self.assertEqual(file_bytes(root), before)


class ChecklistStateTests(unittest.TestCase):
    """N2-03: ticks are saved to field-notes/<name>/checklist-state.json."""

    STATE = "field-notes/alice/checklist-state.json"
    CHECKLIST = "- [ ] Run the scan\n- [x] Save evidence\n"

    def setUp(self):
        self.root = support.make_worktree(self, {"checklists/10-ad.md": self.CHECKLIST})
        self.logdir = support.make_worktree(self, {"alice_20261107T0900Z.log": "log\n"})
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self)

    def save(self, state):
        notebook.save_checklist_state(self.root, self.logdir, "alice", state)

    def load(self):
        return notebook.load_checklist_state(self.root, "alice")

    def tasks(self, text):
        return [record for record in notebook.checklist_records("checklists/10-ad.md", text)
                if record["type"] == "task"]

    def assert_state_error(self, call, text):
        with self.assertRaises(notebook.StateError) as caught:
            call()
        self.assertIn(self.STATE, str(caught.exception))
        self.assertIn(text, str(caught.exception))

    def assert_save_refused(self, named):
        before = file_bytes(self.root)
        with self.assertRaises(compile.RootError) as caught:
            self.save({"k": True})
        self.assertIn(named, str(caught.exception))
        self.assertEqual(file_bytes(self.root), before)
        self.assertEqual(file_bytes(self.outside), {})

    def test_nothing_saved_yet_is_empty(self):
        self.assertEqual(self.load(), {})

    def test_save_makes_the_folders_and_writes_only_the_state_file(self):
        before = file_bytes(self.root)
        self.save({"k": True})
        after = file_bytes(self.root)
        # One new file, and no temp file left behind.
        self.assertEqual(set(after) - set(before), {self.STATE})
        self.assertEqual({path: after[path] for path in before}, before)

    def test_ticks_and_unticks_survive_a_reload(self):
        keys = [task["key"] for task in self.tasks(self.CHECKLIST)]
        self.save({keys[0]: True, keys[1]: False})
        self.assertEqual(self.load(), {keys[0]: True, keys[1]: False})
        self.save({keys[0]: False, keys[1]: True})
        self.assertEqual(self.load(), {keys[0]: False, keys[1]: True})

    def test_saved_tick_wins_over_the_file_mark_both_ways(self):
        unticked, ticked = self.tasks(self.CHECKLIST)
        state = {unticked["key"]: True, ticked["key"]: False}
        self.assertTrue(notebook.task_checked(unticked, state))
        self.assertFalse(notebook.task_checked(ticked, state))

    def test_unsaved_task_shows_the_file_mark(self):
        unticked, ticked = self.tasks(self.CHECKLIST)
        self.assertFalse(notebook.task_checked(unticked, {}))
        self.assertTrue(notebook.task_checked(ticked, {}))

    def test_edited_task_doesnt_keep_the_old_tick(self):
        unticked, ticked = self.tasks(self.CHECKLIST)
        state = {unticked["key"]: True, ticked["key"]: False}
        edited_unticked, edited_ticked = self.tasks("- [ ] Run the scan.\n- [x] Save evidence!\n")
        self.assertFalse(notebook.task_checked(edited_unticked, state))
        self.assertTrue(notebook.task_checked(edited_ticked, state))

    def test_broken_json_is_a_readable_error(self):
        support.write_fake_file(self.root, self.STATE, '{"k": tru')
        self.assert_state_error(self.load, "can't be read")

    def test_non_utf8_file_is_a_readable_error(self):
        support.write_fake_file(self.root, self.STATE, "")
        (self.root / self.STATE).write_bytes('{"café": true}'.encode("cp1252"))
        self.assert_state_error(self.load, "can't be read")

    def test_wrong_shape_is_refused(self):
        for text in ["[]", '"ticks"', "null", '{"k": 1}', '{"k": "true"}', '{"k": null}']:
            with self.subTest(text=text):
                support.write_fake_file(self.root, self.STATE, text)
                self.assert_state_error(self.load, "")

    def test_wrong_shape_is_never_saved(self):
        before = file_bytes(self.root)
        for state in [[], {"k": 1}, {"k": "true"}, {1: True}, {True: True}, {None: False}]:
            with self.subTest(state=state):
                self.assert_state_error(lambda: self.save(state), "")
                # No state file and no temp file: nothing was written.
                self.assertEqual(file_bytes(self.root), before)

    def test_wrong_shape_never_replaces_a_saved_state(self):
        self.save({"k": True})
        before = file_bytes(self.root)
        self.assert_state_error(lambda: self.save({1: False}), "a task key is not text: 1")
        self.assertEqual(file_bytes(self.root), before)

    def test_linked_folder_inside_root_is_used(self):
        (self.root / "shared" / "alice").mkdir(parents=True)
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(self.root / "shared" / "alice")
        self.save({"k": True})
        self.assertTrue((self.root / "shared" / "alice" / "checklist-state.json").is_file())
        self.assertEqual(self.load(), {"k": True})

    def test_linked_state_file_inside_root_is_refused(self):
        # DECISIONS 2026-10-28 Chunk N2 CR-1 (user, A): the state file itself
        # must be a plain file, even when its link stays inside the root.
        support.write_fake_file(self.root, "field-notes/bob/checklist-state.json",
                                '{"bob-key": true}')
        (self.root / "field-notes" / "alice").mkdir()
        (self.root / self.STATE).symlink_to(self.root / "field-notes" / "bob" /
                                            "checklist-state.json")
        self.assert_save_refused("is a link, not a plain file: " + self.STATE)
        with self.assertRaises(compile.RootError) as caught:
            self.load()
        self.assertIn("is a link, not a plain file: " + self.STATE, str(caught.exception))

    def test_linked_folder_outside_root_is_refused(self):
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(self.outside)
        self.assert_save_refused("outside the root: " + self.STATE)

    def test_linked_state_file_outside_root_is_refused(self):
        (self.root / "field-notes" / "alice").mkdir(parents=True)
        (self.root / self.STATE).symlink_to(self.outside / "state.json")
        self.assert_save_refused("outside the root: " + self.STATE)

    def test_linked_folder_into_incoming_is_refused(self):
        (self.root / "incoming" / "bob").mkdir(parents=True)
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(self.root / "incoming" / "bob")
        self.assert_save_refused("incoming/ is read-only, not writing: " + self.STATE)

    def test_linked_folder_into_the_log_folder_is_refused(self):
        # $LOGDIR may point into the working copy; it is still read-only.
        self.logdir = self.root / "logs"
        self.logdir.mkdir()
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(self.logdir)
        self.assert_save_refused("the log folder is read-only, not writing: " + self.STATE)

    def test_failed_save_keeps_the_old_state_and_no_temp_file(self):
        self.save({"k": True})
        before = file_bytes(self.root)
        with mock.patch.object(notebook.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                self.save({"k": False})
        self.assertEqual(file_bytes(self.root), before)
        self.assertEqual(self.load(), {"k": True})

    def test_loading_and_saving_change_no_checklist_bytes(self):
        before = file_bytes(self.root / "checklists")
        self.load()
        self.save({task["key"]: True for task in self.tasks(self.CHECKLIST)})
        self.load()
        self.assertEqual(file_bytes(self.root / "checklists"), before)


class ChecklistViewTests(ServerTestCase):
    """N2-04: the checklist view's data and the tick POST behind its checkboxes."""

    STATE = "field-notes/alice/checklist-state.json"
    CHECKLIST = "# AD\n<script>alert(1)</script>\n- [ ] Run the scan\n- [x] Save evidence\n"

    def setUp(self):
        super().setUp()
        support.write_fake_file(self.root, "checklists/10-ad.md", self.CHECKLIST)
        self.scan_key = notebook.task_key("checklists/10-ad.md", "Run the scan", 1)
        self.evidence_key = notebook.task_key("checklists/10-ad.md", "Save evidence", 1)

    def view(self):
        response, body = self.send_full("GET", "/checklist-view?path=checklists/10-ad.md",
                                         self.good_host())
        self.assertEqual(response.status, 200, body)
        self.assertEqual(response.getheader("Content-Type"), "application/json")
        self.assert_safe_headers(response)
        return json.loads(body)

    def shown(self):
        """Return {task text: shown tick} from the view."""
        return {record["text"]: record["checked"]
                for record in self.view()["records"] if record["type"] == "task"}

    def post(self, body, token="default", host=None):
        """POST raw body bytes to the tick route; token is a value, a list
        (sent more than once), None (not sent) or "default" (this run's)."""
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/checklist-state", skip_host=True)
        connection.putheader("Host", host or self.good_host())
        tokens = [self.server.token] if token == "default" else token
        for value in tokens if isinstance(tokens, list) else ([] if tokens is None else [tokens]):
            connection.putheader("X-CPTC-Token", value)
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        self.assert_safe_headers(response)
        self.assertIn(response.getheader("Content-Type"),
                      ["application/json", "text/plain; charset=utf-8"])
        return response.status, text

    def tick(self, key, checked):
        return self.post(json.dumps({"key": key, "checked": checked}).encode("utf-8"))

    def assert_refused_unchanged(self, status_wanted, body, **post_options):
        before = file_bytes(self.root)
        status, text = self.post(body, **post_options)
        self.assertEqual(status, status_wanted, text)
        self.assertEqual(file_bytes(self.root), before)
        return text

    def test_view_lists_records_in_order_as_data(self):
        data = self.view()
        self.assertEqual(data["path"], "checklists/10-ad.md")
        self.assertIsNone(data["state_error"])
        self.assertEqual(data["records"], [
            {"type": "text", "text": "# AD"},
            # Sent as JSON data; the page shows it with textContent, so it never runs.
            {"type": "text", "text": "<script>alert(1)</script>"},
            {"type": "task", "key": self.scan_key, "text": "Run the scan", "checked": False},
            {"type": "task", "key": self.evidence_key, "text": "Save evidence", "checked": True},
            {"type": "text", "text": ""}])

    def test_view_errors_are_plain_text(self):
        for path, status in [("/checklist-view", 400),
                             ("/checklist-view?path=../x.md", 403),
                             ("/checklist-view?path=findings/F-001-x.md", 403)]:
            with self.subTest(path=path):
                response, _ = self.send_full("GET", path, self.good_host())
                self.assertEqual(response.status, status)
                self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
                self.assert_safe_headers(response)

    def test_saved_ticks_win_over_the_file_marks(self):
        support.write_fake_file(self.root, self.STATE, json.dumps(
            {self.scan_key: True, self.evidence_key: False}))
        self.assertEqual(self.shown(), {"Run the scan": True, "Save evidence": False})

    def test_tick_changes_one_key_and_keeps_the_rest(self):
        other_key = notebook.task_key("checklists/20-web.md", "Other task", 1)
        support.write_fake_file(self.root, self.STATE, json.dumps({other_key: True}))
        self.assertEqual(self.tick(self.scan_key, True),
                         (200, json.dumps({"key": self.scan_key, "checked": True})))
        self.assertEqual(notebook.load_checklist_state(self.root, "alice"),
                         {other_key: True, self.scan_key: True})
        self.assertEqual(self.shown(), {"Run the scan": True, "Save evidence": True})

    def test_tick_and_untick_leave_the_checklist_unchanged(self):
        before = (self.root / "checklists" / "10-ad.md").read_bytes()
        self.assertEqual(self.tick(self.evidence_key, False)[0], 200)
        self.assertEqual(self.shown(), {"Run the scan": False, "Save evidence": False})
        self.assertEqual(self.tick(self.evidence_key, True)[0], 200)
        self.assertEqual(self.shown(), {"Run the scan": False, "Save evidence": True})
        self.assertEqual((self.root / "checklists" / "10-ad.md").read_bytes(), before)

    def test_post_with_the_pages_token_succeeds(self):
        # Carry-forward (N1-08): the token the page carries is the one that works.
        _, page = self.send_full("GET", "/", self.good_host())
        parts = PageParts()
        parts.feed(page)
        body = json.dumps({"key": self.scan_key, "checked": True}).encode("utf-8")
        self.assertEqual(self.post(body, token=parts.tokens[0])[0], 200)

    def test_missing_token_is_refused(self):
        self.assert_refused_unchanged(403, b'{"key": "k", "checked": true}', token=None)

    def test_wrong_token_is_refused(self):
        self.assert_refused_unchanged(403, b'{"key": "k", "checked": true}', token="wrong")

    def test_repeated_token_is_refused(self):
        self.assert_refused_unchanged(403, b'{"key": "k", "checked": true}',
                                      token=[self.server.token, self.server.token])

    def test_wrong_host_is_refused(self):
        self.assert_refused_unchanged(403, b'{"key": "k", "checked": true}',
                                      host="evil.example:" + str(self.port))

    def test_bad_tick_bodies_are_refused(self):
        for body in [b'{"key": "k", "checked": tru', b"[]", b'"tick"',
                     b'{"key": "k"}', b'{"checked": true}',
                     b'{"key": "k", "checked": true, "extra": 1}',
                     b'{"key": 1, "checked": true}', b'{"key": null, "checked": true}',
                     b'{"key": "k", "checked": 1}', b'{"key": "k", "checked": "true"}',
                     b'{"key": "caf\xe9", "checked": true}', b""]:
            with self.subTest(body=body):
                text = self.assert_refused_unchanged(400, body)
                self.assertEqual(text, 'send {"key": "<task key>", "checked": true or false}')

    def test_oversized_tick_is_refused_unread(self):
        text = self.assert_refused_unchanged(400, b" " * (notebook.MAX_TICK_BYTES + 1))
        self.assertTrue(text.startswith("send one tick as JSON, at most "), text)

    def test_broken_state_file_refuses_the_tick_and_stays_unchanged(self):
        support.write_fake_file(self.root, self.STATE, '{"k": tru')
        text = self.assert_refused_unchanged(
            500, json.dumps({"key": self.scan_key, "checked": True}).encode("utf-8"))
        self.assertTrue(text.startswith("tick not saved: " + self.STATE + " can't be read"), text)

    def test_broken_state_file_still_shows_the_checklist(self):
        support.write_fake_file(self.root, self.STATE, '{"k": tru')
        data = self.view()
        self.assertTrue(data["state_error"].startswith(self.STATE + " can't be read"))
        self.assertEqual({record["text"]: record["checked"]
                          for record in data["records"] if record["type"] == "task"},
                         {"Run the scan": False, "Save evidence": True})

    def test_linked_state_file_refuses_the_tick(self):
        # The probe from Chunk N2 CR-1: alice's state file linked to bob's.
        support.write_fake_file(self.root, "field-notes/bob/checklist-state.json",
                                '{"bob-key": true}')
        (self.root / "field-notes" / "alice").mkdir()
        (self.root / self.STATE).symlink_to(self.root / "field-notes" / "bob" /
                                            "checklist-state.json")
        text = self.assert_refused_unchanged(
            403, json.dumps({"key": self.scan_key, "checked": True}).encode("utf-8"))
        self.assertEqual(text, "refused: the tick-state file is a link, not a plain file: "
                         + self.STATE)

    def test_refused_state_path_is_a_403(self):
        outside = support.make_worktree(self)
        (self.root / "field-notes").mkdir()
        (self.root / "field-notes" / "alice").symlink_to(outside)
        text = self.assert_refused_unchanged(
            403, json.dumps({"key": self.scan_key, "checked": True}).encode("utf-8"))
        self.assertTrue(text.startswith("refused: "), text)
        self.assertEqual(file_bytes(outside), {})


class OwnFileTests(ServerTestCase):
    """N2-05: the left column's list of the person's own files."""

    def setUp(self):
        super().setUp()
        # A fresh, empty working copy per test; the route uses it as the root.
        self.home = support.make_worktree(self)
        self.server.settings["root"] = self.home.resolve()
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {"secret.md": "outside\n"})

    def write(self, *paths):
        for path in paths:
            support.write_fake_file(self.home, path, "x\n")

    def get_files(self):
        """GET /files; check it is safe JSON that matches list_own_files()."""
        before = file_bytes(self.home)
        response, body = self.send_full("GET", "/files", self.good_host())
        self.assertEqual(response.status, 200, body)
        self.assertEqual(response.getheader("Content-Type"), "application/json")
        self.assert_safe_headers(response)
        self.assertEqual(file_bytes(self.home), before)
        data = json.loads(body)
        files, refused = notebook.list_own_files(self.home, "alice")
        self.assertEqual(data, {"files": files, "refused": refused})
        return data

    def test_no_folders_yet_is_an_empty_list(self):
        self.assertEqual(self.get_files(), {"files": [], "refused": []})
        self.assertEqual(list(self.home.iterdir()), [])

    def test_every_prefix_is_listed_in_filename_order(self):
        # Written out of order, so the list can't just follow the disk.
        self.write("field-notes/alice/SU-0915.md", "findings/F-002-sqli.md",
                   "field-notes/alice/NOTE-recon.md", "field-notes/alice/IR-001-outage.md",
                   "findings/F-001-default-creds.md", "field-notes/alice/INJ-press.md")
        self.assertEqual(self.get_files()["files"], [
            "findings/F-001-default-creds.md", "findings/F-002-sqli.md",
            "field-notes/alice/INJ-press.md", "field-notes/alice/IR-001-outage.md",
            "field-notes/alice/NOTE-recon.md", "field-notes/alice/SU-0915.md"])

    def test_sorted_by_filename_not_by_folder(self):
        # "field-notes/..." sorts before "findings/..." as a path, but by
        # filename "F-" comes before "NOTE-".
        self.write("field-notes/alice/NOTE-a.md", "findings/F-001-a.md")
        self.assertEqual(self.get_files()["files"],
                         ["findings/F-001-a.md", "field-notes/alice/NOTE-a.md"])

    def test_same_filename_in_both_folders_keeps_both(self):
        self.write("findings/NOTE-x.md", "field-notes/alice/NOTE-x.md")
        self.assertEqual(self.get_files()["files"],
                         ["field-notes/alice/NOTE-x.md", "findings/NOTE-x.md"])

    def test_other_peoples_and_shared_files_are_left_out(self):
        self.write("findings/F-001-a.md", "incoming/bob/findings/F-002-b.md",
                   "incoming/bob/field-notes/bob/NOTE-b.md", "notes/NOTE-study.md",
                   "field-notes/bob/NOTE-bob.md", "field-notes/NOTE-top.md", "NOTE-root.md")
        self.assertEqual(self.get_files()["files"], ["findings/F-001-a.md"])

    def test_other_files_subfolders_and_md_folders_are_left_out(self):
        # findings/old/F-001-a.md has the same name as a listed file, so a
        # search of subfolders would show F-001-a.md twice.
        self.write("findings/F-001-a.md", "findings/F-001-a.txt", "findings/old/F-001-a.md",
                   "findings/old/F-009-old.md", "field-notes/alice/screens/NOTE-x.md")
        (self.home / "field-notes" / "alice" / "NOTE-folder.md").mkdir()
        self.assertEqual(self.get_files()["files"], ["findings/F-001-a.md"])

    def test_links_inside_the_root_are_listed_by_their_own_path(self):
        self.write("shared/F-001-a.md", "elsewhere/NOTE-b.md")
        (self.home / "findings").symlink_to(self.home / "shared")
        (self.home / "field-notes" / "alice").mkdir(parents=True)
        (self.home / "field-notes" / "alice" / "NOTE-b.md").symlink_to(
            self.home / "elsewhere" / "NOTE-b.md")
        self.assertEqual(self.get_files(), {
            "files": ["findings/F-001-a.md", "field-notes/alice/NOTE-b.md"], "refused": []})

    def test_folder_linked_outside_is_refused_and_not_looked_into(self):
        self.write("field-notes/alice/NOTE-a.md")
        (self.home / "findings").symlink_to(self.outside)
        data = self.get_files()
        # The other folder still lists: one bad link doesn't hide the rest.
        self.assertEqual(data["files"], ["field-notes/alice/NOTE-a.md"])
        self.assertEqual(len(data["refused"]), 1)
        self.assertTrue(data["refused"][0].startswith("path is outside the root: findings -> "))
        self.assertNotIn("secret.md", json.dumps(data))

    def test_file_linked_outside_is_refused_not_listed(self):
        self.write("findings/F-001-a.md")
        (self.home / "findings" / "F-002-b.md").symlink_to(self.outside / "secret.md")
        data = self.get_files()
        self.assertEqual(data["files"], ["findings/F-001-a.md"])
        self.assertEqual(len(data["refused"]), 1)
        self.assertTrue(data["refused"][0].startswith(
            "path is outside the root: findings/F-002-b.md -> "))


class NewFileTypeTests(unittest.TestCase):
    """N3-01: the New file table, through new_file_type()."""

    def test_note(self):
        self.assertEqual(notebook.new_file_type("Note"), {
            "path": "field-notes/{name}/NOTE-{slug}.md",
            "needs_nnn": False,
            "template": None,
            "library": False,
        })

    def test_incident_report(self):
        self.assertEqual(notebook.new_file_type("Incident report"), {
            "path": "field-notes/{name}/IR-{nnn}-{slug}.md",
            "needs_nnn": True,
            "template": "templates/incident-report.md",
            "library": False,
        })

    def test_status_update(self):
        self.assertEqual(notebook.new_file_type("Status update"), {
            "path": "field-notes/{name}/SU-{slug}.md",
            "needs_nnn": False,
            "template": "templates/status-update.md",
            "library": False,
        })

    def test_inject_response(self):
        self.assertEqual(notebook.new_file_type("Inject response"), {
            "path": "field-notes/{name}/INJ-{slug}.md",
            "needs_nnn": False,
            "template": "templates/inject-response.md",
            "library": False,
        })

    def test_finding(self):
        # The default template; "library" says a findings-library/ entry may
        # be picked instead. No real library file is read here.
        self.assertEqual(notebook.new_file_type("Finding"), {
            "path": "findings/F-{nnn}-{slug}.md",
            "needs_nnn": True,
            "template": "templates/finding.md",
            "library": True,
        })

    def test_exactly_five_types(self):
        self.assertEqual(list(notebook.NEW_FILE_TYPES), [
            "Note", "Incident report", "Status update", "Inject response", "Finding"])

    def test_only_ir_and_finding_need_a_number(self):
        # needs_nnn and the {nnn} slot in the path must agree for every type.
        for type_name, entry in notebook.NEW_FILE_TYPES.items():
            with self.subTest(type_name=type_name):
                self.assertEqual(entry["needs_nnn"], "{nnn}" in entry["path"])
                self.assertEqual(entry["needs_nnn"], type_name in ["Incident report", "Finding"])

    def test_paths_use_fixed_folders_and_only_name_nnn_slug(self):
        # The folder is written in the table; the only parts filled in later
        # are the slugged name, the checked number and the slugged title.
        for type_name, entry in notebook.NEW_FILE_TYPES.items():
            with self.subTest(type_name=type_name):
                if type_name == "Finding":
                    self.assertTrue(entry["path"].startswith("findings/F-"))
                else:
                    self.assertTrue(entry["path"].startswith("field-notes/{name}/"))
                fields = {field for _, field, _, _ in string.Formatter().parse(entry["path"])
                          if field is not None}
                self.assertLessEqual(fields, {"name", "nnn", "slug"})
                self.assertIn("slug", fields)

    def test_named_templates_exist_in_the_repo(self):
        # Guards against a typo in a template path: each one is a real file.
        repo = support.TOOLS_DIR.parent
        templates = [entry["template"] for entry in notebook.NEW_FILE_TYPES.values()
                     if entry["template"] is not None]
        self.assertEqual(len(templates), 4)
        for template in templates:
            with self.subTest(template=template):
                self.assertTrue((repo / template).is_file())

    def test_unknown_type_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            notebook.new_file_type("Task")
        self.assertIn("unknown file type: 'Task'", str(caught.exception))
        self.assertIn("Note, Incident report, Status update, Inject response, Finding",
                      str(caught.exception))

    def test_near_misses_are_refused(self):
        for type_name in ["note", "NOTE", " Note", "Note ", "", "Incident Report", "finding"]:
            with self.subTest(type_name=type_name), self.assertRaises(ValueError):
                notebook.new_file_type(type_name)

    def test_a_type_that_isnt_text_is_refused(self):
        # A JSON body could send a list or null; a list would otherwise raise
        # TypeError ("unhashable") instead of the readable ValueError.
        for type_name in [None, 1, ["Note"], {"Note": 1}]:
            with self.subTest(type_name=type_name), self.assertRaises(ValueError):
                notebook.new_file_type(type_name)

    def test_changing_a_returned_entry_leaves_the_table_alone(self):
        entry = notebook.new_file_type("Note")
        entry["path"] = "../x.md"
        self.assertEqual(notebook.new_file_type("Note")["path"],
                         "field-notes/{name}/NOTE-{slug}.md")


class LibraryTests(unittest.TestCase):
    """N3-02: findings-library/ entries and their starting titles.

    Every test builds its own fake root, so the real findings-library/ is never read.
    """

    def setUp(self):
        self.home = support.make_worktree(self)
        # A second folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {
            "secret.md": support.make_library_entry(title="Outside secret title")})

    def write(self, path, text):
        support.write_fake_file(self.home, path, text)

    def write_bytes(self, path, data):
        (self.home / path).parent.mkdir(parents=True, exist_ok=True)
        (self.home / path).write_bytes(data)

    def listed(self):
        """list_library(), checking that it changed no file anywhere in the root."""
        before = file_bytes(self.home)
        result = notebook.list_library(self.home)
        self.assertEqual(file_bytes(self.home), before)
        return result

    def test_missing_folder_is_empty_and_creates_nothing(self):
        self.assertEqual(self.listed(), ([], []))
        self.assertEqual(list(self.home.iterdir()), [])

    def test_empty_folder_is_empty(self):
        (self.home / "findings-library").mkdir()
        self.assertEqual(self.listed(), ([], []))

    def test_readme_is_never_an_entry(self):
        self.write("findings-library/README.md", "# Findings library\n")
        self.assertEqual(self.listed(), ([], []))
        with self.assertRaises(compile.RootError) as caught:
            notebook.read_library_entry(self.home, "findings-library/README.md")
        self.assertIn("findings-library/README.md", str(caught.exception))

    def test_two_entries_and_their_titles(self):
        self.write("findings-library/smb-signing.md",
                   support.make_library_entry(title="SMB signing not required"))
        self.write("findings-library/default-creds.md",
                   support.make_library_entry(title="Default admin password"))
        self.write("findings-library/README.md", "# Findings library\n")
        self.assertEqual(self.listed(), ([
            {"path": "findings-library/default-creds.md", "title": "Default admin password"},
            {"path": "findings-library/smb-signing.md", "title": "SMB signing not required"},
        ], []))

    def test_sorted_whatever_order_the_disk_gives(self):
        # The Mac's disk happens to list names in order, so hand back the
        # listing reversed to prove the code sorts it itself.
        self.write("findings-library/a.md", support.make_library_entry(title="A"))
        self.write("findings-library/b.md", support.make_library_entry(title="B"))
        real_glob = notebook.Path.glob
        with mock.patch.object(notebook.Path, "glob",
                               lambda folder, pattern: reversed(sorted(real_glob(folder, pattern)))):
            self.assertEqual(notebook.library_paths(self.home),
                             ["findings-library/a.md", "findings-library/b.md"])

    def test_title_is_returned_exactly(self):
        # Punctuation, double spaces, a trailing space and non-ASCII text all stay.
        title = "Kerberoast: svc_sql (RC4) — weak  pässwörd | 100% "
        self.write("findings-library/a.md", support.make_library_entry(title=title))
        self.assertEqual(self.listed()[0], [{"path": "findings-library/a.md", "title": title}])

    def test_unfilled_title_marker_is_returned_as_written(self):
        # An entry copied straight from templates/finding.md: no title invented.
        self.write("findings-library/a.md", "### [[FINDING_ID]]: [[FINDING_TITLE]]\n")
        self.assertEqual(self.listed()[0][0]["title"], "[[FINDING_TITLE]]")

    def test_first_heading_wins_and_prose_before_it_is_ignored(self):
        self.write("findings-library/a.md",
                   "Some prose first.\n#1 is not a heading (no space after #).\n\n"
                   "### [[FINDING_ID]]: First title\n\n"
                   "### [[FINDING_ID]]: Second title\n")
        self.assertEqual(self.listed(), (
            [{"path": "findings-library/a.md", "title": "First title"}], []))

    def test_titles_and_paths_come_from_disk(self):
        self.write("findings-library/a.md", support.make_library_entry(title="Old title"))
        self.assertEqual(self.listed()[0], [{"path": "findings-library/a.md", "title": "Old title"}])
        (self.home / "findings-library/a.md").rename(self.home / "findings-library/b.md")
        self.write("findings-library/b.md", support.make_library_entry(title="New title"))
        self.assertEqual(self.listed()[0], [{"path": "findings-library/b.md", "title": "New title"}])

    def test_only_md_files_directly_in_the_folder(self):
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        self.write("findings-library/notes.txt", support.make_library_entry(title="Text file"))
        self.write("findings-library/old/nested.md", support.make_library_entry(title="Nested"))
        (self.home / "findings-library/folder.md").mkdir()
        self.assertEqual(self.listed(), (
            [{"path": "findings-library/good.md", "title": "Good"}], []))

    def test_wrong_first_heading_is_refused_and_named(self):
        # One bad entry is refused with its reason; the good one still lists.
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        self.write("findings-library/filled.md", "### F-001: Already numbered\n")
        self.write("findings-library/level.md", "## [[FINDING_ID]]: Wrong level\n")
        self.write("findings-library/top.md", "# Notes\n\n### [[FINDING_ID]]: Under a title\n")
        self.write("findings-library/spaces.md", "###  [[FINDING_ID]]: Two spaces\n")
        self.write("findings-library/none.md", "No heading at all.\n")
        self.write("findings-library/empty.md", "")
        entries, refused = self.listed()
        self.assertEqual(entries, [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(refused, [
            "findings-library/empty.md: no heading; a library entry starts with "
            "'### [[FINDING_ID]]: <title>'",
            "findings-library/filled.md: first heading doesn't start with "
            "'### [[FINDING_ID]]: ': '### F-001: Already numbered'",
            "findings-library/level.md: first heading doesn't start with "
            "'### [[FINDING_ID]]: ': '## [[FINDING_ID]]: Wrong level'",
            "findings-library/none.md: no heading; a library entry starts with "
            "'### [[FINDING_ID]]: <title>'",
            "findings-library/spaces.md: first heading doesn't start with "
            "'### [[FINDING_ID]]: ': '###  [[FINDING_ID]]: Two spaces'",
            "findings-library/top.md: first heading doesn't start with "
            "'### [[FINDING_ID]]: ': '# Notes'",
        ])

    def test_library_title_directly(self):
        self.assertEqual(notebook.library_title("x.md", "### [[FINDING_ID]]: T\n"), "T")
        with self.assertRaises(ValueError) as caught:
            notebook.library_title("findings-library/x.md", "## [[FINDING_ID]]: T\n")
        self.assertTrue(str(caught.exception).startswith("findings-library/x.md: "))

    def test_folder_link_inside_the_root_is_used(self):
        self.write("shared/library/a.md", support.make_library_entry(title="Linked folder"))
        (self.home / "findings-library").symlink_to(self.home / "shared/library")
        self.assertEqual(self.listed(), (
            [{"path": "findings-library/a.md", "title": "Linked folder"}], []))

    def test_folder_link_outside_the_root_is_refused(self):
        # DECISIONS 2026-10-29 Chunk N3 D1: the folder itself linked outside
        # is one refusal in the list, so the New form still opens.
        (self.home / "findings-library").symlink_to(self.outside)
        entries, refused = self.listed()
        self.assertEqual(entries, [])
        self.assertEqual(len(refused), 1)
        self.assertTrue(refused[0].startswith("path is outside the root: findings-library -> "),
                        refused[0])
        self.assertNotIn("secret.md", refused[0])
        self.assertNotIn("Outside secret title", refused[0])
        # library_paths() itself still refuses it, so a create can't read
        # an entry through the link.
        with self.assertRaises(compile.RootError):
            notebook.library_paths(self.home)

    def test_file_link_inside_the_root_is_listed_under_its_own_path(self):
        self.write("shared/real.md", support.make_library_entry(title="Target title"))
        (self.home / "findings-library").mkdir()
        (self.home / "findings-library/linked.md").symlink_to(self.home / "shared/real.md")
        self.assertEqual(self.listed(), (
            [{"path": "findings-library/linked.md", "title": "Target title"}], []))

    def test_file_link_outside_the_root_is_refused_not_read(self):
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        (self.home / "findings-library/linked.md").symlink_to(self.outside / "secret.md")
        entries, refused = self.listed()
        self.assertEqual(entries, [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(len(refused), 1)
        self.assertTrue(refused[0].startswith(
            "path is outside the root: findings-library/linked.md -> "))
        self.assertNotIn("Outside secret title", refused[0])

    def test_outside_link_is_checked_before_anything_follows_it(self):
        # is_file() follows a link, so it must never run on a link that the
        # path check hasn't passed yet (adversary, N3-02 round 1).
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        link = self.home / "findings-library/linked.md"
        link.symlink_to(self.outside / "secret.md")
        followed = []
        real_is_file = notebook.Path.is_file

        def recording_is_file(path):
            followed.append(path)
            return real_is_file(path)

        with mock.patch.object(notebook.Path, "is_file", recording_is_file):
            entries, refused = notebook.list_library(self.home)
        self.assertEqual(entries, [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(len(refused), 1)
        self.assertNotIn(link, followed)
        self.assertNotIn(self.outside / "secret.md", [path.resolve() for path in followed])

    def test_outside_link_to_a_folder_or_nothing_is_refused_not_dropped(self):
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        (self.home / "findings-library/to-folder.md").symlink_to(self.outside)
        (self.home / "findings-library/dangling.md").symlink_to(self.outside / "missing.md")
        entries, refused = self.listed()
        self.assertEqual(entries, [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(len(refused), 2)
        self.assertTrue(refused[0].startswith(
            "path is outside the root: findings-library/dangling.md -> "))
        self.assertTrue(refused[1].startswith(
            "path is outside the root: findings-library/to-folder.md -> "))

    def test_read_entry_refuses_a_folder_named_like_an_entry(self):
        (self.home / "findings-library/folder.md").mkdir(parents=True)
        with self.assertRaises(compile.RootError) as caught:
            notebook.read_library_entry(self.home, "findings-library/folder.md")
        self.assertIn("findings-library/folder.md", str(caught.exception))

    def test_read_entry_returns_the_text_unchanged(self):
        text = support.make_library_entry(title="Read me")
        self.write("findings-library/a.md", text)
        self.assertEqual(notebook.read_library_entry(self.home, "findings-library/a.md"), text)

    def test_read_entry_refuses_dot_dot(self):
        self.write("findings-library/a.md", support.make_library_entry())
        with self.assertRaises(compile.RootError) as caught:
            notebook.read_library_entry(self.home, "findings-library/../findings-library/a.md")
        self.assertIn("findings-library/../findings-library/a.md", str(caught.exception))

    def test_read_entry_refuses_an_absolute_path_outside(self):
        path = str(self.outside / "secret.md")
        with self.assertRaises(compile.RootError) as caught:
            notebook.read_library_entry(self.home, path)
        self.assertIn(path, str(caught.exception))

    def test_read_entry_refuses_a_nul_byte(self):
        self.write("findings-library/a.md", support.make_library_entry())
        with self.assertRaises(compile.RootError) as caught:
            notebook.read_library_entry(self.home, "findings-library/a.md\x00")
        self.assertIn("findings-library/a.md", str(caught.exception))

    def test_read_entry_refuses_a_file_outside_the_library(self):
        self.write("findings/F-001-x.md", support.make_library_entry())
        self.write("findings-library/old/nested.md", support.make_library_entry())
        for path in ["findings/F-001-x.md", "findings-library/old/nested.md"]:
            with self.subTest(path=path), self.assertRaises(compile.RootError) as caught:
                notebook.read_library_entry(self.home, path)
            self.assertIn(path, str(caught.exception))

    def test_bom_is_dropped(self):
        self.write_bytes("findings-library/a.md",
                         b"\xef\xbb\xbf### [[FINDING_ID]]: Saved by Notepad\n")
        self.assertEqual(self.listed()[0][0]["title"], "Saved by Notepad")

    def test_windows_line_ending_leaves_no_carriage_return(self):
        self.write_bytes("findings-library/a.md",
                         b"### [[FINDING_ID]]: Windows title\r\n\r\n#### Summary\r\n")
        self.assertEqual(self.listed()[0][0]["title"], "Windows title")

    def test_windows_1252_entry_is_refused_and_named(self):
        self.write("findings-library/good.md", support.make_library_entry(title="Good"))
        self.write_bytes("findings-library/cp1252.md", "### [[FINDING_ID]]: Café\n".encode("cp1252"))
        entries, refused = self.listed()
        self.assertEqual(entries, [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(len(refused), 1)
        self.assertIn("cp1252.md is not UTF-8 text", refused[0])


class NumberTests(unittest.TestCase):
    """N3-03: the F-NNN collision warning and the suggested IR number."""

    BAD_NUMBERS = ["6", "01", "1000", "abc", "00a", "123\n", "١٢٣", "0\x007", "", " 007"]

    def setUp(self):
        self.home = support.make_worktree(self)
        # A second folder stands in for "somewhere outside", still inside .tmp/.
        # It holds names that would change every result if they were followed.
        self.outside = support.make_worktree(self, {
            "F-007-outside.md": "x\n", "IR-500-outside.md": "x\n",
            "findings/F-007-outside.md": "x\n", "field-notes/eve/IR-500-outside.md": "x\n",
            "eve/IR-500-outside.md": "x\n"})

    def write(self, *paths):
        for path in paths:
            support.write_fake_file(self.home, path, "x\n")

    def link(self, path, target):
        (self.home / path).parent.mkdir(parents=True, exist_ok=True)
        (self.home / path).symlink_to(target)

    def warnings(self, nnn="007"):
        """finding_id_warnings(), checking that it changed and created nothing."""
        before = file_bytes(self.home)
        before_names = sorted(self.home.rglob("*"))
        result = notebook.finding_id_warnings(self.home, nnn)
        self.assertEqual(file_bytes(self.home), before)
        self.assertEqual(sorted(self.home.rglob("*")), before_names)
        return result

    def suggestion(self):
        """suggest_ir_number(), checking that it changed and created nothing."""
        before = file_bytes(self.home)
        before_names = sorted(self.home.rglob("*"))
        result = notebook.suggest_ir_number(self.home)
        self.assertEqual(file_bytes(self.home), before)
        self.assertEqual(sorted(self.home.rglob("*")), before_names)
        return result

    # Case 1 and 12: one number check for both types.

    def test_good_numbers_pass(self):
        for nnn in ["000", "006", "999"]:
            with self.subTest(nnn=nnn):
                self.assertEqual(notebook.validate_nnn(nnn), nnn)
                self.assertEqual(self.warnings(nnn), ([], []))

    def test_bad_numbers_fail(self):
        # IR and F numbers both go through validate_nnn(); the collision
        # check uses it too, so a bad number never reaches a file search.
        for nnn in self.BAD_NUMBERS:
            with self.subTest(nnn=nnn):
                with self.assertRaises(ValueError):
                    notebook.validate_nnn(nnn)
                with self.assertRaises(ValueError):
                    notebook.finding_id_warnings(self.home, nnn)

    def test_suggestion_is_not_reserved_and_can_be_replaced(self):
        self.write("field-notes/alice/IR-004-a.md")
        self.assertEqual(self.suggestion(), ("005", []))
        # Nothing was written, so the same suggestion comes back, and any
        # valid number may be typed instead.
        self.assertEqual(self.suggestion(), ("005", []))
        self.assertEqual(notebook.validate_nnn("006"), "006")
        with self.assertRaises(ValueError):
            notebook.validate_nnn("6")

    # Case 2: nothing there yet.

    def test_missing_folders(self):
        self.assertEqual(self.warnings(), ([], []))
        self.assertEqual(self.suggestion(), ("001", []))
        self.assertEqual(list(self.home.iterdir()), [])

    # Cases 3-7: finding collisions.

    def test_local_finding_collides(self):
        self.write("findings/F-007-old.md")
        self.assertEqual(self.warnings(), (
            ["F-007 already exists: findings/F-007-old.md"], []))

    def test_incoming_finding_collides_without_local_findings(self):
        self.write("incoming/alice/findings/F-007-other.md")
        self.assertEqual(self.warnings(), (
            ["F-007 already exists: incoming/alice/findings/F-007-other.md"], []))

    def test_every_collision_is_reported_in_path_order(self):
        self.write("incoming/zed/findings/F-007-z.md", "incoming/bob/findings/F-007-b.md",
                   "findings/F-007-mine.md", "incoming/bob/findings/F-007-a.md",
                   "findings/F-008-other.md")
        self.assertEqual(self.warnings(), ([
            "F-007 already exists: findings/F-007-mine.md",
            "F-007 already exists: incoming/bob/findings/F-007-a.md",
            "F-007 already exists: incoming/bob/findings/F-007-b.md",
            "F-007 already exists: incoming/zed/findings/F-007-z.md",
        ], []))

    def test_path_order_whatever_order_the_disk_gives(self):
        # The Mac's disk happens to list names in order, so hand back every
        # listing reversed to prove the code sorts them itself.
        self.write("incoming/bob/findings/F-007-a.md", "incoming/bob/findings/F-007-b.md",
                   "incoming/zed/findings/F-007-z.md", "incoming/eve/findings/F-007-e.md")
        self.link("incoming/zed-link", self.outside)
        self.link("incoming/amy-link", self.outside)
        real_glob, real_iterdir = notebook.Path.glob, notebook.Path.iterdir
        with mock.patch.object(notebook.Path, "glob",
                               lambda folder, pattern: reversed(sorted(real_glob(folder, pattern)))), \
                mock.patch.object(notebook.Path, "iterdir",
                                  lambda folder: reversed(sorted(real_iterdir(folder)))):
            warnings, refused = notebook.finding_id_warnings(self.home, "007")
        self.assertEqual(warnings, [
            "F-007 already exists: incoming/bob/findings/F-007-a.md",
            "F-007 already exists: incoming/bob/findings/F-007-b.md",
            "F-007 already exists: incoming/eve/findings/F-007-e.md",
            "F-007 already exists: incoming/zed/findings/F-007-z.md"])
        self.assertEqual(len(refused), 2)
        self.assertTrue(refused[0].startswith("path is outside the root: incoming/amy-link -> "))
        self.assertTrue(refused[1].startswith("path is outside the root: incoming/zed-link -> "))

    def test_refused_file_links_in_path_order_whatever_order_the_disk_gives(self):
        # File-level refusals come from glob(), so they need sorting too
        # (adversary, N3-03 round 1).
        self.link("findings/F-007-a.md", self.outside / "F-007-outside.md")
        self.link("findings/F-007-z.md", self.outside / "F-007-outside.md")
        self.link("field-notes/alice/IR-500-a.md", self.outside / "IR-500-outside.md")
        self.link("field-notes/alice/IR-500-z.md", self.outside / "IR-500-outside.md")
        real_glob = notebook.Path.glob
        with mock.patch.object(notebook.Path, "glob",
                               lambda folder, pattern: reversed(sorted(real_glob(folder, pattern)))):
            warnings, finding_refused = notebook.finding_id_warnings(self.home, "007")
            suggestion, ir_refused = notebook.suggest_ir_number(self.home)
        self.assertEqual((warnings, suggestion), ([], "001"))
        self.assertEqual(len(finding_refused), 2)
        self.assertTrue(finding_refused[0].startswith(
            "path is outside the root: findings/F-007-a.md -> "))
        self.assertTrue(finding_refused[1].startswith(
            "path is outside the root: findings/F-007-z.md -> "))
        self.assertEqual(len(ir_refused), 2)
        self.assertTrue(ir_refused[0].startswith(
            "path is outside the root: field-notes/alice/IR-500-a.md -> "))
        self.assertTrue(ir_refused[1].startswith(
            "path is outside the root: field-notes/alice/IR-500-z.md -> "))

    def test_no_collision(self):
        # An owner folder whose name holds "F-007" doesn't make its F-008 collide.
        self.write("findings/F-006-a.md", "incoming/bob/findings/F-008-b.md",
                   "incoming/F-007-team/findings/F-008-t.md")
        self.assertEqual(self.warnings(), ([], []))

    def test_near_miss_names_dont_collide(self):
        self.write("findings/F-070-a.md", "findings/F-0070-a.md", "findings/F-007x.md",
                   "findings/F-07-a.md", "findings/F-007-a.txt", "findings/F-007_a.md",
                   "findings/old/F-007-a.md", "F-007-top.md", "field-notes/alice/F-007-a.md",
                   "incoming/bob/F-007-a.md", "incoming/bob/findings/old/F-007-a.md",
                   "notes/F-007-a.md")
        (self.home / "findings/F-007-folder.md").mkdir()
        self.assertEqual(self.warnings(), ([], []))
        # The same folder with a correctly named file does collide; so does
        # a name with no slug, which compile.py reads as F-007 too.
        self.write("findings/F-007-real.md", "findings/F-007.md")
        self.assertEqual(self.warnings(), ([
            "F-007 already exists: findings/F-007-real.md",
            "F-007 already exists: findings/F-007.md"], []))

    # Cases 8-11 and 13: the suggested IR number.

    def test_first_ir_is_001(self):
        self.write("field-notes/alice/NOTE-a.md", "field-notes/alice/IR-xyz.md")
        self.assertEqual(self.suggestion(), ("001", []))

    def test_highest_across_local_and_incoming(self):
        self.write("field-notes/alice/IR-001-a.md", "incoming/bob/field-notes/bob/IR-004-b.md")
        self.assertEqual(self.suggestion(), ("005", []))

    def test_every_local_and_incoming_person_counts(self):
        # No name is built in: any field-notes/<name>/ counts, locally and
        # inside any incoming/<owner>/.
        self.write("field-notes/carol/IR-002-c.md",
                   "incoming/dave/field-notes/erin/IR-003-e.md")
        self.assertEqual(self.suggestion(), ("004", []))

    def test_numeric_maximum(self):
        # The highest is neither the first nor the last file scanned, and
        # appears twice; the next number is still suggested once.
        self.write("field-notes/alice/IR-009-a.md", "field-notes/alice/IR-010-b.md",
                   "incoming/bob/field-notes/bob/IR-010-c.md",
                   "incoming/zed/field-notes/zed/IR-003-z.md")
        self.assertEqual(self.suggestion(), ("011", []))

    def test_names_that_dont_count(self):
        self.write("field-notes/alice/IR-002-a.md",
                   "field-notes/alice/IR-01-a.md", "field-notes/alice/IR-1000-a.md",
                   "field-notes/alice/IR-abc.md", "field-notes/alice/IR-٠٠٩-a.md",
                   "field-notes/alice/ir-009-a.md", "field-notes/alice/SU-009-a.md",
                   "field-notes/alice/XIR-009-a.md", "field-notes/alice/IR-009-a.txt",
                   "field-notes/alice/IR-009x.md", "field-notes/alice/old/IR-009-a.md",
                   "field-notes/IR-009-a.md", "IR-009-a.md", "findings/IR-009-a.md",
                   "incoming/bob/IR-009-a.md", "incoming/bob/field-notes/IR-009-a.md",
                   "incoming/bob/findings/IR-009-a.md", "notes/IR-009-a.md")
        (self.home / "field-notes/alice/IR-009-folder.md").mkdir()
        self.assertEqual(self.suggestion(), ("003", []))

    def test_ir_without_a_slug_counts(self):
        self.write("field-notes/alice/IR-004.md")
        self.assertEqual(self.suggestion(), ("005", []))

    def test_999_in_use_leaves_nothing_to_suggest(self):
        self.write("field-notes/alice/IR-001-a.md", "incoming/bob/field-notes/bob/IR-999-z.md")
        self.assertEqual(self.suggestion(), (None, []))
        self.assertEqual(notebook.NO_IR_NUMBER_LEFT,
                         "IR-999 is in use, so there is no next three-digit IR number"
                         " to suggest: type one in.")
        # The field still takes any valid number the user types.
        self.assertEqual(notebook.validate_nnn("002"), "002")

    # Case 14: links that stay inside the root.

    def test_links_inside_the_root_count_under_their_own_paths(self):
        self.write("shared/bob/findings/F-007-b.md", "shared/carol/F-007-c.md",
                   "shared/real.md", "shared/notes/IR-006-n.md",
                   "shared/dave-notes/dave/IR-008-d.md")
        self.link("incoming/bob", self.home / "shared/bob")
        self.link("incoming/carol/findings", self.home / "shared/carol")
        self.link("findings/F-007-linked.md", self.home / "shared/real.md")
        self.link("field-notes/alice", self.home / "shared/notes")
        self.link("incoming/dave/field-notes", self.home / "shared/dave-notes")
        self.assertEqual(self.warnings(), ([
            "F-007 already exists: findings/F-007-linked.md",
            "F-007 already exists: incoming/bob/findings/F-007-b.md",
            "F-007 already exists: incoming/carol/findings/F-007-c.md"], []))
        self.assertEqual(self.suggestion(), ("009", []))

    def test_linked_ir_file_inside_the_root_counts(self):
        self.write("shared/real.md")
        self.link("field-notes/alice/IR-012-linked.md", self.home / "shared/real.md")
        self.assertEqual(self.suggestion(), ("013", []))

    # Case 15: links pointing outside the root. Each level is its own test.

    def assert_one_refusal(self, refused, path):
        self.assertEqual(len(refused), 1, refused)
        self.assertTrue(refused[0].startswith("path is outside the root: " + path + " -> "),
                        refused[0])

    # DECISIONS 2026-10-29 Chunk N3 D1: a top-level folder linked outside is
    # one refusal in the list; the rest of the scan still counts.

    def test_findings_folder_linked_outside_is_refused_incoming_still_counts(self):
        self.link("findings", self.outside / "findings")
        self.write("incoming/bob/findings/F-007-b.md")
        warnings, refused = self.warnings()
        self.assertEqual(warnings, ["F-007 already exists: incoming/bob/findings/F-007-b.md"])
        self.assert_one_refusal(refused, "findings")
        self.assertNotIn("F-007-outside", refused[0])

    def test_incoming_folder_linked_outside_is_refused_local_still_counts(self):
        self.link("incoming", self.outside)
        self.write("findings/F-007-mine.md", "field-notes/alice/IR-002-a.md")
        warnings, refused = self.warnings()
        self.assertEqual(warnings, ["F-007 already exists: findings/F-007-mine.md"])
        self.assert_one_refusal(refused, "incoming")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "003")
        self.assert_one_refusal(refused, "incoming")
        warnings, refused = self.ir_warnings("002")
        self.assertEqual(warnings, ["IR-002 already exists: field-notes/alice/IR-002-a.md"])
        self.assert_one_refusal(refused, "incoming")
        self.assertNotIn("outside.md", refused[0])

    def test_field_notes_folder_linked_outside_is_refused_incoming_still_counts(self):
        self.link("field-notes", self.outside / "field-notes")
        self.write("incoming/bob/field-notes/bob/IR-004-b.md")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "005")
        self.assert_one_refusal(refused, "field-notes")
        self.assertNotIn("IR-500", refused[0])

    def test_every_refusal_comes_back_in_path_order(self):
        self.link("field-notes", self.outside / "field-notes")
        self.link("incoming/eve", self.outside)
        self.link("incoming/bob/field-notes/bob/IR-500-l.md", self.outside / "IR-500-outside.md")
        self.write("incoming/bob/field-notes/bob/IR-003-b.md")
        for refused in [self.suggestion()[1], self.ir_warnings("003")[1]]:
            self.assertEqual(len(refused), 3, refused)
            self.assertTrue(refused[0].startswith("path is outside the root: field-notes -> "))
            self.assertTrue(refused[1].startswith(
                "path is outside the root: incoming/bob/field-notes/bob/IR-500-l.md -> "))
            self.assertTrue(refused[2].startswith("path is outside the root: incoming/eve -> "))
        self.assertEqual(self.suggestion()[0], "004")

    # DECISIONS 2026-10-29 Chunk N3 D2: a typed IR number already in use warns.

    def ir_warnings(self, nnn):
        """ir_number_warnings(), checking that it changed and created nothing."""
        before = file_bytes(self.home)
        before_names = sorted(self.home.rglob("*"))
        result = notebook.ir_number_warnings(self.home, nnn)
        self.assertEqual(file_bytes(self.home), before)
        self.assertEqual(sorted(self.home.rglob("*")), before_names)
        return result

    def test_local_ir_number_collides(self):
        self.write("field-notes/alice/IR-007-old.md")
        self.assertEqual(self.ir_warnings("007"), (
            ["IR-007 already exists: field-notes/alice/IR-007-old.md"], []))

    def test_incoming_ir_number_collides(self):
        self.write("incoming/bob/field-notes/bob/IR-007-b.md")
        self.assertEqual(self.ir_warnings("007"), (
            ["IR-007 already exists: incoming/bob/field-notes/bob/IR-007-b.md"], []))

    def test_every_ir_collision_in_path_order(self):
        self.write("incoming/zed/field-notes/zed/IR-007-z.md", "field-notes/carol/IR-007-c.md",
                   "incoming/bob/field-notes/erin/IR-007-e.md", "field-notes/alice/IR-007.md",
                   "field-notes/alice/IR-008-other.md")
        real_glob, real_iterdir = notebook.Path.glob, notebook.Path.iterdir
        with mock.patch.object(notebook.Path, "glob",
                               lambda folder, pattern: reversed(sorted(real_glob(folder, pattern)))), \
                mock.patch.object(notebook.Path, "iterdir",
                                  lambda folder: reversed(sorted(real_iterdir(folder)))):
            warnings, refused = notebook.ir_number_warnings(self.home, "007")
        self.assertEqual(warnings, [
            "IR-007 already exists: field-notes/alice/IR-007.md",
            "IR-007 already exists: field-notes/carol/IR-007-c.md",
            "IR-007 already exists: incoming/bob/field-notes/erin/IR-007-e.md",
            "IR-007 already exists: incoming/zed/field-notes/zed/IR-007-z.md"])
        self.assertEqual(refused, [])

    def test_ir_near_misses_dont_collide(self):
        self.write("field-notes/alice/IR-07-a.md", "field-notes/alice/IR-0070-a.md",
                   "field-notes/alice/IR-007x.md", "field-notes/alice/IR-007_x.md",
                   "field-notes/alice/ir-007-a.md", "field-notes/alice/IR-007-a.txt",
                   "field-notes/alice/old/IR-007-a.md", "field-notes/IR-007-a.md",
                   "IR-007-a.md", "findings/IR-007-a.md", "incoming/bob/field-notes/IR-007-a.md",
                   "field-notes/alice/IR-٠٠٧-a.md")
        (self.home / "field-notes/alice/IR-007-folder.md").mkdir()
        self.assertEqual(self.ir_warnings("007"), ([], []))

    def test_no_ir_collision(self):
        self.write("field-notes/alice/IR-006-a.md", "incoming/bob/field-notes/bob/IR-008-b.md")
        self.assertEqual(self.ir_warnings("007"), ([], []))

    def test_refused_ir_link_doesnt_hide_a_collision(self):
        self.write("incoming/bob/field-notes/bob/IR-007-b.md")
        self.link("field-notes/alice/IR-007-linked.md", self.outside / "IR-500-outside.md")
        warnings, refused = self.ir_warnings("007")
        self.assertEqual(warnings, ["IR-007 already exists: incoming/bob/field-notes/bob/IR-007-b.md"])
        self.assert_one_refusal(refused, "field-notes/alice/IR-007-linked.md")

    def test_ir_warning_needs_a_good_number(self):
        for nnn in self.BAD_NUMBERS:
            with self.subTest(nnn=nnn), self.assertRaises(ValueError):
                notebook.ir_number_warnings(self.home, nnn)

    def test_owner_folder_linked_outside_is_refused_others_still_count(self):
        self.write("incoming/bob/findings/F-007-b.md", "incoming/bob/field-notes/bob/IR-002-b.md")
        self.link("incoming/eve", self.outside)
        warnings, refused = self.warnings()
        self.assertEqual(warnings, ["F-007 already exists: incoming/bob/findings/F-007-b.md"])
        self.assert_one_refusal(refused, "incoming/eve")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "003")
        self.assert_one_refusal(refused, "incoming/eve")

    def test_owner_findings_folder_linked_outside_is_refused(self):
        self.write("findings/F-007-mine.md")
        self.link("incoming/eve/findings", self.outside / "findings")
        warnings, refused = self.warnings()
        self.assertEqual(warnings, ["F-007 already exists: findings/F-007-mine.md"])
        self.assert_one_refusal(refused, "incoming/eve/findings")

    def test_owner_field_notes_folder_linked_outside_is_refused(self):
        self.write("field-notes/alice/IR-002-a.md")
        self.link("incoming/eve/field-notes", self.outside / "field-notes")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "003")
        self.assert_one_refusal(refused, "incoming/eve/field-notes")

    def test_person_folder_linked_outside_is_refused(self):
        self.write("field-notes/alice/IR-002-a.md")
        self.link("field-notes/eve", self.outside / "eve")
        self.link("incoming/bob/field-notes/eve", self.outside / "eve")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "003")
        self.assertEqual(len(refused), 2, refused)
        self.assertTrue(refused[0].startswith(
            "path is outside the root: field-notes/eve -> "))
        self.assertTrue(refused[1].startswith(
            "path is outside the root: incoming/bob/field-notes/eve -> "))

    def test_finding_file_linked_outside_is_refused(self):
        self.write("findings/F-007-mine.md")
        self.link("incoming/bob/findings/F-007-linked.md", self.outside / "F-007-outside.md")
        warnings, refused = self.warnings()
        self.assertEqual(warnings, ["F-007 already exists: findings/F-007-mine.md"])
        self.assert_one_refusal(refused, "incoming/bob/findings/F-007-linked.md")

    def test_ir_file_linked_outside_is_refused(self):
        self.write("field-notes/alice/IR-002-a.md")
        self.link("field-notes/alice/IR-500-linked.md", self.outside / "IR-500-outside.md")
        suggestion, refused = self.suggestion()
        self.assertEqual(suggestion, "003")
        self.assert_one_refusal(refused, "field-notes/alice/IR-500-linked.md")

    def test_outside_link_is_checked_before_anything_follows_it(self):
        # is_file() and is_dir() follow a link, so neither may run on a link
        # that hasn't passed the path check (the N3-02 round-1 lesson).
        links = [self.home / "incoming/eve", self.home / "incoming/bob/findings/F-007-l.md",
                 self.home / "field-notes/eve"]
        self.link("incoming/eve", self.outside)
        self.link("incoming/bob/findings/F-007-l.md", self.outside / "F-007-outside.md")
        self.link("field-notes/eve", self.outside / "eve")
        followed = []
        real_is_file, real_is_dir = notebook.Path.is_file, notebook.Path.is_dir

        def recording_is_file(path):
            followed.append(path)
            return real_is_file(path)

        def recording_is_dir(path):
            followed.append(path)
            return real_is_dir(path)

        with mock.patch.object(notebook.Path, "is_file", recording_is_file), \
                mock.patch.object(notebook.Path, "is_dir", recording_is_dir):
            notebook.finding_id_warnings(self.home, "007")
            notebook.suggest_ir_number(self.home)
        for link in links:
            self.assertNotIn(link, followed)
        outside = self.outside.resolve()
        for path in followed:
            self.assertNotIn(outside, [path.resolve()] + list(path.resolve().parents))

    # Case 17: read live from disk.

    def test_results_follow_the_disk(self):
        self.assertEqual(self.warnings(), ([], []))
        self.assertEqual(self.suggestion(), ("001", []))
        self.write("incoming/bob/findings/F-007-new.md", "field-notes/alice/IR-041-a.md")
        self.assertEqual(self.warnings(), (
            ["F-007 already exists: incoming/bob/findings/F-007-new.md"], []))
        self.assertEqual(self.suggestion(), ("042", []))
        (self.home / "field-notes/alice/IR-041-a.md").rename(
            self.home / "field-notes/alice/IR-070-a.md")
        self.assertEqual(self.suggestion(), ("071", []))


def tree(root):
    """Every name under root (links not followed) with its bytes, link target or "folder"."""
    found = {}
    for folder, dirs, files in os.walk(str(root)):
        for name in dirs + files:
            path = os.path.join(folder, name)
            key = os.path.relpath(path, str(root))
            if os.path.islink(path):
                found[key] = "link -> " + os.readlink(path)
            elif os.path.isdir(path):
                found[key] = "folder"
            else:
                with open(path, "rb") as handle:
                    found[key] = handle.read()
    return found


# Fake templates with look-alike and unrelated markers, so a test can see that
# only the exact ID and title markers are filled (N3-04 cases 2-6).
FAKE_TEMPLATES = {
    "templates/incident-report.md": (
        "# Incident Report [[IR_ID]]\n\n"
        "- **ID:** [[IR_ID]]\n"
        "- **Not IDs:** [[IR_ID_EXTRA]] [[ IR_ID ]] [[ir_id]] [[IR_ID] [[FINDING_ID]]\n"
        "- **Host:** [[HOST]] [[CHOOSE: Yes / No]]\n"
        "[[NOTE: Keep this note,\nacross two lines.]]\n"),
    "templates/status-update.md": (
        "# Status update\n\n- **Time:** [[DATE]] [[TIME]]\n"
        "- **Refs:** [[IR_ID]] [[FINDING_ID]] [[FINDING_TITLE]]\n"),
    "templates/inject-response.md": (
        "# Inject response\n\n- **Sent:** [[DATE_SENT]] [[TIME_SENT]]\n"
        "- **Refs:** [[IR_ID]] [[FINDING_ID]]\n"),
    "templates/finding.md": (
        "### [[FINDING_ID]]: [[FINDING_TITLE]]\n\n"
        "- **Severity:** [[CHOOSE: Critical / High / Low]]\n"
        "- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]]\n"
        "- **Not IDs:** [[FINDING_ID_EXTRA]] [[FINDING_TITLE_X]] [[IR_ID]] [[PREVIOUS_FINDING_ID]]\n"
        "[[NOTE: Keep this note,\nacross two lines.]]\n"),
}

# A fake library entry: a filled heading, a later heading of the same form,
# and markers that must stay as they are.
LIBRARY_ENTRY = (
    "### [[FINDING_ID]]: SMB signing not required\n\n"
    "- **Severity:** High\n"
    "- **Affected assets:** [[HOST]] ([[HOST_IP]])\n"
    "- `evidence/[[FINDING_ID]]-01.png`: [[WHAT_IT_SHOWS]] [[FINDING_ID_EXTRA]]\n\n"
    "### [[FINDING_ID]]: Related note kept as written\n")


class CreateNewFileTests(unittest.TestCase):
    """N3-04: create_new_file(), the New form's one write."""

    def setUp(self):
        self.home = support.make_worktree(self, FAKE_TEMPLATES)
        self.logs = support.make_worktree(self)
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {
            "secret.md": "outside\n",
            "library/entry.md": LIBRARY_ENTRY,
            "templates/finding.md": "### [[FINDING_ID]]: outside template\n"})

    def create(self, type_name, title, nnn=None, library=None):
        return notebook.create_new_file(self.home, self.logs, "alice", type_name, title,
                                        nnn=nnn, library=library)

    def text(self, path):
        with (self.home / path).open(encoding="utf-8", newline="") as handle:
            return handle.read()

    def link(self, path, target):
        (self.home / path).parent.mkdir(parents=True, exist_ok=True)
        (self.home / path).symlink_to(target)

    def write(self, path, text):
        support.write_fake_file(self.home, path, text)

    def assert_refused(self, error, *args, **kwargs):
        """The call raises error before the first folder or file is made; nothing changes."""
        before = (tree(self.home), tree(self.outside), tree(self.logs))
        with mock.patch.object(notebook.Path, "mkdir", side_effect=AssertionError("mkdir ran")), \
                mock.patch.object(notebook.os, "makedirs", side_effect=AssertionError("makedirs ran")):
            with self.assertRaises(error) as caught:
                self.create(*args, **kwargs)
        self.assertEqual((tree(self.home), tree(self.outside), tree(self.logs)), before)
        return str(caught.exception)

    def assert_created(self, path, *args, **kwargs):
        """The call creates exactly path (plus any folders it needs) and changes nothing else."""
        before = tree(self.home)
        result = self.create(*args, **kwargs)
        after = tree(self.home)
        self.assertEqual(result[0], path)
        new_names = set(after) - set(before)
        self.assertIn(path, new_names)
        for name in new_names - {path}:
            self.assertEqual(after[name], "folder", name)
            self.assertTrue(path.startswith(name + "/"), name)
        for name in before:
            self.assertEqual(after[name], before[name], name)
        return result

    # Cases 1-5: each type lands at its literal path.

    def test_note(self):
        result = self.assert_created("field-notes/alice/NOTE-quick-note.md", "Note", "Quick Note")
        self.assertEqual(result, ("field-notes/alice/NOTE-quick-note.md", [], []))
        self.assertEqual(self.text("field-notes/alice/NOTE-quick-note.md"), "")

    def test_incident_report(self):
        self.assert_created("field-notes/alice/IR-007-incident-title.md",
                            "Incident report", "Incident Title", nnn="007")
        self.assertEqual(self.text("field-notes/alice/IR-007-incident-title.md"), (
            "# Incident Report IR-007\n\n"
            "- **ID:** IR-007\n"
            "- **Not IDs:** [[IR_ID_EXTRA]] [[ IR_ID ]] [[ir_id]] [[IR_ID] [[FINDING_ID]]\n"
            "- **Host:** [[HOST]] [[CHOOSE: Yes / No]]\n"
            "[[NOTE: Keep this note,\nacross two lines.]]\n"))

    def test_status_update_is_a_byte_copy(self):
        self.assert_created("field-notes/alice/SU-status-title.md", "Status update", "Status Title")
        self.assertEqual(self.text("field-notes/alice/SU-status-title.md"),
                         FAKE_TEMPLATES["templates/status-update.md"])

    def test_inject_response_is_a_byte_copy(self):
        self.assert_created("field-notes/alice/INJ-inject-title.md", "Inject response", "Inject Title")
        self.assertEqual(self.text("field-notes/alice/INJ-inject-title.md"),
                         FAKE_TEMPLATES["templates/inject-response.md"])

    def test_finding_from_the_template(self):
        self.assert_created("findings/F-042-finding-title.md", "Finding", "Finding Title", nnn="042")
        self.assertEqual(self.text("findings/F-042-finding-title.md"), (
            "### F-042: Finding Title\n\n"
            "- **Severity:** [[CHOOSE: Critical / High / Low]]\n"
            "- `evidence/F-042-01.png`: [[WHAT_IT_SHOWS]]\n"
            "- **Not IDs:** [[FINDING_ID_EXTRA]] [[FINDING_TITLE_X]] [[IR_ID]] [[PREVIOUS_FINDING_ID]]\n"
            "[[NOTE: Keep this note,\nacross two lines.]]\n"))

    def test_real_templates_get_their_ids(self):
        # The repo's own templates, copied in: the ID and title land where
        # templates/README.md says, and nothing else changes.
        repo = support.TOOLS_DIR.parent
        for name in ["incident-report.md", "finding.md"]:
            source = (repo / "templates" / name).read_bytes()
            (self.home / "templates" / name).write_bytes(source)
        self.create("Incident report", "Real IR", nnn="003")
        self.create("Finding", "Real finding", nnn="004")
        ir_text = (self.home / "field-notes/alice/IR-003-real-ir.md").read_bytes()
        f_text = (self.home / "findings/F-004-real-finding.md").read_bytes()
        repo_ir = (repo / "templates/incident-report.md").read_bytes()
        repo_f = (repo / "templates/finding.md").read_bytes()
        self.assertEqual(ir_text, repo_ir.replace(b"[[IR_ID]]", b"IR-003"))
        self.assertEqual(f_text, repo_f.replace(b"[[FINDING_ID]]", b"F-004")
                         .replace(b"[[FINDING_TITLE]]", b"Real finding"))
        self.assertIn(b"[[PREVIOUS_FINDING_ID]]", f_text)

    # Case 7: a free-text title goes in exactly as typed.

    def test_title_exactly_as_typed(self):
        title = "Admin | `id` $HOME café [[HOST]] [[FINDING_ID]] \\ end "
        result = self.create("Finding", title, nnn="001")
        self.assertEqual(result[0], "findings/F-001-" + notebook.slugify(title) + ".md")
        self.assertEqual(result[0], "findings/F-001-admin-id-home-caf-host-finding-id-end.md")
        first_line = self.text(result[0]).split("\n")[0]
        # The title's own [[FINDING_ID]] is not filled: values are never rescanned.
        self.assertEqual(first_line, "### F-001: " + title)

    # Cases 8-11: library findings.

    def add_library(self, name="smb.md", text=LIBRARY_ENTRY):
        self.write("findings-library/" + name, text)
        return "findings-library/" + name

    def test_library_title_unchanged(self):
        entry = self.add_library()
        result = self.create("Finding", "SMB signing not required", nnn="009", library=entry)
        self.assertEqual(result[0], "findings/F-009-smb-signing-not-required.md")
        self.assertEqual(self.text(result[0]), LIBRARY_ENTRY.replace("[[FINDING_ID]]", "F-009"))

    def test_library_title_edited(self):
        entry = self.add_library()
        result = self.create("Finding", "SMB signing off on DC01", nnn="010", library=entry)
        self.assertEqual(result[0], "findings/F-010-smb-signing-off-on-dc01.md")
        self.assertEqual(self.text(result[0]), (
            "### F-010: SMB signing off on DC01\n\n"
            "- **Severity:** High\n"
            "- **Affected assets:** [[HOST]] ([[HOST_IP]])\n"
            "- `evidence/F-010-01.png`: [[WHAT_IT_SHOWS]] [[FINDING_ID_EXTRA]]\n\n"
            "### F-010: Related note kept as written\n"))

    def test_library_title_edited_with_prose_and_crlf(self):
        entry = self.add_library("crlf.md", "Intro line.\r\n### [[FINDING_ID]]: Old\r\nBody [[HOST]]\r\n")
        result = self.create("Finding", "New", nnn="011", library=entry)
        self.assertEqual((self.home / result[0]).read_bytes(),
                         b"Intro line.\r\n### F-011: New\r\nBody [[HOST]]\r\n")

    def test_library_title_with_markers_is_exact(self):
        entry = self.add_library()
        result = self.create("Finding", "x [[FINDING_ID]] [[FINDING_TITLE]]", nnn="012", library=entry)
        self.assertEqual(self.text(result[0]).split("\n")[0],
                         "### F-012: x [[FINDING_ID]] [[FINDING_TITLE]]")

    def test_library_finding_title_marker_is_filled(self):
        # The spec: the new file has [[FINDING_TITLE]] filled with the title,
        # wherever the text came from.
        entry = self.add_library("t.md", "### [[FINDING_ID]]: Old\n\nSee [[FINDING_TITLE]].\n")
        result = self.create("Finding", "New title", nnn="013", library=entry)
        self.assertEqual(self.text(result[0]), "### F-013: New title\n\nSee New title.\n")

    def test_library_bad_heading_is_refused(self):
        entry = self.add_library("bad.md", "## [[FINDING_ID]]: Wrong level\n")
        message = self.assert_refused(ValueError, "Finding", "T", nnn="001", library=entry)
        self.assertIn("findings-library/bad.md", message)

    def test_library_readme_is_refused(self):
        entry = self.add_library("README.md", "# Library\n")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001", library=entry)
        self.assertIn("findings-library/README.md", message)

    def test_library_subfolder_entry_is_refused(self):
        entry = self.add_library("old/smb.md")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001", library=entry)
        self.assertIn("findings-library/old/smb.md", message)

    def test_library_path_outside_the_folder_is_refused(self):
        self.write("findings/F-001-x.md", LIBRARY_ENTRY)
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="002",
                                      library="findings/F-001-x.md")
        self.assertIn("findings/F-001-x.md", message)

    def test_library_dot_dot_is_refused(self):
        self.add_library()
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001",
                                      library="findings-library/../findings-library/smb.md")
        self.assertIn("findings-library/../findings-library/smb.md", message)

    def test_library_absolute_path_outside_is_refused(self):
        path = str(self.outside / "library/entry.md")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001", library=path)
        self.assertIn(path, message)

    def test_library_nul_is_refused(self):
        self.add_library()
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001",
                                      library="findings-library/smb.md\x00")
        self.assertIn("findings-library/smb.md", message)

    def test_library_entry_linked_outside_is_refused(self):
        self.link("findings-library/linked.md", self.outside / "library/entry.md")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001",
                                      library="findings-library/linked.md")
        self.assertIn("findings-library/linked.md", message)

    def test_library_entry_linked_inside_is_used(self):
        self.write("shared/entry.md", LIBRARY_ENTRY)
        self.link("findings-library/linked.md", self.home / "shared/entry.md")
        result = self.create("Finding", "SMB signing not required", nnn="001",
                             library="findings-library/linked.md")
        self.assertEqual(self.text(result[0]), LIBRARY_ENTRY.replace("[[FINDING_ID]]", "F-001"))

    def test_library_that_isnt_text_is_refused(self):
        self.assert_refused(ValueError, "Finding", "T", nnn="001", library=["findings-library/smb.md"])

    def test_library_only_for_findings(self):
        entry = self.add_library()
        for type_name, nnn in [("Note", None), ("Incident report", "001"),
                               ("Status update", None), ("Inject response", None)]:
            with self.subTest(type_name=type_name):
                message = self.assert_refused(ValueError, type_name, "T", nnn=nnn, library=entry)
                self.assertIn("only a Finding can start from the findings library", message)

    def test_finding_without_library_uses_only_the_template(self):
        self.add_library()
        with mock.patch.object(notebook, "read_library_entry",
                               side_effect=AssertionError("library read")):
            result = self.create("Finding", "Plain", nnn="001")
        self.assertTrue(self.text(result[0]).startswith("### F-001: Plain\n"))

    # Cases 12, 13 and 22: the number.

    def test_typed_number_is_used_not_the_suggestion(self):
        self.write("field-notes/alice/IR-004-old.md", "x\n")
        self.assertEqual(notebook.suggest_ir_number(self.home)[0], "005")
        result = self.create("Incident report", "Next", nnn="006")
        self.assertEqual(result[0], "field-notes/alice/IR-006-next.md")
        self.assertTrue(self.text(result[0]).startswith("# Incident Report IR-006\n"))

    def test_bad_numbers_are_refused(self):
        for type_name in ["Incident report", "Finding"]:
            for nnn in ["6", "0006", "123\n", "١٢٣", "", None, 7, ["007"]]:
                with self.subTest(type_name=type_name, nnn=nnn):
                    message = self.assert_refused(ValueError, type_name, "T", nnn=nnn)
                    self.assertTrue("three digits" in message, message)

    def test_types_without_a_number_refuse_one(self):
        for type_name in ["Note", "Status update", "Inject response"]:
            with self.subTest(type_name=type_name):
                message = self.assert_refused(ValueError, type_name, "T", nnn="007")
                self.assertIn(type_name + " has no number", message)

    def test_missing_number_never_picks_one(self):
        with mock.patch.object(notebook, "suggest_ir_number",
                               side_effect=AssertionError("suggestion used")):
            self.assert_refused(ValueError, "Incident report", "T", nnn=None)
            self.assert_refused(ValueError, "Finding", "T", nnn=None)
            self.create("Incident report", "T", nnn="001")

    # Case 14: the slug.

    def test_dot_dot_title_stays_in_its_folder(self):
        result = self.create("Note", "../A  B!!")
        self.assertEqual(result[0], "field-notes/alice/NOTE-a-b.md")

    def test_empty_slug_is_refused(self):
        for title in ["", "!!!", "../", " - "]:
            with self.subTest(title=title):
                self.assert_refused(ValueError, "Note", title)

    def test_title_that_isnt_text_is_refused(self):
        self.assert_refused(ValueError, "Note", None)

    def test_nul_and_percent_00_never_reach_the_path(self):
        self.assertEqual(self.create("Note", "a\x00b")[0], "field-notes/alice/NOTE-a-b.md")
        self.assertEqual(self.create("Note", "a%00b")[0], "field-notes/alice/NOTE-a-00b.md")

    def test_unknown_type_is_refused(self):
        self.assert_refused(ValueError, "Task", "T")

    # Cases 15 and 16: something already at the output path.

    def test_existing_file_is_refused_and_unchanged(self):
        self.write("field-notes/alice/NOTE-taken.md", "mine\n")
        stat_before = os.stat(str(self.home / "field-notes/alice/NOTE-taken.md"))
        message = self.assert_refused(compile.RootError, "Note", "Taken")
        self.assertIn("field-notes/alice/NOTE-taken.md", message)
        self.assertIn("choose a different title", message)
        stat_after = os.stat(str(self.home / "field-notes/alice/NOTE-taken.md"))
        self.assertEqual((stat_after.st_mtime_ns, stat_after.st_size),
                         (stat_before.st_mtime_ns, stat_before.st_size))

    def test_output_link_inside_the_root_is_refused(self):
        self.write("shared/target.md", "target\n")
        self.link("field-notes/alice/NOTE-x.md", self.home / "shared/target.md")
        self.assert_refused(compile.RootError, "Note", "x")

    def test_output_link_outside_is_refused(self):
        self.link("field-notes/alice/NOTE-x.md", self.outside / "secret.md")
        self.assert_refused(compile.RootError, "Note", "x")

    def test_output_broken_link_is_refused(self):
        self.link("field-notes/alice/NOTE-x.md", self.home / "missing.md")
        self.assert_refused(compile.RootError, "Note", "x")

    def test_output_folder_is_refused(self):
        (self.home / "field-notes/alice/NOTE-x.md").mkdir(parents=True)
        self.assert_refused(compile.RootError, "Note", "x")

    def test_output_hard_link_is_refused(self):
        self.write("shared/target.md", "target\n")
        (self.home / "field-notes/alice").mkdir(parents=True)
        os.link(str(self.home / "shared/target.md"), str(self.home / "field-notes/alice/NOTE-x.md"))
        self.assert_refused(compile.RootError, "Note", "x")

    # Cases 17 and 18: the folders on the way.

    def test_destination_folders_linked_inside_are_used(self):
        (self.home / "shared/f").mkdir(parents=True)
        (self.home / "shared/notes").mkdir(parents=True)
        self.link("findings", self.home / "shared/f")
        self.link("field-notes", self.home / "shared/notes")
        self.assertEqual(self.create("Finding", "Linked", nnn="001")[0], "findings/F-001-linked.md")
        self.assertTrue((self.home / "shared/f/F-001-linked.md").is_file())
        self.assertEqual(self.create("Note", "Linked")[0], "field-notes/alice/NOTE-linked.md")
        self.assertTrue((self.home / "shared/notes/alice/NOTE-linked.md").is_file())

    def test_own_folder_linked_inside_is_used(self):
        (self.home / "shared/alice").mkdir(parents=True)
        self.link("field-notes/alice", self.home / "shared/alice")
        self.create("Note", "Linked")
        self.assertTrue((self.home / "shared/alice/NOTE-linked.md").is_file())

    def test_findings_linked_outside_is_refused(self):
        self.link("findings", self.outside)
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001")
        self.assertIn("findings/F-001-t.md", message)

    def test_field_notes_linked_outside_is_refused(self):
        self.link("field-notes", self.outside)
        self.assert_refused(compile.RootError, "Note", "T")

    def test_own_folder_linked_outside_is_refused(self):
        self.link("field-notes/alice", self.outside)
        self.assert_refused(compile.RootError, "Note", "T")

    def test_own_folder_linked_into_incoming_is_refused(self):
        (self.home / "incoming/bob/field-notes/bob").mkdir(parents=True)
        self.link("field-notes/alice", self.home / "incoming/bob/field-notes/bob")
        message = self.assert_refused(compile.RootError, "Note", "T")
        self.assertIn("incoming/ is read-only", message)

    def test_own_folder_linked_into_the_log_folder_is_refused(self):
        logs = self.home / "logs"
        logs.mkdir()
        self.logs = logs
        self.link("field-notes/alice", logs)
        message = self.assert_refused(compile.RootError, "Note", "T")
        self.assertIn("the log folder is read-only", message)

    def test_file_in_the_way_of_field_notes(self):
        self.write("field-notes", "a file\n")
        message = self.assert_refused(compile.RootError, "Note", "T")
        self.assertIn("field-notes", message)

    def test_file_in_the_way_of_the_own_folder(self):
        self.write("field-notes/alice", "a file\n")
        message = self.assert_refused(compile.RootError, "Note", "T")
        self.assertIn("field-notes/alice", message)

    def test_broken_link_in_the_way_of_findings(self):
        self.link("findings", self.home / "missing-folder")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001")
        self.assertIn("findings", message)

    # Cases 19 and 20: the template.

    def test_templates_folder_linked_inside_is_used(self):
        (self.home / "templates").rename(self.home / "shared-templates")
        self.link("templates", self.home / "shared-templates")
        self.create("Incident report", "T", nnn="001")
        self.assertTrue(self.text("field-notes/alice/IR-001-t.md").startswith("# Incident Report IR-001"))

    def test_template_file_linked_inside_is_used(self):
        (self.home / "templates/finding.md").rename(self.home / "real-finding.md")
        self.link("templates/finding.md", self.home / "real-finding.md")
        self.create("Finding", "T", nnn="001")
        self.assertTrue(self.text("findings/F-001-t.md").startswith("### F-001: T\n"))

    def test_templates_folder_linked_outside_is_refused(self):
        (self.home / "templates").rename(self.home / "old-templates")
        self.link("templates", self.outside / "templates")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001")
        self.assertIn("templates/finding.md", message)

    def test_template_file_linked_outside_is_refused(self):
        (self.home / "templates/finding.md").unlink()
        self.link("templates/finding.md", self.outside / "templates/finding.md")
        message = self.assert_refused(compile.RootError, "Finding", "T", nnn="001")
        self.assertIn("templates/finding.md", message)

    def test_missing_template_is_refused(self):
        (self.home / "templates/status-update.md").unlink()
        message = self.assert_refused(compile.InputError, "Status update", "T")
        self.assertIn("templates/status-update.md", message)

    def test_template_that_is_a_folder_is_refused(self):
        (self.home / "templates/status-update.md").unlink()
        (self.home / "templates/status-update.md").mkdir()
        message = self.assert_refused(compile.InputError, "Status update", "T")
        self.assertIn("templates/status-update.md", message)

    def test_template_not_utf8_is_refused(self):
        (self.home / "templates/status-update.md").write_bytes("# Café\n".encode("cp1252"))
        message = self.assert_refused(compile.InputError, "Status update", "T")
        self.assertIn("status-update.md is not UTF-8 text", message)

    def test_unreadable_template_is_refused(self):
        path = self.home / "templates/status-update.md"
        path.chmod(0)
        self.addCleanup(path.chmod, 0o644)
        if os.access(str(path), os.R_OK):
            self.skipTest("running as a user who can read any file")
        # Checked by hand: tree() can't read this file either.
        with self.assertRaises(OSError) as caught:
            self.create("Status update", "T")
        self.assertIn("templates/status-update.md", str(caught.exception))
        self.assertFalse((self.home / "field-notes").exists())

    def test_crlf_template_keeps_its_line_endings(self):
        (self.home / "templates/incident-report.md").write_bytes(
            b"# Incident Report [[IR_ID]]\r\n\r\n- caf\xc3\xa9 [[HOST]]\r\n")
        self.create("Incident report", "T", nnn="001")
        self.assertEqual((self.home / "field-notes/alice/IR-001-t.md").read_bytes(),
                         b"# Incident Report IR-001\r\n\r\n- caf\xc3\xa9 [[HOST]]\r\n")

    def test_bom_is_dropped(self):
        (self.home / "templates/status-update.md").write_bytes(b"\xef\xbb\xbf# Status\n")
        self.create("Status update", "T")
        self.assertEqual((self.home / "field-notes/alice/SU-t.md").read_bytes(), b"# Status\n")

    # Case 21: duplicate IDs warn but don't block.

    def test_duplicate_finding_id_warns_and_still_creates(self):
        self.write("findings/F-007-old.md", "x\n")
        self.write("incoming/zed/findings/F-007-z.md", "x\n")
        self.write("incoming/bob/findings/F-007-b.md", "x\n")
        self.link("incoming/eve", self.outside)
        result = self.create("Finding", "New", nnn="007")
        self.assertEqual(result[0], "findings/F-007-new.md")
        self.assertEqual(result[1], [
            "F-007 already exists: findings/F-007-old.md",
            "F-007 already exists: incoming/bob/findings/F-007-b.md",
            "F-007 already exists: incoming/zed/findings/F-007-z.md"])
        self.assertEqual(len(result[2]), 1)
        self.assertTrue(result[2][0].startswith("path is outside the root: incoming/eve -> "))
        self.assertTrue((self.home / "findings/F-007-new.md").is_file())

    def test_other_types_get_no_warnings(self):
        self.write("findings/F-007-old.md", "x\n")
        self.assertEqual(self.create("Incident report", "T", nnn="007")[1:], ([], []))

    # DECISIONS 2026-10-29 Chunk N3 D1 and D2 at create time.

    def test_finding_is_created_with_incoming_linked_outside(self):
        self.link("incoming", self.outside)
        result = self.create("Finding", "Linked incoming", nnn="007")
        self.assertEqual(result[0], "findings/F-007-linked-incoming.md")
        self.assertEqual(result[1], [])
        self.assertEqual(len(result[2]), 1)
        self.assertTrue(result[2][0].startswith("path is outside the root: incoming -> "))
        self.assertTrue((self.home / result[0]).is_file())

    def test_duplicate_ir_number_warns_and_still_creates(self):
        self.write("field-notes/alice/IR-007-old.md", "x\n")
        self.write("incoming/bob/field-notes/bob/IR-007-b.md", "x\n")
        self.link("incoming/eve", self.outside)
        result = self.create("Incident report", "New", nnn="007")
        self.assertEqual(result[0], "field-notes/alice/IR-007-new.md")
        self.assertEqual(result[1], [
            "IR-007 already exists: field-notes/alice/IR-007-old.md",
            "IR-007 already exists: incoming/bob/field-notes/bob/IR-007-b.md"])
        self.assertEqual(len(result[2]), 1)
        self.assertTrue(result[2][0].startswith("path is outside the root: incoming/eve -> "))
        self.assertTrue((self.home / result[0]).is_file())

    def test_ir_warning_uses_the_typed_number_not_the_suggestion(self):
        self.write("field-notes/alice/IR-004-old.md", "x\n")
        self.assertEqual(notebook.suggest_ir_number(self.home)[0], "005")
        self.assertEqual(self.create("Incident report", "Reuse", nnn="004")[1],
                         ["IR-004 already exists: field-notes/alice/IR-004-old.md"])
        self.assertEqual(self.create("Incident report", "Next", nnn="005")[1:], ([], []))

    # DECISIONS 2026-10-29 Chunk N3 D5: a title is one line.

    def test_title_with_a_line_break_is_refused(self):
        types = [("Note", None), ("Incident report", "001"), ("Status update", None),
                 ("Inject response", None), ("Finding", "001")]
        titles = ["\nStart", "Mid\ndle", "End\n", "\rStart", "Mid\rdle", "End\r",
                  "\r\nStart", "Mid\r\ndle", "End\r\n",
                  "Legit\n- **Severity:** Critical", "Legit\r- **Severity:** Critical"]
        for type_name, nnn in types:
            for title in titles:
                with self.subTest(type_name=type_name, title=title):
                    message = self.assert_refused(ValueError, type_name, title, nnn=nnn)
                    self.assertEqual(message, "the title must be one line, with no line breaks")

    def test_line_break_is_refused_before_anything_is_read(self):
        self.write("findings-library/smb.md", LIBRARY_ENTRY)
        stop = AssertionError("ran before the title check")
        with mock.patch.object(notebook, "read_template", side_effect=stop), \
                mock.patch.object(notebook, "read_library_entry", side_effect=stop), \
                mock.patch.object(notebook, "finding_id_warnings", side_effect=stop), \
                mock.patch.object(notebook, "ir_number_warnings", side_effect=stop), \
                mock.patch.object(notebook, "check_new_file_path", side_effect=stop):
            self.assert_refused(ValueError, "Finding", "a\nb", nnn="001",
                                library="findings-library/smb.md")
            self.assert_refused(ValueError, "Incident report", "a\rb", nnn="001")

    def test_other_titles_are_not_refused_by_the_line_rule(self):
        for title, path in [("Back\\nslash", "field-notes/alice/NOTE-back-nslash.md"),
                            ("Tab\there", "field-notes/alice/NOTE-tab-here.md"),
                            ("  spaced  out  ", "field-notes/alice/NOTE-spaced-out.md")]:
            with self.subTest(title=title):
                self.assertEqual(self.create("Note", title)[0], path)

    # Case 23: checked before anything changes.

    def test_refusals_come_before_the_first_folder(self):
        # assert_refused patches mkdir to fail, so each of these is caught
        # before any folder is made; a fresh root has no field-notes/ yet.
        self.assertFalse((self.home / "field-notes").exists())
        self.assert_refused(ValueError, "Task", "T")
        self.assert_refused(ValueError, "Note", "!!!")
        self.assert_refused(ValueError, "Finding", "T", nnn="7")
        self.assert_refused(compile.RootError, "Finding", "T", nnn="001",
                            library="findings-library/missing.md")
        (self.home / "templates/finding.md").unlink()
        self.assert_refused(compile.InputError, "Finding", "T", nnn="001")
        self.assertFalse((self.home / "field-notes").exists())
        self.assertFalse((self.home / "findings").exists())

    # Case 24: the exclusive create.

    def test_file_that_appears_after_the_checks_is_never_overwritten(self):
        self.write("field-notes/alice/NOTE-race.md", "someone else's\n")
        real_lexists = os.path.lexists

        def lexists_misses_the_new_file(path):
            # Pretend the file wasn't there when checked, as if it appeared
            # between the check and the open.
            if str(path).endswith("NOTE-race.md"):
                return False
            return real_lexists(path)

        with mock.patch.object(notebook.os.path, "lexists", lexists_misses_the_new_file):
            with self.assertRaises(compile.RootError) as caught:
                self.create("Note", "Race")
        self.assertIn("field-notes/alice/NOTE-race.md", str(caught.exception))
        self.assertEqual(self.text("field-notes/alice/NOTE-race.md"), "someone else's\n")

    def test_a_failed_write_leaves_no_half_file(self):
        with mock.patch.object(notebook, "fill_new_file_markers", return_value=object()):
            with self.assertRaises(TypeError):
                self.create("Status update", "Half")
        self.assertFalse((self.home / "field-notes/alice/SU-half.md").exists())


class NewFileRouteTests(ServerTestCase):
    """N3-05: GET /new-data and POST /new-file, the New form's two routes."""

    FIELDS = {"type": "Note", "title": "T", "nnn": None, "library": None}

    def setUp(self):
        super().setUp()
        # A fresh root with only the fake templates, so nothing else is there.
        self.home = support.make_worktree(self, FAKE_TEMPLATES)
        self.server.settings["root"] = self.home.resolve()
        self.outside = support.make_worktree(self, {"secret.md": "outside\n",
                                                    "eve/IR-500-x.md": "x\n"})

    def write(self, path, text="x\n"):
        support.write_fake_file(self.home, path, text)

    def link(self, path, target):
        (self.home / path).parent.mkdir(parents=True, exist_ok=True)
        (self.home / path).symlink_to(target)

    def new_data(self, status=200):
        before = tree(self.home)
        response, body = self.send_full("GET", "/new-data", self.good_host())
        self.assertEqual(response.status, status, body)
        self.assert_safe_headers(response)
        self.assertEqual(tree(self.home), before)
        if status == 200:
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            return json.loads(body)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        return body

    def post(self, body, token="default", host=None, length=None):
        """POST raw body bytes to /new-file; return (status, text, content type).

        token: a value, a list (sent more than once), None (not sent) or
        "default" (this run's). length: the Content-Length to send, or None
        for the body's real length, or False to send none.
        """
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/new-file", skip_host=True)
        connection.putheader("Host", host or self.good_host())
        tokens = [self.server.token] if token == "default" else token
        for value in tokens if isinstance(tokens, list) else ([] if tokens is None else [tokens]):
            connection.putheader("X-CPTC-Token", value)
        connection.putheader("Content-Type", "application/json")
        if length is not False:
            connection.putheader("Content-Length", str(len(body)) if length is None else length)
        connection.endheaders(body)
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        self.assert_safe_headers(response)
        return response.status, text, response.getheader("Content-Type")

    def create(self, **fields):
        body = dict(self.FIELDS)
        body.update(fields)
        return self.post(json.dumps(body).encode("utf-8"))

    def assert_not_created(self, status_wanted, text_start, *post_args, **post_options):
        """The POST is refused with this status and text, and nothing changes."""
        before = (tree(self.home), tree(self.outside))
        status, text, content_type = self.post(*post_args, **post_options)
        self.assertEqual(status, status_wanted, text)
        self.assertEqual(content_type, "text/plain; charset=utf-8")
        self.assertTrue(text.startswith(text_start), text)
        self.assertEqual((tree(self.home), tree(self.outside)), before)
        return text

    def body(self, **fields):
        body = dict(self.FIELDS)
        body.update(fields)
        return json.dumps(body).encode("utf-8")

    # Cases 1-3 and 12: the New form's data.

    def test_new_data_lists_types_library_and_suggestion(self):
        self.write("findings-library/b-smb.md", "### [[FINDING_ID]]: SMB <script>x</script>\n")
        self.write("findings-library/a-creds.md", "### [[FINDING_ID]]: Default creds\n")
        self.write("findings-library/bad.md", "## [[FINDING_ID]]: Wrong level\n")
        self.write("findings-library/README.md", "# Library\n")
        self.write("field-notes/alice/IR-004-a.md")
        self.link("incoming/eve", self.outside)
        data = self.new_data()
        self.assertEqual(data["types"], [
            {"name": "Note", "needs_nnn": False, "library": False},
            {"name": "Incident report", "needs_nnn": True, "library": False},
            {"name": "Status update", "needs_nnn": False, "library": False},
            {"name": "Inject response", "needs_nnn": False, "library": False},
            {"name": "Finding", "needs_nnn": True, "library": True}])
        self.assertEqual(data["library"], [
            {"path": "findings-library/a-creds.md", "title": "Default creds"},
            {"path": "findings-library/b-smb.md", "title": "SMB <script>x</script>"}])
        self.assertEqual(data["library_refused"], [
            "findings-library/bad.md: first heading doesn't start with "
            "'### [[FINDING_ID]]: ': '## [[FINDING_ID]]: Wrong level'"])
        self.assertEqual(data["ir_suggestion"], "005")
        self.assertEqual(data["ir_note"], "")
        self.assertEqual(len(data["ir_refused"]), 1)
        self.assertTrue(data["ir_refused"][0].startswith("path is outside the root: incoming/eve -> "))
        self.assertEqual(sorted(data), ["ir_note", "ir_refused", "ir_suggestion", "library",
                                        "library_refused", "types"])

    def test_new_data_on_an_empty_root(self):
        empty = support.make_worktree(self)
        self.server.settings["root"] = empty.resolve()
        response, body = self.send_full("GET", "/new-data", self.good_host())
        self.assertEqual(response.status, 200, body)
        data = json.loads(body)
        self.assertEqual([kind["name"] for kind in data["types"]], list(notebook.NEW_FILE_TYPES))
        self.assertEqual((data["library"], data["library_refused"], data["ir_suggestion"],
                          data["ir_note"], data["ir_refused"]), ([], [], "001", "", []))
        self.assertEqual(list(empty.iterdir()), [])

    # DECISIONS 2026-10-29 Chunk N3 D1: a top-level link outside is reported
    # in its refused list, and the New form still opens.

    def test_new_data_library_folder_linked_outside_still_opens(self):
        self.link("findings-library", self.outside)
        data = self.new_data()
        self.assertEqual(len(data["types"]), 5)
        self.assertEqual(data["library"], [])
        self.assertEqual(len(data["library_refused"]), 1)
        self.assertTrue(data["library_refused"][0].startswith(
            "path is outside the root: findings-library -> "))
        self.assertNotIn("secret.md", data["library_refused"][0])
        self.assertEqual((data["ir_suggestion"], data["ir_refused"]), ("001", []))

    def test_new_data_field_notes_linked_outside_still_opens(self):
        self.link("field-notes", self.outside)
        self.write("incoming/bob/field-notes/bob/IR-004-b.md")
        # A refused IR scan doesn't touch the library list.
        self.write("findings-library/good.md", "### [[FINDING_ID]]: Good\n")
        data = self.new_data()
        self.assertEqual((data["library"], data["library_refused"]),
                         ([{"path": "findings-library/good.md", "title": "Good"}], []))
        self.assertEqual(data["ir_suggestion"], "005")
        self.assertEqual(len(data["ir_refused"]), 1)
        self.assertTrue(data["ir_refused"][0].startswith("path is outside the root: field-notes -> "))

    def test_new_data_incoming_linked_outside_still_opens(self):
        self.link("incoming", self.outside)
        self.write("field-notes/alice/IR-002-a.md")
        data = self.new_data()
        self.assertEqual(data["ir_suggestion"], "003")
        self.assertEqual(len(data["ir_refused"]), 1)
        self.assertTrue(data["ir_refused"][0].startswith("path is outside the root: incoming -> "))

    def test_new_data_all_three_linked_outside_still_opens(self):
        outside2 = support.make_worktree(self)
        outside3 = support.make_worktree(self)
        self.link("findings-library", self.outside)
        self.link("field-notes", outside2)
        self.link("incoming", outside3)
        data = self.new_data()
        self.assertEqual([kind["name"] for kind in data["types"]], list(notebook.NEW_FILE_TYPES))
        self.assertEqual((data["library"], data["ir_suggestion"], data["ir_note"]), ([], "001", ""))
        self.assertEqual(len(data["library_refused"]), 1)
        self.assertTrue(data["library_refused"][0].startswith(
            "path is outside the root: findings-library -> "))
        self.assertEqual(len(data["ir_refused"]), 2)
        self.assertTrue(data["ir_refused"][0].startswith("path is outside the root: field-notes -> "))
        self.assertTrue(data["ir_refused"][1].startswith("path is outside the root: incoming -> "))

    def test_new_data_bad_entry_doesnt_hide_good_ones(self):
        self.write("findings-library/good.md", "### [[FINDING_ID]]: Good\n")
        self.link("findings-library/linked.md", self.outside / "secret.md")
        data = self.new_data()
        self.assertEqual(data["library"], [{"path": "findings-library/good.md", "title": "Good"}])
        self.assertEqual(len(data["library_refused"]), 1)
        self.assertTrue(data["library_refused"][0].startswith(
            "path is outside the root: findings-library/linked.md -> "))

    def test_no_ir_number_left(self):
        self.write("incoming/bob/field-notes/bob/IR-999-z.md")
        data = self.new_data()
        self.assertEqual((data["ir_suggestion"], data["ir_note"]), (None, notebook.NO_IR_NUMBER_LEFT))
        status, text, _ = self.create(type="Incident report", title="Typed", nnn="500")
        self.assertEqual(status, 200, text)
        self.assertEqual(json.loads(text)["path"], "field-notes/alice/IR-500-typed.md")

    def test_library_title_marker_is_returned_as_written(self):
        # N3 stop flag (case 27): an entry copied straight from the template
        # gives the literal title "[[FINDING_TITLE]]", which the page puts in
        # the title box as it is. The user decides at the N3 stop.
        self.write("findings-library/raw.md", "### [[FINDING_ID]]: [[FINDING_TITLE]]\n")
        self.assertEqual(self.new_data()["library"],
                         [{"path": "findings-library/raw.md", "title": "[[FINDING_TITLE]]"}])

    # Cases 4, 5, 10 and 11: creating.

    def test_each_type_is_created(self):
        for fields, path in [
                ({"type": "Note", "title": "Quick Note"}, "field-notes/alice/NOTE-quick-note.md"),
                ({"type": "Incident report", "title": "DB down", "nnn": "007"},
                 "field-notes/alice/IR-007-db-down.md"),
                ({"type": "Status update", "title": "Noon"}, "field-notes/alice/SU-noon.md"),
                ({"type": "Inject response", "title": "Inject 1"}, "field-notes/alice/INJ-inject-1.md"),
                ({"type": "Finding", "title": "Weak creds", "nnn": "042"}, "findings/F-042-weak-creds.md")]:
            with self.subTest(path=path):
                status, text, content_type = self.create(**fields)
                self.assertEqual(status, 200, text)
                self.assertEqual(content_type, "application/json")
                self.assertEqual(json.loads(text), {"path": path, "warnings": [], "refused": []})
                self.assertTrue((self.home / path).is_file())
        self.assertEqual((self.home / "field-notes/alice/IR-007-db-down.md").read_text(encoding="utf-8"),
                         FAKE_TEMPLATES["templates/incident-report.md"].replace("[[IR_ID]]\n", "IR-007\n"))
        self.assertTrue((self.home / "findings/F-042-weak-creds.md").read_text(encoding="utf-8")
                        .startswith("### F-042: Weak creds\n"))

    def test_library_finding_is_created(self):
        self.write("findings-library/smb.md", LIBRARY_ENTRY)
        status, text, _ = self.create(type="Finding", title="SMB signing off", nnn="010",
                                      library="findings-library/smb.md")
        self.assertEqual(status, 200, text)
        path = json.loads(text)["path"]
        self.assertEqual(path, "findings/F-010-smb-signing-off.md")
        self.assertTrue((self.home / path).read_text(encoding="utf-8")
                        .startswith("### F-010: SMB signing off\n"))

    def test_fields_go_to_create_new_file_as_sent(self):
        real = notebook.create_new_file
        with mock.patch.object(notebook, "create_new_file", wraps=real) as wrapped:
            self.create(type="Note", title="A")
            self.create(type="Incident report", title="B", nnn="003")
            self.create(type="Finding", title="C", nnn="004")
            self.write("findings-library/smb.md", LIBRARY_ENTRY)
            self.create(type="Finding", title="D", nnn="005", library="findings-library/smb.md")
        root, logdir = self.home.resolve(), self.logdir.resolve()
        self.assertEqual(wrapped.call_args_list, [
            mock.call(root, logdir, "alice", "Note", "A", nnn=None, library=None),
            mock.call(root, logdir, "alice", "Incident report", "B", nnn="003", library=None),
            mock.call(root, logdir, "alice", "Finding", "C", nnn="004", library=None),
            mock.call(root, logdir, "alice", "Finding", "D", nnn="005",
                      library="findings-library/smb.md")])

    def test_duplicate_finding_warnings_come_back(self):
        self.write("findings/F-007-old.md")
        self.write("incoming/zed/findings/F-007-z.md")
        self.write("incoming/bob/findings/F-007-b.md")
        self.link("incoming/eve", self.outside)
        status, text, _ = self.create(type="Finding", title="New", nnn="007")
        self.assertEqual(status, 200, text)
        data = json.loads(text)
        self.assertEqual(data["path"], "findings/F-007-new.md")
        self.assertEqual(data["warnings"], [
            "F-007 already exists: findings/F-007-old.md",
            "F-007 already exists: incoming/bob/findings/F-007-b.md",
            "F-007 already exists: incoming/zed/findings/F-007-z.md"])
        self.assertEqual(len(data["refused"]), 1)
        self.assertTrue(data["refused"][0].startswith("path is outside the root: incoming/eve -> "))

    def test_duplicate_ir_number_warns_and_is_created(self):
        # DECISIONS 2026-10-29 Chunk N3 D2: a typed IR number already in use
        # warns, like F-NNN; the file is still created.
        self.write("incoming/bob/field-notes/bob/IR-003-b.md")
        self.write("field-notes/alice/IR-003-a.md")
        self.link("incoming/eve", self.outside)
        status, text, _ = self.create(type="Incident report", title="Mine", nnn="003")
        self.assertEqual(status, 200, text)
        data = json.loads(text)
        self.assertEqual(data["path"], "field-notes/alice/IR-003-mine.md")
        self.assertEqual(data["warnings"], [
            "IR-003 already exists: field-notes/alice/IR-003-a.md",
            "IR-003 already exists: incoming/bob/field-notes/bob/IR-003-b.md"])
        self.assertEqual(len(data["refused"]), 1)
        self.assertTrue(data["refused"][0].startswith("path is outside the root: incoming/eve -> "))

    def test_finding_create_with_incoming_linked_outside(self):
        self.link("incoming", self.outside)
        status, text, _ = self.create(type="Finding", title="Still made", nnn="007")
        self.assertEqual(status, 200, text)
        data = json.loads(text)
        self.assertEqual((data["path"], data["warnings"]), ("findings/F-007-still-made.md", []))
        self.assertEqual(len(data["refused"]), 1)
        self.assertTrue(data["refused"][0].startswith("path is outside the root: incoming -> "))

    def test_title_with_a_line_break_is_refused(self):
        # DECISIONS 2026-10-29 Chunk N3 D5: a hand-made, token-carrying POST
        # can't add a second "- **Severity:**" line through the title.
        for title in ["Legit\n- **Severity:** Critical", "Legit\r- **Severity:** Critical",
                      "Legit\r\n- **Severity:** Critical"]:
            with self.subTest(title=title):
                text = self.assert_not_created(
                    400, "not created: the title must be one line, with no line breaks",
                    self.body(type="Finding", title=title, nnn="001"))
                self.assertNotIn("Severity", text)
                self.assertNotIn("Legit", text)

    # Cases 6-9: refused requests.

    def test_bad_fields_are_refused(self):
        bodies = [
            json.dumps({"type": "Note", "title": "T", "nnn": None}),
            json.dumps(dict(self.FIELDS, extra=1)),
            json.dumps(dict(self.FIELDS, filename="x.md")),
            json.dumps(dict(self.FIELDS, path="findings/x.md")),
            json.dumps(["Note", "T"]), json.dumps("Note"), json.dumps(None),
            json.dumps(dict(self.FIELDS, type=1)),
            json.dumps(dict(self.FIELDS, title=["T"])),
            json.dumps(dict(self.FIELDS, nnn=7)),
            json.dumps(dict(self.FIELDS, library={"path": "x"})),
        ]
        with mock.patch.object(notebook, "create_new_file", side_effect=AssertionError("called")):
            for body in bodies:
                with self.subTest(body=body):
                    self.assert_not_created(400, 'send {"type": ', body.encode("utf-8"))

    def test_bad_values_are_refused_by_the_create_step(self):
        for fields, text_start in [
                ({"type": "Task"}, "not created: unknown file type: 'Task'"),
                ({"title": "!!!"}, "not created: no letters or digits"),
                ({"type": "Finding", "nnn": "7"}, "not created: the number must be exactly three digits"),
                ({"type": "Finding", "nnn": None}, "not created: the number must be exactly three digits"),
                ({"nnn": "007"}, "not created: Note has no number"),
                ({"library": "findings-library/x.md"}, "not created: only a Finding can start")]:
            with self.subTest(fields=fields):
                self.assert_not_created(400, text_start, self.body(**fields))

    def test_bad_bodies_are_refused(self):
        too_big = str(notebook.MAX_NEW_FILE_BYTES + 1)
        cases = [(b"", False), (b"{}", "abc"), (b"{}", "-1"), (b"{}", too_big), (b"{}", "1e3"),
                 (b"", None), (b"\xff\xfe", None), (b"{not json", None),
                 (b"x" * (notebook.MAX_NEW_FILE_BYTES + 1), None)]
        with mock.patch.object(notebook, "create_new_file", side_effect=AssertionError("called")):
            for body, length in cases:
                with self.subTest(body=body[:20], length=length):
                    self.assert_not_created(400, "send one new file as JSON", body, length=length)

    def test_a_short_body_doesnt_hang_the_server(self):
        # Content-Length says 50, but only 2 bytes come: the read gives up
        # after the handler's timeout, and the server goes on answering.
        # The real timeout is set (the stdlib default, None, waits forever);
        # the test shortens it so it runs quickly.
        self.assertEqual(notebook.NotebookHandler.timeout, 2)
        with mock.patch.object(notebook.NotebookHandler, "timeout", 0.5), \
                mock.patch.object(notebook, "create_new_file", side_effect=AssertionError("called")):
            self.assert_not_created(400, "send one new file as JSON", b"{}", length="50")
        status, _ = self.send("GET", "/files", self.good_host())
        self.assertEqual(status, 200)

    def test_guard_refuses_before_anything(self):
        other_run = notebook.make_token()
        with mock.patch.object(notebook, "create_new_file", side_effect=AssertionError("called")):
            for options in [{"host": "evil.example:" + str(self.port)}, {"token": None},
                            {"token": "wrong"}, {"token": [self.server.token] * 2},
                            {"token": other_run}]:
                with self.subTest(options=options):
                    self.assert_not_created(403, "refused: use http://127.0.0.1:", self.body(),
                                            **options)

    def test_token_from_the_served_page_works(self):
        _, page = self.send_full("GET", "/", self.good_host())
        parts = PageParts()
        parts.feed(page)
        status, text, _ = self.post(self.body(title="From page"), token=parts.tokens[0])
        self.assertEqual(status, 200, text)

    def test_errors_keep_their_reason(self):
        self.write("field-notes/alice/NOTE-taken.md", "mine\n")
        self.assert_not_created(403, "refused: already exists, choose a different title: "
                                "field-notes/alice/NOTE-taken.md", self.body(title="Taken"))
        (self.home / "templates/status-update.md").write_bytes("# Café\n".encode("cp1252"))
        text = self.assert_not_created(500, "not created: ", self.body(type="Status update"))
        self.assertIn("status-update.md is not UTF-8 text", text)
        with mock.patch.object(notebook, "create_new_file",
                               side_effect=PermissionError(13, "Permission denied", "templates/x.md")):
            text = self.assert_not_created(500, "not created: ", self.body())
        self.assertIn("Permission denied: 'templates/x.md'", text)

    # Cases 13 and 14: routes and GETs.

    def test_routes_are_in_the_tables(self):
        self.assertIs(notebook.GET_ROUTES["/new-data"], notebook.send_new_data)
        self.assertIs(notebook.POST_ROUTES["/new-file"], notebook.save_new_file)

    def test_gets_change_nothing(self):
        self.write("findings-library/a.md", "### [[FINDING_ID]]: A\n")
        before = tree(self.home)
        for path in ["/", "/files", "/new-data"]:
            with self.subTest(path=path):
                status, _ = self.send("GET", path, self.good_host())
                self.assertEqual(status, 200)
                self.assertEqual(tree(self.home), before)


class PageParts(HTMLParser):
    """Collects what a test needs from the app page: tags inside <nav> and
    <main>, the text a person would see, and the token in its <meta> tag."""

    def __init__(self):
        super().__init__()
        self.open = []
        self.inside = {"nav": [], "main": []}
        self.visible_text = []
        self.tokens = []

    def handle_starttag(self, tag, attrs):
        if tag == "meta" and dict(attrs).get("name") == "cptc-token":
            self.tokens.append(dict(attrs).get("content"))
        for column in self.inside:
            if column in self.open:
                self.inside[column].append((tag, dict(attrs).get("id")))
        self.open.append(tag)

    def handle_endtag(self, tag):
        if tag in self.open:
            del self.open[len(self.open) - 1 - self.open[::-1].index(tag)]

    def handle_data(self, data):
        hidden = {"title", "style", "script"}
        if data.strip() and not hidden.intersection(self.open):
            self.visible_text.append(data.strip())


class ScanMarkerTests(unittest.TestCase):
    """N4-01: scan_markers(), the fill-in view's field list (OQ-13)."""

    def test_uses_compile_helper_objects(self):
        # The same objects, not copies, so the two tools can't drift apart.
        self.assertIs(notebook.MARKER_RE, compile.MARKER_RE)
        self.assertIs(notebook.strip_markers, compile.strip_markers)

    def test_compile_imports_nothing_from_notebook(self):
        tree = ast.parse((support.TOOLS_DIR / "compile.py").read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertNotIn("notebook", imported)

    def test_each_kind_in_order_with_multiline_note(self):
        text = ("# [[FINDING_ID]]: title\n"
                "- **Severity:** [[CHOOSE: Critical / High / Low]]\n"
                "[[NOTE: An example:\n"
                "    nmap -p 445 10.0.0.5\n"
                "Delete this note.]]\n"
                "[[TODO: who ran it?]]\n")
        self.assertEqual(notebook.scan_markers(text), [
            {"name": "FINDING_ID", "body": None, "marker": "[[FINDING_ID]]"},
            {"name": "CHOOSE", "body": " Critical / High / Low",
             "marker": "[[CHOOSE: Critical / High / Low]]"},
            {"name": "NOTE", "body": " An example:\n    nmap -p 445 10.0.0.5\nDelete this note.",
             "marker": "[[NOTE: An example:\n    nmap -p 445 10.0.0.5\nDelete this note.]]"},
            {"name": "TODO", "body": " who ran it?", "marker": "[[TODO: who ran it?]]"},
        ])

    def test_repeated_name_shown_once_at_first_place(self):
        text = "[[HOST]] [[TODO: a]] [[HOST]] [[NOTE: b]] [[PORT]] [[HOST]] [[CHOOSE: x / y]]"
        self.assertEqual(notebook.scan_markers(text), [
            {"name": "HOST", "body": None, "marker": "[[HOST]]"},
            {"name": "TODO", "body": " a", "marker": "[[TODO: a]]"},
            {"name": "NOTE", "body": " b", "marker": "[[NOTE: b]]"},
            {"name": "PORT", "body": None, "marker": "[[PORT]]"},
            {"name": "CHOOSE", "body": " x / y", "marker": "[[CHOOSE: x / y]]"},
        ])

    def test_repeated_marker_with_body_listed_each_time(self):
        # Each is filled on its own (keyed by position), so none is dropped.
        text = "[[TODO: same]]\n[[TODO: same]]\n"
        self.assertEqual(notebook.scan_markers(text), [
            {"name": "TODO", "body": " same", "marker": "[[TODO: same]]"},
            {"name": "TODO", "body": " same", "marker": "[[TODO: same]]"},
        ])

    def test_bash_test_ignored(self):
        text = "[[HOST]]\nif [[ -f x ]]; then echo y; fi\n[[TODO: next]]\n"
        self.assertEqual(notebook.scan_markers(text), [
            {"name": "HOST", "body": None, "marker": "[[HOST]]"},
            {"name": "TODO", "body": " next", "marker": "[[TODO: next]]"},
        ])

    def test_unclosed_marker_does_not_swallow_the_next(self):
        text = "[[NOTE: never closed\n[[HOST]]\n"
        self.assertEqual(notebook.scan_markers(text), [
            {"name": "HOST", "body": None, "marker": "[[HOST]]"},
        ])

    def test_no_markers(self):
        self.assertEqual(notebook.scan_markers("plain text, done\n"), [])


class MarkerControlTests(unittest.TestCase):
    """N4-02: marker_controls(), each marker's control and box size."""

    def controls(self, text):
        return [(c["name"], c["control"]) for c in notebook.marker_controls(text)]

    def test_name_in_labelled_line_is_one_line_input(self):
        self.assertEqual(notebook.marker_controls("Intro.\n- **Host:** [[HOST]]\n"), [
            {"name": "HOST", "body": None, "marker": "[[HOST]]", "control": "input"},
        ])

    def test_marker_alone_on_its_line_is_textarea(self):
        self.assertEqual(self.controls("Intro.\n  [[SUMMARY]] \t\nMore.\n"),
                         [("SUMMARY", "textarea")])

    def test_line_after_heading_is_textarea_even_with_a_label(self):
        for heading in ("# Top", "###### Deep"):
            with self.subTest(heading=heading):
                text = heading + "\n- **Source IP:** [[SOURCE_IP]]\n"
                self.assertEqual(self.controls(text), [("SOURCE_IP", "textarea")])

    def test_marker_inside_heading_is_one_line(self):
        self.assertEqual(self.controls("# [[FINDING_ID]]: title\n"), [("FINDING_ID", "input")])
        # Even a heading that is only the marker, right under another heading.
        self.assertEqual(self.controls("# Top\n## [[TITLE]]\n"), [("TITLE", "input")])

    def test_choose_is_dropdown_with_literal_options(self):
        self.assertEqual(notebook.marker_controls("[[CHOOSE: first / second / third]]\n"), [
            {"name": "CHOOSE", "body": " first / second / third",
             "marker": "[[CHOOSE: first / second / third]]",
             "control": "dropdown", "options": ["first", "second", "third"]},
        ])

    def test_todo_is_input_with_guidance_sized_by_its_line(self):
        marker = "[[TODO: describe who verified it]]"
        self.assertEqual(notebook.marker_controls("- **Verified by:** " + marker + "\n"), [
            {"name": "TODO", "body": " describe who verified it", "marker": marker,
             "control": "input", "guidance": "describe who verified it"},
        ])
        self.assertEqual(notebook.marker_controls("Text.\n" + marker + "\n"), [
            {"name": "TODO", "body": " describe who verified it", "marker": marker,
             "control": "textarea", "guidance": "describe who verified it"},
        ])

    def test_note_is_help_never_editable(self):
        note = "[[NOTE: Example:\n    nmap -p 445 host\nDelete this.]]"
        for text in (note + "\n", "# Steps\n" + note + "\n", "- **Host:** " + note + "\n"):
            with self.subTest(text=text):
                self.assertEqual(notebook.marker_controls(text), [
                    {"name": "NOTE", "body": " Example:\n    nmap -p 445 host\nDelete this.",
                     "marker": note, "control": "note"},
                ])

    def test_notes_on_the_same_line_are_ignored_for_size(self):
        text = "Text.\n[[NOTE: before]] [[STEPS]] [[NOTE: after]]\n"
        self.assertEqual(self.controls(text), [
            ("NOTE", "note"), ("STEPS", "textarea"), ("NOTE", "note"),
        ])

    def test_multiline_note_ending_on_the_markers_line_is_ignored(self):
        text = "Text.\n[[NOTE: one\ntwo]] [[STEPS]]\n"
        self.assertEqual(self.controls(text), [("NOTE", "note"), ("STEPS", "textarea")])

    def test_two_markers_on_a_line_are_one_line(self):
        self.assertEqual(self.controls("Text.\n[[PREVIOUS_ID]] -> [[NEXT_ID]]\n"),
                         [("PREVIOUS_ID", "input"), ("NEXT_ID", "input")])

    def test_repeated_name_sized_by_its_first_place(self):
        self.assertEqual(self.controls("- **Host:** [[HOST]]\nText.\n[[HOST]]\n"),
                         [("HOST", "input")])
        self.assertEqual(self.controls("Text.\n[[HOST]]\n- **Host:** [[HOST]]\n"),
                         [("HOST", "textarea")])

    def test_windows_line_endings_size_the_same(self):
        self.assertEqual(self.controls("Text.\r\n[[SUMMARY]]\r\n- **Host:** [[HOST]]\r\n"),
                         [("SUMMARY", "textarea"), ("HOST", "input")])

    def test_marker_on_first_line_with_text_is_one_line(self):
        self.assertEqual(self.controls("Host: [[HOST]]"), [("HOST", "input")])

    def test_bare_note_or_choose_is_a_plain_name(self):
        self.assertEqual(self.controls("- **A:** [[NOTE]]\n- **B:** [[CHOOSE]]\n"),
                         [("NOTE", "input"), ("CHOOSE", "input")])

    def test_fields_match_scan_markers(self):
        # Fake text with every kind and a repeated name, so both functions'
        # dedupe and order are compared.
        text = ("# [[FINDING_ID]]: [[TITLE]]\n"
                "- **Severity:** [[CHOOSE: High / Low]]\n"
                "[[NOTE: one\ntwo]]\n"
                "[[TODO: who?]] and [[FINDING_ID]]\n"
                "[[STEPS]]\n")
        controls = notebook.marker_controls(text)
        self.assertEqual(len(controls), 6)
        self.assertEqual([{k: c[k] for k in ("name", "body", "marker")} for c in controls],
                         notebook.scan_markers(text))


class MarkerStatusTests(unittest.TestCase):
    """N4-06: marker_status(), the fill-in view's status line."""

    def test_counts_markers_and_notes(self):
        text = ("# [[FINDING_ID]]: x\n[[NOTE: delete me]]\n- **Severity:** [[CHOOSE: High / Low]]\n"
                "[[TODO: who?]]\n[[NOTE: a\nlonger note]]\n")
        self.assertEqual(notebook.marker_status(text), "5 markers left (2 of them notes)")

    def test_repeated_name_counts_once(self):
        # As its one box: the count matches the boxes and notes shown.
        text = "[[HOST]] and [[HOST]] and [[HOST]]\n[[PORT]]\n"
        self.assertEqual(notebook.marker_status(text), "2 markers left (0 of them notes)")

    def test_repeated_body_markers_count_each(self):
        text = "[[CHOOSE: a / b]]\n[[CHOOSE: a / b]]\n[[NOTE: x]] [[NOTE: x]]\n"
        self.assertEqual(notebook.marker_status(text), "4 markers left (2 of them notes)")

    def test_complete_when_no_markers_left(self):
        for text in ("", "# F-001: done\n", "if [[ -f x ]]; then echo; fi\n"):
            with self.subTest(text=text):
                self.assertEqual(notebook.marker_status(text), "complete")

    def test_only_notes_left_is_not_complete(self):
        self.assertEqual(notebook.marker_status("done\n[[NOTE: read me]]\n"),
                         "1 markers left (1 of them notes)")


class FormatWarningTests(unittest.TestCase):
    """N4-03: format_warnings(), the fill-in view's never-blocking checks (OQ-09)."""

    VECTOR = "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
    BAD_VECTORS = [
        "CVSS:3.1/AC:L/AV:N/PR:N/UI:N/S:U/C:H/I:H/A:H",       # reordered
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H",           # missing A
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H/E:P",   # extra metric
        "CVSS:3.1/AV:X/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",       # invalid value
        "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",       # wrong version
        "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H (9.8)", # trailing text
        "cvss:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",       # case
    ]

    def assert_rule(self, name, good, bad, warning):
        for value in good:
            with self.subTest(name=name, value=value):
                self.assertEqual(notebook.format_warnings(name, value), [])
        for value in bad:
            with self.subTest(name=name, value=value):
                self.assertEqual(notebook.format_warnings(name, value), [warning])

    def test_cvss_rule_is_compiles_regex_object(self):
        self.assertIs(notebook.FORMAT_RULES["CVSS_VECTOR"][0], compile.FULL_CVSS31_VECTOR_RE)

    def test_finding_id(self):
        self.assert_rule("FINDING_ID", ["F-000", "F-999"],
                         ["F-00", "F-0000", "G-001", "f-001", "F-٠٠١", "F-001x",
                          "F-001\n", " F-001", "IR-001"],
                         "should look like F-001")

    def test_ir_id(self):
        self.assert_rule("IR_ID", ["IR-000", "IR-999"],
                         ["IR-00", "IR-0000", "F-001", "ir-001", "IR-٠٠١", "IR-001x",
                          "IR-001\n", " IR-001"],
                         "should look like IR-001")

    def test_cvss_vector(self):
        self.assert_rule("CVSS_VECTOR", [self.VECTOR], self.BAD_VECTORS + [self.VECTOR + "\n"],
                         notebook.FORMAT_RULES["CVSS_VECTOR"][1])

    def test_cvss_vector_agrees_with_compile(self):
        for value in [self.VECTOR, self.VECTOR + "\n"] + self.BAD_VECTORS:
            with self.subTest(value=value):
                passes = compile.FULL_CVSS31_VECTOR_RE.fullmatch(value) is not None
                self.assertEqual(notebook.format_warnings("CVSS_VECTOR", value) == [], passes)

    def test_cvss_score(self):
        self.assert_rule("CVSS_SCORE", ["0.0", "9.9", "10.0"],
                         ["10.1", "11.0", "-1.0", "7", "7.", ".5", "7.55", "07.5", "7.5 high",
                          "7.5\n", "٧.٥"],
                         "should be 0.0 to 10.0 with one decimal, e.g. 7.5")

    def test_dates_for_every_date_name(self):
        for name in ("DATE", "DATE_DETECTED", "DATE_REPORTED"):
            self.assert_rule(name, ["2026-10-29"],
                             ["2026-1-29", "2026-10-9", "26-10-29", "2026/10/29", "2026.10.29",
                              "2026-10-29 morning", "2026-10-29\n", "٢026-10-29"],
                             "should be a date as YYYY-MM-DD")

    def test_times_for_every_time_name(self):
        for name in ("TIME", "TIME_STARTED", "TIME_STOPPED"):
            self.assert_rule(name, ["09:05", "23:59"],
                             ["9:05", "09:5", "09.05", "0905", "09:05 PDT", "09:05\n", "09:05:00"],
                             "should be a time as HH:MM")

    def test_reference_url(self):
        self.assert_rule("REFERENCE_URL", ["http://example.test", "https://example.test/a", "http"],
                         ["example.test", "see http://example.test", "HTTP://example.test",
                          "Https://example.test", " http://example.test"],
                         "should start with http")

    def test_leftover_marker_warns_with_or_without_a_format_problem(self):
        self.assertEqual(notebook.format_warnings("REFERENCE_URL", "http://x/[[Y"),
                         [notebook.LEFTOVER_WARNING])
        self.assertEqual(notebook.format_warnings("FINDING_ID", "F-001 [[NOTE: x]]"),
                         ["should look like F-001", notebook.LEFTOVER_WARNING])

    def test_leftover_warning_follows_qas_own_check(self):
        # Chunk N4 CR-1: only what compile.LEFTOVER_RE reports, so a pasted
        # bash test gets no warning.
        for value in ("if [[ -f /etc/shadow ]]; then cat it; fi", "[[ -f x ]]", "[[a", "[[", "[[1"):
            with self.subTest(value=value):
                self.assertIsNone(compile.LEFTOVER_RE.search(value))
                self.assertEqual(notebook.format_warnings("REPRODUCTION_STEPS", value), [])
        for value in ("[[A", "x [[HOST]] y", "[[_"):
            with self.subTest(value=value):
                self.assertEqual(notebook.format_warnings("REPRODUCTION_STEPS", value),
                                 [notebook.LEFTOVER_WARNING])

    def test_unknown_name_gets_only_the_leftover_warning(self):
        self.assertEqual(notebook.format_warnings("HOST", "anything at all\n"), [])
        self.assertEqual(notebook.format_warnings("HOST", "a [[B"), [notebook.LEFTOVER_WARNING])
        # A name that only contains a checked one isn't checked.
        self.assertEqual(notebook.format_warnings("PREVIOUS_FINDING_ID", "none"), [])

    def test_empty_value_gets_no_warning(self):
        for name in ("FINDING_ID", "CVSS_SCORE", "DATE_DETECTED", "HOST"):
            with self.subTest(name=name):
                self.assertEqual(notebook.format_warnings(name, ""), [])

    def test_warnings_never_block_or_change_the_value(self):
        samples = [("FINDING_ID", "F-1"), ("IR_ID", "x"), ("CVSS_VECTOR", self.BAD_VECTORS[0]),
                   ("CVSS_SCORE", "11.0"), ("DATE", "today"), ("TIME", "noon"),
                   ("REFERENCE_URL", "ftp://x"), ("HOST", "[[X")]
        for name, value in samples:
            with self.subTest(name=name):
                typed = str(value)
                warnings = notebook.format_warnings(name, typed)
                self.assertIsInstance(warnings, list)
                self.assertGreater(len(warnings), 0)
                self.assertTrue(all(isinstance(w, str) for w in warnings))
                self.assertEqual(typed, value)


class ApplyMarkerValueTests(unittest.TestCase):
    """N4-04: apply_marker_values(), the Save step's exact replacement."""

    def fields(self, scanned, *values):
        """scan_markers(scanned)'s fields, given these values in order."""
        fields = notebook.scan_markers(scanned)
        self.assertEqual(len(fields), len(values))
        return [dict(field, value=value) for field, value in zip(fields, values)]

    def test_plain_marker_replaced_rest_unchanged(self):
        text = "# Title\r\n- **Host:** [[HOST]]  \r\n\ttail\n"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, "dc01")),
                         ("# Title\r\n- **Host:** dc01  \r\n\ttail\n", []))

    def test_value_inserted_byte_for_byte(self):
        value = " a | `b` $HOME [[X \\n \\\\ café → \U0001F600\nsecond line\r\n  "
        text = "before [[DETAIL]] after"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, value)),
                         ("before " + value + " after", []))

    def test_inserted_value_is_not_processed_again(self):
        text = "[[HOST]] [[PORT]]"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, "[[PORT]]", "445")),
                         ("[[PORT]] 445", []))

    def test_repeated_name_fills_every_copy_only(self):
        text = "[[HOST]] / [[HOSTNAME]] / [[HOST]]\n[[HOST]]"
        fields = self.fields(text, "dc01", "")
        self.assertEqual(notebook.apply_marker_values(text, fields),
                         ("dc01 / [[HOSTNAME]] / dc01\ndc01", []))

    def test_identical_body_markers_filled_by_position(self):
        text = "1: [[TODO: same]]\n2: [[TODO: same]]\n"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, "first", "second")),
                         ("1: first\n2: second\n", []))

    def test_moved_marker_is_found_where_it_is_now(self):
        scanned = "A [[TODO: who?]]\nB [[HOST]]\n"
        current = "B [[HOST]]\nnew line\nA moved: [[TODO: who?]]\n"
        self.assertEqual(notebook.apply_marker_values(current, self.fields(scanned, "alice", "dc01")),
                         ("B dc01\nnew line\nA moved: alice\n", []))

    def test_missing_marker_warns_and_changes_nothing_else(self):
        scanned = "[[HOST]] [[TODO: who?]] [[PORT]]"
        current = "dc01 typed by hand [[TODO: who?]] [[PORT]]"
        self.assertEqual(
            notebook.apply_marker_values(current, self.fields(scanned, "dc02", "", "")),
            (current, ["[[HOST]] is no longer in the text: value not saved: dc02"]))
        current = "[[HOST]] [[TODO: whom?]] [[PORT]]"
        self.assertEqual(
            notebook.apply_marker_values(current, self.fields(scanned, "", "alice", "")),
            (current, ["[[TODO: who?]] is no longer in the text: value not saved: alice"]))

    def test_missing_marker_warning_keeps_the_value_exactly(self):
        # N5 F3b: the box goes with the rescan, so the warning is where the
        # writer copies the value from: every character as typed.
        value = "  1. `nxc smb 10.0.0.5 -u guest -p ''` | $x [[ -f y ]]\r\n2. [[HOST]] \t"
        current = "steps were here\n"
        self.assertEqual(
            notebook.apply_marker_values(current, self.fields("[[REPRODUCTION_STEPS]]\n", value)),
            (current, ["[[REPRODUCTION_STEPS]] is no longer in the text: value not saved: " + value]))

    def test_one_of_two_identical_body_markers_removed(self):
        # Which copy is left can't be known, so neither value is used and
        # both warn: replacing the survivor could put the wrong value there.
        scanned = "1: [[TODO: same]]\n2: [[TODO: same]]\n"
        current = "2: [[TODO: same]]\n"
        warning = "[[TODO: same]] is in the text 1 times, not 2, so it can't be told apart: value not saved: "
        # Each warning carries its own box's value (N5 F3c).
        self.assertEqual(notebook.apply_marker_values(current, self.fields(scanned, "first", "second")),
                         (current, [warning + "first", warning + "second"]))
        # Only one box filled: still not used, one warning.
        self.assertEqual(notebook.apply_marker_values(current, self.fields(scanned, "", "second")),
                         (current, [warning + "second"]))

    def test_identical_body_marker_copied_also_refused(self):
        scanned = "[[TODO: same]]\n"
        current = "[[TODO: same]]\n[[TODO: same]]\n"
        self.assertEqual(notebook.apply_marker_values(current, self.fields(scanned, "x")),
                         (current, ["[[TODO: same]] is in the text 2 times, not 1,"
                                    " so it can't be told apart: value not saved: x"]))

    def test_told_apart_warning_keeps_the_value_exactly(self):
        # N5 F3c: the box comes back empty, so the value is copied from here.
        value = "  1. `nxc smb 10.0.0.5 -u guest -p ''` | $x [[ -f y ]]\r\n2. [[HOST]] \t"
        scanned = "[[TODO: step]]\n[[TODO: step]]\n"
        current = "[[TODO: step]]\n"
        self.assertEqual(
            notebook.apply_marker_values(current, self.fields(scanned, value, "")),
            (current, ["[[TODO: step]] is in the text 1 times, not 2,"
                       " so it can't be told apart: value not saved: " + value]))

    def test_empty_value_leaves_marker(self):
        text = "a [[HOST]] b [[TODO: who?]] c [[CHOOSE: x / y]]\n"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, "", "", "")), (text, []))
        # Empty and gone: nothing to save, so no warning either.
        self.assertEqual(notebook.apply_marker_values("gone\n", self.fields(text, "", "", "")),
                         ("gone\n", []))

    def test_whitespace_only_value_counts_as_filled(self):
        text = "a [[HOST]] b [[TODO: who?]]"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, " ", "\t\n")),
                         ("a   b \t\n", []))

    def test_note_is_never_replaced(self):
        text = "x [[NOTE: one\ntwo]] y [[NOTE: short]] z\n"
        self.assertEqual(notebook.apply_marker_values(text, self.fields(text, "gone", "also gone")),
                         (text, []))

    def test_mixed_save(self):
        scanned = ("# [[FINDING_ID]]: [[TITLE]]\n"
                   "[[NOTE: help\nmore]]\n"
                   "- **Severity:** [[CHOOSE: High / Low]]\n"
                   "1. [[TODO: step]]\n2. [[TODO: step]]\n"
                   "[[HOST]] then [[FINDING_ID]] [[GONE]]\n")
        current = ("# [[FINDING_ID]]: [[TITLE]]\n"
                   "[[NOTE: help\nmore]]\n"
                   "- **Severity:** [[CHOOSE: High / Low]]\n"
                   "1. [[TODO: step]]\n2. [[TODO: step]]\n"
                   "[[HOST]] then [[FINDING_ID]] typed\n")
        fields = self.fields(scanned, "F-001", "", "ignored", "High", "one", "two [[HOST]]",
                             "dc01", "x")
        self.assertEqual(notebook.apply_marker_values(current, fields), (
            "# F-001: [[TITLE]]\n"
            "[[NOTE: help\nmore]]\n"
            "- **Severity:** High\n"
            "1. one\n2. two [[HOST]]\n"
            "dc01 then F-001 typed\n",
            ["[[GONE]] is no longer in the text: value not saved: x"]))


# A working copy with the person's own files and one file in every place
# the fill-in view must never open or save (N4-05 case 4).
EDITABLE_FILES = {
    "findings/F-001-a.md": "# F-001\n- **Host:** [[HOST]]\n",
    "findings/F-005-other.md": "other finding\n",
    "field-notes/alice/NOTE-x.md": "note\n",
    "field-notes/alice/checklist-state.json": "{}\n",
    "field-notes/bob/NOTE-b.md": "bob's note\n",
    "notes/study.md": "study\n",
    "templates/finding.md": "[[FINDING_ID]]\n",
    "checklists/10-recon.md": "- [ ] scan\n",
    "incoming/bob/findings/F-009-x.md": "bob's finding\n",
    "findings/sub/F-002-nested.md": "nested\n",
    "findings/F-003-x.txt": "not markdown\n",
    "elsewhere/F-001-a.md": "in-root copy\n",
    "elsewhere/alice/NOTE-x.md": "in-root copy\n",
}


# save()'s default base: the file's text as it is on disk at the time.
CURRENT = object()


class EditableFileTests(ServerTestCase):
    """N4-05: GET and POST /file, opening and saving the person's own files."""

    def setUp(self):
        super().setUp()
        self.home = support.make_worktree(self, EDITABLE_FILES)
        self.server.settings["root"] = self.home.resolve()
        self.outside = support.make_worktree(self, {"F-001-a.md": "outside\n",
                                                    "alice/NOTE-x.md": "outside\n",
                                                    "secret.md": "secret\n"})

    def snapshot(self):
        return tree(self.home), tree(self.outside), tree(self.logdir)

    def get(self, path):
        """GET /file?path=...; return (status, JSON or text)."""
        response, body = self.send_full("GET", "/file?path=" + quote(path, safe=""), self.good_host())
        self.assert_safe_headers(response)
        if response.status == 200:
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            return 200, json.loads(body)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        return response.status, body

    def post(self, body, token="default", host=None, length=None):
        """POST raw body bytes to /file; return (status, JSON or text). Options as NewFileRouteTests.post()."""
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest("POST", "/file", skip_host=True)
        connection.putheader("Host", host or self.good_host())
        if token == "default":
            connection.putheader("X-CPTC-Token", self.server.token)
        elif token is not None:
            connection.putheader("X-CPTC-Token", token)
        connection.putheader("Content-Type", "application/json")
        if length is not False:
            connection.putheader("Content-Length", str(len(body)) if length is None else length)
        connection.endheaders(body)
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        self.assert_safe_headers(response)
        if response.status == 200:
            self.assertEqual(response.getheader("Content-Type"), "application/json")
            return 200, json.loads(text)
        self.assertEqual(response.getheader("Content-Type"), "text/plain; charset=utf-8")
        return response.status, text

    def disk_text(self, path):
        """The file's text as GET /file reads it, or "" if it isn't a readable file."""
        try:
            # is_file() first: opening a FIFO would wait forever.
            if (self.home / path).is_file():
                return compile.read_markdown(self.home / path)
        except (OSError, ValueError, compile.InputError):
            pass
        return ""

    def save(self, path, text, fields=(), base=CURRENT, **options):
        """POST a save; base defaults to the file's text now, so only D4 tests go stale."""
        if base is CURRENT:
            base = self.disk_text(path)
        body = json.dumps({"path": path, "text": text, "base": base,
                           "fields": list(fields)}).encode("utf-8")
        return self.post(body, **options)

    def assert_refused(self, status_wanted, text_start, call, *args, **options):
        """call(*args) is refused with this status and text, and nothing on disk changes."""
        before = self.snapshot()
        status, text = call(*args, **options)
        self.assertEqual(status, status_wanted, text)
        self.assertTrue(text.startswith(text_start), text)
        self.assertEqual(self.snapshot(), before)

    def assert_both_refused(self, path, text_start="refused: "):
        self.assert_refused(403, text_start, self.get, path)
        self.assert_refused(403, text_start, self.save, path, "changed\n")

    def link(self, path, target):
        full = self.home / path
        if full.is_dir() and not full.is_symlink():
            shutil.rmtree(str(full))
        elif full.exists():
            full.unlink()
        full.parent.mkdir(parents=True, exist_ok=True)
        full.symlink_to(target)

    # Case 1
    def test_read_own_files(self):
        for path in ("findings/F-001-a.md", "field-notes/alice/NOTE-x.md"):
            with self.subTest(path=path):
                before = self.snapshot()
                text = EDITABLE_FILES[path]
                self.assertEqual(self.get(path), (200, {
                    "path": path, "text": text, "fields": notebook.marker_controls(text),
                    "status": notebook.marker_status(text)}))
                self.assertEqual(self.snapshot(), before)

    def test_only_listed_files_open(self):
        files, _ = notebook.list_own_files(self.home.resolve(), "alice")
        self.assertEqual(files, ["findings/F-001-a.md", "findings/F-005-other.md",
                                 "field-notes/alice/NOTE-x.md"])
        for path in files:
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 200)

    # Case 2
    def test_save_round_trips_exact_bytes(self):
        text = "café → \U0001F600\r\nline\n\ttab  \r\n  trailing \nno final newline"
        for path in ("findings/F-001-a.md", "field-notes/alice/NOTE-x.md"):
            with self.subTest(path=path):
                status, answer = self.save(path, text)
                self.assertEqual((status, answer), (200, {
                    "path": path, "text": text, "fields": [], "status": "complete", "warnings": []}))
                self.assertEqual((self.home / path).read_bytes(), text.encode("utf-8"))
                self.assertEqual(self.get(path)[1]["text"], text)
        # The temp file was renamed into place, so none is left over.
        self.assertEqual(sorted(p.name for p in (self.home / "findings").glob(".save-*")), [])

    def test_save_keeps_the_files_mode(self):
        path = self.home / "findings/F-001-a.md"
        os.chmod(str(path), 0o640)
        self.assertEqual(self.save("findings/F-001-a.md", "x\n")[0], 200)
        self.assertEqual(os.stat(str(path)).st_mode & 0o777, 0o640)

    # Case 3
    def test_bom_is_dropped(self):
        path = self.home / "findings/F-001-a.md"
        path.write_bytes(b"\xef\xbb\xbf# F-001\r\n[[HOST]]\r\n")
        status, answer = self.get("findings/F-001-a.md")
        self.assertEqual(answer["text"], "# F-001\r\n[[HOST]]\r\n")
        # The BOM alone is no change on disk (Chunk N4 D4 case 9).
        self.assertEqual(self.save("findings/F-001-a.md", answer["text"],
                                   base=answer["text"])[0], 200)
        self.assertEqual(path.read_bytes(), b"# F-001\r\n[[HOST]]\r\n")

    # Case 4
    def test_other_places_refused(self):
        for path in ("notes/study.md", "templates/finding.md", "checklists/10-recon.md",
                     "incoming/bob/findings/F-009-x.md", "field-notes/bob/NOTE-b.md",
                     "findings/sub/F-002-nested.md", "findings/F-003-x.txt",
                     "field-notes/alice/checklist-state.json", "elsewhere/F-001-a.md",
                     str(self.logdir / "alice.log"), "findings", "field-notes/alice"):
            with self.subTest(path=path):
                self.assert_both_refused(path, "refused: not one of your own files: ")

    def test_log_folder_inside_own_folder_not_saved(self):
        self.server.settings["logdir"] = (self.home / "field-notes/alice").resolve()
        self.assertEqual(self.get("field-notes/alice/NOTE-x.md")[0], 200)
        self.assert_refused(403, "refused: the log folder is read-only", self.save,
                            "field-notes/alice/NOTE-x.md", "changed\n")

    # Case 5
    def test_missing_file_refused_and_not_created(self):
        self.assert_both_refused("findings/F-404-missing.md", "refused: not one of your own files: ")
        self.assertFalse((self.home / "findings/F-404-missing.md").exists())

    # Case 6
    def test_traversal_and_malformed_paths_refused(self):
        for path in (str(self.home / "findings/F-001-a.md"), "/findings/F-001-a.md",
                     "findings/../findings/F-001-a.md", "findings//F-001-a.md",
                     "./findings/F-001-a.md", "../" + self.outside.name + "/secret.md",
                     "findings\x00/F-001-a.md", "field-notes/al\x00ice/NOTE-x.md",
                     "findings/F-001-a.md\x00", "\x00", ""):
            with self.subTest(path=path):
                self.assert_refused(403, "refused: not one of your own files: ", self.save,
                                    path, "changed\n")
                if path:
                    self.assert_refused(403, "refused: not one of your own files: ", self.get, path)

    def test_get_needs_exactly_one_path(self):
        for query in ("/file", "/file?path=", "/file?path=findings/F-001-a.md&path=findings/F-005-other.md"):
            with self.subTest(query=query):
                before = self.snapshot()
                response, body = self.send_full("GET", query, self.good_host())
                self.assert_safe_headers(response)
                self.assertEqual(response.status, 400)
                self.assertTrue(body.startswith("give one file: "), body)
                self.assertEqual(self.snapshot(), before)

    # Case 7
    def test_links_pointing_outside_refused_at_every_level(self):
        for level, target, path in (
                ("findings", self.outside, "findings/F-001-a.md"),
                ("field-notes", self.outside, "field-notes/alice/NOTE-x.md"),
                ("field-notes/alice", self.outside / "alice", "field-notes/alice/NOTE-x.md"),
                ("findings/F-001-a.md", self.outside / "secret.md", "findings/F-001-a.md")):
            with self.subTest(level=level):
                self.home = support.make_worktree(self, EDITABLE_FILES)
                self.server.settings["root"] = self.home.resolve()
                self.link(level, target)
                self.assert_both_refused(path, "refused: not one of your own files: ")

    # Cases 8 and 9
    def test_in_root_links_open_but_never_save(self):
        for level, target, path in (
                ("findings", "elsewhere", "findings/F-001-a.md"),
                ("field-notes", "elsewhere", "field-notes/alice/NOTE-x.md"),
                ("field-notes/alice", "bob", "field-notes/alice/NOTE-b.md"),
                ("findings/F-001-a.md", "F-005-other.md", "findings/F-001-a.md")):
            with self.subTest(level=level):
                self.home = support.make_worktree(self, EDITABLE_FILES)
                self.server.settings["root"] = self.home.resolve()
                self.link(level, target)
                # Reading follows the in-root link, as the list does (OQ-17).
                self.assertEqual(self.get(path)[0], 200)
                self.assert_refused(403, "refused: a link, not saving through it: " + level,
                                    self.save, path, "changed\n")

    # Case 10
    def test_hard_link_opens_but_never_saves(self):
        os.link(str(self.home / "findings/F-001-a.md"), str(self.home / "findings/F-006-twin.md"))
        for path in ("findings/F-001-a.md", "findings/F-006-twin.md"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 200)
                self.assert_refused(403, "refused: the file has another hard link", self.save,
                                    path, "changed\n")

    # Case 11
    def test_folder_named_md_refused(self):
        (self.home / "findings/F-007-dir.md").mkdir()
        self.assert_both_refused("findings/F-007-dir.md", "refused: not one of your own files: ")

    def test_fifo_named_md_refused(self):
        fifo = self.home / "findings/F-008-pipe.md"
        os.mkfifo(str(fifo))
        before = os.lstat(str(fifo))
        # tree() would open the FIFO and wait, so only its own state is compared.
        for call in (self.get, lambda path: self.save(path, "changed\n")):
            status, text = call("findings/F-008-pipe.md")
            self.assertEqual(status, 403, text)
            self.assertTrue(text.startswith("refused: not one of your own files: "), text)
        after = os.lstat(str(fifo))
        self.assertTrue(stat.S_ISFIFO(after.st_mode))
        self.assertEqual((after.st_ino, after.st_mtime_ns), (before.st_ino, before.st_mtime_ns))

    # Case 12
    def test_text_that_cant_be_utf8_refused(self):
        self.assert_refused(400, "send one save as JSON", self.post,
                            b'{"path": "findings/F-001-a.md", "text": "\xff", "fields": [],'
                            b' "base": "# F-001\\n- **Host:** [[HOST]]\\n"}')
        self.assert_refused(400, "not saved: ", self.post,
                            b'{"path": "findings/F-001-a.md", "text": "a\\ud800b", "fields": [],'
                            b' "base": "# F-001\\n- **Host:** [[HOST]]\\n"}')

    # Case 13
    def test_bad_bodies_refused_before_any_write(self):
        good = {"path": "findings/F-001-a.md", "text": "x\n", "fields": [],
                "base": EDITABLE_FILES["findings/F-001-a.md"]}
        field = {"name": "HOST", "marker": "[[HOST]]", "body": None, "value": "dc01"}

        def body(**changes):
            fields = dict(good)
            fields.update(changes)
            return json.dumps(fields).encode("utf-8")
        cases = [
            (b"", False), (body(), "abc"), (body(), "-1"), (body(), "1e3"),
            (b"x" * 10, str(notebook.MAX_SAVE_BYTES + 1)),
            (b"{not json", None), (b"[]", None), (b'"text"', None),
            (json.dumps({"path": "findings/F-001-a.md", "text": "x"}).encode(), None),
            # Chunk N4 D4 cases 3 and 4: base missing, or not text.
            (json.dumps({k: v for k, v in good.items() if k != "base"}).encode(), None),
            (body(base=None), None), (body(base={}), None), (body(base=[]), None),
            (body(base=1), None), (body(base=True), None),
            (body(extra=1), None), (body(path=1), None), (body(text=None), None),
            (body(fields={}), None), (body(fields=[1]), None),
            (body(fields=[{k: v for k, v in field.items() if k != "value"}]), None),
            (body(fields=[dict(field, value=None)]), None), (body(fields=[dict(field, body=1)]), None),
            (body(fields=[dict(field, name=1)]), None), (body(fields=[dict(field, marker=None)]), None),
        ]
        with mock.patch.object(notebook, "save_editable_file", side_effect=AssertionError("called")):
            for raw, length in cases:
                with self.subTest(raw=raw[:30], length=length):
                    before = self.snapshot()
                    status, text = self.post(raw, length=length)
                    self.assertEqual(status, 400, text)
                    self.assertEqual(self.snapshot(), before)

    def test_a_short_body_doesnt_hang_the_server(self):
        with mock.patch.object(notebook.NotebookHandler, "timeout", 0.5), \
                mock.patch.object(notebook, "save_editable_file", side_effect=AssertionError("called")):
            self.assert_refused(400, "send one save as JSON", self.post, b"{}", length="50")
        self.assertEqual(self.get("findings/F-001-a.md")[0], 200)

    # Case 14
    def test_only_a_fully_allowed_request_saves(self):
        for options in ({"token": None}, {"token": "wrong"}, {"token": notebook.make_token()},
                        {"host": "evil.example:" + str(self.port)}, {"host": "localhost:" + str(self.port)}):
            with self.subTest(options=options):
                self.assert_refused(403, "refused: use http://127.0.0.1:", self.save,
                                    "findings/F-001-a.md", "changed\n", **options)
        self.assertEqual(self.save("findings/F-001-a.md", "changed\n")[0], 200)
        self.assertEqual((self.home / "findings/F-001-a.md").read_bytes(), b"changed\n")

    # Cases 15 and 16 are in every helper: each answer's type and nosniff
    # header, and an unchanged disk after every refusal.

    def test_save_applies_boxes_and_rescans(self):
        status, opened = self.get("findings/F-001-a.md")
        text = opened["text"] + "- **Score:** [[CVSS_SCORE]]\n[[GONE]]\n"
        fields = notebook.marker_controls(text)
        values = {"HOST": "dc01 [[X", "CVSS_SCORE": "11.0", "GONE": "y"}
        # The fields go back as GET gave them, with "control" and all.
        sent = [dict(field, value=values[field["name"]]) for field in fields]
        typed = text.replace("[[GONE]]\n", "")
        status, answer = self.save("findings/F-001-a.md", typed, sent)
        saved = "# F-001\n- **Host:** dc01 [[X\n- **Score:** 11.0\n"
        self.assertEqual((status, answer), (200, {
            "path": "findings/F-001-a.md", "text": saved, "fields": notebook.marker_controls(saved),
            "status": "complete",
            "warnings": ["[[GONE]] is no longer in the text: value not saved: y",
                         "HOST: " + notebook.LEFTOVER_WARNING,
                         "CVSS_SCORE: should be 0.0 to 10.0 with one decimal, e.g. 7.5"]}))


class StaleSaveTests(EditableFileTests):
    """Chunk N4 D4 (DECISIONS 2026-10-29): a save sends back the text it
    started from as "base", and is refused if the file changed since."""

    PATH = "findings/F-001-a.md"
    OPENED = EDITABLE_FILES[PATH]

    # Run only these tests here, not EditableFileTests' again.
    def run(self, result=None):
        if not self._testMethodName.startswith("test_stale_"):
            return result
        return super().run(result)

    def file_state(self):
        """Bytes, mode, inode and change times of the file, plus the folder's names."""
        info = os.lstat(str(self.home / self.PATH))
        return ((self.home / self.PATH).read_bytes(), info.st_mode, info.st_ino,
                info.st_mtime_ns, sorted(os.listdir(str(self.home / "findings"))))

    def assert_stale(self, base=OPENED, text="mine\n"):
        """The save is refused with the 409, writes nothing and makes no temp file."""
        before = self.file_state(), self.snapshot()
        with mock.patch.object(notebook.tempfile, "mkstemp",
                               side_effect=AssertionError("temp file made")):
            status, answer = self.save(self.PATH, text, base=base)
        self.assertEqual((status, answer), (409, notebook.STALE_MESSAGE))
        self.assertEqual((self.file_state(), self.snapshot()), before)

    def test_stale_get_text_is_the_base(self):
        # Cases 1 and 2: GET's text, sent back unchanged, lets the save through.
        status, opened = self.get(self.PATH)
        self.assertEqual(opened["text"], self.OPENED)
        fields = [dict(field, value="dc01") for field in opened["fields"]]
        status, answer = self.save(self.PATH, opened["text"], fields, base=opened["text"])
        self.assertEqual(status, 200, answer)
        self.assertEqual((self.home / self.PATH).read_bytes(), b"# F-001\n- **Host:** dc01\n")

    def test_stale_any_change_on_disk_is_refused(self):
        # Cases 6, 7 and 8: a whole new text, one character, a trailing
        # space, or the same text with Windows line endings.
        for newer in ("someone else's edit\n", self.OPENED.replace("F-001", "F-002"),
                      self.OPENED + " ", self.OPENED.replace("\n", "\r\n")):
            with self.subTest(newer=newer):
                (self.home / self.PATH).write_bytes(newer.encode("utf-8"))
                self.assert_stale()
                self.assertEqual((self.home / self.PATH).read_bytes(), newer.encode("utf-8"))

    def test_stale_base_differing_in_whitespace_is_refused(self):
        # Case 8 the other way round: the disk is unchanged, the base isn't.
        for base in (self.OPENED.replace("\n", "\r\n"), self.OPENED.rstrip("\n"), " " + self.OPENED):
            with self.subTest(base=base):
                self.assert_stale(base=base)

    def test_stale_bom_added_on_disk_is_no_change(self):
        # Case 9: an editor adding a BOM leaves the text as GET reads it.
        (self.home / self.PATH).write_bytes(b"\xef\xbb\xbf" + self.OPENED.encode("utf-8"))
        self.assertEqual(self.save(self.PATH, "mine\n", base=self.OPENED)[0], 200)
        self.assertEqual((self.home / self.PATH).read_bytes(), b"mine\n")

    def test_stale_replaced_by_a_new_file(self):
        # Cases 11 and 12: a new file at the name (as an editor's save does)
        # is stale if its text differs, and saves if it is the same.
        full = self.home / self.PATH
        replacement = self.home / "findings/.replacement"
        replacement.write_text("their version\n", encoding="utf-8")
        os.replace(str(replacement), str(full))
        self.assert_stale()
        self.assertEqual(full.read_bytes(), b"their version\n")
        replacement.write_text(self.OPENED, encoding="utf-8")
        os.replace(str(replacement), str(full))
        self.assertEqual(self.save(self.PATH, "mine\n", base=self.OPENED)[0], 200)
        self.assertEqual(full.read_bytes(), b"mine\n")

    def test_stale_links_swapped_in_are_still_refused_by_d2(self):
        # Case 13: a link swapped in after GET, even to a file holding the
        # same text, is refused by the link checks, and neither file changes.
        for kind in ("symlink", "hard link"):
            with self.subTest(kind=kind):
                self.home = support.make_worktree(self, EDITABLE_FILES)
                self.server.settings["root"] = self.home.resolve()
                twin = self.home / "elsewhere/F-001-a.md"
                twin.write_text(self.OPENED, encoding="utf-8")
                (self.home / self.PATH).unlink()
                if kind == "symlink":
                    (self.home / self.PATH).symlink_to(twin)
                else:
                    os.link(str(twin), str(self.home / self.PATH))
                self.assert_refused(403, "refused: ", self.save, self.PATH, "mine\n",
                                    base=self.OPENED)
                self.assertEqual(twin.read_bytes(), self.OPENED.encode("utf-8"))

    def test_stale_file_now_too_big_or_not_text(self):
        # Case 14: a file grown past what a save can carry is stale; one that
        # is no longer UTF-8 can't be compared, so it isn't saved either.
        full = self.home / self.PATH
        full.write_bytes(b"x" * (notebook.MAX_SAVE_BYTES + 1))
        self.assert_stale()
        full.write_bytes(b"\xff not text\n")
        before = full.read_bytes(), self.snapshot()
        status, answer = self.save(self.PATH, "mine\n", base=self.OPENED)
        self.assertEqual(status, 500, answer)
        self.assertTrue(answer.startswith("not saved: "), answer)
        self.assertEqual((full.read_bytes(), self.snapshot()), before)

    def test_stale_saved_text_is_the_next_base(self):
        # Cases 15, 16 and 17: the answer's text, boxes applied and format
        # warnings and all, is the next base; the first base is now stale.
        text = self.OPENED + "- **Score:** [[CVSS_SCORE]]\n"
        fields = [dict(field, value={"HOST": "dc01", "CVSS_SCORE": "11.0"}[field["name"]])
                  for field in notebook.marker_controls(text)]
        status, first = self.save(self.PATH, text, fields, base=self.OPENED)
        self.assertEqual(status, 200, first)
        self.assertEqual(first["text"], "# F-001\n- **Host:** dc01\n- **Score:** 11.0\n")
        self.assertNotEqual(first["warnings"], [])
        for base in (self.OPENED, text):
            with self.subTest(base=base):
                self.assert_stale(base=base)
        self.assertEqual((self.home / self.PATH).read_text(encoding="utf-8"), first["text"])
        status, second = self.save(self.PATH, "second\n", base=first["text"])
        self.assertEqual(status, 200, second)
        self.assertEqual((self.home / self.PATH).read_bytes(), b"second\n")

    def test_stale_bom_typed_at_the_start_is_not_written(self):
        # Chunk N4 CR-1 (re-review): text starting with U+FEFF (e.g. pasted)
        # is saved without it (DECISIONS N4-05 BOM), so the answer is what
        # GET would read and the next save with it as base goes through.
        for typed in ("\ufeff# x\nnew\n", "\ufeff\ufeff# x\nnew\n"):
            with self.subTest(boms=typed.count("\ufeff")):
                status, first = self.save(self.PATH, typed)
                self.assertEqual(status, 200, first)
                self.assertEqual(first["text"], "# x\nnew\n")
                self.assertEqual((self.home / self.PATH).read_bytes(), b"# x\nnew\n")
                status, second = self.save(self.PATH, first["text"] + "more\n", base=first["text"])
                self.assertEqual(status, 200, second)
                self.assertEqual((self.home / self.PATH).read_bytes(), b"# x\nnew\nmore\n")

    def test_stale_base_too_big_is_refused(self):
        # Case 5: a base past the save size makes the request too big. The
        # server refuses on Content-Length without reading the body, so only
        # its start is sent (as test_bad_bodies_refused_before_any_write does).
        body = json.dumps({"path": self.PATH, "text": "mine\n", "fields": [],
                           "base": "x" * notebook.MAX_SAVE_BYTES}).encode("utf-8")
        self.assertGreater(len(body), notebook.MAX_SAVE_BYTES)
        before = self.file_state(), self.snapshot()
        status, answer = self.post(body[:10], length=str(len(body)))
        self.assertEqual(status, 400, answer)
        self.assertTrue(answer.startswith("send one save as JSON"), answer)
        self.assertEqual((self.file_state(), self.snapshot()), before)


class SaveEndpointTests(EditableFileTests):
    """NT4-07: one marker-box Save through POST /file (N4-07)."""

    # Run only these tests here, not EditableFileTests' again.
    def run(self, result=None):
        if not self._testMethodName.startswith("test_box_save_"):
            return result
        return super().run(result)

    def add_file(self, path, text):
        """Write one of alice's files as exact bytes; GET it and return the answer."""
        (self.home / path).write_bytes(text.encode("utf-8"))
        status, opened = self.get(path)
        self.assertEqual(status, 200, opened)
        return opened

    def box_save(self, path, opened, values, text=None):
        """Save opened's boxes with values ({marker: value}), as the page does.

        Every field goes back in the scan's order, notes with "".
        """
        sent = [dict(field, value=values.get(field["marker"], "")) for field in opened["fields"]]
        typed = opened["text"] if text is None else text
        return self.save(path, typed, sent, base=opened["text"])

    def test_box_save_real_template_writes_once(self):
        path = "findings/F-010-real.md"
        template = (support.TOOLS_DIR.parent / "templates" / "finding.md").read_text(encoding="utf-8")
        opened = self.add_file(path, template)
        title = "Weak `$pass` | in [[ -f x ]] test"
        values = {"[[FINDING_ID]]": "F-1", "[[FINDING_TITLE]]": title,
                  "[[CHOOSE: Confirmed / Exploited / Suspected]]": "Exploited",
                  "[[DATE]]": "2026-1-29", "[[TIME]]": "１４:05",
                  "[[REFERENCE_URL]]": "see [[REF]]"}
        expected = template
        for marker, value in values.items():
            expected = expected.replace(marker, value)
        # FINDING_ID is in the heading and the evidence line; both are filled.
        self.assertEqual(expected.count("F-1"), 2)
        before = self.snapshot()
        with mock.patch.object(notebook.os, "replace", wraps=os.replace) as replace, \
                mock.patch.object(notebook.tempfile, "mkstemp", wraps=tempfile.mkstemp) as mkstemp:
            status, answer = self.box_save(path, opened, values)
        self.assertEqual(status, 200, answer)
        self.assertEqual((self.home / path).read_bytes(), expected.encode("utf-8"))
        # One temp file, one rename onto this file: written once.
        self.assertEqual(mkstemp.call_count, 1)
        self.assertEqual(replace.call_count, 1)
        self.assertEqual(replace.call_args[0][1], str((self.home / path).resolve()))
        # Nothing else changed anywhere.
        after_home, after_outside, after_logdir = self.snapshot()
        before_home = dict(before[0], **{path: after_home[path]})
        self.assertEqual((after_home, after_outside, after_logdir), (before_home,) + before[1:])
        self.assertEqual(answer, {
            "path": path, "text": expected, "fields": notebook.marker_controls(expected),
            "status": notebook.marker_status(expected),
            "warnings": ["FINDING_ID: should look like F-001",
                         "DATE: should be a date as YYYY-MM-DD",
                         # Fullwidth digits aren't [0-9] (Chunk N4 D1).
                         "TIME: should be a time as HH:MM",
                         "REFERENCE_URL: should start with http",
                         "REFERENCE_URL: " + notebook.LEFTOVER_WARNING]})
        # The value "[[REF]]" is now a marker in the file, so it has a box.
        self.assertIn("[[REF]]", [field["marker"] for field in answer["fields"]])
        self.assertEqual(answer["status"], "38 markers left (13 of them notes)")

    def test_box_save_keeps_line_endings_and_spacing(self):
        path = "field-notes/alice/NOTE-crlf.md"
        opened = self.add_file(path, "# a\r\n  [[HOST]]  \r\n\tkeep\r\n\r\n[[PORT]]\n")
        status, answer = self.box_save(path, opened, {"[[HOST]]": "dc01"})
        self.assertEqual(status, 200, answer)
        self.assertEqual((self.home / path).read_bytes(), b"# a\r\n  dc01  \r\n\tkeep\r\n\r\n[[PORT]]\n")

    def test_box_save_uses_the_text_as_sent_not_as_opened(self):
        path = "field-notes/alice/NOTE-typed.md"
        opened = self.add_file(path, "[[HOST]]\n")
        typed = "typed first\n[[HOST]]\nand after\n"
        status, answer = self.box_save(path, opened, {"[[HOST]]": "dc01"}, text=typed)
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["text"], "typed first\ndc01\nand after\n")
        self.assertEqual((self.home / path).read_text(encoding="utf-8"), answer["text"])

    def test_box_save_rescan_keeps_one_box_per_name_and_order(self):
        path = "field-notes/alice/NOTE-rescan.md"
        opened = self.add_file(path, "[[A]] [[B]]\n[[CHOOSE: x / y]]\n[[B]] [[A]]\n"
                                     "[[CHOOSE: x / y]]\n[[TODO: one]]\n")
        # The second of the two identical dropdowns, by position.
        sent = [dict(field, value="") for field in opened["fields"]]
        sent[3]["value"] = "y"
        sent[0]["value"] = "a"
        status, answer = self.save(path, opened["text"], sent, base=opened["text"])
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["text"], "a [[B]]\n[[CHOOSE: x / y]]\n[[B]] a\ny\n[[TODO: one]]\n")
        self.assertEqual([field["marker"] for field in answer["fields"]],
                         ["[[B]]", "[[CHOOSE: x / y]]", "[[TODO: one]]"])
        self.assertEqual(answer["status"], "3 markers left (0 of them notes)")

    def test_box_save_empty_boxes_leave_markers(self):
        path = "field-notes/alice/NOTE-empty.md"
        text = "[[HOST]] [[CHOOSE: a / b]]\n[[TODO: x]]\n"
        opened = self.add_file(path, text)
        status, answer = self.box_save(path, opened, {})
        self.assertEqual((status, answer["text"], answer["warnings"]), (200, text, []))
        self.assertEqual((self.home / path).read_text(encoding="utf-8"), text)

    def test_box_save_notes_stay_and_still_count(self):
        path = "field-notes/alice/NOTE-notes.md"
        opened = self.add_file(path, "[[HOST]]\n[[NOTE: read me]]\n")
        # Even a value sent for the note is ignored: the app never removes a note.
        status, answer = self.box_save(path, opened, {"[[HOST]]": "dc01", "[[NOTE: read me]]": "gone"})
        self.assertEqual(status, 200, answer)
        self.assertEqual(answer["text"], "dc01\n[[NOTE: read me]]\n")
        self.assertEqual(answer["status"], "1 markers left (1 of them notes)")

    def test_box_save_last_marker_gives_complete(self):
        path = "field-notes/alice/NOTE-last.md"
        opened = self.add_file(path, "# x\n[[HOST]]\n")
        status, answer = self.box_save(path, opened, {"[[HOST]]": "dc01"})
        self.assertEqual((status, answer["fields"], answer["status"]), (200, [], "complete"))


class AppShellTests(ServerTestCase):
    def get_page(self):
        response, page = self.send_full("GET", "/", self.good_host())
        self.assertEqual(response.status, 200)
        parts = PageParts()
        parts.feed(page)
        return page, parts

    def test_nav_has_the_file_list_new_checklists_and_export(self):
        page, parts = self.get_page()
        self.assertEqual(parts.inside["nav"], [("button", "theme-toggle"),
                                               ("div", "file-list"),
                                               ("button", "new-button"),
                                               ("button", "checklists-button"),
                                               ("button", "export-button")])
        self.assertEqual(parts.inside["main"], [])
        # No Logs/Compile controls yet: the only words on the page are the
        # four buttons'. Export comes after Checklists, where Logs will go
        # between them (Look and layout).
        self.assertEqual(parts.visible_text, ["Light / dark", "New", "Checklists", "Export"])
        # The file list loads when the page opens.
        self.assertIn("\nloadFiles();\n</script>", page)

    def test_page_carries_this_runs_token_once(self):
        page, parts = self.get_page()
        self.assertEqual(parts.tokens, [self.server.token])
        self.assertNotIn(notebook.TOKEN_SLOT, page)

    def test_token_is_escaped_in_the_page(self):
        # A real token never has these characters; this proves escape() runs.
        self.server.token = 'x"><script>alert(1)</script>'
        page, parts = self.get_page()
        self.assertEqual(parts.tokens, [self.server.token])
        self.assertNotIn('x"><script>', page)

    def test_script_posts_the_token_and_locks_boxes(self):
        # The display-safety asserts are in PageSafetyTests (NT4-06).
        page, _ = self.get_page()
        # All four POSTs (a tick, a new file, a save of a file, an export)
        # send the token.
        self.assertEqual(page.count('"X-CPTC-Token": TOKEN'), 4)
        self.assertEqual(page.count("fetch("), 8)
        self.assertIn('fetch("/new-file", {\n      method: "POST",', page)
        self.assertIn('box.type = "checkbox";', page)
        # A box is locked while its save is pending and, if the save fails,
        # goes back to its value from before the click (not just flipped).
        self.assertIn("box.disabled = true;", page)
        self.assertIn("box.checked = !wanted;", page)

    def test_new_form_sends_only_type_title_number_and_library(self):
        page, _ = self.get_page()
        # The request is built from these four fields and nothing else: no
        # file name or path field, and a number or library entry only when
        # the type uses one.
        self.assertIn("var request = {\n"
                      "      type: kind.name,\n"
                      "      title: title.value,\n"
                      "      nnn: kind.needs_nnn ? nnn.value : null,\n"
                      "      library: kind.library && library.value ? library.value : null\n"
                      "    };", page)
        self.assertIn("body: JSON.stringify(request)", page)
        # A one-line title box.
        self.assertIn('title.type = "text";', page)
        # Hidden fields follow the type the server describes.
        self.assertIn("nnnRow.hidden = !kind.needs_nnn;", page)
        self.assertIn("libraryRow.hidden = !kind.library;", page)

    def test_refused_reasons_and_the_new_file_are_shown(self):
        page, _ = self.get_page()
        for line in ["data.refused.forEach(function (reason) {",
                     "data.library_refused.forEach(function (reason) {",
                     "data.ir_refused.forEach(function (reason) {",
                     "result.warnings.forEach(function (warning) {",
                     "result.refused.forEach(function (reason) {",
                     "loadFiles(result.path);"]:
            with self.subTest(line=line):
                self.assertIn(line, page)
        # After a create the IR suggestion is fetched again, so two incident
        # reports in a row don't both get the same number (Chunk N3 CR-1).
        self.assertIn("loadFiles(result.path);\n        refreshSuggestion();", page)
        self.assertIn('function refreshSuggestion() {\n    fetch("/new-data")', page)

    def test_follows_system_dark_mode_and_has_a_toggle(self):
        page, _ = self.get_page()
        self.assertIn("@media (prefers-color-scheme: dark)", page)
        self.assertIn(':root[data-theme="dark"]', page)
        self.assertIn(':root[data-theme="light"]', page)
        self.assertIn('getElementById("theme-toggle").addEventListener("click"', page)


class PageSafetyTests(ServerTestCase):
    """NT4-06: the one automated page-source display-safety test (Constraint 9)."""

    # The display-safety source asserts. Only the test below may make them.
    SAFETY_STRINGS = {"innerHTML", "outerHTML", "insertAdjacentHTML", "document.write",
                      "textContent", ".value", "made.textContent = text;",
                      "fileText.value = data.text;", "fileText.value = result.text;",
                      "kept.value = text;"}

    def test_page_source_is_display_safe(self):
        response, page = self.send_full("GET", "/", self.good_host())
        self.assertEqual(response.status, 200)
        # No way for text to become HTML: no innerHTML or its relatives.
        self.assertNotIn("innerHTML", page)
        self.assertNotIn("outerHTML", page)
        self.assertNotIn("insertAdjacentHTML", page)
        self.assertNotIn("document.write", page)
        self.assertIn("textContent", page)
        self.assertIn(".value", page)
        # Every element's text goes through element(), which uses textContent,
        # and a file's text goes into its textarea through .value only.
        self.assertIn("made.textContent = text;", page)
        self.assertIn("fileText.value = data.text;", page)
        # Its only other use is as the next Save's base, never as page content.
        self.assertIn("var base = data.text;", page)
        self.assertEqual(page.count("data.text"), 2)
        # After a Save, the saved text; after a Reload, the kept text.
        self.assertIn("fileText.value = result.text;", page)
        self.assertIn("kept.value = text;", page)
        self.assert_no_other_test_makes_these_asserts()

    def assert_no_other_test_makes_these_asserts(self):
        """NT4-06: no other test in this file asserts on SAFETY_STRINGS."""
        tree = ast.parse((support.TOOLS_DIR / "tests" / "test_notebook.py").read_text(encoding="utf-8"))
        others = []
        for function in ast.walk(tree):
            if not isinstance(function, ast.FunctionDef) or function.name == "test_page_source_is_display_safe":
                continue
            for call in ast.walk(function):
                if (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)
                        and call.func.attr in ("assertIn", "assertNotIn") and call.args
                        and isinstance(call.args[0], ast.Constant)
                        and call.args[0].value in self.SAFETY_STRINGS):
                    others.append(function.name)
        self.assertEqual(others, [])


class FillInPageTests(ServerTestCase):
    """N4-06: the page's fill-in view. The controls come from marker_controls()
    (MarkerControlTests); these check the page builds the matching element."""

    def get_page(self):
        response, page = self.send_full("GET", "/", self.good_host())
        self.assertEqual(response.status, 200)
        return page

    def test_each_listed_file_opens_in_the_fill_in_view(self):
        page = self.get_page()
        self.assertIn('getJson("/file?path=" + encodeURIComponent(path), showFillIn);', page)

    def test_each_control_kind_gets_its_element(self):
        page = self.get_page()
        # A dropdown starts on an empty choice, then the options as sent.
        self.assertIn('if (field.control === "dropdown") {\n    var list = element("select");', page)
        self.assertIn('var none = list.appendChild(element("option", "(not chosen)"));\n'
                      '    none.value = "";', page)
        self.assertIn("field.options.forEach(function (text) {", page)
        self.assertIn('if (field.control === "textarea") {\n    var big = element("textarea");', page)
        # Anything else is a one-line input.
        self.assertIn('var line = element("input");\n  line.type = "text";\n  return line;', page)

    def test_boxes_follow_the_field_order_and_show_guidance(self):
        page = self.get_page()
        self.assertIn("answer.fields.forEach(function (field) {", page)
        self.assertIn("var box = markerBox(field);\n"
                      "      entries.push({field: field, box: box});\n"
                      "      var row = addField(boxes, field.name, box);", page)
        self.assertIn("if (field.guidance !== undefined) {\n"
                      "        row.appendChild(element(\"p\", field.guidance));", page)

    def test_a_note_is_highlighted_help_and_never_a_box(self):
        page = self.get_page()
        # The note's branch returns before any box is made.
        self.assertIn('if (field.control === "note") {', page)
        self.assertIn('boxes.appendChild(element("pre")).appendChild(element("mark", "NOTE:" + field.body));\n'
                      "        entries.push({field: field, box: null});\n"
                      "        return;", page)

    def test_view_shows_the_path_and_status(self):
        page = self.get_page()
        self.assertIn('main.appendChild(element("h2", data.path));\n'
                      '  var statusLine = main.appendChild(element("p"));', page)
        self.assertIn("statusLine.textContent = answer.status;", page)

    def test_every_save_is_one_post_with_the_text_base_and_token(self):
        # N4-07/N4-08: Save and autosave both go through post(): the
        # textarea's text as it is now, the base, and the fields.
        page = self.get_page()
        self.assertEqual(page.count('fetch("/file", {'), 1)
        self.assertIn("    var sent = fileText.value;\n"
                      "    warningsShown = false;\n"
                      "    busy = true;\n"
                      "    save.disabled = true;", page)
        self.assertIn('fetch("/file", {\n'
                      '      method: "POST",\n'
                      '      headers: {"Content-Type": "application/json", "X-CPTC-Token": TOKEN},\n'
                      "      body: JSON.stringify({path: data.path, text: sent, base: base, fields: fields})",
                      page)
        # The saved text is the next base.
        self.assertIn("        done();\n"
                      "        /* The saved text is the next base. */\n"
                      "        base = result.text;", page)

    def test_save_sends_every_field_and_shows_its_warnings(self):
        page = self.get_page()
        self.assertIn("var fields = entries.map(function (entry) {\n"
                      "      return {name: entry.field.name, marker: entry.field.marker,"
                      " body: entry.field.body,\n"
                      '              value: entry.box ? entry.box.value : ""};', page)
        # A Save sends the text too, so its pending autosave is dropped.
        self.assertIn('  save.addEventListener("click", function () {\n'
                      "    /* This save sends the textarea's text too, so no autosave is needed. */\n"
                      "    clearTimeout(timer);", page)
        self.assertIn("    fileText.readOnly = true;\n    lockBoxes(true);\n    post(fields, function (result) {", page)
        # A refused Save unlocks them; a saved one rebuilds them unlocked.
        self.assertIn("      fileText.readOnly = false;\n      lockBoxes(false);", page)
        self.assertIn("        entry.box.disabled = locked;", page)
        self.assertIn("      showBoxes(result);\n"
                      '      messages.textContent = "";\n'
                      "      failureShown = false;\n"
                      '      messages.appendChild(element("p", "Saved."));', page)
        self.assertIn("      result.warnings.forEach(function (warning) {\n"
                      '        messages.appendChild(element("pre", "Warning: " + warning));', page)

    def test_a_refused_save_keeps_the_boxes_and_base(self):
        # Not rebuilt: the boxes keep their values, base stays, Save unlocks.
        page = self.get_page()
        self.assertIn("    function notSaved(status, text) {\n"
                      "      /* The boxes keep their values and base stays, so the user can retry. */\n"
                      "      done();\n"
                      "      failed();\n"
                      '      messages.textContent = "";\n'
                      '      messages.appendChild(element("p", "Not saved: " + text));', page)

    def test_autosave_two_seconds_after_typing_stops(self):
        # N4-08: each keystroke restarts the timer; it sends the text alone.
        page = self.get_page()
        self.assertIn("var AUTOSAVE_DELAY = 2000;", page)
        self.assertIn('  fileText.addEventListener("input", function () {\n'
                      '    savedLine.textContent = "not saved yet";\n'
                      "    textSaved = false;\n"
                      "    if (stopped) {\n"
                      "      return;\n"
                      "    }\n"
                      "    clearTimeout(timer);\n"
                      "    timer = setTimeout(autosave, AUTOSAVE_DELAY);", page)
        self.assertIn("    post([], function (result) {", page)
        # One save at a time: an autosave due during one waits for it.
        self.assertIn("    if (busy) {\n      timer = setTimeout(autosave, AUTOSAVE_DELAY);\n      return;", page)

    def test_saved_time_shows_only_after_a_save_of_the_text_shown(self):
        page = self.get_page()
        self.assertIn("        if (fileText.value === sent) {\n"
                      '          savedLine.textContent = "saved at " + new Date().toTimeString().slice(0, 8);',
                      page)

    def test_autosave_leaves_boxes_holding_values_alone(self):
        page = self.get_page()
        self.assertIn("      if (!boxesHoldValues()) {\n        showBoxes(result);", page)
        self.assertIn('return entry.box !== null && entry.box.value !== "";', page)

    def test_changed_on_disk_stops_autosave_and_offers_reload(self):
        # N5 F1 (C): a 409 from autosave or Save stops autosave; Reload
        # shows the file from disk and keeps the textarea's text.
        page = self.get_page()
        self.assertIn("      if (status === 409) {\n        offerReload();", page)
        self.assertIn("  function offerReload() {\n"
                      "    stopped = true;\n"
                      "    clearTimeout(timer);", page)
        self.assertIn("      var mine = unsavedText();\n"
                      '      fetch("/file?path=" + encodeURIComponent(data.path)).then(function (response) {',
                      page)
        # A Reload answering after the view was left draws nothing.
        self.assertIn("            if (openView === view) {\n              showFillIn(fresh, mine);", page)
        # A failed reload keeps the view, and so the text.
        self.assertIn('messages.appendChild(element("p", "Not reloaded: " + text));', page)

    def test_leaving_a_file_saves_its_text_first(self):
        # Adversary C7: a file's own view saves its text before the page
        # moves on, so a refusal shows where the text is, never in a view
        # that is already gone.
        page = self.get_page()
        self.assertIn("goTo(function () {\n"
                      '        getJson("/file?path=" + encodeURIComponent(path), showFillIn);', page)
        self.assertIn("goTo(function () {\n    getJson(\"/new-data\", showNewForm);", page)
        self.assertIn("goTo(function () {\n    getJson(\"/checklists\", showChecklistList);", page)
        self.assertIn("  openView.leave(function () {\n    openView = null;\n    next();", page)
        self.assertIn("  var view = {leave: leave, holdsUnsaved: holdsUnsaved};\n  openView = view;\n", page)
        # Saved text leaves at once; a save on its way is waited for; a
        # refused or stopped one keeps the page here with a way out.
        self.assertIn("    if (textSaved) {\n      quit(next);\n      return;\n    }\n"
                      "    if (stopped || failureShown) {\n      offerLeave(next);", page)
        self.assertIn('var away = leaveRow.appendChild(element("button", "Leave without saving"));', page)
        # Chunk N5 CR-1: a view the user left sends nothing more.
        self.assertIn('    away.addEventListener("click", function () {\n      quit(next);', page)
        self.assertIn("  function quit(next) {\n"
                      "    stopped = true;\n"
                      "    clearTimeout(timer);\n"
                      "    timer = null;\n"
                      "    next();", page)
        self.assertEqual(page.count("quit(next);"), 2)
        # Only a save of exactly the text shown counts as saved.
        self.assertIn("    textSaved = false;", page)
        self.assertIn('          savedLine.textContent = "saved at " + new Date().toTimeString().slice(0, 8);\n'
                      "          textSaved = true;", page)

    def test_box_values_show_unsaved_until_saved(self):
        # N4-09: the indicator follows the boxes: on while any holds a
        # value, off once a Save rebuilds them empty (showBoxes()).
        page = self.get_page()
        self.assertIn('unsavedMark.textContent = boxesHoldValues() ? " unsaved" : "";', page)
        self.assertIn('  boxes.addEventListener("input", showUnsavedMark);\n'
                      '  boxes.addEventListener("change", showUnsavedMark);', page)
        self.assertIn("    saveRow.appendChild(unsavedMark);\n    showUnsavedMark();", page)

    def test_leaving_with_box_values_asks_once(self):
        # N4-09: one warning while boxes hold values; staying changes
        # nothing; leaving never puts the values in the file.
        page = self.get_page()
        # Chunk N5 CR-2: a save on its way is waited for; a Save's
        # warnings keep the page here.
        self.assertIn("  function leave(next) {\n"
                      "    if (busy) {\n"
                      "      afterSave = function () {\n"
                      "        if (!warningsShown) {\n"
                      "          leave(next);\n"
                      "        }\n"
                      "      };\n"
                      "      return;\n"
                      "    }\n"
                      "    if (boxesHoldValues() && !window.confirm(\"Your box values aren't saved"
                      " and will be lost. Leave anyway?\")) {\n"
                      "      return;\n"
                      "    }\n"
                      "    leaveText(next);", page)
        self.assertEqual(page.count("window.confirm("), 1)
        self.assertIn("    var sent = fileText.value;\n    warningsShown = false;", page)
        self.assertIn("      warningsShown = result.warnings.length > 0;", page)

    def test_closing_the_page_warns_for_unsaved_values_or_text(self):
        page = self.get_page()
        # N5 L6: also while the text can't be saved after a refusal.
        self.assertIn("    return boxesHoldValues() || (!textSaved && (stopped || failureShown));", page)
        self.assertIn('window.addEventListener("beforeunload", function (event) {\n'
                      "  if (openView !== null && openView.holdsUnsaved()) {\n"
                      "    event.preventDefault();\n"
                      '    event.returnValue = "";', page)

    def test_unsaved_text_also_keeps_box_values(self):
        # N5 F1d: Reload rebuilds the boxes, so their values go under the text.
        page = self.get_page()
        self.assertIn("      if (entry.box !== null && entry.box.value !== \"\") {", page)
        self.assertIn('        text += entry.field.name + ": " + entry.box.value + "\\n";', page)

    def test_unsaved_text_is_kept_read_only_with_a_copy_button(self):
        page = self.get_page()
        self.assertIn("    kept.readOnly = true;\n", page)
        self.assertIn('var row = addField(main, "Your unsaved text", kept);', page)
        self.assertIn('var copy = row.appendChild(element("button", "Copy"));', page)
        self.assertIn("navigator.clipboard.writeText(text).then(function () {", page)
        self.assertIn('" Not copied (" + error + "): select the text and copy it by hand."', page)


# One file in each export folder plus everything that must stay out of the zip.
EXPORT_FILES = {
    "findings/F-001-a.md": "finding\n",
    "evidence/scan.txt": "scan output\n",
    "evidence/web01/shot.txt": "nested evidence\n",
    "field-notes/alice/NOTE-x.md": "alice's note\n",
    "tracker/findings-index.csv": "finding_id\nF-001\n",
    "field-notes/bob/NOTE-b.md": "bob's note\n",
    "incoming/bob/findings/F-009-x.md": "bob's finding\n",
    "notebooks/n.md": "not exported\n",
    "notes/study.md": "study\n",
    "report.md": "report\n",
    "cptc-export-alice-20261107T101500.zip": "an earlier export\n",
}

# The members of EXPORT_FILES, in manifest order: folder by folder, then by name.
EXPORT_MEMBERS = ["findings/F-001-a.md", "evidence/scan.txt", "evidence/web01/shot.txt",
                  "field-notes/alice/NOTE-x.md", "tracker/findings-index.csv"]


class ExportManifestTests(unittest.TestCase):
    """N5-01: which files the zip export takes (Export (a); OQ-12; Chunk N6 E1, E2)."""

    def setUp(self):
        self.home = support.make_worktree(self, EXPORT_FILES)
        self.logs = support.make_worktree(self, {"session-1.log": "log one\n",
                                                 "old/session-0.log": "log zero\n",
                                                 "session-1.cmds.log": ""})
        # A third folder stands in for "somewhere outside", still inside .tmp/.
        self.outside = support.make_worktree(self, {"secret.txt": "outside\n"})

    def manifest(self, include_logs=False):
        return notebook.export_manifest(self.home, self.logs, "alice", include_logs)

    def names(self, include_logs=False):
        return [member for member, path in self.manifest(include_logs)[0]]

    def skipped(self, include_logs=False):
        return self.manifest(include_logs)[1]

    def test_export_folders_are_the_four_mirror_folders(self):
        self.assertEqual(notebook.export_folders("alice"),
                         ["findings", "evidence", "field-notes/alice", "tracker"])

    def test_only_the_four_folders_are_taken(self):
        self.assertEqual(self.names(), EXPORT_MEMBERS)
        self.assertEqual(self.skipped(), [])
        roots = {member.split("/")[0] for member in self.names()}
        self.assertEqual(roots, {"findings", "evidence", "field-notes", "tracker"})

    def test_each_member_is_its_own_file(self):
        members, skipped = self.manifest()
        for member, path in members:
            self.assertEqual(path, self.home / member)
            self.assertEqual(path.read_text(encoding="utf-8"), EXPORT_FILES[member])

    def test_logs_are_left_out_by_default(self):
        members, skipped = notebook.export_manifest(self.home, self.logs, "alice")
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS)

    def test_logs_go_under_logs_when_asked_for(self):
        members, skipped = self.manifest(include_logs=True)
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS + [
            "logs/old/session-0.log", "logs/session-1.cmds.log", "logs/session-1.log"])
        self.assertEqual(skipped, [])
        # An empty log is still a file, so it is still taken.
        self.assertEqual(members[-2][1], self.logs / "session-1.cmds.log")
        for member, path in members:
            # Named by the log folder's contents, never its path on this box.
            self.assertNotIn(str(self.logs), member)

    def test_logs_have_no_size_limit(self):
        big = self.logs / "big.log"
        with big.open("wb") as handle:
            handle.truncate(64 * 1024 * 1024)
        self.assertIn("logs/big.log", self.names(include_logs=True))

    def test_nothing_to_export_is_an_empty_manifest(self):
        home = support.make_worktree(self)
        missing_logs = home / "no-logs-here"
        self.assertEqual(notebook.export_manifest(home, missing_logs, "alice", True), ([], []))

    def test_member_names_are_plain_relative_paths(self):
        names = self.names(include_logs=True)
        self.assertEqual(len(names), len(set(names)))
        for member in names:
            self.assertFalse(member.startswith("/"), member)
            self.assertNotIn("\\", member)
            self.assertNotIn("..", member.split("/"))

    def test_order_never_depends_on_the_disk(self):
        expected = self.manifest(include_logs=True)
        real_listdir = os.listdir
        # On this Mac the disk happens to list names sorted, so reverse it.
        with mock.patch("os.listdir", lambda path: sorted(real_listdir(path), reverse=True)):
            self.assertEqual(self.manifest(include_logs=True), expected)

    def assert_link_skipped(self, link, report, include_logs=False):
        """Check the link is reported, its target is not taken, and the rest still is."""
        members, skipped = self.manifest(include_logs)
        self.assertEqual(skipped, ["not exported: symlink: " + report])
        for member, path in members:
            self.assertNotEqual(path, link)
            self.assertFalse(member.startswith(report + "/"), member)
            self.assertNotIn("secret", member)
        return [member for member, path in members]

    def test_nested_file_link_inside_the_root_is_skipped(self):
        link = self.home / "evidence" / "copy.md"
        link.symlink_to(self.home / "findings" / "F-001-a.md")
        self.assertEqual(self.assert_link_skipped(link, "evidence/copy.md"), EXPORT_MEMBERS)

    def test_nested_file_link_outside_the_root_is_skipped(self):
        link = self.home / "findings" / "secret.txt"
        link.symlink_to(self.outside / "secret.txt")
        self.assertEqual(self.assert_link_skipped(link, "findings/secret.txt"), EXPORT_MEMBERS)

    def test_nested_folder_link_is_skipped(self):
        link = self.home / "evidence" / "web02"
        link.symlink_to(self.home / "evidence" / "web01")
        self.assertEqual(self.assert_link_skipped(link, "evidence/web02"), EXPORT_MEMBERS)

    def test_nested_folder_link_outside_the_root_is_skipped(self):
        link = self.home / "field-notes" / "alice" / "loot"
        link.symlink_to(self.outside)
        self.assertEqual(self.assert_link_skipped(link, "field-notes/alice/loot"), EXPORT_MEMBERS)

    def test_linked_log_is_skipped(self):
        link = self.logs / "secret.log"
        link.symlink_to(self.outside / "secret.txt")
        names = self.assert_link_skipped(link, "logs/secret.log", include_logs=True)
        self.assertIn("logs/session-1.log", names)

    def move_and_link(self, folder, target):
        """Replace folder (root-relative) with a link to target."""
        shutil.rmtree(str(self.home / folder))
        (self.home / folder).symlink_to(target)
        return self.home / folder

    def without(self, prefix):
        return [member for member in EXPORT_MEMBERS if not member.startswith(prefix + "/")]

    def test_linked_findings_folder_is_skipped(self):
        link = self.move_and_link("findings", self.home / "incoming" / "bob" / "findings")
        self.assertEqual(self.assert_link_skipped(link, "findings"), self.without("findings"))

    def test_linked_evidence_folder_outside_the_root_is_skipped(self):
        link = self.move_and_link("evidence", self.outside)
        self.assertEqual(self.assert_link_skipped(link, "evidence"), self.without("evidence"))

    def test_linked_tracker_folder_is_skipped(self):
        link = self.move_and_link("tracker", self.home / "notes")
        self.assertEqual(self.assert_link_skipped(link, "tracker"), self.without("tracker"))

    def test_linked_own_field_notes_folder_is_skipped(self):
        link = self.move_and_link("field-notes/alice", self.home / "field-notes" / "bob")
        self.assertEqual(self.assert_link_skipped(link, "field-notes/alice"),
                         self.without("field-notes/alice"))

    def test_linked_field_notes_folder_is_skipped(self):
        # field-notes/alice exists in the target, so following the link would find it.
        shared = support.make_worktree(self, {"alice/NOTE-other.md": "not alice's\n"})
        link = self.move_and_link("field-notes", shared)
        self.assertEqual(self.assert_link_skipped(link, "field-notes"),
                         self.without("field-notes/alice"))

    def test_linked_log_folder_is_skipped(self):
        link = self.home / "loglink"
        link.symlink_to(self.logs)
        members, skipped = notebook.export_manifest(self.home, link, "alice", True)
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS)
        self.assertEqual(skipped, ["not exported: symlink: logs"])

    def test_broken_link_is_skipped(self):
        link = self.home / "evidence" / "gone.txt"
        link.symlink_to(self.home / "evidence" / "missing.txt")
        self.assertEqual(self.assert_link_skipped(link, "evidence/gone.txt"), EXPORT_MEMBERS)

    def test_link_loop_is_skipped(self):
        link = self.home / "evidence" / "loop"
        link.symlink_to(link)
        self.assertEqual(self.assert_link_skipped(link, "evidence/loop"), EXPORT_MEMBERS)

    def test_folder_link_back_up_is_skipped(self):
        link = self.home / "evidence" / "web01" / "up"
        link.symlink_to(self.home / "evidence")
        self.assertEqual(self.assert_link_skipped(link, "evidence/web01/up"), EXPORT_MEMBERS)

    def test_fifo_is_skipped_without_opening_it(self):
        fifo = self.home / "evidence" / "pipe"
        os.mkfifo(str(fifo))
        # Opening a FIFO for reading would hang here, so finishing at all shows
        # it was never opened.
        members, skipped = self.manifest()
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS)
        self.assertEqual(skipped, ["not exported: not a regular file: evidence/pipe"])

    @unittest.skipIf(os.geteuid() == 0, "root can read a folder with no permissions")
    def test_unreadable_folder_is_skipped_and_the_rest_taken(self):
        locked = self.home / "evidence" / "web01"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o700)
        members, skipped = self.manifest()
        self.assertEqual([member for member, path in members],
                         [member for member in EXPORT_MEMBERS if "web01" not in member])
        self.assertEqual(len(skipped), 1)
        self.assertTrue(skipped[0].startswith("not exported: can't read: evidence/web01 ("),
                        skipped)

    def test_a_file_where_a_folder_should_be_is_skipped(self):
        # In the zip it would be a file named "tracker", not the mirror layout.
        home = support.make_worktree(self, {"tracker": "not a folder\n",
                                            "findings/F-001-a.md": "finding\n"})
        log_file = home / "findings" / "F-001-a.md"
        members, skipped = notebook.export_manifest(home, log_file, "alice", True)
        self.assertEqual([member for member, path in members], ["findings/F-001-a.md"])
        self.assertEqual(skipped, ["not exported: not a folder: tracker",
                                   "not exported: not a folder: logs"])

    def test_a_file_where_field_notes_should_be_is_skipped(self):
        home = support.make_worktree(self, {"field-notes": "not a folder\n"})
        self.assertEqual(notebook.export_manifest(home, self.logs, "alice"),
                         ([], ["not exported: not a folder: field-notes"]))

    def test_a_fifo_where_field_notes_should_be_is_skipped(self):
        home = support.make_worktree(self)
        os.mkfifo(str(home / "field-notes"))
        self.assertEqual(notebook.export_manifest(home, self.logs, "alice"),
                         ([], ["not exported: not a folder: field-notes"]))

    @unittest.skipIf(os.geteuid() == 0, "root can read a folder with no permissions")
    def test_unreadable_field_notes_folder_is_skipped_and_the_rest_taken(self):
        locked = self.home / "field-notes"
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o700)
        members, skipped = self.manifest()
        self.assertEqual([member for member, path in members], self.without("field-notes/alice"))
        self.assertEqual(len(skipped), 1)
        self.assertTrue(skipped[0].startswith("not exported: can't read: field-notes/alice ("),
                        skipped)

    @unittest.skipIf(os.geteuid() == 0, "root can read a folder with no permissions")
    def test_listable_but_not_searchable_folder_is_skipped_and_the_rest_taken(self):
        # Read but no search permission: its names list, but none can be looked at.
        locked = self.home / "evidence" / "web01"
        locked.chmod(0o400)
        self.addCleanup(locked.chmod, 0o700)
        members, skipped = self.manifest()
        self.assertEqual([member for member, path in members],
                         [member for member in EXPORT_MEMBERS if "web01" not in member])
        self.assertEqual(len(skipped), 1)
        self.assertTrue(skipped[0].startswith("not exported: can't read: evidence/web01/shot.txt ("),
                        skipped)

    def logs_inside(self, folder):
        """Return a log folder made inside the working copy at folder (root-relative)."""
        support.write_fake_file(self.home, folder + "/session-9.log", "secret log\n")
        return self.home / folder

    def test_log_folder_inside_evidence_is_left_out_by_default(self):
        logs = self.logs_inside("evidence/logs")
        members, skipped = notebook.export_manifest(self.home, logs, "alice")
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS)
        self.assertEqual(skipped, ["not exported: the log folder: evidence/logs"])

    def test_log_folder_inside_evidence_goes_only_under_logs(self):
        logs = self.logs_inside("evidence/logs")
        members, skipped = notebook.export_manifest(self.home, logs, "alice", True)
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS + ["logs/session-9.log"])
        self.assertEqual(skipped, ["not exported: the log folder: evidence/logs"])

    def test_log_folder_as_an_export_folder_is_left_out(self):
        # LOGDIR set to the working copy's evidence/ itself.
        logs = self.home / "evidence"
        members, skipped = notebook.export_manifest(self.home, logs, "alice")
        self.assertEqual([member for member, path in members], self.without("evidence"))
        self.assertEqual(skipped, ["not exported: the log folder: evidence"])

    def test_log_folder_reached_through_a_link_is_still_left_out(self):
        # LOGDIR names a link outside the working copy that points into evidence/.
        self.logs_inside("evidence/logs")
        link = self.outside / "loglink"
        link.symlink_to(self.home / "evidence" / "logs")
        members, skipped = notebook.export_manifest(self.home, link, "alice", True)
        self.assertEqual([member for member, path in members], EXPORT_MEMBERS)
        self.assertEqual(skipped, ["not exported: the log folder: evidence/logs",
                                   "not exported: symlink: logs"])


# The export's file name for alice (Export (a)).
EXPORT_NAME_RE = re.compile(r"cptc-export-alice-[0-9]{8}T[0-9]{6}\.zip")

# A fixed clock for write_export(), so the file name is known.
EXPORT_TIME = datetime.datetime(2026, 11, 7, 10, 30, 0)

# The folder entries every export zip starts with (alice, logs not included).
EXPORT_FOLDER_ENTRIES = ["findings/", "evidence/", "field-notes/alice/", "tracker/"]


class ExportZipTests(unittest.TestCase):
    """N5-02: the export zip in the root, unzipped as incoming/<name>/ (Export (a))."""

    def setUp(self):
        self.home = support.make_worktree(self, EXPORT_FILES)
        # Bytes a text round trip would change: binary, empty, BOM + CRLF.
        (self.home / "evidence" / "shot.png").write_bytes(bytes(range(256)))
        (self.home / "evidence" / "empty.txt").write_bytes(b"")
        (self.home / "tracker" / "timeline.csv").write_bytes(b"\xef\xbb\xbftime,event\r\n10:15,x\r\n")
        self.logs = support.make_worktree(self, {"session-1.log": "log one\n",
                                                 "old/session-0.log": "log zero\n"})
        self.outside = support.make_worktree(self, {"secret.txt": "outside\n"})

    def export(self, include_logs=False, now=EXPORT_TIME, home=None):
        return notebook.write_export(home or self.home, self.logs, "alice", include_logs, now)

    def unzip(self, path):
        """Unzip path into a fresh test folder; return its files as {path: bytes}."""
        target = support.make_worktree(self)
        with zipfile.ZipFile(str(path)) as archive:
            self.assertIsNone(archive.testzip())
            archive.extractall(str(target))
        return file_bytes(target)

    def mirror(self, root, folders):
        """Return root's files under folders and field-notes/alice/ as {path: bytes}.

        Like file_bytes(), but links are left out, as the export leaves them out.
        """
        return {path: data for path, data in file_bytes(root).items()
                if (path.split("/")[0] in folders or path.startswith("field-notes/alice/"))
                and not (root / path).is_symlink()}

    def test_file_name_and_place(self):
        path, skipped = self.export()
        self.assertEqual(path, self.home / "cptc-export-alice-20261107T103000.zip")
        self.assertTrue(EXPORT_NAME_RE.fullmatch(path.name), path.name)
        self.assertEqual(path.parent, self.home)
        self.assertTrue(path.is_file())

    def test_real_clock_name_matches(self):
        path, skipped = notebook.write_export(self.home, self.logs, "alice")
        self.assertTrue(EXPORT_NAME_RE.fullmatch(path.name), path.name)

    def test_a_slugged_name_is_used_as_it_is(self):
        path, skipped = notebook.write_export(self.home, self.logs, "alice-smith", False, EXPORT_TIME)
        self.assertEqual(path.name, "cptc-export-alice-smith-20261107T103000.zip")

    def test_namelist_is_the_manifest(self):
        path, skipped = self.export()
        members, expected_skipped = notebook.export_manifest(self.home, self.logs, "alice")
        with zipfile.ZipFile(str(path)) as archive:
            names = archive.namelist()
        self.assertEqual(names, EXPORT_FOLDER_ENTRIES + [member for member, source in members])
        self.assertEqual(skipped, [])
        for name in names:
            self.assertTrue(name.startswith(("findings/", "evidence/", "field-notes/alice/",
                                             "tracker/")), name)

    def test_unzipped_tree_is_the_mirror_byte_for_byte(self):
        path, skipped = self.export()
        self.assertEqual(self.unzip(path),
                         self.mirror(self.home, ("findings", "evidence", "tracker")))

    def test_logs_unzip_under_logs_byte_for_byte(self):
        path, skipped = self.export(include_logs=True)
        files = self.unzip(path)
        expected = self.mirror(self.home, ("findings", "evidence", "tracker"))
        expected.update({"logs/" + name: data for name, data in file_bytes(self.logs).items()})
        self.assertEqual(files, expected)

    def test_logs_left_out_by_default(self):
        path, skipped = self.export()
        self.assertFalse([name for name in self.unzip(path) if name.startswith("logs/")])

    def test_members_are_compressed(self):
        # Logs are text and can be large, so the zip moves faster compressed.
        path, skipped = self.export(include_logs=True)
        with zipfile.ZipFile(str(path)) as archive:
            for info in archive.infolist():
                if not info.is_dir():
                    self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED, info.filename)

    def test_file_times_are_kept(self):
        source = self.home / "findings" / "F-001-a.md"
        os.utime(str(source), (1793000000, 1793000000))
        path, skipped = self.export()
        with zipfile.ZipFile(str(path)) as archive:
            stored = archive.getinfo("findings/F-001-a.md").date_time
        self.assertEqual(stored, datetime.datetime.fromtimestamp(1793000000).timetuple()[:6])

    def test_a_file_time_after_2107_becomes_the_last_zip_time(self):
        # Year 2128: e.g. evidence copied with its times from a box with a bad clock.
        os.utime(str(self.home / "findings" / "F-001-a.md"), (5e9, 5e9))
        path, skipped = self.export()
        with zipfile.ZipFile(str(path)) as archive:
            self.assertEqual(archive.getinfo("findings/F-001-a.md").date_time, (2107, 12, 31, 23, 59, 58))
        self.assertEqual(skipped, [])

    def test_times_this_computer_cant_convert_become_the_first_or_last(self):
        # Far past year 9999: fromtimestamp() itself raises an error.
        self.assertEqual(notebook.zip_time(1e15), notebook.ZIP_LATEST)
        self.assertEqual(notebook.zip_time(-1e15), notebook.ZIP_EARLIEST)
        self.assertEqual(notebook.zip_time(5e9), (2107, 12, 31, 23, 59, 58))
        self.assertEqual(notebook.zip_time(0), (1980, 1, 1, 0, 0, 0))

    def test_a_log_growing_past_the_zip64_limit_is_copied_whole(self):
        # A limit of 300 bytes stands in for 2 GB: the log is bigger than
        # that once copied, as a log still being written can be.
        log = self.logs / "session-1.log"
        log.write_bytes(b"x" * 400)
        with mock.patch.object(zipfile, "ZIP64_LIMIT", 300):
            path, skipped = self.export(include_logs=True)
        self.assertEqual(skipped, [])
        self.assertEqual(self.unzip(path)["logs/session-1.log"], b"x" * 400)

    def test_a_file_time_before_1980_becomes_1980(self):
        os.utime(str(self.home / "findings" / "F-001-a.md"), (0, 0))
        path, skipped = self.export()
        with zipfile.ZipFile(str(path)) as archive:
            self.assertEqual(archive.getinfo("findings/F-001-a.md").date_time, (1980, 1, 1, 0, 0, 0))

    def test_links_and_their_targets_stay_out_and_are_reported(self):
        (self.home / "evidence" / "secret.txt").symlink_to(self.outside / "secret.txt")
        (self.home / "evidence" / "copy.md").symlink_to(self.home / "findings" / "F-001-a.md")
        path, skipped = self.export()
        self.assertEqual(skipped, ["not exported: symlink: evidence/copy.md",
                                   "not exported: symlink: evidence/secret.txt"])
        files = self.unzip(path)
        self.assertNotIn("evidence/secret.txt", files)
        self.assertNotIn("evidence/copy.md", files)
        self.assertNotIn(b"outside\n", files.values())
        self.assertEqual(files, self.mirror(self.home, ("findings", "evidence", "tracker")))

    def test_a_second_export_leaves_out_the_first(self):
        first, skipped = self.export()
        second, skipped = self.export(now=EXPORT_TIME + datetime.timedelta(seconds=1))
        self.assertNotEqual(first, second)
        for name in self.unzip(second):
            self.assertNotIn("cptc-export", name)
        self.assertEqual(self.unzip(first), self.unzip(second))

    def root_names(self):
        return sorted(path.name for path in self.home.iterdir())

    def test_same_second_export_is_refused_and_the_first_kept(self):
        first, skipped = self.export()
        before = first.read_bytes()
        names = self.root_names()
        (self.home / "findings" / "F-002-new.md").write_text("new\n", encoding="utf-8")
        # Refused before any file is copied, so no big zip is written for nothing.
        with mock.patch.object(notebook, "add_zip_file") as add, \
                self.assertRaises(FileExistsError) as caught:
            self.export()
        add.assert_not_called()
        self.assertEqual(str(caught.exception), "an export named cptc-export-alice-20261107T103000.zip"
                         " already exists; try again in a second")
        self.assertEqual(first.read_bytes(), before)
        self.assertEqual(self.root_names(), names)

    def test_a_link_with_the_export_name_pointing_outside_is_refused(self):
        link = self.home / "cptc-export-alice-20261107T103000.zip"
        link.symlink_to(self.outside / "secret.txt")
        # writable_path() refuses it first, as for every other write.
        with self.assertRaises(compile.RootError):
            self.export()
        self.assertEqual((self.outside / "secret.txt").read_text(encoding="utf-8"), "outside\n")
        self.assertTrue(link.is_symlink())

    def test_a_link_with_the_export_name_inside_the_root_is_refused(self):
        link = self.home / "cptc-export-alice-20261107T103000.zip"
        link.symlink_to(self.home / "report.md")
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertEqual((self.home / "report.md").read_text(encoding="utf-8"), "report\n")
        self.assertTrue(link.is_symlink())

    def test_a_dangling_link_with_the_export_name_is_refused(self):
        # A link to a file that doesn't exist yet: writing through it would create one.
        link = self.home / "cptc-export-alice-20261107T103000.zip"
        link.symlink_to(self.home / "made-by-export.zip")
        with self.assertRaises(FileExistsError):
            self.export()
        self.assertFalse((self.home / "made-by-export.zip").exists())

    def test_a_failed_write_leaves_no_zip_and_no_temp_file(self):
        names = self.root_names()
        calls = []

        def fail_on_second(archive, member, path, skipped):
            calls.append(member)
            if len(calls) == 2:
                raise OSError("disk full")
            real_add(archive, member, path, skipped)

        real_add = notebook.add_zip_file
        with mock.patch.object(notebook, "add_zip_file", fail_on_second):
            with self.assertRaises(OSError):
                self.export()
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.root_names(), names)

    def test_a_failed_naming_leaves_no_zip_and_no_temp_file(self):
        names = self.root_names()
        with mock.patch.object(notebook.os, "link", side_effect=OSError("link failed")):
            with self.assertRaises(OSError):
                self.export()
        self.assertEqual(self.root_names(), names)

    def test_the_temp_file_is_never_named_like_an_export(self):
        seen = []

        def look(archive, member, path, skipped):
            seen.extend(name for name in self.root_names() if name.startswith(".cptc-export-"))
            real_add(archive, member, path, skipped)

        real_add = notebook.add_zip_file
        with mock.patch.object(notebook, "add_zip_file", look):
            path, skipped = self.export()
        self.assertTrue(seen)
        for name in seen:
            self.assertTrue(name.endswith(".part"), name)
            self.assertIsNone(EXPORT_NAME_RE.fullmatch(name))
        self.assertEqual([name for name in self.root_names() if name.startswith(".cptc-export-")], [])

    def test_a_refused_root_path_writes_nothing(self):
        # LOGDIR set to the working copy itself: the root is then read-only.
        names = self.root_names()
        with self.assertRaises(compile.RootError):
            notebook.write_export(self.home, self.home, "alice", False, EXPORT_TIME)
        self.assertEqual(self.root_names(), names)

    def export_with_members(self, members):
        """Export with export_manifest() returning members, as if the disk changed after it looked."""
        with mock.patch.object(notebook, "export_manifest", return_value=(members, [])):
            return self.export()

    def test_a_file_swapped_for_a_link_after_the_manifest_is_skipped(self):
        swapped = self.home / "evidence" / "scan.txt"
        swapped.unlink()
        swapped.symlink_to(self.outside / "secret.txt")
        path, skipped = self.export_with_members([("findings/F-001-a.md", self.home / "findings/F-001-a.md"),
                                                  ("evidence/scan.txt", swapped)])
        self.assertEqual(skipped, ["not exported: symlink: evidence/scan.txt"])
        self.assertEqual(list(self.unzip(path)), ["findings/F-001-a.md"])

    def test_a_file_swapped_for_a_fifo_after_the_manifest_is_skipped(self):
        swapped = self.home / "evidence" / "scan.txt"
        swapped.unlink()
        os.mkfifo(str(swapped))
        # Opening it to read without O_NONBLOCK would hang here.
        path, skipped = self.export_with_members([("evidence/scan.txt", swapped)])
        self.assertEqual(skipped, ["not exported: not a regular file: evidence/scan.txt"])
        self.assertEqual(self.unzip(path), {})

    def test_a_file_gone_after_the_manifest_is_skipped(self):
        gone = self.home / "evidence" / "scan.txt"
        gone.unlink()
        path, skipped = self.export_with_members([("evidence/scan.txt", gone)])
        self.assertEqual(len(skipped), 1)
        self.assertTrue(skipped[0].startswith("not exported: can't read: evidence/scan.txt ("), skipped)

    def test_a_backslash_name_is_skipped(self):
        # Taken before the file is made, so it holds only the rest of the mirror.
        expected = self.mirror(self.home, ("findings", "evidence", "tracker"))
        (self.home / "evidence" / "web01\\shot.txt").write_text("backslash\n", encoding="utf-8")
        path, skipped = self.export()
        self.assertEqual(skipped, ["not exported: name has a backslash: evidence/web01\\shot.txt"])
        # evidence/web01/shot.txt is still the real nested file, not this one.
        self.assertEqual(self.unzip(path), expected)

    def test_a_name_that_is_not_utf8_is_skipped(self):
        # os.listdir() gives such a name with a lone surrogate standing in for the bad byte.
        member = "evidence/bad\udcff.txt"
        path, skipped = self.export_with_members([(member, self.home / "evidence" / "scan.txt")])
        self.assertEqual(skipped, ["not exported: name isn't UTF-8: " + member])
        self.assertEqual(self.unzip(path), {})

    def test_skips_from_the_manifest_are_kept(self):
        os.mkfifo(str(self.home / "evidence" / "pipe"))
        path, skipped = self.export()
        self.assertEqual(skipped, ["not exported: not a regular file: evidence/pipe"])

    def test_nothing_to_export_still_makes_an_empty_zip(self):
        home = support.make_worktree(self)
        path, skipped = self.export(home=home)
        self.assertEqual((path.name, skipped), ("cptc-export-alice-20261107T103000.zip", []))
        with zipfile.ZipFile(str(path)) as archive:
            self.assertEqual(archive.namelist(), EXPORT_FOLDER_ENTRIES)

    def test_an_empty_export_unzips_to_the_four_folders(self):
        path, skipped = self.export(home=support.make_worktree(self))
        target = support.make_worktree(self)
        with zipfile.ZipFile(str(path)) as archive:
            archive.extractall(str(target))
        self.assertEqual(sorted(entry.relative_to(target).as_posix() for entry in target.rglob("*")),
                         ["evidence", "field-notes", "field-notes/alice", "findings", "tracker"])

    def test_logs_folder_entry_only_with_logs(self):
        path, skipped = self.export(include_logs=True)
        with zipfile.ZipFile(str(path)) as archive:
            self.assertEqual(archive.namelist()[:5], EXPORT_FOLDER_ENTRIES + ["logs/"])
            for folder in EXPORT_FOLDER_ENTRIES + ["logs/"]:
                # Marked as a folder for unzip tools too, not only by its "/".
                self.assertTrue(stat.S_ISDIR(archive.getinfo(folder).external_attr >> 16), folder)
        path, skipped = self.export(now=EXPORT_TIME + datetime.timedelta(seconds=1))
        with zipfile.ZipFile(str(path)) as archive:
            self.assertNotIn("logs/", archive.namelist())

    def test_a_file_named_like_the_export_while_writing_is_kept(self):
        # Another program makes a file of the same name after the first check.
        taken = self.home / "cptc-export-alice-20261107T103000.zip"
        real_add = notebook.add_zip_file

        def make_it_first(archive, member, path, skipped):
            if not taken.exists():
                taken.write_bytes(b"not ours\n")
            real_add(archive, member, path, skipped)

        with mock.patch.object(notebook, "add_zip_file", make_it_first):
            with self.assertRaises(FileExistsError) as caught:
                self.export()
        self.assertEqual(str(caught.exception), "an export named cptc-export-alice-20261107T103000.zip"
                         " already exists; try again in a second")
        self.assertEqual(taken.read_bytes(), b"not ours\n")
        self.assertEqual([name for name in self.root_names() if name.startswith(".cptc-export-")], [])

    def test_no_code_extracts_a_zip(self):
        names = set()
        for node in ast.walk(ModuleSafetyTests.TREE):
            if isinstance(node, ast.Attribute):
                names.add(node.attr)
            elif isinstance(node, ast.Name):
                names.add(node.id)
        for name in ("extract", "extractall", "unpack_archive"):
            with self.subTest(name=name):
                self.assertNotIn(name, names)


class ExportRouteTests(ServerTestCase):
    """N5-03: POST /export writes the zip and reports where (Export (a))."""

    def setUp(self):
        super().setUp()
        support.write_fake_file(self.root, "evidence/scan.txt", "scan\n")
        support.write_fake_file(self.logdir, "session-1.log", "log one\n")

    def post(self, body, token="default", host=None, path="/export"):
        """POST raw body bytes; return (status, text, content type)."""
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        self.addCleanup(connection.close)
        connection.putrequest("POST", path, skip_host=True)
        connection.putheader("Host", host or self.good_host())
        if token is not None:
            connection.putheader("X-CPTC-Token", self.server.token if token == "default" else token)
        connection.putheader("Content-Type", "application/json")
        connection.putheader("Content-Length", str(len(body)))
        connection.endheaders(body)
        response = connection.getresponse()
        text = response.read().decode("utf-8")
        self.assert_safe_headers(response)
        return response.status, text, response.getheader("Content-Type")

    def export(self, include_logs):
        status, text, content_type = self.post(json.dumps({"include_logs": include_logs}).encode("utf-8"))
        self.assertEqual((status, content_type), (200, "application/json"), text)
        return json.loads(text)

    def zips(self):
        return sorted(path.name for path in self.root.iterdir() if path.name.endswith(".zip"))

    def members(self, path):
        with zipfile.ZipFile(path) as archive:
            return archive.namelist()

    def test_export_reports_the_saved_path(self):
        result = self.export(False)
        self.assertEqual(set(result), {"path", "skipped"})
        path = Path(result["path"])
        self.assertEqual(path.parent, self.root.resolve())
        self.assertTrue(EXPORT_NAME_RE.fullmatch(path.name), path.name)
        self.assertEqual(self.zips(), [path.name])
        self.assertEqual(result["skipped"], [])
        self.assertEqual(self.members(path), EXPORT_FOLDER_ENTRIES + ["findings/F-001-x.md",
                                                                      "evidence/scan.txt"])

    def test_logs_only_when_ticked(self):
        self.assertNotIn("logs/session-1.log", self.members(self.export(False)["path"]))
        # A second later, so the two zips don't share a name.
        with mock.patch.object(notebook, "export_file_name",
                               lambda name, now: "cptc-export-alice-20261107T103001.zip"):
            path = self.export(True)["path"]
        self.assertIn("logs/session-1.log", self.members(path))

    def test_skipped_links_are_reported_and_the_zip_still_made(self):
        (self.root / "evidence" / "copy.md").symlink_to(self.root / "findings" / "F-001-x.md")
        result = self.export(False)
        self.assertEqual(result["skipped"], ["not exported: symlink: evidence/copy.md"])
        self.assertNotIn("evidence/copy.md", self.members(result["path"]))

    def assert_not_exported(self, status_wanted, text_wanted, body, **options):
        status, text, content_type = self.post(body, **options)
        self.assertEqual((status, text), (status_wanted, text_wanted))
        self.assertEqual(content_type, "text/plain; charset=utf-8")
        self.assertEqual(self.zips(), [])
        self.assertEqual([path.name for path in self.root.iterdir() if path.name.startswith(".")], [])

    def test_bad_bodies_are_refused_before_any_zip(self):
        wanted = 'send {"include_logs": true or false}'
        for body in [b"{}", b'{"include_log": false}', b'{"include_logs": "true"}',
                     b'{"include_logs": 1}', b'{"include_logs": null}',
                     b'{"include_logs": false, "path": "x"}', b"[true]", b"not json", b"\xff"]:
            with self.subTest(body=body), \
                    mock.patch.object(notebook, "write_export") as write:
                self.assert_not_exported(400, wanted, body)
                write.assert_not_called()

    def test_a_long_body_is_refused(self):
        body = json.dumps({"include_logs": False, "pad": "x" * 2000}).encode("utf-8")
        self.assert_not_exported(400, "send the export choice as JSON, at most 1024 bytes", body)

    def test_no_or_wrong_token_or_host_writes_nothing(self):
        body = b'{"include_logs": false}'
        refused = "refused: use http://127.0.0.1:" + str(self.port)
        for options in [{"token": None}, {"token": "wrong"}, {"host": "evil.example:80"}]:
            with self.subTest(options=options), \
                    mock.patch.object(notebook, "write_export") as write:
                status, text, content_type = self.post(body, **options)
                self.assertEqual((status, text), (403, refused))
                write.assert_not_called()
        self.assertEqual(self.zips(), [])

    def test_get_export_is_not_a_route(self):
        status, text = self.send("GET", "/export", self.good_host())
        self.assertEqual(status, 404)
        self.assertEqual(self.zips(), [])

    def test_same_second_export_is_a_409(self):
        with mock.patch.object(notebook, "export_file_name",
                               lambda name, now: "cptc-export-alice-20261107T103000.zip"):
            first = self.export(False)["path"]
            before = Path(first).read_bytes()
            status, text, content_type = self.post(b'{"include_logs": false}')
        self.assertEqual((status, text), (409, "not exported: an export named "
                                          "cptc-export-alice-20261107T103000.zip already exists;"
                                          " try again in a second"))
        self.assertEqual(Path(first).read_bytes(), before)

    def test_a_refused_root_is_a_403(self):
        # LOGDIR set to the working copy itself: the root is then read-only.
        self.server.settings["logdir"] = self.root.resolve()
        status, text, content_type = self.post(b'{"include_logs": false}')
        self.assertEqual(status, 403)
        self.assertTrue(text.startswith("refused: the log folder is read-only, not writing: "), text)
        self.assertEqual(self.zips(), [])

    def test_a_write_failure_is_a_500_with_no_zip(self):
        with mock.patch.object(notebook, "add_zip_file", side_effect=OSError("disk full")):
            self.assert_not_exported(500, "not exported: disk full", b'{"include_logs": false}')


class ExportPageTests(ServerTestCase):
    """N5-03: the page's Export view. Display safety is PageSafetyTests' (NT4-06)."""

    def get_page(self):
        response, page = self.send_full("GET", "/", self.good_host())
        self.assertEqual(response.status, 200)
        return page

    def test_export_button_opens_the_export_view(self):
        page = self.get_page()
        self.assertIn('document.getElementById("export-button").addEventListener("click", function () {\n'
                      "  goTo(showExport);\n});", page)
        self.assertEqual(page.count("export-button"), 2)

    def test_include_logs_starts_unticked_with_its_warning(self):
        page = self.get_page()
        self.assertIn('logs.type = "checkbox";\n  /* Off every time the view opens (Export (a)). */\n'
                      "  logs.checked = false;", page)
        self.assertIn('label.appendChild(element("span", "Include logs"));', page)
        self.assertIn('main.appendChild(element("p", "Logs are large and may contain secrets such as " +\n'
                      '    "passwords and keys. Only include them when your team needs them."));', page)

    def test_the_request_carries_only_the_box(self):
        page = self.get_page()
        self.assertIn('fetch("/export", {\n      method: "POST",', page)
        self.assertIn("body: JSON.stringify({include_logs: logs.checked})", page)

    def test_the_saved_path_and_every_left_out_file_show(self):
        page = self.get_page()
        self.assertIn('status.appendChild(element("p", "Saved " + result.path));', page)
        self.assertIn('if (result.skipped.length > 0) {\n'
                      '          status.appendChild(element("p", "Left out of the zip:"));', page)
        self.assertIn("result.skipped.forEach(function (line) {\n"
                      '          status.appendChild(element("p", line));', page)

    def test_a_failure_shows_its_text_and_unlocks_the_button(self):
        page = self.get_page()
        self.assertIn("make.disabled = true;", page)
        self.assertIn("function notMade(text) {\n      make.disabled = false;\n"
                      '      status.appendChild(element("p", text));', page)
        self.assertIn("return response.text().then(notMade);", page)
        self.assertIn('notMade("Not exported: " + error);', page)


if __name__ == "__main__":
    unittest.main()
