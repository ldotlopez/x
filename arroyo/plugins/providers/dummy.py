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


from arroyo import Provider


import re
from urllib import parse


class EzTV(Provider):
    DEFAULT_URI = 'https://eztv.io/'
    URI_GLOBS = 'https://eztv.io/*'

    def paginate(self, uri):
        parsed = parse.urlparse(uri)
        pathcomponents = parsed.path.split('/')
        pathcomponents = list(filter(lambda x: x, pathcomponents))

        # https://eztv.ag/ -> page_0 if not pathcomponents:
        if not pathcomponents:
            pathcomponents = ['page_0']

        # https://eztv.ag/shows/546/black-mirror/
        if len(pathcomponents) != 1:
            yield uri
            return

        # Anything non standard
        m = re.findall(r'^page_(\d+)$', pathcomponents[0])
        if not m:
            yield uri
            return

        # https://eztv.ag/page_0
        page = int(m[0])
        while True:
            yield '{scheme}://{netloc}/page_{page}'.format(
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                page=page)
            page += 1

    def parse(self, buffer):
        _ = self.parse_as_soup(buffer)
        return []


class RarBG(Provider):
    URI_REGEXPS = [
        r'https?://(www.)?rarbg.com/.*'
    ]


class ThePirateBay(Provider):
    DEFAULT_URI = 'https://lepiratebay.org/recent'
    URI_REGEXPS = [
        r'https?://(www.)?thepiratebay.com/.*'
    ]

    def paginate(self, uri):
        # Add leading '/'
        if not uri.endswith('/'):
            uri += '/'

        # Get page
        try:
            page = int(re.findall(r'/(\d+)/', uri)[0])
        except IndexError:
            page = 0
            uri += '0/'

        pre, post = re.split(r'/\d+/', uri, maxsplit=1)

        while True:
            yield pre + '/' + str(page) + '/' + post
            page += 1

    # def parse(self, buffer):
    #     soup = self.parse_as_soup(buffer)
    #     return [soup]
