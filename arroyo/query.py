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


import logging
import warnings


from arroyo.core import services
from arroyo import analyze


class Query(dict):
    def __init__(self, **kwargs):
        if 'state' not in kwargs:
            kwargs['state'] = 'none'

        super().__init__(**kwargs)

    @classmethod
    def fromstring(cls, s):
        entity, _, _ = analyze.parse(s)
        params = {k: v for (k, v) in entity.dict().items() if v is not None}
        return cls(**params)

    def __repr__(self):
        r = '<Query (%s) at %s>'
        return r % (
            ','.join(['%s=%s' % (k, v) for (k, v) in self.items()]),
            hex(id(self))
        )

    def __str__(self):
        """
        Prevent usage of old APIs
        """
        raise SystemError()

    def str(self):
        def _get_base_string(key='name'):
            try:
                return self[key].strip()
            except KeyError:
                pass

            try:
                return self[key + '_glob'].replace('*', ' ').strip()
            except KeyError:
                pass

            return ''

        def _source_base_string():
            return _get_base_string('name')

        def _episode_base_string():
            ret = _get_base_string('series')
            if not ret:
                return _source_base_string()

            try:
                ret += " ({})".format(self['series_year'])
            except KeyError:
                pass

            try:
                ret += " S" + str(self['season']).zfill(2)
            except KeyError:
                return ret

            try:
                ret += "E" + str(self['number']).zfill(2)
            except KeyError:
                pass

            return ret

        def _movie_base_string():
            ret = _get_base_string('title')
            try:
                ret += " ({})".format(self['movie_year'])
            except KeyError:
                pass

            return ret

        handlers = {
            'episode': _episode_base_string,
            'movie': _movie_base_string,
            'source': _source_base_string,
        }

        try:
            return handlers[self['type']]()

        except KeyError:
            err = "base_string for {type} not implmented"
            err = err.format(type=self.type)
            raise NotImplementedError(err)


class Engine:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('arroyo.query-engine')

    def get_sorter(self):
        name = services.settings.get('sorter')
        return services.loader.get('sorters.' + name)

    def get_filter(self, name):
        plugins = [services.loader.get(x)
                   for x in services.loader.list('filters')]

        for plugin in plugins:
            if plugin.can_handle(name):
                return plugin

        raise MissingFilterError(name)

    def build_filter_context(self, query):
        filters = []
        missing = []

        for (key, value) in query.items():
            try:
                f = self.get_filter(key)
            except MissingFilterError:
                missing.append(key)
                continue

            filters.append((f, key, value))

        if missing:
            raise MissingFiltersError(missing)

        return filters

    def build_filter(self, query):
        warnings.warn("Deprected method")
        return self.build_filter_context(query)

    def apply(self, ctx, collection, mp=True):
        ret = collection
        for (f, key, value) in ctx:
            prev = len(ret)
            ret = f.apply(key, value, ret)
            curr = len(ret)

            logmsg = "applied filter '%s' over %s items: %s items left"
            logmsg = logmsg % (key, prev, curr)
            self.logger.debug(logmsg)

            if not ret:
                logmsg = "skipping remaing filters"
                self.logger.debug(logmsg)
                break

        return ret

    def sort(self, collection):
        groups = {}

        # There is some hack here...
        # Entity hash function is case-insentive so `entity not in groups`
        # works as c-i but... adding key to groups (`groups[key]`) is c-s.
        # I get some duplicates here. i.ex. with series with different
        # capitalizations: Dark vs DARK vs dark.
        # The hack: use the result from hash as key and add the real key as the
        # first element. Later, before return, the entity is unpacked.
        for source in collection:
            key = hash(source.entity) or hash(source)
            if key not in groups:
                groups[key] = [source.entity or source]

            groups[key].append(source)

        sorter = self.get_sorter()
        ret = [
            (x.pop(0), sorter.sort(x))
            for (x) in groups.values()
        ]
        return ret


class MissingFilterError(Exception):
    pass


class MissingFiltersError(MissingFilterError):
    pass
