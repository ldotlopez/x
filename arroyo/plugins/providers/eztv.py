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
import time
from datetime import datetime
from urllib import parse

import humanfriendly
from arroyo import extensions


class EzTV(extensions.Provider):
    BASE_URI = "https://eztv.io"
    DEFAULT_URI = BASE_URI + "/page_0"
    URI_REGEXPS = [r"^http(s)?://([^.]\.)?eztv\.[^.]{2,3}/"]

    def paginate(self, uri):
        parsed = parse.urlparse(uri)
        pathcomponents = parsed.path.split("/")
        pathcomponents = list(filter(lambda x: x, pathcomponents))

        # https://eztv.ag/ -> page_0 if not pathcomponents:
        if not pathcomponents:
            pathcomponents = ["page_0"]

        # https://eztv.ag/shows/546/black-mirror/
        if len(pathcomponents) != 1:
            yield uri
            return

        # Anything non standard
        m = re.findall(r"^page_(\d+)$", pathcomponents[0])
        if not m:
            yield uri
            return

        # https://eztv.ag/page_0
        page = int(m[0])
        while True:
            yield "{scheme}://{netloc}/page_{page}".format(
                scheme=parsed.scheme, netloc=parsed.netloc, page=page
            )
            page += 1

    def get_query_uri(self, query):
        # eztv only has series
        if query.get("type") != "episode":
            excmsg = "query is not for an episode"
            raise extensions.IncompatibleQueryError(excmsg)

        try:
            series = query["series"]
        except KeyError:
            excmsg = "query doesn't have a series parameter"
            raise extensions.IncompatibleQueryError(excmsg)

        q = series.strip().replace(" ", "-")

        return "{base}/search/{q}".format(base=self.BASE_URI, q=parse.quote_plus(q))

    def parse(self, buffer):
        soup = self.parse_as_soup(buffer)
        rows = self.parse_page(soup)
        items = [self.parse_row(row) for row in rows]

        return items

    def parse_page(self, soup):
        # Get links with magnets
        magnets = [
            x for x in soup.select("a") if x.attrs.get("href", "").startswith("magnet")
        ]

        # Go up until we get 'tr's
        rows = [x.findParent("tr") for x in magnets]

        return rows

    def parse_row(self, row):
        # Get magnet and name from the magnet link
        name, magnet = self.parse_name_and_uri(row)
        try:
            size = self.parse_size(row)
        except ValueError:
            size = None

        try:
            timestamp = self.parse_timestamp(row)
        except ValueError:
            timestamp = None

        return {
            "name": name,
            "uri": magnet,
            "size": size,
            "timestamp": timestamp,
            "language": "eng-us",
            "type": "episode",
        }

    def parse_name_and_uri(self, node):
        magnet = [
            x for x in node.select("a") if x.attrs.get("href").startswith("magnet:?")
        ][0]
        parsed = parse.urlparse(magnet.attrs["href"])
        name = parse.parse_qs(parsed.query)["dn"][0]

        return (name, magnet.attrs["href"])

    def parse_size(self, node):
        s = str(node)

        m = re.search(r"(\d+(\.\d+)?\s+[TGMK]B)", s, re.IGNORECASE)
        if not m:
            raise ValueError("No size value found")

        try:
            return humanfriendly.parse_size(m.group(0))
        except humanfriendly.InvalidSize as e:
            raise ValueError("Invalid size") from e

    def parse_timestamp(cls, node):
        def _do_diff(diff):
            return int(time.mktime(datetime.now().timetuple())) - diff

        _table_mults = {
            "s": 1,
            "m": 60,
            "h": 60 * 60,
            "d": 60 * 60 * 24,
            "w": 60 * 60 * 24 * 7,
            "mo": 60 * 60 * 24 * 30,
            "y": 60 * 60 * 24 * 365,
        }

        s = str(node)

        # Search for minutes, hours, days
        m = re.search(r"(\d+)([mhd]) (\d+)([smhd])", s)
        if m:
            amount1 = int(m.group(1))
            qual1 = m.group(2)
            amount2 = int(m.group(3))
            qual2 = m.group(4)
            diff = amount1 * _table_mults[qual1] + amount2 * _table_mults[qual2]

            return _do_diff(diff)

        # Search for weeks, months, years
        m = re.search(r"(\d+) (w|mo|y)", s)
        if m:
            diff = int(m.group(1)) * _table_mults[m.group(2)]
            return _do_diff(diff)

        # :shrug:
        raise ValueError("No created value found")
