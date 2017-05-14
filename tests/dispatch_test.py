"""Tests for traversing objects and dispatching requests to them."""
# pylint: disable=missing-docstring,no-self-use,too-few-public-methods
# pylint: disable=invalid-name

import unittest

from werkzeug.exceptions import BadRequest

from pystapler.dispatch import StaplerRoot, traversable, default
from pystapler.response import plaintext

class Root(StaplerRoot):
    @traversable
    def spam(self):
        return Renderable('spam')

    @traversable('hovercraft')
    def eggs(self):
        return Renderable('eggs')

    @traversable
    def parrot(self):
        raise BadRequest('resting!')

    def xyzzy(self):
        raise AssertionError('should never happen')

    @traversable
    def required_arg(self, spam):
        # pylint: disable=unused-argument
        raise AssertionError('should never happen')

    @traversable
    def default_args(self, spam='spam!'):
        return Renderable(spam)

    @traversable
    def keyword_args(self, **kwargs):
        return Renderable(repr(kwargs.keys()))


class Renderable(object):
    def __init__(self, text):
        self.text = text

    @default
    @plaintext
    def render(self):
        return self.text


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.client = Root().test_client()

    def test_spam(self):
        """The /spam URL should map to the spam() method."""
        response = self.client.get('/spam')
        self.assertEquals(200, response.status_code)
        self.assertEquals(b'spam', response.data)

    def test_eggs(self):
        """The eggs method is traversable under a different name, so 404."""
        response = self.client.get('/eggs')
        self.assertEquals(404, response.status_code)

    def test_hovercraft(self):
        """The /hovercraft URL should map to the eggs() method."""
        response = self.client.get('/hovercraft')
        self.assertEquals(200, response.status_code)
        self.assertEquals(b'eggs', response.data)

    def test_parrot(self):
        """The /parrot URL should result in an exception."""
        response = self.client.get('/parrot')
        self.assertEquals(400, response.status_code)

    def test_xyzzy(self):
        """The xyzzy method is not traversable and should result in a 404."""
        response = self.client.get('/xyzzy')
        self.assertEquals(404, response.status_code)

    def test_required_arg(self):
        """The /required_arg URL should fail without spam provided."""
        response = self.client.get('/required_arg')
        self.assertEquals(400, response.status_code)

    def test_default_args(self):
        """The /default_args URL should work without spam provided."""
        response = self.client.get('/default_args')
        self.assertEquals(200, response.status_code)
        self.assertEquals(b'spam!', response.data)

    def test_keyword_args(self):
        """The /keyword_args URL should get the whole request_params dict."""
        response = self.client.get('/keyword_args')
        self.assertEquals(200, response.status_code)
        self.assertIn(b"'request'", response.data)


# vim: et ts=4
