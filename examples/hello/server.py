#!/usr/bin/env python
"""Example server using pystapler framework."""

from pystapler.dispatch import StaplerRoot, traversable, main
from pystapler.response import plaintext

class Root(StaplerRoot):
    @traversable
    @plaintext
    def hello(self, name='world'):
        return 'Hello, {}!'.format(name)

if __name__ == '__main__':
    main(Root())
