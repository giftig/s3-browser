#!/usr/bin/env python3

import argparse
import logging
import os
import readline
import sys
import textwrap

from s3_browser import bookmarks
from s3_browser import client
from s3_browser import completion
from s3_browser import paths
from s3_browser import tokeniser
from s3_browser import utils

logger = logging.getLogger(__name__)


class Cli(object):
    DEFAULT_PS1 = 's3://\001\x1b[36m\002{path_short}\001\x1b[0m\002> '
    SPLASH = textwrap.dedent(
        """
        Welcome to the interactive AWS S3 navigator.
        Written by Giftiger Wunsch.

        \x1b[36mContribute: https://www.github.com/giftig/s3_browser/\x1b[0m

        Type 'help' for help.
        """
    )

    RECOGNISED_COMMANDS = [
        'bookmark', 'cd', 'clear', 'exit', 'file', 'head', 'help', 'll',
        'ls', 'prompt', 'pwd', 'refresh'
    ]

    def __init__(
        self,
        working_dir=None,
        ps1=None,
        history_file=None,
        bookmark_file=None
    ):
        self.history_file = history_file
        self.ps1 = ps1 or Cli.DEFAULT_PS1
        self.current_path = paths.S3Path.from_path(working_dir or '/')

        self.client = client.S3Client()

        if bookmark_file:
            self.bookmarks = bookmarks.BookmarkManager(bookmark_file)
        else:
            self.bookmarks = None

        self.completion = completion.CliCompleter(self)
        self.completion.bind()

    @staticmethod
    def _err(msg):
        """Print a message in red"""
        print('\x1b[31m{}\x1b[0m'.format(msg), file=sys.stderr)

    def normalise_path(self, path):
        # Render variables present in the path
        context = (
            {} if not self.bookmarks else
            {k: v.path for k, v in self.bookmarks.bookmarks.items()}
        )
        path = tokeniser.render(tokeniser.tokenise(path), context)

        # Strip off the protocol prefix if provided
        if path.startswith('s3://'):
            path = path[5:]

        # Special case: ~ refers to the root of the current bucket
        if path == '~' or path == '~/':
            return paths.S3Path(bucket=self.current_path.bucket, path=None)

        path = os.path.join('/' + str(self.current_path), path)
        return paths.S3Path.from_path(path)

    def cd(self, path=''):
        full_path = self.normalise_path(path)

        if self.client.is_path(full_path):
            self.current_path = full_path
            return True

        self._err('cannot access \'{}\': no such s3 directory'.format(path))
        return False

    def ls(self, path='', full_details=False):
        bookmarked = {str(v): k for k, v in self.bookmarks.bookmarks.items()}
        results = self.client.ls(self.normalise_path(path))

        # Annotate any present bookmarks so that we can see them in the display
        # We need to do some juggling of the values to do that as we have
        # absolute buckets, prefixes relative to the pwd, etc.
        if full_details:
            for r in results:
                b = bookmarked.get(str(self.normalise_path(r.path_string)))
                r.bookmark = b

        results = [
            str(r) if not full_details else r.full_details
            for r in results
        ]

        utils.print_grid(results)

    def add_bookmark(self, name, path):
        name = bookmarks.BookmarkManager.clean_key(name)
        if not name:
            self._err('{} is an invalid name for a bookmark'.format(name))
            return

        path = self.normalise_path(path)

        if not self.client.is_path(path):
            self._err(
                'cannot bookmark \'{}\': not an s3 directory'.format(path)
            )
            return

        if not self.bookmarks.add_bookmark(name, path):
            self._err('Failed to add bookmark')
            return

    def remove_bookmark(self, name):
        if not self.bookmarks.remove_bookmark(name):
            self._err('{} is not the name of a bookmark'.format(name))
            return False

        return True

    def list_bookmarks(self):
        for k, v in self.bookmarks.bookmarks.items():
            print('\x1b[33m${: <18}\x1b[0m {}'.format(k, str(v)))

    def bookmark_help(self):
        print(textwrap.dedent(
            """
            Add, remove, or list bookmarks.

            add NAME PATH   Add a bookmark called NAME pointing at PATH
            rm NAME         Remove the named bookmark
            list, ls        List all bookmarks
            """
        ))

    def bookmark(self, op, *args):
        if not self.bookmarks:
            self._err('Bookmarks are unavailable')
            return

        f = {
            'add': self.add_bookmark,
            'ls': self.list_bookmarks,
            'list': self.list_bookmarks,
            'help': self.bookmark_help,
            'rm': self.remove_bookmark
        }.get(op)

        if not f:
            self._err(
                'Bad operation \'{}\'. Try help for correct usage'.format(op)
            )
            return

        return f(*args)

    def print_head_data(self, key):
        """
        Print key size and other extended metadata about a key in a nice
        readable format
        """
        key = self.normalise_path(key)
        data = self.client.head(key)
        data = utils.strip_s3_metadata(data)

        print('\x1b[33m{}\x1b[0m'.format(key.canonical))
        print()
        utils.print_dict(data)

    def _render_prompt(self):
        return self.ps1.format(
            path=self.current_path,
            path_short=self.current_path.short_format,
            path_end=(
                self.current_path.name or self.current_path.bucket or '/'
            )
        )

    def help(self):
        print(textwrap.dedent(
            """
            Available commands:

            help            Print this help message
            exit            Bye!

            bookmark        Add, remove, or list bookmarks.
                            Use 'bookmark help' for more details.
            cd [path]       Change directory
            clear           Clear the screen
            file [key]      Show extended metadata about a given key
            head [key]      Alias for file
            ll [path]       Like ls, but show modified times and object types
            ls [path]       List the contents of an s3 "directory"
            prompt [str]    Override the current prompt string
            pwd             Print the current working directory
            refresh         Clear the ls cache

            Tab completion is available on cd, ls, and ll.

            Command history is available (stored in ~/.s3_browser_history)
            """
        ))

    def override_prompt(self, *args):
        if not args:
            self.ps1 = self.DEFAULT_PS1
        else:
            self.ps1 = ' '.join(args) + ' '

    def exit(self):
        if self.history_file:
            readline.write_history_file(self.history_file)

        sys.exit(0)

    def clear_cache(self):
        size = self.client.clear_cache()
        print('Cleared {} cached paths.'.format(size))

    def prompt(self):
        cmd = input(self._render_prompt()).split()
        if not cmd:
            return

        def _ll(path=''):
            return self.ls(path, full_details=True)

        func = {
            'cd': self.cd,
            'bookmark': self.bookmark,
            'clear': lambda: os.system('clear'),
            'exit': self.exit,
            'file': self.print_head_data,
            'head': self.print_head_data,
            'help': self.help,
            'll': _ll,
            'ls': self.ls,
            'prompt': self.override_prompt,
            'pwd': lambda: print(self.current_path.canonical),
            'refresh': self.clear_cache
        }.get(cmd[0])

        if not func:
            self._err('Unrecognised command: \'{}\''.format(cmd[0]))
            return

        try:
            func(*cmd[1:])
        except TypeError as e:
            self._err(str(e))
            logger.exception('Error while running command %s', cmd)

    def read_loop(self):
        if self.history_file and os.path.isfile(self.history_file):
            readline.read_history_file(self.history_file)

        print(self.SPLASH)

        while True:
            try:
                self.prompt()
            except KeyboardInterrupt:
                print('')
            except Exception as e:
                self._err(str(e))
                logger.exception('Unexpected error')


def configure_debug_logging():
    logging.basicConfig(
        filename='/tmp/s3_browser.log',
        format='%(asctime)s %(levelname)s %(module)s:%(funcName)s %(message)s',
        level=logging.INFO
    )

    logging.getLogger('s3_browser').setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser('s3-browser')
    parser.add_argument(
        '-p', '--prompt', dest='prompt', type=str, default=None,
        help=(
            'Prompt string to use; use the special patterns {path}, '
            '{path_short}, or {path_end} for displaying the current path'
        )
    )
    parser.add_argument(
        '--bookmarks', dest='bookmark_file', type=str,
        default='{}/.s3_browser_bookmarks'.format(
            os.environ.get('HOME', '/etc')
        )
    )
    parser.add_argument(
        '--history', dest='history_file', type=str,
        default='{}/.s3_browser_history'.format(os.environ.get('HOME', '/etc'))
    )
    parser.add_argument(
        '--debug', dest='debug', action='store_true', default=False,
        help='Turn on debug mode, logging information to /tmp/s3_browser.log'
    )
    parser.add_argument('working_dir', nargs='?', type=str, default='/')
    args = parser.parse_args()

    if args.debug:
        configure_debug_logging()
        logger.info('Starting s3 browser in debug mode')
    else:
        logging.disable(logging.CRITICAL)

    Cli(
        working_dir=args.working_dir,
        ps1=args.prompt,
        history_file=args.history_file,
        bookmark_file=args.bookmark_file
    ).read_loop()


if __name__ == '__main__':
    main()
