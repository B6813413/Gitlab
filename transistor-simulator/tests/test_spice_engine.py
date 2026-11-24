import unittest
from spice_engine import SPICE_DEFAULTS, build_netlist, validate_spice_inputs

class TestNetlist(unittest.TestCase):
    def test_dc_netlist_has_op_and_expected_nodes(self):
        net = build_netlist(SPICE_DEFAULTS, "dc")
        self.assertIn(".op", net)
        self.assertNotIn(".ac", net)
        self.assertNotIn(".tran", net)
        for token in ("R1 vcc b 100k", "R2 b 0 22k", "RC vcc c 2.2k",
                      "RE e 0 1k", "Q1 c b e", "CIN vin b 10u",
                      "COUT c vout 10u", "RL vout 0 10k", ".end"):
            self.assertIn(token, net)

    def test_ac_and_tran_are_distinct_directives(self):
        ac = build_netlist(SPICE_DEFAULTS, "ac")
        tran = build_netlist(SPICE_DEFAULTS, "tran")
        self.assertIn(".ac dec", ac)
        self.assertIn("vdb(vout)", ac)
        self.assertNotIn(".tran", ac)
        self.assertIn(".tran", tran)
        self.assertIn("v(vin)", tran)
        self.assertNotIn(".ac", tran)

    def test_changed_params_change_netlist(self):
        base = build_netlist(SPICE_DEFAULTS, "tran")
        changed = build_netlist(dict(SPICE_DEFAULTS, re="2k", freq="2k"), "tran")
        self.assertNotEqual(base, changed)
        self.assertIn("RE e 0 2k", changed)
        self.assertIn("2k 0 0", changed)

    def test_unknown_analysis_raises(self):
        with self.assertRaises(ValueError):
            build_netlist(SPICE_DEFAULTS, "bogus")

class TestSpiceValidation(unittest.TestCase):
    def test_re_zero_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, re="0"))
        self.assertIn("re", errs)
        self.assertEqual(errs["re"], "ต้องมากกว่า 0")

    def test_injection_string_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, amp="0.01;rm -rf /"))
        self.assertIn("amp", errs)

    def test_non_finite_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, freq="nan"))
        self.assertIn("freq", errs)


class TestSpiceValidationGuards(unittest.TestCase):
    """Extra guards for behaviour the brief mandates without sample tests."""

    def test_defaults_are_valid(self):
        self.assertEqual(validate_spice_inputs(SPICE_DEFAULTS), {})

    def test_bjt_model_injection_rejected(self):
        errs = validate_spice_inputs(
            dict(SPICE_DEFAULTS, bjt_model="QNPN)\n.model evil NPN")
        )
        self.assertIn("bjt_model", errs)

    def test_cin_zero_rejected(self):
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, cin="0"))
        self.assertEqual(errs.get("cin"), "ต้องมากกว่า 0")

    def test_netlist_builder_refuses_invalid_params(self):
        with self.assertRaises(ValueError):
            build_netlist(dict(SPICE_DEFAULTS, amp="0.01;rm -rf /"), "dc")
