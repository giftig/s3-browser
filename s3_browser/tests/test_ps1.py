import pytest
from prompt_toolkit.styles import Style

from s3_browser.ps1 import read_style


@pytest.mark.parametrize(
    ("s", "expected"),
    [
        ("foo:ansired bar:ansiwhite", Style.from_dict({"foo": "ansired", "bar": "ansiwhite"})),
        ("", Style.from_dict({})),
    ],
)
def test_read_style(s: str, expected: Style) -> None:
    actual = read_style(s)
    assert actual.__dict__ == expected.__dict__
