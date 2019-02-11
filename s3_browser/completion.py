import readline


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """
    def __init__(self, cli):
        self.commands = ['cd', 'clear', 'exit', 'ls', 'pwd']
        self.cli = cli
        self.s3_client = self.cli.client

    def complete_path(self, text, state):
        res = self.s3_client.ls(
            self.cli.normalise_path(text),
            path_fragment=True
        )
        entry = res[state] if state < len(res) else None

        # Need to patch the last part of the suggested value onto the end of
        # our current string, as we have a relative path etc
        if entry:
            last_slash = text.rfind('/')
            if last_slash != -1:
                stripped_text = text[:last_slash + 1]
            else:
                stripped_text = ''

            return stripped_text + entry

        return entry

    def complete(self, text, state):
        buf = readline.get_line_buffer()

        if not buf and state < len(self.commands):
            return self.commands[state]

        words = buf.split(' ')
        cmd = words[0]
        if cmd in ['cd', 'ls']:
            args = buf[len(cmd) + 1:]
            return self.complete_path(args, state)

        return None

    def bind(self):
        readline.set_completer_delims(' \t\n;')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(self.complete)
