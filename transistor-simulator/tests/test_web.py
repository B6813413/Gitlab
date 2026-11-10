import unittest

from app import app, format_current, format_voltage, format_resistance


class TestIndexPage(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_get_index_returns_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        for field in (b'name="vcc"', b'name="r1"', b'name="r2"', b'name="rc"',
                      b'name="re"', b'name="beta"', b'name="vbe"'):
            self.assertIn(field, resp.data)
        self.assertIn(b'value="0.7"', resp.data)

class TestCalculateRoute(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.valid = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                      "re": "1k", "beta": "100", "vbe": "0.7"}

    def test_post_valid_shows_operating_point(self):
        resp = self.client.post("/", data=self.valid)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"2.164 V", resp.data)
        self.assertIn(b"18.033 k\xce\xa9", resp.data)
        self.assertIn(b"12.299 \xc2\xb5A", resp.data)
        self.assertIn(b"1.230 mA", resp.data)
        self.assertIn(b"1.242 mA", resp.data)
        self.assertIn(b"1.242 V", resp.data)
        self.assertIn(b"1.942 V", resp.data)
        self.assertIn(b"9.294 V", resp.data)
        self.assertIn(b"8.052 V", resp.data)
        self.assertIn(b"Active", resp.data)

    def test_post_saturation_shows_warning(self):
        resp = self.client.post("/", data=dict(self.valid, rc="10k"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Saturation", resp.data)
        self.assertIn(b"1.073 mA", resp.data)
        self.assertIn("Forward-Active".encode("utf-8"), resp.data)

    def test_formatters_use_engineering_units(self):
        self.assertEqual(format_current(12.299e-06), "12.299 \u00b5A")
        self.assertEqual(format_current(1.229858e-03), "1.230 mA")
        self.assertEqual(format_voltage(8.0521553), "8.052 V")
        self.assertEqual(format_resistance(18032.7869), "18.033 k\u03a9")
