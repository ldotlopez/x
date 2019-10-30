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


from arroyo.plugins.providers.epublibre import EPubLibre
from arroyo.plugins.providers.eztv import EzTV
from arroyo.plugins.providers.torrentapi import TorrentAPI


class TestProviderMixin:
    PROVIDER_CLASS = None
    TEST_HANDLED_URLS = []
    TEST_HANDLED_URLS_NEGATIVE = []

    def test_default_uri(self):
        cls = self.PROVIDER_CLASS
        default_uri = getattr(cls, 'DEFAULT_URI', None)

        self.assertTrue(isinstance(default_uri, str) and
                        default_uri != '',
                        msg="provider doesn't have default uri")

        self.assertTrue(cls.can_handle(default_uri),
                        msg="provider can't handle its own default uri")

    def test_handlers(self):
        cls = self.PROVIDER_CLASS
        globs = getattr(cls, 'URI_GLOBS')
        regexps = getattr(cls, 'URI_REGEXPS')

        self.assertTrue(isinstance(globs, list))
        self.assertTrue(isinstance(regexps, list))
        self.assertTrue(globs or regexps)

    def test_paginate(self):
        # FIXME: Not tested
        cls = self.PROVIDER_CLASS
        g = cls().paginate(cls.DEFAULT_URI)

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
        cls = self.PROVIDER_CLASS
        tests = ([(url, True) for url in self.TEST_HANDLED_URLS] +
                 [(url, False) for url in self.TEST_HANDLED_URLS_NEGATIVE])

        for (url, expected) in tests:
            can_handle = cls.can_handle(url)
            self.assertTrue(can_handle == expected)

    def test_query(self):
        pass

    def test_parse(self):
        pass


class TestEPubLibre(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = EPubLibre


class TestEzTV(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = EzTV


class TestTorrentAPI(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = TorrentAPI


if __name__ == '__main__':
    unittest.main()
