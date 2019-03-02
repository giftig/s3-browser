import readline


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """
    EXPECTS_KEY = {'file'}
    EXPECTS_PATH = {'cd', 'ls', 'll'}.union(EXPECTS_KEY)

    def __init__(self, cli):
        self.cli = cli
        self.s3_client = self.cli.client

    def complete_path(self, text, state, allow_keys=False):
        res = [
            str(r) for r in self.s3_client.ls(
                self.cli.normalise_path(text),
                path_fragment=not text.endswith('/')
            )
            if allow_keys or r.is_prefix() or r.is_bucket()
        ]
        return str(res[state]) if state < len(res) else None

    def complete_bookmark(self, text, state):
        # TODO: Autocomplete $ or ${}
        return None

    def complete(self, text, state):
        buf = readline.get_line_buffer()

        if ' ' not in buf:
            matches = [
                c for c in self.cli.RECOGNISED_COMMANDS if c.startswith(buf)
            ]
            if state < len(matches):
                return matches[state]

            return None

        words = buf.split(' ')
        cmd = words[0]
        if cmd in self.EXPECTS_PATH:
            args = buf[len(cmd) + 1:]
            return self.complete_path(args, state, cmd in self.EXPECTS_KEY)

        return None

    def bind(self):
        readline.set_completer_delims(' \t\n/;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.complete)
