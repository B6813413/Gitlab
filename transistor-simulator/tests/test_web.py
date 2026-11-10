import unittest

from app import app


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
