import unittest


import time

from arroyo.query import Engine as QueryEngine
from arroyo.plugins.filters.generic import (
    SourceAttributeFilter,
    EpisodeAttributeFilter,
    MovieAttributeFilter
)
from arroyo.plugins.sorters.basic import (
    Basic as BasicSorter
)

from testlib import (
    build_item,
)


class TestGenericFilter(unittest.TestCase):
    def test_eq_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        # Test strings
        self.assertTrue(f.filter('name', 'Series A S01E01', i))
        self.assertFalse(f.filter('name', 'xxx', i))

        # Test integers
        self.assertTrue(f.filter('size', 100, i))
        self.assertFalse(f.filter('size', 200, i))

    def test_glob_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        self.assertTrue(f.filter('name-glob', 'Series * S01E01', i))
        self.assertFalse(f.filter('name-glob', 'Foo *', i))

    def test_like_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        self.assertTrue(f.filter('name-like', r'Series [AB] S01E01', i))
        self.assertFalse(f.filter('name-like', r'Series [CD] S01E01', i))

    def test_in_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        self.assertTrue(f.filter('provider-in', 'prov1, prov2', i))

    def test_max_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')
        self.assertTrue(f.filter('size-max', 100, i))
        self.assertFalse(f.filter('size-max', 99, i))

    def test_min_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')
        self.assertTrue(f.filter('size-min', 100, i))
        self.assertFalse(f.filter('size-min', 101, i))

    def test_type(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        self.assertTrue(f.filter('type', 'episode', i))
        self.assertFalse(f.filter('type', 'movie', i))

    def test_age(self):
        now = int(time.time())
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', created=now-100)

        self.assertTrue(f.filter('age-min', 50, i))
        self.assertFalse(f.filter('age-min', 200, i))

        self.assertTrue(f.filter('age-max', 200, i))
        self.assertFalse(f.filter('age-max', 50, i))

    def test_since(self):
        f = SourceAttributeFilter()
        i = build_item('Foo', created=1577833200)  # 2020-01-01

        self.assertTrue(f.filter('since', '2019', i))
        self.assertFalse(f.filter('since', '2021', i))


class TestEntityAttributeFilter(unittest.TestCase):
    def test_basic_attribute_match(self):
        f = EpisodeAttributeFilter()
        i = build_item('Series A S02E03')

        self.assertTrue(f.filter('series', 'Series A', i))
        self.assertFalse(f.filter('series', 'Series B', i))

    def test_alias_filter(self):
        f = EpisodeAttributeFilter()
        i = build_item('Series A (2017) S02E03')

        self.assertTrue(f.filter('series-year', '2017', i))

    def test_alias_filter_with_modifier(self):
        f = MovieAttributeFilter()
        i = build_item("My.Friend.Flicka.1943.1080p.AMZN.WEBRip.DDP2.0.x264")

        self.assertTrue(f.filter('movie-year-max', '1950', i))

    def test_filter_none(self):
        f = MovieAttributeFilter()
        m1 = build_item('Some movie (1998).avi', type='movie')
        m2 = build_item('Some movie.avi', type='movie')

        self.assertTrue(f.filter('movie-year', '1998', m1))
        self.assertFalse(f.filter('movie-year', '1998', m2))


class TestSorter(unittest.TestCase):
    def test_proper(self):
        s = BasicSorter()

        i1 = build_item('series x s01e01.mp4')
        i2 = build_item('series x s01e01.proper.mp4')

        r = s.sort([i1, i2])
        self.assertTrue(r[0] == i2)

    def test_by_seeds(self):
        s = BasicSorter()

        i1 = build_item('the.movie', seeds=1000)
        i2 = build_item('the.movie', seeds=100)
        i3 = build_item('the.movie', seeds=500)

        r = s.sort([i1, i2, i3])
        self.assertTrue(r == [i1, i3, i2])

    def test_by_ratio(self):
        s = BasicSorter()

        i1 = build_item('the.movie', seeds=100, leechers=5)
        i2 = build_item('the.movie', seeds=100, leechers=200)
        i3 = build_item('the.movie', seeds=100, leechers=50)

        r = s.sort([i1, i2, i3])
        self.assertTrue(r == [i1, i3, i2])


if __name__ == '__main__':
    unittest.main()
