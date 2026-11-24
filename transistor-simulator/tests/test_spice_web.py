import unittest
from unittest.mock import patch

from app import app


BASE_FIELDS = {
    "analysis": "spice_dc", "mode": "voltage_divider",
    "vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
    "rl": "10", "cin": "10", "cout": "10", "amp": "0.01", "freq": "1k",
    "bjt_model": "QNPN",
}


def result(status="success", analysis="dc", values=None, series=None,
           error=None):
    return {
        "status": status,
        "engine": "ngspice",
        "analysis": analysis,
        "model": "QNPN",
        "values": values,
        "series": series,
        "log_excerpt": "ok" if status == "success" else "",
        "error": error,
    }


class TestSpiceDispatch(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_get_has_analysis_selector_and_still_two_forms(self):
        html = self.client.get("/").get_data(as_text=True)
        self.assertEqual(html.count("<form"), 2)
        self.assertIn('name="analysis"', html)
        self.assertIn("SPICE DC (.op)", html)

    def test_spice_result_block_has_provenance_and_units(self):
        html = self.client.get("/").get_data(as_text=True)
        for marker in ("analysis", "Engine status", "SPICE (.op)",
                       "Bode", "Transient"):
            self.assertIn(marker, html)

    @patch("app.run_analysis")
    def test_post_spice_dc_shows_engine_status(self, mock_run):
        mock_run.return_value = result(
            values={"vb": 1.942, "ve": 1.242, "vc": 9.294,
                    "vce": 8.052, "ic": 0.00123})
        resp = self.client.post("/", data=BASE_FIELDS)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Engine: ngspice", resp.data)
        self.assertIn(b"SPICE (.op)", resp.data)
        self.assertIn(b"1.230 mA", resp.data)

    @patch("app.run_analysis")
    def test_engine_error_never_shows_success_values(self, mock_run):
        mock_run.return_value = result(
            status="error", error="ไม่พบ ngspice")
        resp = self.client.post("/", data=BASE_FIELDS)
        self.assertEqual(resp.status_code, 502)
        self.assertNotIn(b"Success", resp.data)
        self.assertIn("ไม่พบ ngspice".encode("utf-8"), resp.data)

    @patch("app.run_analysis")
    def test_changed_source_changes_params_sent_to_engine(self, mock_run):
        mock_run.side_effect = lambda params, analysis, **kw: result(
            status="error", analysis=analysis, error="stop", values=None)
        base = {"analysis": "spice_tran", "re": "1", "amp": "0.01", "freq": "1k"}
        self.client.post("/", data=base)
        self.client.post("/", data=dict(base, amp="0.02", freq="2k"))
        self.assertNotEqual(mock_run.call_args_list[0].args[0]["amp"],
                            mock_run.call_args_list[1].args[0]["amp"])
        self.assertNotEqual(mock_run.call_args_list[0].args[0]["freq"],
                            mock_run.call_args_list[1].args[0]["freq"])

    @patch("app.run_analysis")
    def test_unknown_analysis_is_rejected_before_engine(self, mock_run):
        resp = self.client.post("/", data=dict(BASE_FIELDS, analysis="bogus"))
        self.assertEqual(resp.status_code, 400)
        mock_run.assert_not_called()

    @patch("app.run_analysis")
    def test_invalid_spice_input_never_reaches_engine(self, mock_run):
        resp = self.client.post("/", data=dict(BASE_FIELDS, re="abc"))
        self.assertEqual(resp.status_code, 400)
        mock_run.assert_not_called()

    @patch("app.run_analysis")
    def test_ac_success_renders_bode_svg(self, mock_run):
        mock_run.return_value = result(
            analysis="ac",
            series=[{"freq": 100, "gain_db": -3, "phase_deg": -170},
                    {"freq": 1000, "gain_db": -5, "phase_deg": -180}])
        resp = self.client.post("/", data=dict(BASE_FIELDS, analysis="spice_ac"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Bode", resp.data)
        self.assertIn(b"Frequency (Hz)", resp.data)
        self.assertIn(b"Gain (dB)", resp.data)

    @patch("app.run_analysis")
    def test_tran_success_renders_waveform_svg(self, mock_run):
        mock_run.return_value = result(
            analysis="tran",
            series=[{"time": 0, "vin": 0.01, "vout": -0.1},
                    {"time": 0.001, "vin": 0.02, "vout": -0.2}])
        resp = self.client.post("/", data=dict(BASE_FIELDS, analysis="spice_tran"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Transient", resp.data)
        self.assertIn(b"Time (ms)", resp.data)
