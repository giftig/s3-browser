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


class S3Bucket(object):
    """
    Simple representation of a bucket

    Primarily just to match the S3Prefix and S3Key API
    """
    def __init__(self, bucket):
        self.bucket = bucket

    @property
    def full_details(self):
        """
        Just the bucket name, and mention that it's a bucket

        Designed to line up with S3Key's implementation of the same method
        """
        return '{: >19} {}'.format('BUCKET', self.bucket)

    def __str__(self):
        return self.bucket


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

    @property
    def full_details(self):
        """
        Just the prefix content, and mention that it's a prefix

        Designed to line up with S3Key's implementation of the same method
        """
        return '{: >19} {}'.format('PREFIX', self.prefix)

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
        self.updated_on = (
            updated_on.strftime('%Y-%m-%d %H:%M:%S') if updated_on else None
        )

    def is_prefix(self):
        return False

    def is_key(self):
        return True

    @property
    def full_details(self):
        return '{updated_on: >19} {key}'.format(
            updated_on=self.updated_on,
            key=self.key
        )

    def __str__(self):
        return self.key