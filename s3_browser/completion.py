import logging
import os
import readline
import shlex

logger = logging.getLogger(__name__)


class CliCompleter(object):
    """
    Tab-complete functionality for the cli
    """

    EXPECTS_KEY = {"cat", "file", "head", "rm"}
    EXPECTS_S3_PATH = {"cd", "ls", "ll"}.union(EXPECTS_KEY)

    def __init__(self, cli):
        self.cli = cli
        self.s3_client = self.cli.client

    def _split_cmd(self, buf):
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
                "Error while splitting with shlex: %s, trying with ending "
                "double-quote",
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
                "Still failed splitting with shlex: %s, trying with ending "
                "single-quote",
                e,
            )

        try:
            return shlex.split(buf + "'")
        except ValueError as e:
            logger.error("Failed last attempt at splitting with shlex: %s", e)
            raise

    def complete_command(self, cmd, state):
        """
        Complete a command if we're just starting to write a command (i.e.
        no spaces in the command yet)
        """
        matches = [c for c in self.cli.RECOGNISED_COMMANDS if c.startswith(cmd)]
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
        # ~ is a special case referring to the root of the current bucket,
        # so just add a forward slash to continue the path from that root
        if partial == "~":
            return "~/" if state == 0 else None

        special_results = []
        search_term = None
        basename = os.path.basename(partial)

        # If our path ends with . or .., we might be looking for keys prefixed
        # with those strings, or expect to complete as ./ or ../ with the
        # relative meanings of those terms. In which case, we need to look for
        # files with that prefix in the directory above them, rather than
        # following the relative paths, as well as suggesting ./ or ../
        if basename in {".", ".."}:
            special_results.append(basename + "/")
            search_term = self.cli.normalise_path(os.path.dirname(partial))
            search_term.path = os.path.join(search_term.path, basename)
        else:
            search_term = self.cli.normalise_path(partial)

        hits = [
            shlex.quote(str(r))
            for r in self.s3_client.ls(
                search_term, path_fragment=not partial.endswith("/")
            )
            if allow_keys or not r.is_key
        ]

        res = special_results + hits
        return res[state] if state < len(res) else None

    def complete_local_path(self, partial, state):
        """
        Autocomplete for an expected local filesystem path
        """
        if os.path.isfile(partial):
            return shlex.quote(os.path.basename(partial)) if state == 0 else None

        hits = []

        if partial.endswith("/") and os.path.isdir(partial):
            hits = os.listdir(partial)
        else:
            parent = os.path.dirname(partial)
            frag = os.path.basename(partial)

            if not parent or os.path.isdir(parent):
                hits = [h for h in os.listdir(parent or ".") if h.startswith(frag)]

        return shlex.quote(hits[state]) if state < len(hits) else None

    def complete_put_get(self, words, state, s3_first):
        """
        A put operation expects a local path first, followed by an S3 path. A
        get operation expects them the other way round. We can determine which
        one we should be completing by the current argument count, ignoring any
        flags.
        """
        args = [w for w in words[1:] if not w.startswith("-")]
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

        words = self._split_cmd(buf)
        cmd = words[0]

        if len(words) == 1:
            return self.complete_command(cmd, state)

        if cmd == "put":
            return self.complete_put_get(words, state, s3_first=False)

        if cmd == "get":
            return self.complete_put_get(words, state, s3_first=True)

        if cmd in self.EXPECTS_S3_PATH:
            return self.complete_s3_path(words[-1], state, cmd in self.EXPECTS_KEY)

        return None

    def bind(self):
        readline.set_completer_delims(" \t\n/;")
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self.complete)
