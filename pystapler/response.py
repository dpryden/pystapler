# -*- coding: utf-8 -*-
"""Pystapler: application server framework for Python.

This module implements helper functionality for returning responses.

TODO(dpryden): Document types exported from this module.

Copyright 2017 Daniel Pryden <daniel@pryden.net>; All rights reserved.
See the LICENSE file for licensing details.
"""

from decorator import decorator

from werkzeug.wrappers import Response


def template(template_environment, template_name):
    """Decorates a method that renders its response using a template.

    Parameters:
        template_environment:
            An environment object that contains templates which can be
            rendered to HTML. This can be a Jinja2 Environment object, or it
            can be any other template environment, as long as it has a
            get_template() method that takes a string and returns an object
            that has a method named render().

            The decorated function is expected to return a mapping object
            which will provide keyword arguments to be passed to the render()
            method of the template object.

        template_name:
            The name of the template. The corresponding template object will
            be looked up from the environment using this name.

    Example Usage:

        env = jinja2.Environment(...)

        @template(env, 'my_template.html')
        def render_my_template(self):
            return {'spam': 1, 'eggs', 2}

    """
    template_obj = template_environment.get_template(template_name)

    @decorator
    def decorator_closure(method, *args, **kwargs):
        """@template decorator closure."""
        template_vars = method(*args, **kwargs)
        return template_obj.render(**template_vars)

    return decorator_closure


@decorator
def plaintext(method, *args, **kwargs):
    """Decorates a method that returns a string.

    The returned string is served as a text/plain response.
    """
    text = method(*args, **kwargs)
    return Response(response=text, content_type='text/plain')


# vim: et ts=4
