import unittest

from s3_browser.tokeniser import RawString as S
from s3_browser.tokeniser import Token as T
from s3_browser.tokeniser import TokeniserException
from s3_browser.tokeniser import render
from s3_browser.tokeniser import tokenise


class TokeniserTest(unittest.TestCase):
    def test_tokeniser(self):
        """Test that the tokeniser works for various variable combinations"""
        tests = (
            ('literal string ok', [S('literal string ok')]),
            ('   whitespacey   ', [S('   whitespacey   ')]),
            (r'\\\\', [S(r'\\\\')]),
            (
                r'escaped \$ \$dollar \$signs \$\$',
                [S('escaped $ $dollar $signs $$')]
            ),
            (
                '$var$variable$foo',
                [T('var'), T('variable'), T('foo')]
            ),
            (
                '$var $variable $foo',
                [T('var'), S(' '), T('variable'), S(' '), T('foo')]
            ),
            (
                '${brace yourself} winter is coming',
                [T('brace yourself'), S(' winter is coming')]
            ),
            (
                '${$$$inside all is literal$$$}${}',
                [T('$$$inside all is literal$$$'), T('')]
            ),
            ('end on a $', [S('end on a ')])
        )

        for t in tests:
            actual = [e.__dict__ for e in tokenise(t[0])]
            expected = [e.__dict__ for e in t[1]]

            self.assertEqual(actual, expected)

    def test_tokeniser_failures(self):
        """Test that the tokeniser fails for malformed variables"""
        with self.assertRaises(TokeniserException):
            tokenise('${wut')

    def test_render(self):
        """Test that tokens can be correctly rendered back into a string"""
        context = {
            'foo': 'hodor',
            'bar': 'arya',
            'baz': 'bran'
        }

        tests = (
            ([T('foo'), S(' hodor '), T('foo')], 'hodor hodor hodor'),
            ([S('simple string')], 'simple string'),
            ([S(r'\\\\\\')], r'\\\\\\'),
            (
                [T('bar'), S('\'s brother is '), T('baz')],
                'arya\'s brother is bran'
            )
        )

        for t in tests:
            self.assertEquals(render(t[0], context), t[1])

    def test_render_unknown_token(self):
        """Test that rendering fails for unknown tokens"""
        with self.assertRaises(TokeniserException):
            render([T('foo')], {'bar': 'baz'})
