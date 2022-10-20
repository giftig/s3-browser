import readline


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """
    EXPECTS_KEY = {'file', 'cat'}
    EXPECTS_PATH = {'cd', 'ls', 'll'}.union(EXPECTS_KEY)

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

    def complete_path(self, partial, state, allow_keys=False):
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

    def complete_bookmark(self, text, state):
        # TODO: Autocomplete $ or ${}
        return None

    def complete(self, text, state):
        """
        Autocomplete the next word by figuring out the context of what we're
        doing and delegating to the appropriate completion method
        """
        buf = readline.get_line_buffer()
        words = buf.split(' ')
        cmd = words[0]

        if len(words) == 1:
            return self.complete_command(cmd, state)

        # TODO: This is slightly naive as it assumes all arguments are expected
        # to be a path if any of them are, but as it's only providing
        # suggestions that's not a big problem
        if cmd in self.EXPECTS_PATH:
            return self.complete_path(
                words[-1],
                state,
                cmd in self.EXPECTS_KEY
            )

        return None

    def bind(self):
        readline.set_completer_delims(' \t\n/;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.complete)
