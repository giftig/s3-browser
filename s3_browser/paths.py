import os


class S3Path(object):
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
