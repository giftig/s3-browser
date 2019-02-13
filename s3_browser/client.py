import boto3

from s3_browser import paths


class S3Client(object):
    """
    Encapsulates all the functionality required of the s3 browser, wrapping
    the boto s3 client and adding memoisation and a more concise and path-like
    API
    """
    def __init__(self, debug=False):
        self.boto = boto3.client('s3')
        self.path_cache = {}

    # FIXME: rm
    def _debug(self, msg):
        with open('/tmp/s3-client-debug.log', 'a') as f:
            f.write(msg + '\n')

    def ls(self, path, path_fragment=False):
        """
        Lists files directly under the given s3 path

        :type path: s3_browser.paths.S3Path
        """
        self._debug('ls called: {}, {}'.format(path, path_fragment))
        cache_key = (str(path), path_fragment)
        cached = self.path_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            if not path.bucket:
                return [
                    paths.S3Bucket(b['Name'])
                    for b in self.boto.list_buckets().get('Buckets', [])
                ]

            if not path_fragment:
                search_path = path.path + '/' if path.path else ''
            else:
                search_path = path.path or ''

            last_slash = search_path.rfind('/')
            search_len = last_slash + 1 if last_slash != -1 else 0

            self._debug(
                'Listing objects. full path: "{}", search_path: "{}"'.format(
                    path, search_path
                )
            )
            # TODO: [ab]use pagination (see boto/boto3#134)
            res = self.boto.list_objects(
                Bucket=path.bucket,
                Prefix=search_path,
                Delimiter='/'
            )
            # TODO: Mark prefixes vs keys, and store modified date with key
            prefixes = [
                paths.S3Prefix(r['Prefix'][search_len:])
                for r in res.get('CommonPrefixes', [])
            ]
            keys = [
                paths.S3Key(r['Key'][search_len:], r['LastModified'])
                for r in res.get('Contents', [])
                if r['Key'] != search_path
            ]
            self._debug(
                'Results: {} -- {}'.format(prefixes, keys)
            )
            return prefixes + keys

        res = _fetch()
        if res:
            self.path_cache[cache_key] = res

        return res

    def is_path(self, path):
        return bool(self.ls(path))
