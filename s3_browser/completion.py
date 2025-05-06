import logging
import os
import shlex
from collections.abc import Iterable
from typing import ClassVar

from botocore.exceptions import ClientError
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

logger = logging.getLogger(__name__)

QUOTES: set[str] = {"'", '"'}


class CliCompleter(Completer):
    """Tab-complete functionality for the cli, powered by prompt_toolkit"""

    EXPECTS_KEY: ClassVar[set[str]] = {"cat", "file", "head", "rm"}
    EXPECTS_S3_PATH: ClassVar[set[str]] = {"cd", "ls", "ll"}.union(EXPECTS_KEY)

    def __init__(self, cli):
        self.cli = cli
        self.s3_client = self.cli.client

    def _split_cmd(self, buf: str) -> list[str]:
        """
        Attempt to safely split an incomplete command in a shell-safe way.
        Shlex can get us most of the way there, but we have to deal with
        possibly partially-quoted incomplete strings by adding the missing
        quote before parsing where appropriate.
        """
        # Single empty command to complete, if we haven't started typing at all
        if not buf:
            return [""]

        # FIXME: Can we do this analysis more intelligently using shlex.shlex
        # and scanning / tokenising directly?

        # If the command is already safe to parse by shlex, we're done
        try:
            result = shlex.split(buf)

            # Deal with the case where we end with a space, and will want to
            # complete the next argument with an empty string input
            if buf.endswith(" "):
                result.append("")

            return result
        except ValueError as e:
            logger.debug(
                "Error while splitting with shlex: %s, trying with ending double-quote",
                e,
            )

        # Try with an ending double quote to complete an unclosed double-quoted
        # string. We could attempt to figure out whether the unclosed string
        # was double- or single-quoted and use the correct one, but there are
        # several edge cases like ["this isn't easy] which would complicate
        # that approach. Trying one then the other lets us use shlex's more
        # intelligent parsing to handle those cases
        try:
            return shlex.split(buf + '"')
        except ValueError as e:
            logger.debug(
                "Still failed splitting with shlex: %s, trying with ending single-quote",
                e,
            )

        try:
            return shlex.split(buf + "'")
        except ValueError as e:
            logger.error("Failed last attempt at splitting with shlex: %s", e)
            raise

    @staticmethod
    def _get_path_start_pos(path: str, doc: Document) -> int:
        """
        Attempt to calculate the correct start position for the given "partial" path passed to
        subcommand completers, bearing in mind that partial quotes would have been stripped from
        partial.

        Usually this is back to the last forward slash, but if there was a quote before the partial
        (which we should be able to find in the text from the Document) we should also go back one
        char further.
        """
        offset = 1

        text = doc.current_line_before_cursor

        # Strip a closing quote if there is one, and account for it in the offset
        if text and text[-1] in QUOTES:
            text = text[:-1]
            offset -= 1

        # Now strip the quote before our path if there is one, and account for it again
        if text.endswith(path) and text[-len(path) - 1] in QUOTES:
            offset -= 1

        slash_index = path.rfind("/")

        return slash_index - len(path) + offset

    def complete_command(self, cmd, doc: Document) -> Iterable[Completion]:
        """
        Complete a command if we're just starting to write a command (i.e.
        no spaces in the command yet)
        """
        return [
            Completion(c, start_position=-doc.cursor_position)
            for c in self.cli.RECOGNISED_COMMANDS
            if c.startswith(cmd)
        ]

    def complete_s3_path(
        self, partial: str, doc: Document, allow_keys: bool = False
    ) -> Iterable[Completion]:
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
        # ~ is a special case referring to the root of the current bucket,
        # so just add a forward slash to continue the path from that root
        if partial == "~":
            return ["~/"]

        special_results = []
        search_path = None
        basename = os.path.basename(partial)

        # If our path ends with . or .., we might be looking for keys prefixed
        # with those strings, or expect to complete as ./ or ../ with the
        # relative meanings of those terms. In which case, we need to look for
        # files with that prefix in the directory above them, rather than
        # following the relative paths, as well as suggesting ./ or ../
        if basename in {".", ".."} and self.cli.current_path.bucket is not None:
            special_results.append(basename + "/")
            search_path = self.cli.normalise_path(os.path.dirname(partial))
            search_path.path = os.path.join(search_path.path or "", basename)
        else:
            search_path = self.cli.normalise_path(partial)

        try:
            results = self.s3_client.ls(
                search_path,
                path_fragment=bool(not partial.endswith("/") and partial),
            )
        except ClientError:
            results = []
            logger.exception("Unexpected error while completing s3 path")

        hits = [
            shlex.quote(r.path_string.lstrip("/"))
            for r in results if allow_keys or not r.is_key
        ]

        res = special_results + hits
        return [Completion(r, start_position=self._get_path_start_pos(partial, doc)) for r in res]

    def complete_local_path(self, partial: str, doc: Document) -> Iterable[Completion]:
        """
        Autocomplete for an expected local filesystem path
        """
        start_pos = self._get_path_start_pos(partial, doc)

        # Expand users and do nothing further if ~ or ~user is provided alone
        if "~" in partial and "/" not in partial:
            return [Completion(shlex.quote(os.path.expanduser(partial)), start_position=start_pos)]

        partial = os.path.expanduser(partial)

        if os.path.isfile(partial):
            return [Completion(shlex.quote(os.path.basename(partial)), start_position=start_pos)]

        hits = []

        if partial.endswith("/") and os.path.isdir(partial):
            hits = os.listdir(partial)
        else:
            parent = os.path.dirname(partial)
            frag = os.path.basename(partial)

            if not parent or os.path.isdir(parent):
                hits = [h for h in os.listdir(parent or ".") if h.startswith(frag)]

        return [Completion(shlex.quote(hit), start_position=start_pos) for hit in hits]

    def complete_put_get(
        self, words: list[str], doc: Document, s3_first: bool
    ) -> Iterable[Completion]:
        """
        A put operation expects a local path first, followed by an S3 path. A
        get operation expects them the other way round. We can determine which
        one we should be completing by the current argument count, ignoring any
        flags.
        """
        args = [w for w in words[1:] if not w.startswith("-")]
        arg_count = len(args)

        if s3_first and arg_count == 1 or not s3_first and arg_count == 2:
            return self.complete_s3_path(args[-1], doc, allow_keys=True)

        if s3_first and arg_count == 2 or not s3_first and arg_count == 1:
            return self.complete_local_path(args[-1], doc)

        return []

    def complete_bookmark(self, text: str, doc: Document) -> Iterable[Completion]:
        # TODO: Autocomplete $ or ${}
        return []

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        """
        Autocomplete the next word by figuring out the context of what we're
        doing and delegating to the appropriate completion method
        """
        # TODO: Document also supports cursor_position and selection states, so we can do more
        # advanced completion than we could with readline
        words = self._split_cmd(document.text)
        cmd = words[0]

        if len(words) == 1:
            return self.complete_command(cmd, document)

        if cmd == "put":
            return self.complete_put_get(words, document, s3_first=False)

        if cmd == "get":
            return self.complete_put_get(words, document, s3_first=True)

        if cmd in self.EXPECTS_S3_PATH:
            return self.complete_s3_path(words[-1], document, cmd in self.EXPECTS_KEY)

        return []
