import readline


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """
    EXPECTS_PATH = ['cd', 'ls', 'll']

    def __init__(self, cli):
        self.commands = [
            'cd', 'clear', 'exit', 'help', 'll', 'ls', 'prompt', 'pwd',
            'refresh'
        ]
        self.cli = cli
        self.s3_client = self.cli.client

    def complete_path(self, text, state):
        res = [
            str(r) for r in self.s3_client.ls(
                self.cli.normalise_path(text),
                path_fragment=not text.endswith('/')
            )
            if r.is_prefix() or r.is_bucket()
        ]
        return str(res[state]) if state < len(res) else None

    def complete(self, text, state):
        buf = readline.get_line_buffer()

        if not buf and state < len(self.commands):
            return self.commands[state]

        words = buf.split(' ')
        cmd = words[0]
        if cmd in self.EXPECTS_PATH:
            args = buf[len(cmd) + 1:]
            return self.complete_path(args, state)

        return None

    def bind(self):
        readline.set_completer_delims(' \t\n/;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.complete)
