import unittest

from testlib import build_source


class TestSource(unittest.TestCase):
    def test_urn_as_id(self):
        src = build_source('foo')
        self.assertEqual(
            src.id,
            "urn:btih:0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        )

    def test_invalid_urn(self):
        with self.assertRaises(ValueError):
            src = build_source('foo', uri="magnet:?dn=foo&xt=urn:btih:invalid")


    def test_id_case_normalization(self):
        src = build_source('foo', uri="magnet:?dn=foo&xt=urn:btih:0BEEC7B5EA3F0FDBC95D0DD47F3C5BC275DA8A33")
        self.assertEqual(
            src.id,
            "urn:btih:0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        )

    def test_id_b64_normalization(self):
        src = build_source('foo', uri="magnet:?dn=foo&xt=urn:btih:BPXMPNPKH4H5XSK5BXKH6PC3YJ25VCRT")
        self.assertEqual(
            src.id,
            "urn:btih:0beec7b5ea3f0fdbc95d0dd47f3c5bc275da8a33"
        )

if __name__ == '__main__':
    unittest.main()
