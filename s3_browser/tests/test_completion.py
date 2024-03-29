import os
import shlex
from unittest.mock import MagicMock, patch

from s3_browser.cli import Cli
from s3_browser.completion import CliCompleter
from s3_browser.paths import S3Key, S3Prefix


class TestCompletion:
    def _completer(self):
        """Create a CLI completer and return both it and the mocked CLI"""
        m = MagicMock()
        m.RECOGNISED_COMMANDS = Cli.RECOGNISED_COMMANDS
        return CliCompleter(m)

    def _complete(self, completer, get_line_buffer, text, state):
        """
        Make the readline line buffer mock return the value we want, and then
        check completer.complete with that in mind.
        """
        get_line_buffer.return_value = text
        res = completer.complete(None, state)
        get_line_buffer.reset_mock()
        return res

    @patch("readline.get_line_buffer")
    def test_complete_empty_command(self, mock):
        """Tab on an empty string should list all commands"""
        completer = self._completer()

        for i, cmd in enumerate(Cli.RECOGNISED_COMMANDS):
            assert self._complete(completer, mock, "", i) == cmd

    @patch("readline.get_line_buffer")
    def test_complete_partial_command(self, mock):
        completer = self._completer()
        assert self._complete(completer, mock, "c", 0) == "cat"
        assert self._complete(completer, mock, "c", 1) == "cd"
        assert self._complete(completer, mock, "c", 2) == "clear"
        assert self._complete(completer, mock, "bo", 0) == "bookmark"

    @patch("readline.get_line_buffer")
    def test_complete_s3_path_commands(self, mock):
        """Tab on several commands should complete S3 paths or keys"""
        completer = self._completer()
        prefixes = [S3Prefix("ash"), S3Prefix("mia")]
        files = [S3Key("tric.txt")]

        expected_paths = [str(p) for p in prefixes] + [None]
        expected_files = [str(p) for p in prefixes] + [str(f) for f in files] + [None]

        completer.cli.client.ls.return_value = prefixes + files

        for i, p in enumerate(expected_paths):
            assert self._complete(completer, mock, "cd ", i) == p
            assert self._complete(completer, mock, "ls ", i) == p
            assert self._complete(completer, mock, "ll ", i) == p

        for i, f in enumerate(expected_files):
            assert self._complete(completer, mock, "cat ", i) == f
            assert self._complete(completer, mock, "cat ./ ", i) == f
            assert self._complete(completer, mock, "file ", i) == f
            assert self._complete(completer, mock, "get ", i) == f
            assert self._complete(completer, mock, "head ", i) == f
            assert self._complete(completer, mock, "put ./ ", i) == f
            assert self._complete(completer, mock, "rm ", i) == f
            assert self._complete(completer, mock, "rm ./ ", i) == f

        # . and .. should suggest the relative dirs and also any s3 key hits
        # Note that it'd be limited to dot-prefixed paths in reality, but our
        # mock always returns expected_files for a key search in this case
        for i, f in enumerate(["./"] + expected_files):
            assert self._complete(completer, mock, "cat .", i) == f

        for i, f in enumerate(["../"] + expected_files):
            assert self._complete(completer, mock, "cat ..", i) == f

    @patch("readline.get_line_buffer")
    def test_complete_local_path(self, mock):
        """Tab on put should complete s3 path or local path arguments"""
        completer = self._completer()

        files = [shlex.quote(f) for f in os.listdir(".")]
        for i, f in enumerate(files):
            assert self._complete(completer, mock, "put ", i) == f
            assert self._complete(completer, mock, "get . ", i) == f

    @patch("readline.get_line_buffer")
    def test_complete_paths_with_quotes(self, mock):
        """Tab complete should work where paths need quoting"""
        completer = self._completer()
        completer.cli.client.ls.return_value = [S3Key("argh spaces.txt")]

        partials = [
            "cat ",
            "cat a",
            "cat arg",
            "cat argh",
            'cat "argh spaces',
            "cat 'argh spaces",
            'cat "argh spaces"',
            "cat 'argh spaces'",
        ]
        expected = "'argh spaces.txt'"

        for p in partials:
            assert self._complete(completer, mock, p, 0) == expected
