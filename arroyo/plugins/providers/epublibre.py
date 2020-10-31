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


from urllib import parse

from arroyo import extensions


class EPubLibre(extensions.Provider):
    DEFAULT_URI = "https://epublibre.org/catalogo/index/0/nuevo/novedades/sin/todos/"
    URI_REGEXPS = [r"^http(s)?://([^.]\.)?epublibre\.org/"]

    def get_query_uri(self, query):
        if query.get("type") != "ebook":
            excmsg = "query is not for an ebook"
            raise extensions.IncompatibleQueryError(excmsg)

        author = query.get("ebook_author")
        title = query.get("ebook_title")
        name = query.get("name")

        if not author and not title and not name:
            excmsg = "ebook_title or ebook_author or name is required"
            raise extensions.IncompatibleQueryError(excmsg)

        if author or title:
            querystr = "%s %s" % (author or "", title or "")
        else:
            querystr = name

        querystr = parse.quote(querystr.strip())
        return self.DEFAULT_URI + querystr

    def parse_soup(self, soup):
        if soup.select("#titulo_libro"):
            return self.parse_detailed(soup)
        else:
            return self.parse_listing(soup)

    def parse_listing(self, soup):
        def _parse_book(book):
            href = book.attrs["href"]
            title = book.select_one("h1").text
            author = book.select_one("h2").text
            return {
                "name": "{author} {title}".format(author=author, title=title),
                "meta": {"book.author": author, "book.title": title},
                "type": "book",
                "uri": href,
            }

        ret = [_parse_book(x) for x in soup.select("a.popover-libro")]
        return ret

    def parse_detailed(self, soup):
        href = soup.select_one("a[href^=magnet:?]").attrs["href"]
        title = soup.select_one(".det_titulo").text.strip()
        author = soup.select_one(".aut_sec").text.strip()
        return [
            {"uri": href, "name": "{author} {title}".format(author=author, title=title)}
        ]
