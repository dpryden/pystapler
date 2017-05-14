"""Tests of starting a complete server."""
# pylint: disable=missing-docstring,no-self-use

from contextlib import closing
import multiprocessing
import socket
import time
import unittest

from six.moves.urllib.request import urlopen

from pystapler.dispatch import StaplerRoot, traversable, main
from pystapler.response import plaintext

def _find_unused_port():
    """Returns a port number which is not currently in use."""
    # pylint: disable=no-member
    with closing(socket.socket()) as sock:
        sock.bind(('0.0.0.0', 0))
        return sock.getsockname()[1]


class Root(StaplerRoot):
    @traversable
    @plaintext
    def hello(self, name='world'):
        return 'Hello, {}!'.format(name)


class ServerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _find_unused_port()

        def test_server():
            root = Root()
            root.config.port = cls.port
            root.config.debug = False
            main(root)

        cls.server = multiprocessing.Process(target=test_server)
        cls.server.start()

        # Sleep for a short time to ensure that the server gets a chance to
        # start and open its port before we send requests to it.
        # TODO(dpryden): This should be changed to use a reliable mechanism
        # to detect that the test server has started rather than just blindly
        # waiting for a period of time.
        time.sleep(.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        cls.server.join()

    def execute_get(self, path):
        url = 'http://localhost:{}{}'.format(self.port, path)
        with closing(urlopen(url)) as contents:
            # pylint: disable=no-member
            return contents.read()

    def test_hello(self):
        """The /hello route on the Root server should return a response."""
        self.assertEquals(b'Hello, world!', self.execute_get('/hello'))

    def test_parameter(self):
        """Query string parameters should be injectable."""
        self.assertEquals(b'Hello, Daniel!',
                          self.execute_get('/hello?name=Daniel'))


# vim: et ts=4
