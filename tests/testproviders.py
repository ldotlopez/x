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


from arroyo.plugins.providers.dummy import (
    RarBG,
    ThePirateBay,
)


class TestProviderMixin:
    PROVIDER_CLASS = None
    TEST_HANDLED_URLS = []
    TEST_HANDLED_URLS_NEGATIVE = []

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


class TestRarBG(TestProviderMixin, unittest.TestCase):
    PROVIDER_CLASS = RarBG
    TEST_HANDLED_URLS = [
        'https://www.rarbg.com/a/b'
    ]
    TEST_HANDLED_URLS_NEGATIVE = [
        'http://www.foobar.com/'
    ]


if __name__ == '__main__':
    unittest.main()