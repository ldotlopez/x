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


UNDEF = object()


class Settings:
    def __init__(self, storage):
        self._storage = storage
        self.data = self._storage.read()

    def get(self, key, default=UNDEF):
        validatekey(key)
        try:
            return self.data[key]
        except KeyError as e:
            if default is UNDEF:
                raise e
            else:
                return default

    def set(self, key, value):
        validatekey(key)
        if self.is_namespace(key):
            raise ValueError()

        self.data[key] = value
        self._sync()

    def _sync(self):
        self._storage.write(self.data)

    def is_namespace(self, key):
        nstest = key + '.'
        for x in self.data:
            if x.startswith(nstest):
                return True

        return False


def validatekey(key: str) -> None:
    parts = key.split('.')

    if not all(parts):
        raise ValueError(key)

    if not all([re.search(r'^[a-z0-9_]+$', p)
                for p in parts]):
        raise ValueError(key)
