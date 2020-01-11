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


from arroyo.query import (
    Query,
    InvalidQueryParameters
)


TESTS = [
    ('foo.s01e02',
     dict(type='episode', series='foo', season=1, number=2)),

    ('foo.s01e02.720p',
     dict(type='episode', series='foo', season=1, number=2, quality='720p')),

    ('foo.s01e02.720p x265',
     dict(type='episode', series='foo', season=1, number=2, quality='720p', codec='H.265')),

    ('foo 2019 4k',
     dict(type='movie', title='foo', movie_year=2019, quality='2160p')),

    ('BBC.Earths.Tropical.Islands.2of3.Borneo.1080p.HDTV',
     dict(type='episode', series='BBC Earths Tropical Islands', season=0, number=2, source='HDTV', quality='1080p')),
]


class QueryTest(unittest.TestCase):
    def test_fromstring(self):
        for (s, expected) in TESTS:
            if expected is InvalidQueryParameters:
                with self.assertRaises(InvalidQueryParameters):
                    Query.fromstring(s)

            else:
                expected['state'] = expected.pop('state', 'none')

                q1 = Query.fromstring(s)
                q2 = Query(**expected)

                self.assertEqual(
                    sorted(dict(q1).items()),
                    sorted(dict(q2).items()),
                    msg=s)


if __name__ == '__main__':
    unittest.main()
