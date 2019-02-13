import os


class S3Path(object):
    """
    Represents a combination of bucket and absolute path within that bucket.

    Intended to be used to track an s3 location being visited or checked.
    """
    def __init__(self, bucket, path):
        self.bucket = bucket
        self.path = os.path.realpath('/{}'.format(path))[1:] if path else None
        self.name = self.path.split('/')[-1] or None if self.path else None

    @staticmethod
    def from_path(path):
        stripped = path.strip('/')
        if not stripped:
            return S3Path(None, None)

        comp = stripped.split('/')
        return S3Path(comp[0], '/'.join(comp[1:]))

    @property
    def short_format(self):
        if not self.bucket:
            return '/'

        if self.path and '/' in self.path:
            return '{}/…/{}'.format(self.bucket, self.name)

        return str(self)

    def __str__(self):
        if not self.bucket:
            return '/'

        return '{}/{}'.format(self.bucket or '', self.path or '')


class S3Prefix(object):
    """
    Simple representation of an S3 prefix and associated metadata

    Note that the prefix provided is arbitrary and not necessarily the full,
    absolute prefix to the destination; it is a wrapper around a prefix result
    and is only useful in the context of a particular query
    """
    def __init__(self, prefix):
        self.prefix = prefix

    def is_prefix(self):
        return True

    def is_key(self):
        return False

    def __str__(self):
        return self.prefix


class S3Key(object):
    """
    Representation of an S3 key and associated metadata

    Note that the key provided is arbitrary and not necessarily the full key;
    it is a wrapper around a key result and is only useful in the context of
    a particular query
    """
    def __init__(self, key, updated_on=None):
        self.key = key
        self.updated_on = updated_on

    def is_prefix(self):
        return False

    def is_key(self):
        return True

    def __str__(self):
        return self.key
