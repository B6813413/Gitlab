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

    def test_post_invalid_returns_400_with_message(self):
        resp = self.client.post("/", data=dict(self.valid, vcc="0"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ต้องมากกว่า 0".encode("utf-8"), resp.data)

    def test_invalid_post_keeps_user_values(self):
        resp = self.client.post("/", data=dict(self.valid, r1="abc"))
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b'value="abc"', resp.data)
        self.assertIn(b'value="22k"', resp.data)

    def test_all_blank_returns_400(self):
        resp = self.client.post("/", data={})
        self.assertEqual(resp.status_code, 400)
        self.assertNotIn(b"Active", resp.data)

    def test_post_cutoff_shows_warning(self):
        resp = self.client.post("/", data=dict(self.valid, r2="2.2k"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Cutoff", resp.data)
        self.assertIn("Forward-Active".encode("utf-8"), resp.data)

    def test_post_with_kohm_unit_select(self):
        data = {"vcc": "12", "vcc_unit": "V",
                "r1": "100", "r1_unit": "kohm",
                "r2": "22", "r2_unit": "kohm",
                "rc": "2.2", "rc_unit": "kohm",
                "re": "1", "re_unit": "kohm",
                "beta": "100", "vbe": "0.7"}
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"8.052 V", resp.data)
        self.assertIn(b"1.230 mA", resp.data)

    def test_post_with_bad_kohm_value_returns_400(self):
        data = dict(self.valid, r1="abc", r1_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn(b"abc", resp.data)


class TestBiasModeSelection(unittest.TestCase):
    """เลือกโหมดวงจรได้สามแบบ; โหมดเดิมต้องให้ผลเดิมเมื่อกรอกค่าเดิม."""

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        self.common = {"vcc": "12", "rc": "2.2k", "beta": "100", "vbe": "0.7"}

    def test_get_shows_mode_selector(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'name="mode"', resp.data)
        self.assertIn(b"Voltage Divider Bias", resp.data)
        self.assertIn(b"Fixed Bias", resp.data)
        self.assertIn(b"Emitter Bias", resp.data)

    def test_post_voltage_divider_preserves_lab2_result(self):
        # Voltage Divider กับค่าเดิมต้องให้ผลเหมือน Lab 2 (เดิมต้องให้ผลเดิม)
        data = dict(self.common, mode="voltage_divider",
                    r1="100k", r2="22k", re="1k",
                    r1_unit="kohm", r2_unit="kohm", re_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"1.230 mA", resp.data)   # IC
        self.assertIn(b"8.052 V", resp.data)    # VCE
        self.assertIn(b"1.942 V", resp.data)    # VB
        self.assertIn(b"Voltage Divider Bias", resp.data)

    def test_post_fixed_bias_shows_result(self):
        data = dict(self.common, mode="fixed", rb="1000k", rb_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"1.130 mA", resp.data)   # IC
        self.assertIn(b"9.514 V", resp.data)    # VCE
        self.assertIn(b"Fixed Bias", resp.data)
        self.assertNotIn(b"VTH", resp.data)     # Fixed Bias ไม่มี VTH/RTH

    def test_post_emitter_bias_shows_result(self):
        data = dict(self.common, mode="emitter", rb="1000k", re="1k",
                    rb_unit="kohm", re_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"1.026 mA", resp.data)   # IC
        self.assertIn(b"8.705 V", resp.data)    # VCE
        self.assertIn(b"Emitter Bias", resp.data)

    def test_post_fixed_rb_zero_returns_400(self):
        # RB = 0 → ต้องมากกว่า 0 → HTTP 400, เว็บไม่ล่ม, ไม่แสดงผลเก่า
        data = dict(self.common, mode="fixed", rb="0", rb_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ต้องมากกว่า 0".encode("utf-8"), resp.data)

    def test_post_emitter_missing_re_returns_400(self):
        data = dict(self.common, mode="emitter", rb="1000k", rb_unit="kohm")
        resp = self.client.post("/", data=data)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("re".encode("utf-8"), resp.data)
