import unittest
from unittest.mock import MagicMock
from unittest.mock import patch

from s3_browser.cli import Cli
from s3_browser.completion import CliCompleter
from s3_browser.paths import S3Key
from s3_browser.paths import S3Prefix


class CompletionTestCase(unittest.TestCase):
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

    @patch('readline.get_line_buffer')
    def test_complete_empty_command(self, mock):
        """Tab on an empty string should list all commands"""
        completer = self._completer()

        for i, cmd in enumerate(Cli.RECOGNISED_COMMANDS):
            self.assertEquals(self._complete(completer, mock, '', i), cmd)

    @patch('readline.get_line_buffer')
    def test_complete_partial_command(self, mock):
        completer = self._completer()
        self.assertEquals(self._complete(completer, mock, 'c', 0), 'cd')
        self.assertEquals(self._complete(completer, mock, 'c', 1), 'clear')
        self.assertEquals(self._complete(completer, mock, 'bo', 0), 'bookmark')

    @patch('readline.get_line_buffer')
    def test_complete_path_commands(self, mock):
        """Tab on ls, ll, cd should list paths, file should also list keys"""
        completer = self._completer()
        prefixes = [S3Prefix('ash'), S3Prefix('mia')]
        files = [S3Key('tric.txt')]

        expected_paths = [str(p) for p in prefixes] + [None]
        expected_files = (
            [str(p) for p in prefixes] + [str(f) for f in files] + [None]
        )

        completer.cli.client.ls.return_value = prefixes + files

        for i, p in enumerate(expected_paths):
            self.assertEquals(self._complete(completer, mock, 'cd ', i), p)
            self.assertEquals(self._complete(completer, mock, 'ls ', i), p)
            self.assertEquals(self._complete(completer, mock, 'll ', i), p)

        for i, f in enumerate(expected_files):
            self.assertEquals(self._complete(completer, mock, 'file ', i), f)
