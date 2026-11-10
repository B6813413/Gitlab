import unittest

from dc_bias import dc_operating_point, parse_resistance, validate_inputs


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
