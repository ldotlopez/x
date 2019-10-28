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


from arroyo import (
    normalize,
    schema
)


import sys


class Query(dict):
    def __init__(self, type, **kwargs):
        schema.validate_entity_name(type)

        kwargs['type'] = type
        super().__init__(**kwargs)

    @classmethod
    def fromstring(cls, s):
        entity, _, _ = normalize.parse(s)
        params = {k: v for (k, v) in entity.dict().items() if v is not None}
        return cls(**params)


class Engine:
    def __init__(self, loader):
        self.loader = loader
        self.plugins = [loader.get(x) for x in loader.list('filters')]

    def get_filter(self, name):
        for plugin in self.plugins:
            if plugin.can_handle(name):
                return plugin

        raise MissingFilterError(name)

    def build_filter(self, query):
        filters = []

        for (key, value) in query.items():
            try:
                f = self.get_filter(key)
            except MissingFilterError:
                errmsg = "Missing filter for %s"
                errmsg = errmsg % key
                print(errmsg, file=sys.stderr)
                continue

            filters.append((f, key, value))

        return filters

    def apply(self, filters, items, mp=True):
        ret = items
        for (f, key, value) in filters:
            ret = f.apply(key, value, ret)

        return ret


class MissingFilterError(Exception):
    pass
