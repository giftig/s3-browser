#!/usr/bin/env python3

import os
import sys

from s3_browser import client
from s3_browser import completion
from s3_browser import paths


class Cli(object):
    DEFAULT_PS1 = 's3://\x1b[36m{path_short}\x1b[0m> '

    def __init__(self, initial_path=None, ps1=None):
        self.ps1 = ps1 or Cli.DEFAULT_PS1
        self.current_path = paths.S3Path.from_path(initial_path or '/')

        self.client = client.S3Client()

        self.completion = completion.CliCompleter(self)
        self.completion.bind()

    @staticmethod
    def _err(msg):
        """Print a message in red"""
        print('\x1b[31m', msg, '\x1b[0m', file=sys.stderr)

    def normalise_path(self, path):
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

    def prompt(self):
        cmd = input(self._render_prompt()).split()
        if not cmd:
            return

        func = {
            'cd': self.cd,
            'clear': lambda: os.system('clear'),
            'exit': sys.exit,
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
        while True:
            try:
                self.prompt()
            except KeyboardInterrupt:
                print('')


def main():
    Cli(*sys.argv[1:]).read_loop()


if __name__ == '__main__':
    main()
