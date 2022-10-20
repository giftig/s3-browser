import shutil


# TODO: This could probably be a couple of hundred content types
_SAFE_CONTENT_TYPE_PREFIXES = [
    'application/json',
    'application/xml',
    'application/yaml',
    'text/'
]


def _is_safe_content_type(ct):
    """Compare content type to the list of (likely) safe prefixes"""
    if not ct:
        return False

    for prefix in _SAFE_CONTENT_TYPE_PREFIXES:
        if ct.startswith(prefix):
            return True

    return False


def print_grid(data):
    """
    Print a list of strings in a grid according to the terminal size
    """
    largest = 0
    for e in data:
        largest = max(len(e), largest)

    # Add spacing
    largest += 1

    w = shutil.get_terminal_size().columns
    num_cols = int(w / largest)

    # Give up if we can't fit the data into columns anyway
    if num_cols <= 1:
        for e in data:
            print(e)

        return

    # Pad the strings to all be the same length, and divide into columns
    padded = [e.ljust(largest) for e in data]
    col_size = int(len(data) / num_cols)
    groups = [col_size] * num_cols

    # Account for remainder: first x columns need to be longer
    for i in range(len(data) % num_cols):
        groups[i] += 1

    output = [''] * groups[0]
    i = 0
    for g in groups:
        for j in range(g):
            output[j] += padded[i]
            i += 1

    for line in output:
        print(line)


def print_dict(data, indent_level=0):
    """Pretty-print a dict full of key-value metadata pairs"""
    indent = '  ' * indent_level

    def _format_key(k):
        return '{}{}{: <40}{}'.format(
            indent, '\x1b[36m', k + ':', '\x1b[0m'
        )

    for k, v in sorted(data.items()):
        if not isinstance(v, dict):
            print('{}{}'.format(_format_key(k), v))
        else:
            print(_format_key(k))
            print_dict(v, indent_level=indent_level + 1)


def pretty_size(n):
    """
    Convert a size in bytes to a human-readable string, rounded to nearest
    whole number of suitable units (B, KB, MB, GB or TB)
    """
    size = int(n)
    shortened = None

    for suffix in ('B', 'KB', 'MB', 'GB', 'TB'):
        if size <= 1023 or suffix == 'TB':
            shortened = '{} {}'.format(round(size), suffix)
            break

        size /= 1024

    return shortened


def strip_s3_metadata(data):
    """Strip s3 head_object metadata down to the useful stuff"""
    metadata = data.get('Metadata', {})
    http_head = data.get('ResponseMetadata', {}).get('HTTPHeaders', {})

    content_length = int(http_head.get('content-length') or 0)
    pretty_len = pretty_size(content_length)
    if pretty_len:
        content_length = '{} ({} bytes)'.format(pretty_len, content_length)

    return {
        'Content-Length': content_length,
        'Content-Type': http_head.get('content-type'),
        'Last-Modified': http_head.get('last-modified'),
        'Metadata': metadata
    }


def print_object(obj):
    """
    Safely print a data stream representing an S3 object

    Refuses to print binary data, allowing only text/* content types along with
    some typical non-binary application/* content types such as JSON and XML

    Currently assumes UTF-8 encoding; a future iteration may try to interpret
    the encoding from the content-type header if provided.
    """
    metadata = strip_s3_metadata(obj)
    content_type = metadata.get('Content-Type')

    if not _is_safe_content_type(content_type):
        raise ValueError(
            'Refusing to print unsafe content type "{}"'.format(content_type)
        )

    with obj['Body'] as c:
        print(c.read().decode('utf-8'), end='')
