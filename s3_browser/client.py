import boto3
import logging

from s3_browser import paths

logger = logging.getLogger(__name__)


class S3Client(object):
    """
    Encapsulates all the functionality required of the s3 browser, wrapping
    the boto s3 client and adding memoisation and a more concise and path-like
    API
    """
    def __init__(self, debug=False):
        self.boto = boto3.client('s3')
        self.path_cache = {}

    def clear_cache(self):
        size = len(self.path_cache)
        self.path_cache = {}
        return size

    def ls(self, path, path_fragment=False):
        """
        Lists files directly under the given s3 path

        :type path: s3_browser.paths.S3Path
        """
        logger.debug('ls called: %s, %s', path, path_fragment)
        cache_key = (str(path), path_fragment)
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

    def is_path(self, path):
        # TODO: Do this with head_object instead?
        return bool(self.ls(path))
