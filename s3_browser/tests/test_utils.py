import datetime
import unittest

from s3_browser import utils


class UtilsTest(unittest.TestCase):
    def test_pretty_size(self):
        """Test that the pretty-size util approximates filesizes correctly"""
        cases = [
            (0, "0 B"),
            (233, "233 B"),
            (1023, "1023 B"),
            (1024, "1 KB"),
            (1024**2 - 1, "1 MB"),
            (12345678, "12 MB"),
            (1024**3 + 100, "1 GB"),
            (1024**4 + 1, "1 TB"),
            (1024**5 * 2, "2048 TB"),
        ]

        for v, expected in cases:
            actual = utils.pretty_size(v)
            assert actual == expected

    def test_strip_s3_metadata(self):
        """Test that full s3 metadata is correctly stripped to essentials"""

        # Anonymised sample response from a head_object call with boto3
        data = {
            "ResponseMetadata": {
                "RequestId": "XXXXXXXXXXXXXXXX",
                "HostId": "hhhhhhhhhhhhhhhhhhhhhhhhhh",
                "HTTPStatusCode": 200,
                "HTTPHeaders": {
                    "x-amz-id-2": "ababababababababaabababababab",
                    "x-amz-request-id": "XXXXXXXXXXXXXXXX",
                    "date": "Wed, 20 Oct 2021 00:00:00 GMT",
                    "last-modified": "Fri, 22 May 2021 00:00:00 GMT",
                    "etag": '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
                    "accept-ranges": "bytes",
                    "content-type": "application/json",
                    "server": "AmazonS3",
                    "content-length": "13337",
                },
                "RetryAttempts": 0,
            },
            "AcceptRanges": "bytes",
            "LastModified": datetime.datetime(2021, 5, 22, 0, 0, 0, tzinfo=datetime.UTC),
            "ContentLength": 13409,
            "ETag": '"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"',
            "ContentType": "application/x-tar",
            "Metadata": {},
        }

        expected = {
            "Content-Length": "13 KB (13337 bytes)",
            "Content-Type": "application/json",
            "Last-Modified": "Fri, 22 May 2021 00:00:00 GMT",
            "Metadata": {},
        }

        actual = utils.strip_s3_metadata(data)

        assert actual == expected
