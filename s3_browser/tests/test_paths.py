import unittest

from s3_browser.paths import S3Bucket
from s3_browser.paths import S3Key
from s3_browser.paths import S3Path
from s3_browser.paths import S3Prefix


class PathsTest(unittest.TestCase):
    def _test_s3_object_api(self, obj):
        """
        Check that the given object satisfies the s3 object API

        It must have all the common properties required by the CLI to render
        it in a few ways, and it must render without error both with and
        without a bookmark annotation declared
        """
        def basic_checks():
            self.assertIsNotNone(obj.is_key)
            self.assertIsNotNone(obj.full_details)
            self.assertIsNotNone(obj.path_string)

        basic_checks()
        obj.bookmark = 'my_bookmark'
        basic_checks()

    def test_s3_path_from_path_string(self):
        """S3Path should be created properly from various path strings"""
        tests = [
            ('', S3Path(None, None)),
            ('/', S3Path(None, None)),
            ('a/b/c/d/e/f/g', S3Path('a', 'b/c/d/e/f/g')),
            ('/hodor-hodor', S3Path('hodor-hodor', None)),
            ('s3://hodor-hodor', S3Path('hodor-hodor', None)),
            (
                's3://hodorhodor/hodor/hodor/hodor.txt',
                S3Path('hodorhodor', 'hodor/hodor/hodor.txt')
            )
        ]

        for input, expected in tests:
            self.assertEqual(S3Path.from_path(input), expected)

    def test_s3_path_short_format(self):
        """S3Path should render a concise format for ease of use in prompts"""
        tests = [
            ('/', '/'),
            ('a/b/c/d/e/f/g', 'a/…/g'),
            (
                'something-pretty-long/middle/end-of-long-thing',
                'something-pretty-long/…/end-of-long-thing'  # TODO: improve?
            ),
            ('foo/bar', 'foo/bar')
        ]

        for input, expected in tests:
            self.assertEqual(S3Path.from_path(input).short_format, expected)

    def test_s3_bucket_api(self):
        """S3Bucket should support the defined S3 object API"""
        bucket = S3Bucket('westeros')

        self._test_s3_object_api(bucket)
        self.assertFalse(bucket.is_key)

    def test_s3_prefix_api(self):
        """S3Prefix should support the defined S3 object API"""
        prefix = S3Prefix('winterfell/stark')

        self._test_s3_object_api(prefix)
        self.assertFalse(prefix.is_key)

    def test_s3_key_api(self):
        """S3Key should support the defined S3 object API"""
        key = S3Key('winterfell/stark/arya.json')

        self._test_s3_object_api(key)
        self.assertTrue(key.is_key)
