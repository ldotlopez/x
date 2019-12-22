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


import importlib


class ClassLoader:
    def __init__(self, defs=None):
        self._reg = {}
        if defs:
            for (name, cls) in defs.items():
                self.register(name, cls)

    def resolve(self, clsstr):
        parts = clsstr.split('.')
        mod, cls = '.'.join(parts[0:-1]), parts[-1]

        if not mod:
            raise ValueError(clsstr)

        mod = importlib.import_module(mod)
        return getattr(mod, cls)

    def register(self, name, target):
        self._reg[name] = target

    def get(self, name, *args, **kwargs):
        return self.get_class(name)(*args, **kwargs)

    def get_class(self, name):
        try:
            cls = self._reg[name]
        except KeyError as e:
            raise ClassNotFoundError(name) from e

        if isinstance(cls, str):
            cls = self.resolve(cls)
            self._reg[name] = cls

        if not isinstance(cls, type):
            raise TypeError(type)

        return cls

    def list(self, ns=''):
        if ns:
            prefix = ns + '.'

        ret = [name for (name, cls) in self._reg.items()
               if name.startswith(prefix)]

        return ret


class ClassNotFoundError(Exception):
    pass
