import pytest

from s3_browser.paths import S3Bucket, S3Key, S3Path, S3Prefix


def _test_s3_object_api(obj):
    """
    Check that the given object satisfies the s3 object API

    It must have all the common properties required by the CLI to render
    it in a few ways, and it must render without error both with and
    without a bookmark annotation declared
    """

    def basic_checks():
        assert obj.is_key is not None
        assert obj.full_details is not None
        assert obj.path_string is not None

    basic_checks()
    obj.bookmark = "my_bookmark"
    basic_checks()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", S3Path(None, None)),
        ("/", S3Path(None, None)),
        ("a/b/c/d/e/f/g", S3Path("a", "b/c/d/e/f/g")),
        ("/hodor-hodor", S3Path("hodor-hodor", None)),
        ("s3://hodor-hodor", S3Path("hodor-hodor", None)),
        (
            "s3://hodorhodor/hodor/hodor/hodor.txt",
            S3Path("hodorhodor", "hodor/hodor/hodor.txt"),
        ),
    ]
)
def test_s3_path_from_path_string(value, expected):
    """S3Path should be created properly from various path strings"""
    assert S3Path.from_path(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/", "/"),
        ("a/b/c/d/e/f/g", "a/…/g"),
        (
            "something-pretty-long/middle/end-of-long-thing",
            "something-pretty-long/…/end-of-long-thing",  # TODO: improve?
        ),
        ("foo/bar", "foo/bar"),
    ]
)
def test_s3_path_short_format(value, expected):
    """S3Path should render a concise format for ease of use in prompts"""
    assert S3Path.from_path(value).short_format == expected


def test_s3_bucket_api():
    """S3Bucket should support the defined S3 object API"""
    bucket = S3Bucket("westeros")

    _test_s3_object_api(bucket)
    assert bucket.is_key is False


def test_s3_prefix_api():
    """S3Prefix should support the defined S3 object API"""
    prefix = S3Prefix("winterfell/stark")

    _test_s3_object_api(prefix)
    assert prefix.is_key is False


def test_s3_key_api():
    """S3Key should support the defined S3 object API"""
    key = S3Key("winterfell/stark/arya.json")

    _test_s3_object_api(key)
    assert key.is_key is True
