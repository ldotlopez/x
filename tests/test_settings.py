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
from arroyo.kit.settings import (
    Settings,
    InvalidKeyError,
    NotNamespaceError
)
from arroyo.kit.storage import MemoryStorage


class TestSettings(unittest.TestCase):
    def setUp(self):
        self.s = Settings(MemoryStorage())

    def test_set_get(self):
        self.s.set('foo', 1)
        self.assertEqual(self.s.get('foo'), 1)

    def test_get_with_default(self):
        self.assertEqual(self.s.get('foo', 1), 1)

    def test_get_without_default(self):
        with self.assertRaises(KeyError):
            self.s.get('foo')

    def test_get_on_namespace(self):
        self.s.set('foo.a', 1)
        self.s.set('foo.b', 2)
        self.s.set('foo.c', 3)

        self.assertEqual(self.s.get('foo'), dict(a=1, b=2, c=3))

    def test_invalid_key(self):
        with self.assertRaises(InvalidKeyError):
            self.s.get('.a')

        with self.assertRaises(InvalidKeyError):
            self.s.get('a.')

        with self.assertRaises(InvalidKeyError):
            self.s.get('')

        with self.assertRaises(InvalidKeyError):
            self.s.get('a..b')

        with self.assertRaises(InvalidKeyError):
            self.s.get('a-b')

        with self.assertRaises(InvalidKeyError):
            self.s.get('aB')

    def test_children(self):
        self.s.set('query.name1.foo', 'bar')
        self.s.set('query.name2.foo', 'bar')

        children = self.s.children('query')
        self.assertEqual(children, ['name1', 'name2'])

    def test_children_of_leaf(self):
        self.s.set('query.name1.foo', 'bar')
        with self.assertRaises(NotNamespaceError):
            self.s.children('query.name1.foo')

    def test_children_of_missing_key(self):
        with self.assertRaises(InvalidKeyError):
            self.s.children('foo')


if __name__ == '__main__':
    unittest.main()
