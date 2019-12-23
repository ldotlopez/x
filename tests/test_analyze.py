import unittest


from arroyo.analyze import analyze
from arroyo.schema import Movie


from testlib import build_source


class TestAnalyze(unittest.TestCase):
    def test_source_with_invalid_type_hint(self):
        src = build_source('foo')  # build_source doesnt do parse
        src.hints = {'type': 'other'}

        asrc = analyze(src, mp=False)[0]

        self.assertTrue(isinstance(asrc.entity, Movie))


if __name__ == '__main__':
    unittest.main()
