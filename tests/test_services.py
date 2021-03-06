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


from arroyo.services import ClassLoader


class Foo:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def ident(self, *args, **kwargs):
        return (args, kwargs)


class TestClassLoader(unittest.TestCase):
    def test_get_class(self):
        cl = ClassLoader()
        cl.register('x', Foo)
        foocls = cl.get_class('x')

        self.assertTrue(foocls is Foo)

    def test_get(self):
        cl = ClassLoader()
        cl.register('foo', Foo)
        foo = cl.get('foo', 1, 2, a=3)

        self.assertTrue(isinstance(foo, Foo))
        self.assertTrue(foo.args == (1, 2))
        self.assertTrue(foo.kwargs == dict(a=3))


if __name__ == '__main__':
    unittest.main()
