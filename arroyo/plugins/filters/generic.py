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


import arroyo
from arroyo import (
    core,
    schema,
)


import fnmatch
import functools
import re
import time


class StateFilter(arroyo.Filter):
    HANDLES = ['state']

    def filter(self, name, value, item):
        if value == 'all':
            return True

        if not item.entity:
            return True

        if not core.db.downloads.sources_for_entity(item.entity):
            return True

        return False


class SourceAttributeFilter(arroyo.Filter):
    HANDLES = [
        # item.source attrib
        'created', 'created-min', 'created-max',
        'leechers', 'leechers-min', 'leechers-max',
        'name', 'name-like', 'name-glob',
        'provider', 'provider-in',
        'seeds', 'seeds-min', 'seeds-max',
        'size', 'size-min', 'size-max',
        'uri', 'uri-like', 'uri-glob',

        # other names
        'age', 'age-min', 'age-max',
        'type', 'type-in',
    ]

    def filter(self, name, value, source):
        basename, fn = eval_filter_name(name)

        if basename == 'type':
            try:
                sourcevalue = source.entity.type
            except AttributeError:
                return False

        elif basename == 'age':
            now = int(time.time())
            sourcevalue = max(now - (source.created or 0), 0)

        else:
            sourcevalue = getattr(source, basename)

        value = convert_type(value, sourcevalue)
        return fn(value, sourcevalue)


class MetadataAttributeFilter(arroyo.Filter):
    ENTITY_TYPE = None
    HANDLES = ['codec', 'quality']

    def filter(self, name, value, source):
        m = {
            'quality': 'core.video.screen-size',
            'codec': 'core.video.codec'
        }
        mkey = m.get(name) or name
        if not source.metadata or mkey not in source.metadata:
            return False

        # Normalize both values
        srcvalue = source.metadata[mkey].lower()
        usrvalue = value.lower()

        if name == 'codec':
            # Normalize codec values
            codec_sub = functools.partial(re.sub,
                                          r'^(h|x)\.?26([45])', r'h26\2')
            srcvalue = codec_sub(srcvalue)
            usrvalue = codec_sub(usrvalue)

        return srcvalue == usrvalue


class EntityAttributeFilter(arroyo.Filter):
    ENTITY_TYPE = None
    HANDLES = []

    def filter(self, name, value, source):
        if not isinstance(source.entity, self.ENTITY_TYPE):
            return False

        basename, fn = eval_filter_name(name)

        sourcevalue = getattr(source.entity, basename)
        value = convert_type(value, sourcevalue)
        return fn(value, sourcevalue)


class EpisodeAttributeFilter(EntityAttributeFilter):
    ENTITY_TYPE = schema.Episode
    HANDLES = [
        'series', 'series-glob', 'series-like',
        'series-year',
        'season', 'season-min', 'season-max',
        'number', 'number-min', 'number-max'
    ]

    def filter(self, name, value, item):
        name = name.replace('series-', '')
        return super().filter(name, value, item)


class MovieAttributeFilter(EntityAttributeFilter):
    ENTITY_TYPE = schema.Movie
    HANDLES = [
        'title', 'title-glob', 'title-like',
        'movie-year', 'movie-year-min', 'movie-year-max'
    ]

    def filter(self, name, value, item):
        name = name.replace('movie-', '')
        return super().filter(name, value, item)


def convert_type(value, target):
    return type(target)(value)


def eval_filter_name(name):
    if name.endswith('-like'):
        name = name[:-5]
        fn = cmp_like

    elif name.endswith('-glob'):
        name = name[:-5]
        fn = cmp_glob

    elif name.endswith('-min'):
        name = name[:-4]
        fn = cmp_min

    elif name.endswith('-max'):
        name = name[:-4]
        fn = cmp_max

    elif name.endswith('-in'):
        name = name[:-3]
        fn = cmp_in

    else:
        fn = cmp_eq

    return name, fn


def cmp_eq(filtervalue, sourcevalue):
    if isinstance(filtervalue, str) and isinstance(sourcevalue, str):
        filtervalue = filtervalue.lower()
        sourcevalue = sourcevalue.lower()

    return filtervalue == sourcevalue


def cmp_min(filtervalue, sourcevalue):
    return filtervalue <= sourcevalue


def cmp_max(filtervalue, sourcevalue):
    return filtervalue >= sourcevalue


def cmp_glob(filtervalue, sourcevalue):
    return fnmatch.fnmatch(sourcevalue, filtervalue)


def cmp_like(filtervalue, sourcevalue):
    return re.match(filtervalue, sourcevalue) is not None


def cmp_in(options, sourcevalue):
    return False
