import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from spice_engine import (
    SPICE_DEFAULTS,
    build_netlist,
    parse_ac_log,
    parse_op_log,
    parse_print_table,
    run_analysis,
    validate_spice_inputs,
)

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

    def test_ac_netlist_prints_vin_reference_for_gain_and_phase(self):
        # Gain must be Vout/Vin, not absolute Vout; phase must subtract Vin.
        ac = build_netlist(SPICE_DEFAULTS, "ac")
        for expression in ("vdb(vout)", "vdb(vin)", "vp(vout)", "vp(vin)"):
            self.assertIn(expression, ac)

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

    def test_capacitance_rejects_resistance_style_k_suffix(self):
        # Caps are microfarads only; "10k" must not silently become 10000 uF.
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, cin="10k"))
        self.assertEqual(errs.get("cin"), "ต้องเป็นตัวเลขที่จำกัด")

    def test_empty_capacitance_uses_required_message(self):
        # A cleared required field must get the same message as Lab 03.
        errs = validate_spice_inputs(dict(SPICE_DEFAULTS, cin=""))
        self.assertEqual(errs.get("cin"), "กรุณากรอกค่านี้")

    def test_netlist_builder_refuses_invalid_params(self):
        with self.assertRaises(ValueError):
            build_netlist(dict(SPICE_DEFAULTS, amp="0.01;rm -rf /"), "dc")


# ---- ngspice log parsers ---------------------------------------------------

#: Shape emitted for the Task 1 DC netlist: node rows plus the device current
#: column ``@q1[ic]``.  ``vce`` and ``ic`` are NOT printed as their own rows;
#: the parser must derive/map them.
OP_LOG = """\
Circuit: CE amplifier reference (Lab 04, no emitter bypass)

Node                                   Voltage
----                                   -------
vcc                                    1.200000e+01
b                                      1.942000e+00
e                                      1.242000e+00
c                                      9.294000e+00
@q1[ic]                                1.230000e-03
"""

#: Robustness: ngspice 3x prints .print tables with an Index column instead of
#: vertical pairs.  The same parser must read that shape too.
OP_TABLE_LOG = """\
Index   v(b)         v(e)         v(c)         @q1[ic]
------  -----------  -----------  -----------  -----------
0       1.942000e+00 1.242000e+00 9.294000e+00 1.230000e-03
"""

#: Real ngspice 47 shape for ``.print ac vdb(vout) vp(vout) vdb(vin) vp(vin)``:
#: one table per function family, keyed by Index/frequency.  At 1 kHz the
#: output is -35.1402 dB absolute vs -40 dB input, i.e. +4.8598 dB gain, and
#: -3.13926 rad output phase vs 0 rad input, i.e. about -179.86 degrees.
AC_LOG = """\
Index   frequency       vdb(vout)       vp(vout)
------  --------        -----------     --------
40      1.000000e+03    -3.51402e+01    -3.13926e+00
100     1.000000e+06    -3.51402e+01    -3.14159e+00

Index   frequency       vdb(vin)        vp(vin)
------  --------        -----------     --------
40      1.000000e+03    -4.00000e+01    0.000000e+00
100     1.000000e+06    -4.00000e+01    0.000000e+00
"""

#: Same circuit with a doubled source: both absolute dB values rise by
#: 20*log10(2) = 6.0206 dB, so the derived gain must stay +4.8598 dB.
AC_LOG_2X = """\
Index   frequency       vdb(vout)       vp(vout)
------  --------        -----------     --------
40      1.000000e+03    -2.91196e+01    -3.13926e+00
100     1.000000e+06    -2.91196e+01    -3.14159e+00

Index   frequency       vdb(vin)        vp(vin)
------  --------        -----------     --------
40      1.000000e+03    -3.39794e+01    0.000000e+00
100     1.000000e+06    -3.39794e+01    0.000000e+00
"""

TRAN_LOG = """\
Index   time            vin             vout
------  --------        -----------     -----------
0       1.000000e-04    1.000000e-02    -1.750000e-02
"""


class TestParsers(unittest.TestCase):
    def test_parse_op_log(self):
        op = parse_op_log(OP_LOG)
        self.assertAlmostEqual(op["vb"], 1.942)
        self.assertAlmostEqual(op["ic"], 0.00123)
        self.assertAlmostEqual(op["ve"], 1.242)
        self.assertAlmostEqual(op["vc"], 9.294)
        self.assertAlmostEqual(op["vce"], 8.052)
        self.assertEqual(set(op), {"vb", "ve", "vc", "vce", "ic"})

    def test_parse_op_log_reads_tabular_print_output(self):
        op = parse_op_log(OP_TABLE_LOG)
        self.assertAlmostEqual(op["vb"], 1.942)
        self.assertAlmostEqual(op["vce"], 8.052)
        self.assertAlmostEqual(op["ic"], 0.00123)

    def test_parse_op_log_refuses_incomplete_log(self):
        # A log without the operating point must not yield fabricated values.
        with self.assertRaises(ValueError):
            parse_op_log("ngspice: fatal error, no operating point\n")

    def test_parse_print_table_skips_header_and_maps_columns(self):
        rows = parse_print_table(TRAN_LOG, ["time", "vin", "vout"])
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0]["vout"], -0.0175)

    def test_parse_print_table_returns_empty_list_without_data(self):
        self.assertEqual(parse_print_table("no table here\n", ["freq"]), [])
        self.assertEqual(parse_print_table("", ["freq"]), [])

    def test_parse_ac_log_skips_frequencies_without_vin_reference(self):
        # A Vout-only table cannot produce Vin-referenced gain; never invent it.
        vout_only = "\n".join(AC_LOG.splitlines()[:4]) + "\n"
        self.assertEqual(parse_ac_log(vout_only), [])


class TestRunnerErrors(unittest.TestCase):
    @patch("spice_engine.shutil.which", return_value=None)
    def test_missing_engine_returns_error_not_success(self, _):
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "error")
        self.assertIn("ngspice", r["error"])
        self.assertIsNone(r["values"])

    @patch("spice_engine.subprocess.run")
    def test_nonzero_exit_returns_error(self, mock_run):
        mock_run.return_value = SimpleNamespace(returncode=1, stdout="", stderr="fatal")
        r = run_analysis(SPICE_DEFAULTS, "dc", engine_path="ngspice")
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_nonzero_exit_with_engine_present_keeps_no_values(self, mock_run, _):
        mock_run.return_value = SimpleNamespace(
            returncode=1, stdout="", stderr="fatal: unknown model"
        )
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])
        self.assertIsNone(r["series"])
        self.assertIn("fatal", r["log_excerpt"])

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_empty_log_returns_error(self, mock_run, _):
        mock_run.return_value = SimpleNamespace(returncode=0, stdout="", stderr="")
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])
        self.assertIsNone(r["series"])
        self.assertTrue(r["error"])

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch(
        "spice_engine.subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="ngspice", timeout=20),
    )
    def test_timeout_returns_error(self, mock_run, _):
        r = run_analysis(SPICE_DEFAULTS, "dc", timeout=20)
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])
        self.assertIsNone(r["series"])

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_invalid_params_never_reach_the_solver(self, mock_run, _):
        r = run_analysis(dict(SPICE_DEFAULTS, re="0"), "dc")
        self.assertEqual(r["status"], "error")
        self.assertIsNone(r["values"])
        mock_run.assert_not_called()


class TestRunnerSuccess(unittest.TestCase):
    @staticmethod
    def _fake_run(log, *, stdout="", stderr="", returncode=0):
        def fake_run(cmd, **kwargs):
            if log is not None:
                Path(kwargs["cwd"], "run.log").write_text(log, encoding="utf-8")
            return SimpleNamespace(
                returncode=returncode, stdout=stdout, stderr=stderr
            )

        return fake_run

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_success_dc_returns_op_values(self, mock_run, _):
        mock_run.side_effect = self._fake_run(OP_LOG)
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "success")
        self.assertEqual(r["analysis"], "dc")
        self.assertEqual(r["model"], "QNPN")
        self.assertAlmostEqual(r["values"]["vce"], 8.052)
        self.assertAlmostEqual(r["values"]["ic"], 0.00123)
        self.assertIsNone(r["series"])
        self.assertEqual(r["error"], "")
        self.assertTrue(r["log_excerpt"])

        args, kwargs = mock_run.call_args
        cmd = args[0]
        self.assertIsInstance(cmd, list)
        self.assertIn("ngspice", cmd[0])
        self.assertIn("-b", cmd)
        self.assertIn("case.cir", cmd)
        self.assertEqual(kwargs["timeout"], 20)
        self.assertFalse(kwargs.get("shell", False))
        self.assertNotIn("shell=True", str(cmd))

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_runner_does_not_request_raw_file_that_suppresses_print(self, mock_run, _):
        # ngspice 47 ignores every .print line when -r writes a rawfile:
        # the ASCII log then has no table for parse_op_log/parse_print_table.
        mock_run.side_effect = self._fake_run(OP_LOG)
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "success")
        cmd = mock_run.call_args.args[0]
        self.assertIn("-o", cmd)
        self.assertNotIn("-r", cmd)
        self.assertNotIn("run.raw", cmd)

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_success_ac_derives_vin_referenced_gain_and_degree_phase(self, mock_run, _):
        mock_run.side_effect = self._fake_run(AC_LOG)
        r = run_analysis(SPICE_DEFAULTS, "ac")
        self.assertEqual(r["status"], "success")
        self.assertIsNone(r["values"])
        self.assertEqual(len(r["series"]), 2)
        # -35.1402 dB Vout - (-40 dB Vin) = +4.8598 dB amplifier gain.
        self.assertAlmostEqual(r["series"][0]["gain_db"], 4.8598, places=4)
        # -3.14159 rad Vout - 0 rad Vin = -180 degrees, not -3.14 degrees.
        self.assertAlmostEqual(r["series"][1]["phase_deg"], -180.0, places=1)

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_ac_gain_does_not_change_when_only_amplitude_changes(self, mock_run, _):
        # Both logs come from the same amplifier; only the source amplitude
        # doubled.  The derived gain must stay identical.
        fake_runs = iter([
            self._fake_run(AC_LOG),
            self._fake_run(AC_LOG_2X),
        ])

        def next_run(cmd, **kwargs):
            return next(fake_runs)(cmd, **kwargs)

        mock_run.side_effect = next_run
        first = run_analysis(SPICE_DEFAULTS, "ac")
        second = run_analysis(dict(SPICE_DEFAULTS, amp="0.02"), "ac")
        self.assertEqual(first["status"], "success")
        self.assertEqual(second["status"], "success")
        for a, b in zip(first["series"], second["series"]):
            self.assertAlmostEqual(a["gain_db"], b["gain_db"], places=4)
            self.assertAlmostEqual(a["phase_deg"], b["phase_deg"], places=1)

    @patch("spice_engine.shutil.which", return_value=r"C:\tools\ngspice.exe")
    @patch("spice_engine.subprocess.run")
    def test_log_excerpt_is_bounded_to_2000_chars(self, mock_run, _):
        noisy = "x" * 5000 + "\n"
        mock_run.side_effect = self._fake_run(noisy, stderr="boom")
        r = run_analysis(SPICE_DEFAULTS, "dc")
        self.assertEqual(r["status"], "error")
        self.assertLessEqual(len(r["log_excerpt"]), 2000)
