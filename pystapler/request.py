# -*- coding: utf-8 -*-
"""Pystapler: application server framework for Python.

This module implements helpers for extracting information from a request.

Copyright 2017 Daniel Pryden <daniel@pryden.net>; All rights reserved.
See the LICENSE file for licensing details.
"""


class RequestParams(dict):
    """Injectable parameters of a request.

    TODO(dpryden): Document the parameters available in this dictionary.
    """
    # pylint: disable=too-few-public-methods
    # TODO(dpryden): Make this lazy rather than eager?

    def __init__(self, request):
        dict.__init__(self)
        for parameter in request.args:
            self[parameter] = request.args[parameter]
        self['request'] = request
        self['form'] = request.form


# vim: et ts=4
