#!/usr/bin/env python3

import argparse
import logging
import os
import shlex
import sys
import textwrap
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import ThreadedCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from s3_browser import bookmarks, client, completion, paths, tokeniser, utils
from s3_browser import ps1 as ps1_utils
from s3_browser.argparse import ArgumentParser as SafeParser

logger = logging.getLogger(__name__)


class PathFormat(Enum):
    full = "full"
    short = "short"
    end = "end"
    none = "none"


@dataclass
class Ps1:
    style: Style
    path_format: PathFormat


class Cli:
    SPLASH = textwrap.dedent(
        """
        Welcome to the interactive AWS S3 navigator.
        Written by Rob Moore.

        \x1b[36mContribute: https://www.github.com/giftig/s3-browser/\x1b[0m

        Type 'help' for help.
        """
    )

    RECOGNISED_COMMANDS: ClassVar[list[str]] = [
        "bookmark",
        "cat",
        "cd",
        "clear",
        "exit",
        "file",
        "get",
        "head",
        "help",
        "ll",
        "ls",
        "prompt",
        "put",
        "pwd",
        "refresh",
        "rm",
    ]

    def __init__(  # noqa: PLR0913
        self,
        endpoint: str | None,
        working_dir: str,
        ps1: Ps1,
        history_file: str,
        bookmark_file: str,
        history_search: bool = True,
        complete_while_typing: bool = False,
    ):
        self.history_file = history_file
        self.current_path = paths.S3Path.from_path(working_dir or "/")
        self.ps1 = ps1

        self.client = client.S3Client(endpoint=endpoint)

        if bookmark_file:
            self.bookmarks = bookmarks.BookmarkManager(bookmark_file)
        else:
            self.bookmarks = None

        self.prompt_session = PromptSession(
            auto_suggest=AutoSuggestFromHistory(),
            history=FileHistory(history_file),
            completer=ThreadedCompleter(completion.CliCompleter(self)),
            complete_while_typing=False,
            enable_history_search=True,
        )

    @staticmethod
    def _err(msg):
        """Print a message in red"""
        print(f"\x1b[31m{msg}\x1b[0m", file=sys.stderr)

    def normalise_path(self, path: str) -> paths.S3Path:
        # Render variables present in the path
        context = (
            {} if not self.bookmarks else {k: v.path for k, v in self.bookmarks.bookmarks.items()}
        )
        path = tokeniser.render(tokeniser.tokenise(path), context)

        # Strip off the protocol prefix if provided
        if path.startswith("s3://"):
            path = path[5:]

        # Special case: ~ refers to the root of the current bucket
        if path in {"~", "~/"}:
            return paths.S3Path(bucket=self.current_path.bucket, path=None)

        path = os.path.join("/" + str(self.current_path), path)
        return paths.S3Path.from_path(path)

    def cd(self, path=""):
        full_path = self.normalise_path(path)

        if self.client.is_path(full_path):
            self.current_path = full_path
            return True

        self._err(f"cannot access '{path}': no such s3 directory")
        return False

    def ls(self, *args):
        parser = SafeParser("ls")
        parser.add_argument(
            "-l",
            dest="full_details",
            action="store_true",
            help="Use a long list format, including additional s3 metadata",
        )
        parser.add_argument(
            "-1", dest="oneline", action="store_true", help="List one result per line"
        )
        parser.add_argument("path", default="", nargs="?")
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

        results = [str(r) if not args.full_details else r.full_details for r in results]

        if args.oneline:
            for r in results:
                print(r)
        else:
            utils.print_grid(results)

    def cat(self, *args):
        parser = SafeParser("cat")
        parser.add_argument("keys", nargs="+", help="S3 key(s) to concatenate")
        args = parser.parse_args(args)

        if parser.exited:
            return

        paths = [self.normalise_path(p) for p in args.keys]

        for p in paths:
            obj = self.client.get_object(p)
            utils.print_object(obj)

    def rm(self, *args):
        parser = SafeParser("rm")
        parser.add_argument("keys", nargs="+", help="S3 key(s) to delete")
        args = parser.parse_args(args)

        if parser.exited:
            return

        paths = [self.normalise_path(p) for p in args.keys]

        for p in paths:
            self.client.rm(p)

    def put(self, *args):
        parser = SafeParser("put")
        parser.add_argument("local_file", help="Local file to upload to S3")
        parser.add_argument("s3_key", nargs=1, help="S3 key at which to write the file")
        args = parser.parse_args(args)

        if parser.exited:
            return

        local_file = os.path.expanduser(args.local_file)

        self.client.put(local_file, self.normalise_path(args.s3_key))

    def get(self, *args):
        parser = SafeParser("get")
        parser.add_argument("s3_key", nargs=1, help="S3 key to download")
        parser.add_argument("local_path", help="Local destination for downloaded file")
        args = parser.parse_args(args)

        if parser.exited:
            return

        s3_key = self.normalise_path(args.s3_key)
        local_file = os.path.expanduser(args.local_path)

        if os.path.isdir(args.local_path):
            local_file = os.path.join(args.local_path, os.path.basename(s3_key.path))

        self.client.get(s3_key, local_file)

    def add_bookmark(self, name, path):
        if not bookmarks.BookmarkManager.validate_key(name):
            self._err(f"{name} is an invalid name for a bookmark")
            return

        path = self.normalise_path(path)

        if not self.client.is_path(path):
            self._err(f"cannot bookmark '{path}': not an s3 directory")
            return

        if not self.bookmarks.add_bookmark(name, path):
            self._err("Failed to add bookmark")
            return

    def remove_bookmark(self, name):
        if not self.bookmarks.remove_bookmark(name):
            self._err(f"{name} is not the name of a bookmark")
            return False

        return True

    def list_bookmarks(self):
        for k, v in self.bookmarks.bookmarks.items():
            print(f"\x1b[33m${k: <18}\x1b[0m {v}")

    def bookmark_help(self):
        print(
            textwrap.dedent(
                """
            Add, remove, or list bookmarks.

            add NAME PATH   Add a bookmark called NAME pointing at PATH
            rm NAME         Remove the named bookmark
            list, ls        List all bookmarks
            """
            )
        )

    def bookmark(self, op, *args):
        if not self.bookmarks:
            self._err("Bookmarks are unavailable")
            return None

        f = {
            "add": self.add_bookmark,
            "ls": self.list_bookmarks,
            "list": self.list_bookmarks,
            "help": self.bookmark_help,
            "rm": self.remove_bookmark,
        }.get(op)

        if not f:
            self._err(f"Bad operation '{op}'. Try help for correct usage")
            return None

        return f(*args)

    def print_head_data(self, key):
        """
        Print key size and other extended metadata about a key in a nice
        readable format
        """
        key = self.normalise_path(key)
        data = self.client.head(key)
        data = utils.strip_s3_metadata(data)

        print(f"\x1b[33m{key.canonical}\x1b[0m")
        print()
        utils.print_dict(data)

    def _prompt(self) -> None:
        """Prompt for input with prompt toolkit"""
        path: str | None = {
            PathFormat.full: str(self.current_path),
            PathFormat.short: self.current_path.short_format,
            PathFormat.end: str(self.current_path.name or self.current_path.bucket or "/"),
            PathFormat.none: None,
        }.get(self.ps1.path_format, self.current_path.short_format)

        if path is not None:
            msg = [("class:basic", "s3://"), ("class:path", path), ("class:basic", "> ")]
        else:
            msg = [("class:basic", "> ")]

        return self.prompt_session.prompt(msg, style=self.ps1.style)

    def help(self):
        print(
            textwrap.dedent(
                """
                Available commands:

                help                Print this help message
                exit                Bye!

                bookmark            Add, remove, or list bookmarks.
                                    Use 'bookmark help' for more details.
                cat [paths]         Print / concat contents of one or more path(s)
                cd [path]           Change directory
                clear               Clear the screen
                file [key]          Show extended metadata about a given key
                get [s3] [local]    Download an S3 key to local disk
                head [key]          Alias for file
                ll [path]           Like ls, but show modified times and object types
                ls [path]           List the contents of an s3 "directory"
                prompt fmt [fmt]    Override the format of the current s3 path appearing in the
                                    prompt: valid values for fmt are "short", "full", "end", "none"
                prompt style [str]  Override the prompt styles. See s3-browser --help
                put [local] [s3]    Upload a local file to S3
                pwd                 Print the current working directory
                refresh             Clear the ls cache
                rm [keys]           Delete one or more keys

                Tab completion is available for most commands.

                Most commands support the --help flag to see full usage
                information, e.g. cat --help

                Command history is available (stored in ~/.s3_browser_history)
                """
            )
        )

    def _override_prompt_format(self, path_format: str) -> None:
        self.ps1.path_format = PathFormat(path_format)

    def _override_prompt_style(self, prompt_style: str) -> None:
        self.ps1.style = ps1_utils.read_style(prompt_style)

    def override_prompt(self, *args):
        if not args:
            raise ValueError("Subcommand missing for prompt: specify fmt or style")

        subcmd = args[0]

        func = {
            "fmt": self._override_prompt_format,
            "style": self._override_prompt_style,
        }.get(subcmd)

        if not func:
            raise ValueError(f"Invalid subcommand for prompt: {subcmd}")

        func(*args[1:])

    def exit(self):
        sys.exit(0)

    def clear_cache(self):
        size = self.client.clear_cache()
        print(f"Cleared {size} cached paths.")

    def prompt(self):
        cmd = shlex.split(self._prompt())
        if not cmd:
            return

        def _ll(*args):
            return self.ls("-l", *args)

        func = {
            "bookmark": self.bookmark,
            "cat": self.cat,
            "cd": self.cd,
            "clear": lambda: os.system("clear"),  # noqa: S605, S607
            "exit": self.exit,
            "file": self.print_head_data,
            "get": self.get,
            "head": self.print_head_data,
            "help": self.help,
            "ll": _ll,
            "ls": self.ls,
            "prompt": self.override_prompt,
            "put": self.put,
            "pwd": lambda: print(self.current_path.canonical),
            "refresh": self.clear_cache,
            "rm": self.rm,
        }.get(cmd[0])

        if not func:
            self._err(f"Unrecognised command: '{cmd[0]}'")
            return

        try:
            func(*cmd[1:])
        except TypeError as e:
            self._err(str(e))
            logger.exception("Error while running command %s", cmd)

    def read_loop(self):
        """The main start up + main loop of the cli"""
        print(self.SPLASH)

        while True:
            try:
                self.prompt()
            except KeyboardInterrupt:
                print("")
            except Exception as e:
                self._err(str(e))
                logger.exception("Unexpected error")


def configure_debug_logging():
    logging.basicConfig(
        filename="/tmp/s3_browser.log",  # noqa: S108
        format="%(asctime)s %(levelname)s %(module)s:%(funcName)s %(message)s",
        level=logging.INFO,
    )

    logging.getLogger("s3_browser").setLevel(logging.DEBUG)
    logger.setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser("s3-browser")
    parser.add_argument(
        "--prompt-path-format",
        dest="prompt_path_format",
        type=str,
        default="short",
        help="Path format to use in the prompt. Options are: full, short, end.",
    )
    parser.add_argument(
        "--prompt-style",
        dest="prompt_style",
        type=str,
        default="path:ansicyan",
        help=(
            "Style string to use for the prompt, allowing colouring the basic prompt and the path "
            "portion of the prompt. e.g. 'basic:#ffffff path:#ffff00'. See prompt_toolkit for "
            "more information."
        ),
    )
    parser.add_argument(
        "-e",
        "--endpoint",
        type=str,
        default=None,
        help=(
            "Optional endpoint URL to use if not the default Amazon S3 URL. "
            "Hoststring like https://example.com:1234"
        ),
    )
    parser.add_argument(
        "--bookmarks",
        dest="bookmark_file",
        type=str,
        default="{}/.s3_browser_bookmarks".format(os.environ.get("HOME", "/etc")),
    )
    parser.add_argument(
        "--history",
        dest="history_file",
        type=str,
        default="{}/.s3_browser_history".format(os.environ.get("HOME", "/etc")),
    )
    parser.add_argument(
        "--complete-while-typing",
        dest="complete_while_typing",
        action="store_true",
        help=(
            "Enable complete-while-typing, autocompleting buckets and paths without requiring "
            "an explicit tab to request autocompletion. Note that this will perform S3 prefix "
            "searches as you type, which may incur a cost. Implies --no-history-search due to "
            "conflicting keybinds, see prompt_toolkit for more details."
        )
    )
    parser.add_argument(
        "--no-history-search",
        dest="history_search",
        action="store_false",
        help=(
            "Disable history search, i.e. up and down arrows will no longer look for command "
            "prefixes in your history"
        )
    )
    parser.add_argument(
        "--debug",
        dest="debug",
        action="store_true",
        default=False,
        help="Turn on debug mode, logging information to /tmp/s3_browser.log",
    )
    parser.add_argument("working_dir", nargs="?", type=str, default="/")
    args = parser.parse_args()

    if args.debug:
        configure_debug_logging()
        logger.info("Starting s3 browser in debug mode")
    else:
        logging.disable(logging.CRITICAL)

    ps1 = Ps1(
        style=ps1_utils.read_style(args.prompt_style),
        path_format=PathFormat[args.prompt_path_format],
    )

    Cli(
        endpoint=args.endpoint,
        working_dir=args.working_dir,
        ps1=ps1,
        history_file=args.history_file,
        bookmark_file=args.bookmark_file,
        history_search=args.history_search,
        complete_while_typing=args.complete_while_typing,
    ).read_loop()


if __name__ == "__main__":
    main()
