import unittest


import time
from urllib import parse


from arroyo.normalize import normalize_one
from arroyo.schema import Source
from arroyo.plugins.filters.generic import (
    SourceAttributeFilter,
    EpisodeAttributeFilter,
    MovieAttributeFilter
)


def build_source(name, **kwargs):
    uri = 'magnet:?dn=' + parse.quote(name)
    params = {
        'uri': uri,
        'provider': 'mock'
    }
    params.update(kwargs)
    return Source(name=name, **params)


def build_item(name, **kwargs):
    src = build_source(name, **kwargs)
    item = normalize_one(src)

    return item


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
        self.assertFalse(f.filter('name-like', r'Series \d+ S01E01', i))

    def test_in_func(self):
        f = SourceAttributeFilter()
        i = build_item('Series A S01E01', size=100, provider='prov1')

        # Test containers
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


class TestEntityAttributeFilter(unittest.TestCase):
    def test_a(self):
        f = EpisodeAttributeFilter()
        i = build_item('Series A S02E03')

        self.assertTrue(f.filter('series', 'Series A', i))
        self.assertFalse(f.filter('series', 'Series B', i))

    def test_b(self):
        f = EpisodeAttributeFilter()
        i = build_item('Series A (2017) S02E03')

        self.assertTrue(f.filter('series-year', '2017', i))


if __name__ == '__main__':
    unittest.main()
