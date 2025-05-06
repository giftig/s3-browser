from unittest import mock

import pytest

from s3_browser import ps1 as ps1_utils
from s3_browser.cli import Cli, PathFormat, Ps1
from s3_browser.paths import S3Path


@pytest.mark.parametrize(
    ("path", "working_dir", "expected"),
    [
        # Absolute paths
        ("/bucket", "/", S3Path(bucket="bucket", path=None)),
        ("/bucket", "/bucket/", S3Path(bucket="bucket", path=None)),
        ("/bucket", "/bucket/a/b/c", S3Path(bucket="bucket", path=None)),
        ("/bucket/a/b/c", "/", S3Path(bucket="bucket", path="a/b/c")),
        ("/bucket/a/b/c", "/bucket/", S3Path(bucket="bucket", path="a/b/c")),
        ("/bucket/a/b/c", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c")),
        # Absolute paths with protocol
        ("s3:///bucket", "/", S3Path(bucket="bucket", path=None)),
        ("s3://bucket", "/", S3Path(bucket="bucket", path=None)),
        ("s3:///bucket", "/bucket", S3Path(bucket="bucket", path=None)),
        ("s3://bucket", "/bucket/a/b/c", S3Path(bucket="bucket", path=None)),
        ("s3:///bucket/a/b/c", "/bucket", S3Path(bucket="bucket", path="a/b/c")),
        ("s3://bucket/a/b/c", "/bucket", S3Path(bucket="bucket", path="a/b/c")),
        ("s3:///bucket/a/b/c", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c")),
        ("s3://bucket/a/b/c", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c")),
        # Absolute paths with tildes (relative to bucket)
        ("~", "/", S3Path(bucket=None, path=None)),
        ("~", "/bucket/", S3Path(bucket="bucket", path=None)),
        ("~", "/bucket/a/b/c", S3Path(bucket="bucket", path=None)),
        ("~/", "/", S3Path(bucket=None, path=None)),
        ("~/", "/bucket/", S3Path(bucket="bucket", path=None)),
        ("~/", "/bucket/a/b/c", S3Path(bucket="bucket", path=None)),
        # Relative paths
        ("bucket", "/", S3Path(bucket="bucket", path=None)),
        ("bucket/a/b", "/", S3Path(bucket="bucket", path="a/b")),
        ("a/b/c", "/bucket", S3Path(bucket="bucket", path="a/b/c")),
        ("c/d", "/bucket/a/b", S3Path(bucket="bucket", path="a/b/c/d")),
        # Relative dotted paths
        (".", "/bucket/", S3Path(bucket="bucket", path=None)),
        (".", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c")),
        (".", "/bucket/a/b/c/", S3Path(bucket="bucket", path="a/b/c")),
        ("..", "/bucket/", S3Path(bucket=None, path=None)),
        ("..", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b")),
        # Complex dotted paths
        ("../c", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c")),
        ("../../b", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b")),
        ("../../././b", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b")),
        ("d/././e", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c/d/e")),
        ("d/../d", "/bucket/a/b/c", S3Path(bucket="bucket", path="a/b/c/d")),
    ],
)
def test_normalise_path(path: str, working_dir: str, expected: S3Path):
    s3_mock = mock.MagicMock()

    cli = Cli(
        s3_client=s3_mock,
        working_dir=working_dir,
        ps1=Ps1(
            style=ps1_utils.read_style("basic:ansiwhite"),
            path_format=PathFormat.short,
        ),
        history_file=None,
        bookmark_file=None,
        history_search=True,
        complete_while_typing=False,
    )

    actual = cli.normalise_path(path)

    assert expected == actual
