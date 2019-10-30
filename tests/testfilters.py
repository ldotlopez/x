import unittest


from arroyo.normalize import normalize_one

from urllib import parse
from arroyo.schema import Source
from arroyo.plugins.filters.generic import Generic


def build_source(name, **kwargs):
    uri = 'magnet:?dn=' + parse.quote(name)
    return Source(provider='mock', name=name, uri=uri, **kwargs)


def build_item(name, **kwargs):
    src = build_source(name, **kwargs)
    item = normalize_one(src)

    return item


class TestGenericFilter(unittest.TestCase):
    def test_string_filter(self):
        f = Generic()
        i = build_item('Series A S01E01')

        self.assertTrue(f.filter('name', 'Series A S01E01', i))
        self.assertFalse(f.filter('name', 'xxx', i))


if __name__ == '__main__':
    unittest.main()
