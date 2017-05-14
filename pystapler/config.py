# -*- coding: utf-8 -*-
"""Pystapler: application server framework for Python.

This module implements the configuration mechanism.

TODO(dpryden): Document types exported from this module.

Copyright 2017 Daniel Pryden <daniel@pryden.net>; All rights reserved.
See the LICENSE file for licensing details.
"""

import logging


LOGGER = logging.getLogger(__name__)


class StaplerConfig(object):
    """Base configuration class.

    Applications may extend from this class to provide additional startup
    configuration variables.
    """
    # pylint: disable=too-few-public-methods
    # TODO(dpryden): Implement config mechanism
    port = 8080
    debug = True


# vim: et ts=4
