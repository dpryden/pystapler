# Pystapler: application server framework for Python.

This framework is inspired by Kohsuke Kawaguchi's Stapler framework for Java
(stapler.kohsuke.org), but obviously adapted to Python. It implements WSGI
support using the popular Werkzeug utility library.

Example Usage:

    from pystapler import pystapler

    class Root(pystapler.StaplerRoot):
        assets = pystapler.static_root('assets')
        env = pystapler.JinjaEnvironment('templates')

        def __init__(self):
            self.guestbook = []

        @pystapler.traversable('_')
        def underscore(self):
            return MutationActions(self)

        @pystapler.default
        @pystapler.template(env, 'home.html')
        def home(self):
            return {'guestbook': self.guestbook}

    class MutationActions(object):
        def __init__(self, root):
            self.__root = root

        @pystapler.post
        def add_guest(self, guest_name):
            root.guestbook.append(guest_name)
            return pystapler.redirect_to(root)

    if __name__ == '__main__':
        pystapler.main(Root)

You can launch this application using:

    uwsgi --socket 0.0.0.0:8080 --wsgi-file example.py --callable Root

Or, for development:

    python example.py --port 8080 --debug

Copyright 2017 Daniel Pryden <daniel@pryden.net>; All rights reserved.
See the LICENSE file for licensing details.
