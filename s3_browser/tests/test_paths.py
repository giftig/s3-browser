import unittest

from s3_browser.paths import S3Path


class PathsTest(unittest.TestCase):
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

    def test_short_format(self):
        """S3Path should render a concise format for ease of use in prompts"""
        tests = [
            ('a/b/c/d/e/f/g', 'a/…/g'),
            (
                'something-pretty-long/middle/end-of-long-thing',
                'something-pretty-long/…/end-of-long-thing'  # TODO: improve?
            ),
            ('foo/bar', 'foo/bar')
        ]

        for input, expected in tests:
            self.assertEqual(S3Path.from_path(input).short_format, expected)
