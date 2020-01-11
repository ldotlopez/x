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


import hashlib
from urllib import parse

from arroyo.analyze import analyze_one
from arroyo.schema import Source


def build_source(name, **kwargs):
    sha1 = hashlib.sha1()
    sha1.update(name.encode('utf-8'))

    uri = 'magnet:?dn=%s&xt=urn:btih:%s' % (
        parse.quote(name), sha1.hexdigest())
    params = {
        'uri': uri,
        'provider': 'mock'
    }
    params.update(kwargs)
    return Source(name=name, **params)


def build_item(name, **kwargs):
    src = build_source(name, **kwargs)
    item = analyze_one(src)
    return item
