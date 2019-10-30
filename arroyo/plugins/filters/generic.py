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


from arroyo import Filter


import fnmatch
import re


class Generic(Filter):
    HANDLES = [
        # item.source attrib
        'created', 'created-min', 'created-max',
        'leechers', 'leechers-min', 'leechers-max',
        'name', 'name-like', 'name-glob',
        'provider', 'provider-in',
        'seeds''seeds-min', 'seeds-max',
        'size', 'size-min', 'size-max',
        'uri', 'uri-like', 'uri-glob',

        # other keys
        'age', 'age-min', 'age-max',
        'type', 'type-in',
    ]

    def filter(self, key, value, item):
        key, fn = eval_key(key)
        return fn(value, key, g)


def eval_key(key):
    if key.endswith('-like'):
        key = key[:-5]
        fn = cmp_like

    elif key.endswith('-glob'):
        key = key[:-5]
        fn = cmp_glob

    elif key.endswith('-min'):
        key = key[:-4]
        fn = cmp_min

    elif key.endswith('-max'):
        key = key[:-4]
        fn = cmp_max

    else:
        fn = cmp_eq

    return key, fn


def cmp_eq(a, b):
    return a == b


def cmp_min(n, limit):
    return n >= limit


def cmp_max(n, limit):
    return n <= limit


def cmp_glob(s, pattern):
    return fnmatch.fnmatch(s, pattern)


def cmp_like(s, pattern):
    re.match(pattern, s)
