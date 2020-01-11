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
    analyze,
    schema
)


class Query(dict):
    def __init__(self, **kwargs):
        if 'state' not in kwargs:
            kwargs['state'] = 'none'

        super().__init__(**kwargs)

    @classmethod
    def fromstring(cls, s):
        # Keep in sync with MetadataAttributeFilter.HANDLES
        # from plugins/filters/generic.py
        metadata_pairs = [
            ('codec', analyze.Tags.VIDEO_CODEC),
            ('quality', analyze.Tags.VIDEO_SCREEN_SIZE),
            ('source', analyze.Tags.RELEASE_SOURCE)
        ]

        entity, metadata, parsed = analyze.parse(s)

        params = {k: v for
                  (k, v) in entity.dict().items()
                  if v is not None}

        if 'year' in params:
            if isinstance(entity, schema.Episode):
                params['series_year'] = params.pop('year', None)

            if isinstance(entity, schema.Movie):
                params['movie_year'] = params.pop('year', None)

        params.update({
            name: metadata[tag]
            for (name, tag) in metadata_pairs
            if tag in metadata
        })

        return cls(**params)

    def __repr__(self):
        r = '<Query (%s) at %s>'
        return r % (
            ','.join(['%s=%s' % (k, v) for (k, v) in self.items()]),
            hex(id(self))
        )

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
    def __init__(self, srvs, logger=None):
        self.srvs = srvs
        self.logger = logger or self.srvs.logger.getChild('query.Engine')

    def get_sorter(self):
        name = self.srvs.settings.get('sorter')
        return self.srvs.loader.get('sorters.' + name, self.srvs)

    def get_filter(self, name):
        plugins = [self.srvs.loader.get(x, self.srvs)
                   for x in self.srvs.loader.list('filters')]

        for plugin in plugins:
            if plugin.can_handle(name):
                return plugin

        raise MissingFilterError(name)

    def build_filter_context(self, query):
        filters = []
        missing = []

        for (name, value) in query.items():
            # Normalize filter name.
            name = name.replace('_', '-')

            try:
                f = self.get_filter(name)
            except MissingFilterError:
                missing.append(name)
                continue

            filters.append((f, name, value))

        if missing:
            raise MissingFiltersError(missing)

        return filters

    def apply(self, ctx, collection, mp=True):
        ret = collection
        for (f, key, value) in ctx:
            prev = len(ret)
            ret = f.apply(key, value, ret)
            curr = len(ret)

            logmsg = "applied filter '%s' over %s items: %s items left"
            logmsg = logmsg % (key, prev, curr)
            self.srvs.logger.debug(logmsg)

            if not ret:
                logmsg = "skipping remaing filters"
                self.srvs.logger.debug(logmsg)
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
