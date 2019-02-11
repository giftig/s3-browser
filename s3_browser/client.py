import boto3


class S3Client(object):
    """
    Encapsulates all the functionality required of the s3 browser, wrapping
    the boto s3 client and adding memoisation and a more concise and path-like
    API
    """
    def __init__(self):
        self.boto = boto3.client('s3')
        self.path_cache = {}

    def ls(self, path, path_fragment=False):
        """
        Lists files directly under the given s3 path

        :type path: s3_browser.paths.S3Path
        """
        p = str(path)
        cached = self.path_cache.get(p)
        if cached is not None:
            return cached

        def _fetch():
            if not path.bucket:
                return [
                    b['Name']
                    for b in self.boto.list_buckets().get('Buckets', [])
                ]

            if not path_fragment:
                search_path = path.path + '/' if path.path else ''
            else:
                search_path = path.path or ''

            last_slash = search_path.rfind('/')
            search_len = last_slash + 1 if last_slash != -1 else 0

            # TODO: [ab]use pagination (see boto/boto3#134)
            res = self.boto.list_objects(
                Bucket=path.bucket,
                Prefix=search_path,
                Delimiter='/'
            )
            # TODO: Mark prefixes vs keys, and store modified date with key
            prefixes = [
                r['Prefix'][search_len:]
                for r in res.get('CommonPrefixes', [])
            ]
            keys = [
                r['Key'] for r in res.get('Contents', [])
                if r['Key'] != search_path
            ]
            return prefixes + keys

        res = _fetch()
        if res:
            self.path_cache[p] = res

        return res

    def is_path(self, path):
        return bool(self.ls(path))
