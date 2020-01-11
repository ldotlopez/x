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


import unittest


from arroyo.services import Services
from arroyo.query import Query
from arroyo.plugins.providers import IncompatibleQueryError


from arroyo.plugins.providers.epublibre import EPubLibre
from arroyo.plugins.providers.eztv import EzTV
from arroyo.plugins.providers.torrentapi import TorrentAPI


class TestProviderMixin:
    PROVIDER_CLASS = None
    TEST_HANDLED_URLS = []
    TEST_HANDLED_URLS_NEGATIVE = []
    TEST_QUERY_URLS = []

    def _get_provider_cls(self):
        return self.PROVIDER_CLASS

    def _get_provider(self):
        return self._get_provider_cls()(Services())

    def test_default_uri(self):
        cls = self._get_provider_cls()
        default_uri = getattr(cls, 'DEFAULT_URI', None)

        self.assertTrue(isinstance(default_uri, str) and
                        default_uri != '',
                        msg="provider doesn't have default uri")

        self.assertTrue(cls.can_handle(default_uri),
                        msg="provider can't handle its own default uri")

    def test_handlers(self):
        cls = self._get_provider_cls()
        globs = getattr(cls, 'URI_GLOBS')
        regexps = getattr(cls, 'URI_REGEXPS')

        self.assertTrue(isinstance(globs, list))
        self.assertTrue(isinstance(regexps, list))
        self.assertTrue(globs or regexps)

    def test_paginate(self):
        # FIXME: Not tested
        provider = self._get_provider()
        g = provider.paginate(provider.DEFAULT_URI)

        uris = set()
        count = 0
        for _ in range(10):
            try:
                uris.add(next(g))
                count = count + 1
            except StopIteration:
                break

        self.assertTrue(len(uris) > 0,
                        msg="paginate doesn't produce any element")
        self.assertTrue(len(uris) == count,
                        msg="paginate produces duplicates")

    def test_url_handler(self):
        cls = self._get_provider_cls()
        tests = ([(url, True) for url in self.TEST_HANDLED_URLS] +
                 [(url, False) for url in self.TEST_HANDLED_URLS_NEGATIVE])

        for (url, expected) in tests:
            can_handle = cls.can_handle(url)
            self.assertTrue(can_handle == expected)

    def test_query(self):
        provider = self._get_provider()
        for (query, url_or_exc) in self.TEST_QUERY_URLS:
            if isinstance(query, str):
                query = Query.fromstring(query)
            else:
                query = Query(**query)

            if type(url_or_exc) is type and issubclass(url_or_exc, Exception):
                with self.assertRaises(url_or_exc):
                    provider.get_query_uri(query)
            else:
                url = provider.get_query_uri(query)
                self.assertEqual(url_or_exc, url)

    def test_parse(self):
        pass


class TestEPubLibre(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = EPubLibre
    TEST_QUERY_URLS = [
        ('westworld.s01e02', IncompatibleQueryError),
        ('some.movie.2019', IncompatibleQueryError),
        (dict(type='ebook', ebook_title='title'), 'https://epublibre.org/catalogo/index/0/nuevo/novedades/sin/todos/title'),
        (dict(type='ebook', ebook_title='title', ebook_author='author'), 'https://epublibre.org/catalogo/index/0/nuevo/novedades/sin/todos/author%20title'),
        (dict(type='ebook', ebook_author='author'), 'https://epublibre.org/catalogo/index/0/nuevo/novedades/sin/todos/author'),
        (dict(type='ebook', name='title'), 'https://epublibre.org/catalogo/index/0/nuevo/novedades/sin/todos/title'),
        (dict(type='ebook', other='foo'), IncompatibleQueryError),
    ]


class TestEzTV(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = EzTV
    TEST_QUERY_URLS = [
        ('westworld.s01e02', 'https://eztv.io/search/westworld'),
        ('some.movie.2019', IncompatibleQueryError)
    ]


class TestTorrentAPI(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = TorrentAPI
    TEST_QUERY_URLS = [
        ('westworld.s01e02', 'http://torrentapi.org/pubapi_v2.php?app_id=arroyo&mode=search&search_string=westworld+S01E02&category=tv'),
        ('some.movie.2019', 'http://torrentapi.org/pubapi_v2.php?app_id=arroyo&mode=search&search_string=some+movie&category=movies')
    ]


if __name__ == '__main__':
    unittest.main()
