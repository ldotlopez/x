# -*- coding: utf-8 -*-

# Copyright (C) 2015 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


import re
from collections import abc


UNDEF = object()
SEPARATOR = '.'


class Settings:
    def __init__(self, storage, separator=SEPARATOR):
        self._storage = storage
        self._separator = separator
        self.data = self._storage.read()

    def get(self, key, default=UNDEF):
        validatekey(key, separator=self._separator)
        try:
            d, key = _get_subdict(self.data, key,
                                  separator=self._separator, create=False)
            return d[key]

        except KeyError as e:
            if default is UNDEF:
                raise KeyError(key) from e
            else:
                return default

    def set(self, key, value):
        validatekey(key, separator=self._separator)
        d, key = _get_subdict(self.data, key,
                              separator=self._separator, create=True)
        d[key] = value
        self._sync()

    def _sync(self):
        self._storage.write(self.data)

    def children(self, key):
        validatekey(key, separator=self._separator)
        try:
            d, k = _get_subdict(self.data, key,
                                separator=self._separator, create=False)
        except KeyError as e:
            raise InvalidKeyError(key) from e

        if k not in d:
            raise InvalidKeyError(key)

        if not isinstance(d[k], abc.Mapping):
            raise NotNamespaceError(key)

        return list(d[k].keys())


class SettingsError(Exception):
    pass


class NotNamespaceError(SettingsError):
    pass


class InvalidKeyError(SettingsError):
    pass


def validatekey(key: str, separator=SEPARATOR) -> None:
    parts = key.split(separator)

    if not all(parts):
        raise InvalidKeyError(key)

    if not all([re.search(r'^[a-z0-9\-]+$', p)
                for p in parts]):
        raise InvalidKeyError(key)

    if key[0] == '-' or key[-1] == '-':
        raise InvalidKeyError(key)


def _get_subdict(d, key, separator=SEPARATOR, create=False):
    if SEPARATOR not in key:
        return d, key

    k, k2 = key.split(SEPARATOR, 1)
    if create and k not in d:
        d[k] = {}

    return _get_subdict(d[k], k2, create=create)
