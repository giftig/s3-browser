import argparse


class ArgumentParser(argparse.ArgumentParser):
    """
    An argument parser which doesn't terminate the application

    Errors are instead reported as ValueError so that they may be handled.

    When we would normally exit safely, such as with --help, we'll add an extra
    flag to the parser so that the caller can determine it shouldn't proceed.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exited = False

    def error(self, message):
        raise ValueError(message)

    def exit(self):
        self.exited = True
