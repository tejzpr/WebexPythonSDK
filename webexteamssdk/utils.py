# -*- coding: utf-8 -*-
"""Package helper functions and classes.

Copyright (c) 2016-2018 Cisco and/or its affiliates.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


from __future__ import (
    absolute_import,
    division,
    print_function,
    unicode_literals,
)

from future import standard_library
standard_library.install_aliases()
native_str = str

import json
import mimetypes
import os
import sys
import urllib.parse
from builtins import *
from collections import OrderedDict, namedtuple
from datetime import datetime, timedelta, tzinfo

from past.builtins import basestring

from .config import WEBEX_TEAMS_DATETIME_FORMAT
from .exceptions import (
    ApiError, RateLimitError,
)
from .response_codes import RATE_LIMIT_RESPONSE_CODE


EncodableFile = namedtuple('EncodableFile',
                           ['file_name', 'file_object', 'content_type'])


def to_unicode(string):
    """Convert a string (bytes, str or unicode) to unicode."""
    assert isinstance(string, basestring)
    if sys.version_info[0] >= 3:
        if isinstance(string, bytes):
            return string.decode('utf-8')
        else:
            return string
    else:
        if isinstance(string, str):
            return string.decode('utf-8')
        else:
            return string


def to_bytes(string):
    """Convert a string (bytes, str or unicode) to bytes."""
    assert isinstance(string, basestring)
    if sys.version_info[0] >= 3:
        if isinstance(string, str):
            return string.encode('utf-8')
        else:
            return string
    else:
        if isinstance(string, unicode):
            return string.encode('utf-8')
        else:
            return string


def validate_base_url(base_url):
    """Verify that base_url specifies a protocol and network location."""
    parsed_url = urllib.parse.urlparse(base_url)
    if parsed_url.scheme and parsed_url.netloc:
        return parsed_url.geturl()
    else:
        error_message = "base_url must contain a valid scheme (protocol " \
                        "specifier) and network location (hostname)"
        raise ValueError(error_message)


def is_web_url(string):
    """Check to see if string is an validly-formatted web url."""
    assert isinstance(string, basestring)
    parsed_url = urllib.parse.urlparse(string)
    return ((parsed_url.scheme.lower() == 'http' or
             parsed_url.scheme.lower() == 'https') and
            parsed_url.netloc)


def is_local_file(string):
    """Check to see if string is a valid local file path."""
    assert isinstance(string, basestring)
    return os.path.isfile(string)


def open_local_file(file_path):
    """Open the file and return an EncodableFile tuple."""
    assert isinstance(file_path, basestring)
    assert is_local_file(file_path)
    file_name = os.path.basename(file_path)
    file_object = open(file_path, 'rb')
    content_type = mimetypes.guess_type(file_name)[0] or 'text/plain'
    return EncodableFile(file_name=file_name,
                         file_object=file_object,
                         content_type=content_type)


def check_type(o, acceptable_types, may_be_none=True):
    """Object is an instance of one of the acceptable types or None.

    Args:
        o: The object to be inspected.
        acceptable_types: A type or tuple of acceptable types.
        may_be_none(bool): Whether or not the object may be None.

    Raises:
        TypeError: If the object is None and may_be_none=False, or if the
            object is not an instance of one of the acceptable types.

    """
    if not isinstance(acceptable_types, tuple):
        acceptable_types = (acceptable_types,)

    if may_be_none and o is None:
        # Object is None, and that is OK!
        pass
    elif isinstance(o, acceptable_types):
        # Object is an instance of an acceptable type.
        pass
    else:
        # Object is something else.
        error_message = (
            "We were expecting to receive an instance of one of the following "
            "types: {types}{none}; but instead we received {o} which is a "
            "{o_type}.".format(
                types=", ".join([repr(t.__name__) for t in acceptable_types]),
                none="or 'None'" if may_be_none else "",
                o=o,
                o_type=repr(type(o).__name__)
            )
        )
        raise TypeError(error_message)


def dict_from_items_with_values(*dictionaries, **items):
    """Creates a dict with the inputted items; pruning any that are `None`.

    Args:
        *dictionaries(dict): Dictionaries of items to be pruned and included.
        **items: Items to be pruned and included.

    Returns:
        dict: A dictionary containing all of the items with a 'non-None' value.

    """
    dict_list = list(dictionaries)
    dict_list.append(items)
    result = {}
    for d in dict_list:
        for key, value in d.items():
            if value is not None:
                result[key] = value
    return result


def raise_if_extra_kwargs(kwargs):
    """Raise a TypeError if kwargs is not empty."""
    if kwargs:
        raise TypeError("Unexpected **kwargs: {!r}".format(kwargs))


def check_response_code(response, expected_response_code):
    """Check response code against the expected code; raise ApiError.

    Checks the requests.response.status_code against the provided expected
    response code (erc), and raises a ApiError if they do not match.

    Args:
        response(requests.response): The response object returned by a request
            using the requests package.
        expected_response_code(int): The expected response code (HTTP response
            code).

    Raises:
        ApiError: If the requests.response.status_code does not match the
            provided expected response code (erc).

     """
    if response.status_code == expected_response_code:
        pass
    elif response.status_code == RATE_LIMIT_RESPONSE_CODE:
        raise RateLimitError(response)
    else:
        raise ApiError(response)


def extract_and_parse_json(response):
    """Extract and parse the JSON data from an requests.response object.

    Args:
        response(requests.response): The response object returned by a request
            using the requests package.

    Returns:
        The parsed JSON data as the appropriate native Python data type.

    """
    return json.loads(response.text, object_hook=OrderedDict)


def json_dict(json_data):
    """Given a dictionary or JSON string; return a dictionary.

    Args:
        json_data(dict, str): Input JSON object.

    Returns:
        A Python dictionary with the contents of the JSON object.

    Raises:
        TypeError: If the input object is not a dictionary or string.

    """
    if isinstance(json_data, dict):
        return json_data
    elif isinstance(json_data, basestring):
        return json.loads(json_data, object_hook=OrderedDict)
    else:
        raise TypeError(
            "'json_data' must be a dictionary or valid JSON string; "
            "received: {!r}".format(json_data)
        )


class ZuluTimeZone(tzinfo):
    """Zulu Time Zone."""

    def tzname(self, dt):
        """Time Zone Name."""
        # The future package's newstr is messing with Python2 compatibility
        return native_str("Z")

    def utcoffset(self, dt):
        """UTC Offset."""
        return timedelta(0)

    def dst(self, dt):
        """Daylight Savings Time Offset."""
        return timedelta(0)


class WebexTeamsDateTime(datetime):
    """Webex Teams formatted Python datetime."""

    @classmethod
    def strptime(cls, date_string, format=WEBEX_TEAMS_DATETIME_FORMAT):
        """strptime with the Webex Teams DateTime format as the default."""
        return super(WebexTeamsDateTime, cls).strptime(
            date_string, format
        ).replace(tzinfo=ZuluTimeZone())

    def strftime(self, fmt=WEBEX_TEAMS_DATETIME_FORMAT):
        """strftime with the Webex Teams DateTime format as the default."""
        return super(WebexTeamsDateTime, self).strftime(fmt)

    def __str__(self):
        """Human readable string representation of this WebexTeamsDateTime."""
        dt = self.astimezone(ZuluTimeZone())
        return dt.strftime("%Y-%m-%dT%H:%M:%S.{:0=3}%Z").format(
            self.microsecond // 1000
        )
