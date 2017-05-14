# -*- coding: utf-8 -*-
"""Pystapler: application server framework for Python.

This module implements the request dispatching logic.

TODO(dpryden): Document types exported from this module.

Copyright 2017 Daniel Pryden <daniel@pryden.net>; All rights reserved.
See the LICENSE file for licensing details.
"""
from __future__ import absolute_import

import inspect
import logging

from six import iteritems

from werkzeug.exceptions import HTTPException, BadRequest, NotFound
from werkzeug.serving import run_simple
from werkzeug.test import Client
from werkzeug.utils import cached_property
from werkzeug.wrappers import BaseResponse, Request
from werkzeug.wsgi import responder

from pystapler.request import RequestParams


PREFIX = '_pystapler_'
DEFAULT = object()
NOT_FOUND = object()
NOT_TRAVERSABLE = object()

LOGGER = logging.getLogger(__name__)


class StaplerRoot(object):
    """Base class for the root object of a Pystapler application.

    An instance of this class is a valid WSGI application.
    """
    __config = None

    @property
    def config(self):
        """A StaplerConfig instance containing startup configuration data.

        Subclasses should override this property with their own subclass of
        StaplerConfig to configure additional startup-time configuration
        properties.
        """
        if self.__config is None:
            from pystapler.config import StaplerConfig
            self.__config = StaplerConfig()
        return self.__config

    @responder
    def __call__(self, environ, start_response):
        """Implements the WSGI application protocol."""
        request = Request(environ)
        LOGGER.info('%s %s', request.method, request.path)
        path_segments = request.path.lstrip('/').split('/')

        request_params = RequestParams(request)

        object_info = _ObjectInfo(self)
        try:
            return object_info.dispatch(path_segments, request_params)
        except HTTPException as ex:
            return ex

    def test_client(self, response_wrapper=BaseResponse):
        """Returns a Werkzeug test client for this application.

        See the Werkzeug documentation on test utilities for more information:
        http://werkzeug.pocoo.org/docs/0.12/test/
        """
        return Client(self, response_wrapper=response_wrapper)


def _build_traversal_map(cls):
    """Computes the traversal map for a given type.

    This is a dictionary mapping traversable members of the type to
    _MethodInfo objects that contain metadata about those members.
    """
    LOGGER.debug('Scanning for traversable paths on %s', cls)
    result = {}
    for member_name, member in iteritems(cls.__dict__):
        if callable(member):
            method_info = _MethodInfo(member)
            traversable_as = method_info.traversable_as
            if traversable_as is not None:
                result[traversable_as] = method_info
                LOGGER.debug(
                    'Found traversable path "%s" on %s', traversable_as, cls)
                continue
            if method_info.default:
                result[DEFAULT] = method_info
                LOGGER.debug(
                    'Found default path "%s" on %s', member_name, cls)
                continue
        LOGGER.debug(
            'Found non-traversable path "%s" on %s', member_name, cls)
        result[member_name] = NOT_TRAVERSABLE
    return result


def _get_traversal_map(obj):
    """Returns the traversal map for an object.

    This map is built from the type of the object, and is cached on the
    type object itself, to avoid recomputing it every time.
    """
    cls = type(obj)
    attribute_name = PREFIX + 'traversal_map'
    traversal_map = getattr(cls, attribute_name, None)
    if traversal_map is None:
        traversal_map = _build_traversal_map(cls)
        setattr(cls, attribute_name, traversal_map)
    return traversal_map


class _ObjectInfo(object):
    """Wrapper around an object that is used for request dispatching."""
    def __init__(self, obj):
        self.__object = obj
        self.__traversal_map = _get_traversal_map(obj)

    def lookup(self, member_name):
        """Looks up a member of the wrapped object by name.

        Parameters:
            member_name: a string indicating the member of interest.

        Returns:
            One of the following:
                a _MethodInfo object:
                    Returned if the member is a method. Note that this object
                    may be cached and the same instance reused on multiple
                    requests.
                the special value NOT_TRAVERSABLE:
                    Returned if the member cannot be traversed into, for
                    example if it is a method but it is not decorated with
                    the @pystapler.traversable decorator.
                the special value NOT_FOUND:
                    If there is no member of this object with the given name.
        """
        return self.__traversal_map.get(member_name, NOT_FOUND)

    def dispatch(self, path_segments, request_params):
        """Dispatches a request to this object.

        Parameters:
            path_segments:
                A list of remaining path segment(s) relative to this object.
                For example, if the request path was /spam/eggs/hovercraft,
                and the result of dispatching '/spam' returned the current
                object, path_segments will be the list ['eggs', 'hovercraft'].
            request_params:
                A dictionary of parameters derived from the current request
                which can be used to satisfy method arguments.

        Returns:
            A Werkzeug response object or other WSGI application object, which
            will be used to create the HTTP response.
        """
        if path_segments:
            path_segment = path_segments[0]
            extra_path_segments = path_segments[1:]
            member = self.lookup(path_segment)
        else:
            path_segment = '<default>'
            extra_path_segments = []
            member = self.lookup(DEFAULT)
        if member is NOT_FOUND:
            LOGGER.debug(
                'Path segment "%s" not found on %s', path_segment, self.__object)
            return NotFound()
        if member is NOT_TRAVERSABLE:
            LOGGER.warning(
                'Attempted to traverse member "%s" of %s, but it is '
                'not traversable.',
                path_segment, self.__object)
            return NotFound()
        return member.traverse(
            self.__object, extra_path_segments, request_params)


class _MethodInfo(object):
    """Wrapper around a method object is used for request dispatching.

    Any attribute that was added using a keyword argument passed to
    _decorate_impl will be exposed as a member of this object.
    """
    def __init__(self, method):
        self.__method = method
        self.__attributes = {}

    def __getattr__(self, attribute):
        assert not attribute.startswith('_')
        if attribute in self.__attributes:
            return self.__attributes[attribute]
        qualified_attribute = PREFIX + attribute
        value = getattr(self.__method, qualified_attribute, None)
        self.__attributes[attribute] = value
        return value

    @cached_property
    def name(self):
        """Returns the name that this method is traversable as."""
        if self.traversable_as is not None:
            return self.traversable_as
        return self.__method.__name__

    @cached_property
    def argspec(self):
        """Returns an ArgSpec named tuple for the wrapped method."""
        return inspect.getargspec(self.__method)

    @cached_property
    def required_args(self):
        """Returns the names of the required arguments of the wrapped method.

        An argument is considered required if it does not have a default value.
        The "self" parameter of a method is not considered required, as it
        will be supplied automatically.
        """
        args = self.argspec.args
        defaults = self.argspec.defaults
        if defaults:
            args = args[:-len(defaults)]
        # I tried using inspect.ismethod to detect this case, but it doesn't
        # work because the function object can be decorated (and, in our case,
        # usually is), and the decorated function object is NOT a method.
        # So I make do with this hacky solution.
        if args[0] == 'self':
            args = args[1:]
        return args

    def traverse(self, obj, extra_path_segments, request_params):
        """Traverses to the given method, and continues dispatching if needed.

        The underlying method may accept any number of arguments. Arguments to
        the method are supplied using the request_params dictionary (see the
        module documentation for details). If the method accepts an argument
        but the request_params dictionary does not contain the given key, a
        400 Bad Request error will be returned instead.

        If the wrapped method returns a callable object, it is assumed to be
        a Werkzeug response object or other WSGI compilant application object,
        and it is used to render the response directly. Otherwise, dispatching
        continues, using the remaining path segments and whatever object was
        returned.

        Parameters:
            obj:
                The object to call the method on.
            extra_path_segments:
                A list of strings representing the remaining path segments
                that have not yet been matched. For example, if the requested
                path is /spam/eggs, and the current method is traversable as
                'spam', this list will be ['eggs'].
            request_params:
                A dictionary of parameters derived from the current request
                which can be used to satisfy method arguments.

        Returns:
            A Werkzeug response object or other WSGI application object, which
            will be used to create the HTTP response.
        """
        for required_arg in self.required_args:
            if required_arg not in request_params:
                LOGGER.warning(
                    'Attempted to invoke method "%s" but required '
                    'parameter "%s" was not provided.',
                    self.name, required_arg)
                raise BadRequest(
                    'Required parameter "{}" not provided'.format(
                        required_arg))
        if self.argspec.keywords:
            # If the method accepts kwargs, give it all the request params.
            kwargs = dict(request_params)
        else:
            # Otherwise, just give it the ones it's asked for.
            kwargs = {
                key : request_params[key]
                for key in self.argspec.args
                if key in request_params}
        kwargs['self'] = obj
        method = self.__method
        result = method(**kwargs)
        LOGGER.info(
            'Traversing "%s" resulted in an object of type %s',
            self.name, type(result))
        if callable(result):
            return result
        return _ObjectInfo(result).dispatch(extra_path_segments, request_params)


def _decorate_impl(method, **kwargs):
    """Decorates a method object with pystapler attributes."""
    for attribute, value in iteritems(kwargs):
        qualified_attribute = PREFIX + attribute
        setattr(method, qualified_attribute, value)
    return method


def default(method):
    """Marks a method as the default rendering of an object.

    This is conceptually similar to an index.html file: it's what gets
    rendered if nothing else is specified.
    """
    return _decorate_impl(method, default=True)


def traversable(obj):
    """Marks a method as traversable.

    This method is intended to be invoked as a decorator, but it optionally
    accepts a string argument indicating the path name that should correspond
    to the decorated method.

    Example use:

        class MyApp(StaplerRoot):
            @traversable
            def spam(self):
                # The /spam URL will map to this method.
                ...

            @traversable('/something-completely-different')
            def eggs(self):
                # The /something-completely-different URL will map to this
                # method. The /eggs URL will not be mapped to anything.
                ...
    """
    if callable(obj):
        name = obj.__name__
        return _decorate_impl(obj, traversable_as=name)

    # If the argument is not callable, assume it's a string which is the name
    # we want to be traversable by.
    name = obj
    def decorator_closure(method):
        """Decorator closure that will decorate with the given name."""
        return _decorate_impl(method, traversable_as=name)
    return decorator_closure


def main(root):
    """Launches an application with a simple runner for debugging.

    Parameters:
        root:
            An instance of StaplerRoot representing the application.
    """
    config = root.config
    LOGGER.info('Launching server on http://localhost:%d', config.port)
    run_simple(
        hostname='0.0.0.0',
        port=config.port,
        application=root,
        use_debugger=config.debug,
        use_reloader=config.debug)


# vim: et ts=4
