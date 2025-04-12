import pytest

from s3_browser.tokeniser import RawString as S, render, Token as T, tokenise, TokeniserException


@pytest.mark.parametrize(
    "input,expected",
    [
        ("literal string ok", [S("literal string ok")]),
        ("   whitespacey   ", [S("   whitespacey   ")]),
        (r"\\\\", [S(r"\\\\")]),
        (r"escaped \$ \$dollar \$signs \$\$", [S("escaped $ $dollar $signs $$")]),
        ("$var$variable$foo", [T("var"), T("variable"), T("foo")]),
        ("$var $variable $foo", [T("var"), S(" "), T("variable"), S(" "), T("foo")]),
        (
            "${brace yourself} winter is coming",
            [T("brace yourself"), S(" winter is coming")],
        ),
        (
            "${$$$inside all is literal$$$}${}",
            [T("$$$inside all is literal$$$"), T("")],
        ),
        ("end on a $", [S("end on a ")]),
    ]
)
def test_tokeniser(input, expected):
    """Test that the tokeniser works for various variable combinations"""
    actual = tokenise(input)

    assert actual == expected


def test_tokeniser_failures():
    """Test that the tokeniser fails for malformed variables"""
    with pytest.raises(TokeniserException):
        tokenise("${wut")


def test_render():
    """Test that tokens can be correctly rendered back into a string"""
    context = {"foo": "hodor", "bar": "arya", "baz": "bran"}

    tests = (
        ([T("foo"), S(" hodor "), T("foo")], "hodor hodor hodor"),
        ([S("simple string")], "simple string"),
        ([S(r"\\\\\\")], r"\\\\\\"),
        ([T("bar"), S("'s brother is "), T("baz")], "arya's brother is bran"),
    )

    for t in tests:
        assert render(t[0], context) == t[1]


def test_render_unknown_token():
    """Test that rendering fails for unknown tokens"""
    with pytest.raises(TokeniserException):
        render([T("foo")], {"bar": "baz"})
