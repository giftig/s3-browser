#!/usr/bin/env python3

import argparse
import logging
import os
import readline
import shlex
import sys
import textwrap

from s3_browser import bookmarks
from s3_browser import client
from s3_browser import completion
from s3_browser import paths
from s3_browser import tokeniser
from s3_browser import utils
from s3_browser.argparse import ArgumentParser as SafeParser

logger = logging.getLogger(__name__)


class Cli(object):
    DEFAULT_PS1 = 's3://\001\x1b[36m\002{path_short}\001\x1b[0m\002> '
    SPLASH = textwrap.dedent(
        """
        Welcome to the interactive AWS S3 navigator.
        Written by Rob Moore.

        \x1b[36mContribute: https://www.github.com/giftig/s3-browser/\x1b[0m

        Type 'help' for help.
        """
    )

    RECOGNISED_COMMANDS = [
        'bookmark', 'cat', 'cd', 'clear', 'exit', 'file', 'get', 'head',
        'help', 'll', 'ls', 'prompt', 'put', 'pwd', 'refresh', 'rm'
    ]

    def __init__(
        self,
        endpoint=None,
        working_dir=None,
        ps1=None,
        history_file=None,
        bookmark_file=None
    ):
        self.history_file = history_file
        self.ps1 = ps1 or Cli.DEFAULT_PS1
        self.current_path = paths.S3Path.from_path(working_dir or '/')

        self.client = client.S3Client(endpoint=endpoint)

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

    def ls(self, *args):
        parser = SafeParser('ls')
        parser.add_argument(
            '-l', dest='full_details', action='store_true',
            help='Use a long list format, including additional s3 metadata'
        )
        parser.add_argument(
            '-1', dest='oneline', action='store_true',
            help='List one result per line'
        )
        parser.add_argument('path', default='', nargs='?')
        args = parser.parse_args(args)

        if parser.exited:
            return

        bookmarked = {str(v): k for k, v in self.bookmarks.bookmarks.items()}
        results = self.client.ls(self.normalise_path(args.path))

        # Annotate any present bookmarks so that we can see them in the display
        # We need to do some juggling of the values to do that as we have
        # absolute buckets, prefixes relative to the pwd, etc.
        if args.full_details:
            for r in results:
                b = bookmarked.get(str(self.normalise_path(r.path_string)))
                r.bookmark = b

        results = [
            str(r) if not args.full_details else r.full_details
            for r in results
        ]

        if args.oneline:
            for r in results:
                print(r)
        else:
            utils.print_grid(results)

    def cat(self, *args):
        parser = SafeParser('cat')
        parser.add_argument('keys', nargs='+', help='S3 key(s) to concatenate')
        args = parser.parse_args(args)

        if parser.exited:
            return

        paths = [self.normalise_path(p) for p in args.keys]
        streams = []

        for p in paths:
            obj = self.client.get_object(p)
            utils.print_object(obj)

        for s in streams:
            utils.print_stream(s)

    def rm(self, *args):
        parser = SafeParser('rm')
        parser.add_argument('keys', nargs='+', help='S3 key(s) to delete')
        args = parser.parse_args(args)

        if parser.exited:
            return

        paths = [self.normalise_path(p) for p in args.keys]

        for p in paths:
            self.client.rm(p)

    def put(self, *args):
        parser = SafeParser('put')
        parser.add_argument(
            'local_file', help='Local file to upload to S3'
        )
        parser.add_argument(
            's3_key', nargs=1, help='S3 key at which to write the file'
        )
        args = parser.parse_args(args)

        if parser.exited:
            return

        self.client.put(args.local_file, self.normalise_path(args.s3_key))

    def get(self, *args):
        parser = SafeParser('get')
        parser.add_argument('s3_key', nargs=1, help='S3 key to download')
        parser.add_argument(
            'local_path', help='Local destination for downloaded file'
        )
        args = parser.parse_args(args)

        if parser.exited:
            return

        s3_key = self.normalise_path(args.s3_key)
        local_file = args.local_path

        if os.path.isdir(args.local_path):
            local_file = os.path.join(
                args.local_path,
                os.path.basename(s3_key.path)
            )

        self.client.get(s3_key, local_file)

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

            help             Print this help message
            exit             Bye!

            bookmark         Add, remove, or list bookmarks.
                             Use 'bookmark help' for more details.
            cat [paths]      Print / concat contents of one or more path(s)
            cd [path]        Change directory
            clear            Clear the screen
            file [key]       Show extended metadata about a given key
            head [key]       Alias for file
            ll [path]        Like ls, but show modified times and object types
            ls [path]        List the contents of an s3 "directory"
            prompt [str]     Override the current prompt string
            put [local] [s3] Upload a local file to S3
            pwd              Print the current working directory
            refresh          Clear the ls cache
            rm [keys]        Delete one or more keys

            Tab completion is available for most commands.

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
        cmd = shlex.split(input(self._render_prompt()))
        if not cmd:
            return

        def _ll(*args):
            return self.ls('-1', *args)

        func = {
            'cd': self.cd,
            'bookmark': self.bookmark,
            'cat': self.cat,
            'clear': lambda: os.system('clear'),
            'exit': self.exit,
            'file': self.print_head_data,
            'get': self.get,
            'head': self.print_head_data,
            'help': self.help,
            'll': _ll,
            'ls': self.ls,
            'prompt': self.override_prompt,
            'put': self.put,
            'pwd': lambda: print(self.current_path.canonical),
            'refresh': self.clear_cache,
            'rm': self.rm
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
        """The main start up + main loop of the cli"""
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
        '-e-', '--endpoint', type=str, default=None,
        help=(
            'Optional endpoint URL to use if not the default Amazon S3 URL. '
            'Hoststring like https://example.com:1234'
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
        endpoint=args.endpoint,
        working_dir=args.working_dir,
        ps1=args.prompt,
        history_file=args.history_file,
        bookmark_file=args.bookmark_file
    ).read_loop()


if __name__ == '__main__':
    main()
