import logging
import os
import readline

logger = logging.getLogger(__name__)


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """
    EXPECTS_KEY = {'cat', 'file', 'head', 'rm'}
    EXPECTS_S3_PATH = {'cd', 'ls', 'll'}.union(EXPECTS_KEY)

    def __init__(self, cli):
        self.cli = cli
        self.s3_client = self.cli.client

    def complete_command(self, cmd, state):
        """
        Complete a command if we're just starting to write a command (i.e.
        no spaces in the command yet)
        """
        matches = [
            c for c in self.cli.RECOGNISED_COMMANDS if c.startswith(cmd)
        ]
        if state < len(matches):
            return matches[state]

        return None

    def complete_s3_path(self, partial, state, allow_keys=False):
        """
        Autocomplete for an expected S3 path by looking up possible paths at
        the current path prefix to complete with.


        :param partial: The partial path we're trying to tab-complete (may be
            an empty string)
        :param state: The numerical state provided by the autocomplete system;
            refers to the index of the results being requested in this
            invocation.
        :param allow_keys: If True, we'll allow completing individual keys;
            otherwise we'll only allow completing prefixes (i.e. pseudo
            directories). This distinguishes something you can cd into, for
            example.
        """
        res = [
            str(r) for r in self.s3_client.ls(
                self.cli.normalise_path(partial),
                path_fragment=not partial.endswith('/')
            )
            if allow_keys or not r.is_key
        ]
        return str(res[state]) if state < len(res) else None

    def complete_local_path(self, partial, state):
        """
        Autocomplete for an expected local filesystem path
        """
        if os.path.isfile(partial):
            return os.path.basename(partial) if state == 0 else None

        hits = []

        if partial.endswith('/') and os.path.isdir(partial):
            hits = os.listdir(partial)
        else:
            parent = os.path.dirname(partial)
            frag = os.path.basename(partial)

            if not parent or os.path.isdir(parent):
                hits = [
                    h for h in os.listdir(parent or '.')
                    if h.startswith(frag)
                ]

        return hits[state] if state < len(hits) else None

    def complete_put_get(self, words, state, s3_first):
        """
        A put operation expects a local path first, followed by an S3 path. A
        get operation expects them the other way round. We can determine which
        one we should be completing by the current argument count, ignoring any
        flags.
        """
        args = [w for w in words[1:] if not w.startswith('-')]
        arg_count = len(args)

        if s3_first and arg_count == 1 or not s3_first and arg_count == 2:
            return self.complete_s3_path(args[-1], state, allow_keys=True)

        if s3_first and arg_count == 2 or not s3_first and arg_count == 1:
            return self.complete_local_path(args[-1], state)

        return None

    def complete_bookmark(self, text, state):
        # TODO: Autocomplete $ or ${}
        return None

    def complete(self, text, state):
        """
        Autocomplete the next word by figuring out the context of what we're
        doing and delegating to the appropriate completion method
        """
        buf = readline.get_line_buffer()

        # TODO: Deal with partial quoted strings somehow; shlex won't work
        # if the quotes aren't complete yet and .split is too naive
        words = buf.split(' ')
        cmd = words[0]

        if len(words) == 1:
            return self.complete_command(cmd, state)

        if cmd == 'put':
            return self.complete_put_get(words, state, s3_first=False)

        if cmd == 'get':
            return self.complete_put_get(words, state, s3_first=True)

        if cmd in self.EXPECTS_S3_PATH:
            return self.complete_s3_path(
                words[-1],
                state,
                cmd in self.EXPECTS_KEY
            )

        return None

    def bind(self):
        readline.set_completer_delims(' \t\n/;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.complete)
