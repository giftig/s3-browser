import boto3
import logging
import os

import magic

from s3_browser import paths

logger = logging.getLogger(__name__)


class S3Client(object):
    """
    Encapsulates all the functionality required of the s3 browser, wrapping
    the boto s3 client and adding memoisation and a more concise and path-like
    API
    """
    def __init__(self, endpoint=None):
        self.boto = boto3.client('s3', endpoint_url=endpoint)
        self.path_cache = {}
        self.mime_typer = magic.Magic(mime=True)

    def clear_cache(self):
        size = len(self.path_cache)
        self.path_cache = {}
        return size

    def invalidate_cache(self, path):
        """
        Invalidate cache entries for a particular S3Path

        Because prefixes (pseudo-dirs) aren't actually "real", deleting all
        keys under a prefix causes that prefix to also cease to exist. That
        means we have to recursively invalidate the cache for every path
        prefix in the key in case some of those prefixes are now empty.

        i.e. for key s3://bucketname/foo/bar/baz/data.xml we'd have to refresh:
            - s3://bucketname/foo/bar/baz/data.xml
            - s3://bucketname/foo/bar/baz
            - s3://bucketname/foo/bar
            - s3://bucketname/foo
            - s3://bucketname/
        """
        cache_keys = []
        next_path = path

        while True:
            cache_keys.extend(
                [(next_path.canonical, True), (next_path.canonical, False)]
            )

            next = os.path.dirname(next_path.path)
            if next == next_path.path:
                break

            next_path.path = next

        logger.debug('Clearing cache keys: %s', cache_keys)
        logger.debug('Cache keys present: %s', self.path_cache.keys())
        for k in cache_keys:
            self.path_cache.pop(k, None)

    def ls(self, path, path_fragment=False):
        """
        Lists files directly under the given s3 path

        :type path: s3_browser.paths.S3Path
        """
        logger.debug('ls called: %s, %s', path, path_fragment)
        cache_key = (path.canonical, path_fragment)
        cached = self.path_cache.get(cache_key)

        if cached is not None:
            logger.debug('cache hit')
            return cached

        logger.debug('cache miss')

        def _fetch():
            if not path.bucket or not path.path and path_fragment:
                logger.debug('Listing buckets')
                res = [
                    paths.S3Bucket(b['Name'])
                    for b in self.boto.list_buckets().get('Buckets', [])
                ]
                if path.bucket:
                    logger.debug('Trimming bucket list: "%s"', path.bucket)
                    res = [r for r in res if r.bucket.startswith(path.bucket)]

                logger.debug('Found buckets: %s', [str(r) for r in res])
                return res

            if not path_fragment:
                search_path = path.path + '/' if path.path else ''
            else:
                search_path = path.path or ''

            last_slash = search_path.rfind('/')
            search_len = last_slash + 1 if last_slash != -1 else 0

            logger.debug(
                'Listing objects. full path: "%s", search_path: "%s"',
                path, search_path
            )
            # TODO: [ab]use pagination (see boto/boto3#134)
            res = self.boto.list_objects(
                Bucket=path.bucket,
                Prefix=search_path,
                Delimiter='/'
            )
            prefixes = [
                paths.S3Prefix(r['Prefix'][search_len:])
                for r in res.get('CommonPrefixes', [])
            ]
            keys = [
                paths.S3Key(r['Key'][search_len:], r['LastModified'])
                for r in res.get('Contents', [])
                if r['Key'] != search_path
            ]
            logger.debug(
                'results: prefixes: %s -- keys: %s',
                [str(p) for p in prefixes], [str(k) for k in keys]
            )
            return prefixes + keys

        res = _fetch()
        if res:
            self.path_cache[cache_key] = res

        return res

    def head(self, path):
        """Get head metadata for a path"""
        res = None
        if not path.path:
            res = self.boto.head_bucket(Bucket=path.bucket)
        else:
            res = self.boto.head_object(Bucket=path.bucket, Key=path.path)

        logger.debug('Head %s: response = %s', path, res)
        return res

    def rm(self, path):
        """Delete a key"""
        self.boto.delete_object(Bucket=path.bucket, Key=path.path)
        self.invalidate_cache(path)

    def put(self, f, dest):
        """Write a file to an S3Path"""
        content_type = self.mime_typer.from_file(f)
        logger.debug(
            'Uploading %s to %s with content-type %s', f, dest, content_type
        )

        self.boto.upload_file(
            Filename=f,
            Bucket=dest.bucket,
            Key=dest.path,
            ExtraArgs={'ContentType': content_type}
        )

        self.invalidate_cache(dest)

    def get(self, key, dest):
        """Download a key (S3Path) to a local file"""
        logger.debug('Downloading %s to %s', key, dest)
        self.boto.download_file(
            Bucket=key.bucket,
            Key=key.path,
            Filename=dest
        )

    def get_object(self, path):
        """Get a full object at a path"""
        return self.boto.get_object(Bucket=path.bucket, Key=path.path)

    def is_path(self, path):
        # TODO: Do this with head_object instead?
        return bool(self.ls(path))
