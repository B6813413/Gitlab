import unittest

from dc_bias import (
    compute_bias, dc_operating_point, emitter_bias, fixed_bias,
    parse_resistance, validate_inputs,
)


class TestDCOperatingPoint(unittest.TestCase):
    def test_active_region_matches_reference(self):
        r = dc_operating_point(12, 100000, 22000, 2200, 1000, 100, 0.7)
        self.assertAlmostEqual(r["vth"], 2.1639344262295084, places=9)
        self.assertAlmostEqual(r["rth"], 18032.786885245903, places=6)
        self.assertAlmostEqual(r["ib"], 1.2298581462608458e-05, places=12)
        self.assertAlmostEqual(r["ic"], 0.0012298581462608458, places=12)
        self.assertAlmostEqual(r["ie"], 0.0012421567277234543, places=12)
        self.assertAlmostEqual(r["ve"], 1.2421567277234544, places=9)
        self.assertAlmostEqual(r["vb"], 1.9421567277234544, places=9)
        self.assertAlmostEqual(r["vc"], 9.29431207822614, places=9)
        self.assertAlmostEqual(r["vce"], 8.052155350502685, places=9)
        self.assertEqual(r["region"], "active")

    def test_zero_r1_plus_r2_raises_value_error(self):
        with self.assertRaises(ValueError):
            dc_operating_point(12, 100.0, -100.0, 2200, 1000, 100, 0.7)

    def test_zero_rc_plus_re_raises_value_error(self):
        with self.assertRaises(ValueError):
            dc_operating_point(12, 100000, 22000, 2200, -2200, 100, 0.7)

    def test_saturation_region_detected(self):
        r = dc_operating_point(12, 100000, 22000, 10000, 1000, 100, 0.7)
        self.assertEqual(r["region"], "saturation")
        self.assertAlmostEqual(r["ic_sat"], 1.0727272727272728e-03, places=12)
        self.assertLess(r["vce"], 0)

    def test_cutoff_region_detected(self):
        r = dc_operating_point(12, 100000, 2200, 2200, 1000, 100, 0.7)
        self.assertEqual(r["region"], "cutoff")
        self.assertLessEqual(r["vth"], 0.7)

    def test_beta_one_is_active(self):
        r = dc_operating_point(12, 100000, 22000, 2200, 1000, 1, 0.7)
        self.assertEqual(r["region"], "active")
        self.assertAlmostEqual(r["ib"], 7.307692307692309e-05, places=12)


class TestParseResistance(unittest.TestCase):
    def test_plain_ohms(self):
        self.assertEqual(parse_resistance("100000"), 100000.0)

    def test_k_suffix(self):
        self.assertEqual(parse_resistance("100k"), 100000.0)
        self.assertEqual(parse_resistance("2.2k"), 2200.0)
        self.assertEqual(parse_resistance(" 10 K "), 10000.0)

    def test_invalid_raises(self):
        for bad in ("", "abc", "nan", "inf", "1e999"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    parse_resistance(bad)


class TestValidateInputs(unittest.TestCase):
    def base(self, **over):
        data = {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                "re": "1k", "beta": "100", "vbe": "0.7"}
        data.update(over)
        return data

    def test_valid_input_has_no_errors(self):
        self.assertEqual(validate_inputs(self.base()), {})

    def test_blank_field_is_rejected(self):
        self.assertIn("vcc", validate_inputs(self.base(vcc="")))

    def test_non_numeric_is_rejected(self):
        self.assertIn("r1", validate_inputs(self.base(r1="abc")))

    def test_non_finite_is_rejected(self):
        self.assertIn("rc", validate_inputs(self.base(rc="1e999")))

    def test_non_positive_resistors_rejected(self):
        for field in ("r1", "r2", "rc"):
            with self.subTest(field=field):
                self.assertIn(field, validate_inputs(self.base(**{field: "0"})))

    def test_negative_re_is_rejected(self):
        self.assertIn("re", validate_inputs(self.base(re="-1")))

    def test_beta_must_be_positive(self):
        for bad in ("0", "-5", "abc"):
            with self.subTest(bad=bad):
                self.assertIn("beta", validate_inputs(self.base(beta=bad)))

    def test_vbe_must_be_between_zero_and_vcc(self):
        self.assertIn("vbe", validate_inputs(self.base(vbe="0")))
        self.assertIn("vbe", validate_inputs(self.base(vbe="12")))

    def test_zero_vcc_is_rejected(self):
        self.assertIn("vcc", validate_inputs(self.base(vcc="0")))

    def test_zero_r1_plus_r2_does_not_divide_by_zero(self):
        errors = validate_inputs(self.base(r1="0", r2="0"))
        self.assertIn("r1", errors)
        self.assertIn("r2", errors)

class TestParseResistanceUnit(unittest.TestCase):
    def test_kohm_unit_multiplier(self):
        self.assertEqual(parse_resistance("100", "kohm"), 100000.0)
        self.assertEqual(parse_resistance("2.2", "kohm"), 2200.0)
        self.assertEqual(parse_resistance("100", "ohm"), 100.0)
        self.assertEqual(parse_resistance("1000", "ohm"), 1000.0)

    def test_k_suffix_overrides_unit(self):
        self.assertEqual(parse_resistance("100k", "kohm"), 100000.0)
        self.assertEqual(parse_resistance("2.2k", "ohm"), 2200.0)


class TestValidateInputsWithUnits(unittest.TestCase):
    def base(self, **over):
        data = {"vcc": "12", "r1": "100", "r1_unit": "kohm",
                "r2": "22", "r2_unit": "kohm",
                "rc": "2.2", "rc_unit": "kohm",
                "re": "1", "re_unit": "kohm",
                "beta": "100", "vbe": "0.7"}
        data.update(over)
        return data

    def test_valid_kohm_input_has_no_errors(self):
        self.assertEqual(validate_inputs(self.base()), {})

    def test_zero_kohm_resistor_is_rejected(self):
        self.assertIn("r1", validate_inputs(self.base(r1="0")))

    def test_invalid_kohm_value_is_rejected(self):
        self.assertIn("r2", validate_inputs(self.base(r2="abc")))


class TestFixedBias(unittest.TestCase):
    """Fixed Bias — คำนวณมืออิสระ (อิสระจากเว็บแอปที่ทดสอบ).

    VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V, RB=1 MΩ
    IB = (12 − 0.70) / 1,000,000 = 11.3 µA
    IC = 100 × IB = 1.13 mA; VE = 0; VB = 0.70 V
    VC = 12 − 1.13 mA × 2.2 kΩ = 9.514 V; VCE = 9.514 V
    """

    def test_fixed_bias_matches_hand_calculation(self):
        r = fixed_bias(12.0, 2200.0, 100.0, 0.7, 1_000_000.0)
        self.assertAlmostEqual(r["ib"], 1.13e-05, places=12)
        self.assertAlmostEqual(r["ic"], 1.13e-03, places=12)
        self.assertAlmostEqual(r["ie"], 1.1413e-03, places=12)
        self.assertAlmostEqual(r["ve"], 0.0, places=12)
        self.assertAlmostEqual(r["vb"], 0.7, places=12)
        self.assertAlmostEqual(r["vc"], 9.514, places=9)
        self.assertAlmostEqual(r["vce"], 9.514, places=9)
        self.assertEqual(r["region"], "active")
        self.assertIsNone(r["warning"])

class TestEmitterBias(unittest.TestCase):
    """Emitter Bias — คำนวณมืออิสระ (อิสระจากเว็บแอปที่ทดสอบ).

    VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V, RB=1 MΩ, RE=1 kΩ
    IB = (12 − 0.70) / [1,000,000 + 101 × 1,000] ≈ 10.2634 µA
    IC = 100 × IB ≈ 1.0263 mA
    VE = IE × RE ≈ 1.0366 V; VB ≈ 1.7366 V
    VC = 12 − IC × 2.2 kΩ ≈ 9.7421 V; VCE ≈ 8.7054 V
    """

    def test_emitter_bias_matches_hand_calculation(self):
        r = emitter_bias(12.0, 2200.0, 100.0, 0.7, 1_000_000.0, 1000.0)
        self.assertAlmostEqual(r["ib"], 1.02633969e-05, places=10)
        self.assertAlmostEqual(r["ic"], 1.02633969e-03, places=10)
        self.assertAlmostEqual(r["ie"], 1.03660309e-03, places=10)
        self.assertAlmostEqual(r["ve"], 1.03660309, places=7)
        self.assertAlmostEqual(r["vb"], 1.73660309, places=7)
        self.assertAlmostEqual(r["vc"], 9.74205268, places=7)
        self.assertAlmostEqual(r["vce"], 8.70544959, places=7)
        self.assertEqual(r["region"], "active")
        self.assertIsNone(r["warning"])

    def test_emitter_bias_higher_re_lowers_ic(self):
        # เปลี่ยน RE จาก 1 kΩ → 2 kΩ: IC ต้องลดลง (ทิศทางเดียวกับกรณี A4)
        r1k = emitter_bias(12.0, 2200.0, 100.0, 0.7, 1_000_000.0, 1000.0)
        r2k = emitter_bias(12.0, 2200.0, 100.0, 0.7, 1_000_000.0, 2000.0)
        self.assertLess(r2k["ic"], r1k["ic"])
        self.assertGreater(r2k["ve"], r1k["ve"])
        # VCE = VC - VE: เมื่อ RE มากขึ้น VE เพิ่มมากกว่าที่ VC เพิ่ม → VCE ลดลง
        self.assertLess(r2k["vce"], r1k["vce"])


class TestComputeBiasDispatch(unittest.TestCase):
    """compute_bias เลือกฟังก์ชันตามโหมด; โหมดไม่รู้จักต้องแจ้งข้อผิดพลาด."""

    def test_voltage_divider_unchanged(self):
        r = compute_bias("voltage_divider", {
            "vcc": 12.0, "r1": 100000.0, "r2": 22000.0, "rc": 2200.0,
            "re": 1000.0, "beta": 100.0, "vbe": 0.7,
        })
        self.assertEqual(r["mode"], "voltage_divider")
        self.assertAlmostEqual(r["ic"], 0.0012298581462608458, places=12)
        self.assertAlmostEqual(r["vce"], 8.052155350502685, places=9)
        self.assertIsNone(r["error"])

    def test_fixed_via_compute_bias(self):
        r = compute_bias("fixed", {
            "vcc": 12.0, "rc": 2200.0, "beta": 100.0, "vbe": 0.7, "rb": 1_000_000.0,
        })
        self.assertEqual(r["mode"], "fixed")
        self.assertAlmostEqual(r["ic"], 1.13e-03, places=12)
        self.assertAlmostEqual(r["vce"], 9.514, places=9)
        self.assertIsNone(r["error"])

    def test_emitter_via_compute_bias(self):
        r = compute_bias("emitter", {
            "vcc": 12.0, "rc": 2200.0, "beta": 100.0, "vbe": 0.7,
            "rb": 1_000_000.0, "re": 1000.0,
        })
        self.assertEqual(r["mode"], "emitter")
        self.assertAlmostEqual(r["ic"], 1.02633969e-03, places=10)
        self.assertAlmostEqual(r["vce"], 8.70544959, places=7)
        self.assertIsNone(r["error"])

    def test_unknown_mode_returns_error(self):
        r = compute_bias("bogus_mode", {
            "vcc": 12.0, "rc": 2200.0, "beta": 100.0, "vbe": 0.7,
        })
        self.assertIsNotNone(r["error"])
        self.assertIn("ไม่รู้จัก", r["error"])

    def test_missing_common_input_returns_error(self):
        r = compute_bias("fixed", {"vcc": 12.0, "rc": 2200.0, "beta": 100.0})
        self.assertIsNotNone(r["error"])


class TestValidateInputsPerMode(unittest.TestCase):
    """validate_inputs ตรวจเฉพาะช่องที่จำเป็นของโหมดนั้น (Lab 03)."""

    def base_divider(self):
        return {"vcc": "12", "r1": "100k", "r2": "22k", "rc": "2.2k",
                "re": "1k", "beta": "100", "vbe": "0.7"}

    def base_fixed(self):
        return {"vcc": "12", "rc": "2.2k", "rb": "1000k", "beta": "100", "vbe": "0.7"}

    def base_emitter(self):
        return {"vcc": "12", "rc": "2.2k", "rb": "1000k", "re": "1k",
                "beta": "100", "vbe": "0.7"}

    def test_divider_valid_no_errors(self):
        self.assertEqual(validate_inputs(self.base_divider(), "voltage_divider"), {})

    def test_fixed_valid_no_errors(self):
        self.assertEqual(validate_inputs(self.base_fixed(), "fixed"), {})

    def test_emitter_valid_no_errors(self):
        self.assertEqual(validate_inputs(self.base_emitter(), "emitter"), {})

    def test_fixed_does_not_require_r1_r2(self):
        # Fixed Bias ไม่ต้องกรอก R1/R2 → ต้องไม่มีข้อผิดพลาดเรื่อง r1/r2
        data = self.base_fixed()
        errors = validate_inputs(data, "fixed")
        self.assertNotIn("r1", errors)
        self.assertNotIn("r2", errors)

    def test_fixed_requires_rb(self):
        data = self.base_fixed()
        data["rb"] = ""
        self.assertIn("rb", validate_inputs(data, "fixed"))

    def test_emitter_requires_rb_and_re(self):
        data = self.base_emitter()
        data["rb"] = ""
        self.assertIn("rb", validate_inputs(data, "emitter"))
        data = self.base_emitter()
        data["re"] = ""
        self.assertIn("re", validate_inputs(data, "emitter"))

    def test_fixed_rb_zero_rejected(self):
        data = self.base_fixed()
        data["rb"] = "0"
        self.assertIn("rb", validate_inputs(data, "fixed"))

    def test_unknown_mode_rejected(self):
        self.assertIn("mode", validate_inputs({}, "bogus_mode"))
