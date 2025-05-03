import os
import shlex
from unittest.mock import MagicMock, patch

import pytest
from prompt_toolkit.completion import CompleteEvent, Completion
from prompt_toolkit.document import Document

from s3_browser.cli import Cli
from s3_browser.completion import CliCompleter
from s3_browser.paths import S3Key, S3Prefix

test_prefixes = [S3Prefix("ash"), S3Prefix("mia")]
test_files = [S3Key("tric.txt")]


class TestCompletion:
    def _completer(self) -> CliCompleter:
        """Create a CLI completer and return both it and the mocked CLI"""
        m = MagicMock()
        m.RECOGNISED_COMMANDS = Cli.RECOGNISED_COMMANDS
        m.client.ls.return_value = test_prefixes + test_files
        return CliCompleter(m)

    def _complete(self, cmd: str, completer: CliCompleter | None = None) -> list[Completion]:
        """Convenience function to invoke completion with a simple string"""
        completer = completer or self._completer()
        return list(
            completer.get_completions(
                Document(text=cmd, cursor_position=len(cmd)),
                CompleteEvent(),
            )
        )

    def test_complete_empty_command(self) -> None:
        """Tab on an empty string should list all commands"""
        expected = [Completion(cmd, start_position=0) for cmd in Cli.RECOGNISED_COMMANDS]
        actual = self._complete("")

        assert actual == expected

    @pytest.mark.parametrize(
        ("partial", "expected"),
        [
            ("c", ["cat", "cd", "clear"]),
            ("bo", ["bookmark"]),
        ],
    )
    def test_complete_partial_command(self, partial: str, expected: list[str]) -> None:
        expected = [Completion(e, start_position=-len(partial)) for e in expected]
        actual = self._complete(partial)

        assert actual == expected

    @pytest.mark.parametrize(
        ("partial", "expected"),
        [
            # Accept files or prefixes
            ("cat ", test_prefixes + test_files),
            ("cat ./ ", test_prefixes + test_files),
            ("file ", test_prefixes + test_files),
            ("get ", test_prefixes + test_files),
            ("head ", test_prefixes + test_files),
            ("put ./ ", test_prefixes + test_files),
            ("rm ", test_prefixes + test_files),
            ("rm ./ ", test_prefixes + test_files),
            # Accept prefixes only
            ("cd ", test_prefixes),
            ("ls ", test_prefixes),
            ("ll ", test_prefixes),
            # Complete the relative path first: N.B. ../ only works here because the mock always
            # returns the same keys / prefixes regardless of search path
            ("cat .", ["./", *test_prefixes, *test_files]),
            ("cat ..", ["../", *test_prefixes, *test_files]),
        ],
    )
    def test_complete_s3_path_commands(self, partial: str, expected: str) -> None:
        """Tab on several commands should complete S3 paths or keys"""
        start_pos = partial.rfind(" ") - len(partial) + 1
        expected = [Completion(str(e), start_position=start_pos) for e in expected]
        actual = self._complete(partial)

        assert actual == expected

    @pytest.mark.parametrize("partial", ["put ", "get . "])
    def test_complete_local_path(self, partial: str) -> None:
        """Tab on put or get . should complete local path arguments"""
        # TODO: Would be a better / more controlled test to create a test dir with defined files
        # rather than relying on cwd
        files = [shlex.quote(f) for f in os.listdir(".")]

        expected = [Completion(f, start_position=0) for f in files]
        actual = self._complete(partial)

        assert actual == expected

    @patch("os.path.expanduser")
    @pytest.mark.parametrize("partial", ["put ~", "get . ~"])
    def test_complete_local_path_tilde(self, mock_expanduser, partial: str):
        """Should replace a lone ~ with the home dir path"""
        mock_expanduser.return_value = "/home/ash"

        expected = [Completion("/home/ash", start_position=-1)]
        actual = self._complete(partial)

        assert actual == expected

    @patch("os.path.expanduser")
    @pytest.mark.parametrize("partial", ["put ~/", "get . ~/"])
    def test_complete_local_path_tilde_path(self, mock_expanduser, partial: str):
        """Should complete paths containing ~ as home dir"""
        mock_expanduser.return_value = "./"
        files = [shlex.quote(f) for f in os.listdir(".")]

        expected = [Completion(f, start_position=0) for f in files]
        actual = self._complete(partial)

        assert actual == expected
        mock_expanduser.assert_called_once_with("~/")

    @pytest.mark.parametrize(
        "partial",
        [
            "cat ",
            "cat a",
            "cat arg",
            "cat argh",
            'cat "argh spaces',
            "cat 'argh spaces",
            'cat "argh spaces"',
            "cat 'argh spaces'",
        ],
    )
    def test_complete_paths_with_quotes(self, partial):
        """Tab complete should work where paths need quoting"""
        completer = self._completer()
        completer.cli.client.ls.return_value = [S3Key("argh spaces.txt")]

        expected = [Completion("'argh spaces.txt'", start_position=4 - len(partial))]
        actual = self._complete(partial, completer=completer)

        assert actual == expected
