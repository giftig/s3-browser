#!/usr/bin/env python3

import argparse
import logging
import os
import readline
import sys

from s3_browser import client
from s3_browser import completion
from s3_browser import paths

logger = logging.getLogger(__name__)


class Cli(object):
    DEFAULT_PS1 = 's3://\001\x1b[36m\002{path_short}\001\x1b[0m\002> '

    def __init__(self, working_dir=None, ps1=None, history_file=None):
        self.history_file = history_file
        self.ps1 = ps1 or Cli.DEFAULT_PS1
        self.current_path = paths.S3Path.from_path(working_dir or '/')

        self.client = client.S3Client()

        self.completion = completion.CliCompleter(self)
        self.completion.bind()

    @staticmethod
    def _err(msg):
        """Print a message in red"""
        print('\x1b[31m', msg, '\x1b[0m', file=sys.stderr)

    def normalise_path(self, path):
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
        # TODO: Add some presentation + an ll equivalent
        for p in self.client.ls(self.normalise_path(path)):
            if full_details:
                p = p.full_details

            print(p)

    def _render_prompt(self):
        return self.ps1.format(
            path=self.current_path,
            path_short=self.current_path.short_format,
            path_end=(
                self.current_path.name or self.current_path.bucket or '/'
            )
        )

    def exit(self):
        if self.history_file:
            readline.write_history_file(self.history_file)

        sys.exit(0)

    def prompt(self):
        cmd = input(self._render_prompt()).split()
        if not cmd:
            return

        def _ll(path=''):
            return self.ls(path, full_details=True)

        func = {
            'cd': self.cd,
            'clear': lambda: os.system('clear'),
            'exit': self.exit,
            'll': _ll,
            'ls': self.ls,
            'pwd': lambda: print('s3://{}'.format(self.current_path))
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

    Cli(
        working_dir=args.working_dir,
        ps1=args.prompt,
        history_file=args.history_file
    ).read_loop()


if __name__ == '__main__':
    main()
