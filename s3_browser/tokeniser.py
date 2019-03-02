
def tokenise(s):
    """Breaks a string down into variable tokens"""
    acc = []
    curr = ''
    is_var = False
    is_braced = False
    is_escaped = False

    for c in s:
        if not is_var:
            if c == '\\' and not is_escaped:
                is_escaped = True
                continue

            if c == '$' and not is_escaped:
                is_var = True

                if curr != '':
                    acc.append(RawString(curr))

                curr = ''
                continue

            if is_escaped and c != '$':
                curr += '\\'

            is_escaped = False
            curr += c
            continue

        if c == '{' and curr == '':
            is_braced = True
            continue

        if is_braced:
            if c == '}':
                acc.append(Token(curr))
                is_var = False
                is_braced = False
                curr = ''
                continue

            curr += c
            continue

        if not str.isalnum(c) and c != '_':
            acc.append(Token(curr))
            is_var = False
            is_braced = False
            curr = ''

            if c == '\\':
                is_escaped = True
            elif c == '$':
                is_var = True
            else:
                curr = c
            continue

        curr += c

    # Handle final token
    if is_var and is_braced:
        raise TokeniserException('Unclosed braced variable')

    if curr != '':
        acc.append(Token(curr) if is_var else RawString(curr))

    return acc


def render(tokens, context):
    """
    Render a string of tokens and raw strings into a completed string

    :param tokens: A list of `Token` and `RawString`s as provided by `tokenise`
    """
    acc = ''
    for t in tokens:
        v = getattr(t, 'value', None)
        if v:
            acc += v
            continue

        if t.name not in context:
            raise TokeniserException('Unknown token \'{}\''.format(t.name))

        acc += context[t.name]

    return acc


class Token(object):
    def __init__(self, name):
        self.name = name


class RawString(object):
    def __init__(self, value):
        self.value = value


class TokeniserException(Exception):
    def __init__(self, msg):
        super(TokeniserException, self).__init__(msg)
