#!/usr/bin/env python3

import argparse
import os
import readline
import sys

from s3_browser import client
from s3_browser import completion
from s3_browser import paths


class Cli(object):
    DEFAULT_PS1 = 's3://\x1b[36m{path_short}\x1b[0m> '

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

    def ls(self, path=''):
        # TODO: Add some presentation + an ll equivalent
        for p in self.client.ls(self.normalise_path(path)):
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

        func = {
            'cd': self.cd,
            'clear': lambda: os.system('clear'),
            'exit': self.exit,
            'ls': self.ls,
            'pwd': lambda: print('s3://{}'.format(self.current_path))
        }.get(cmd[0])

        if not func:
            self._err('Unrecognised command: \'{}\''.format(cmd[0]))
            return

        try:
            func(*cmd[1:])
        except TypeError as e:
            print('\x1b[31m', e, '\x1b[0m')
            return

    def read_loop(self):
        if self.history_file and os.path.isfile(self.history_file):
            readline.read_history_file(self.history_file)

        while True:
            try:
                self.prompt()
            except KeyboardInterrupt:
                print('')


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
    parser.add_argument('working_dir', nargs='?', type=str, default='/')
    args = parser.parse_args()

    Cli(
        working_dir=args.working_dir,
        ps1=args.prompt,
        history_file=args.history_file
    ).read_loop()


if __name__ == '__main__':
    main()
