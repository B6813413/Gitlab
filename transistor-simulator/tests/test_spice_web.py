import re
import unittest
from pathlib import Path
from unittest.mock import patch

from app import app


SPICE_ANALYSES = ("spice_dc", "spice_ac", "spice_tran")

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
    def test_unknown_analysis_on_get_returns_400_too(self, mock_run):
        resp = self.client.get("/?analysis=bogus")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("ไม่รู้จักการวิเคราะห์", resp.get_data(as_text=True))
        mock_run.assert_not_called()

    @patch("app.run_analysis")
    def test_invalid_spice_input_never_reaches_engine(self, mock_run):
        resp = self.client.post("/", data=dict(BASE_FIELDS, re="abc"))
        self.assertEqual(resp.status_code, 400)
        mock_run.assert_not_called()

    def test_spice_model_is_a_fixed_select_not_free_text(self):
        # The reference netlist defines exactly one model; a free-text field
        # invited misleading model-name validation errors.
        html = self.client.get("/?analysis=spice_ac").get_data(as_text=True)
        self.assertRegex(html, r'<select[^>]*name="bjt_model"')
        self.assertIn('<option value="QNPN"', html)
        self.assertNotRegex(html, r'<input[^>]*name="bjt_model"')

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

    @patch("app.run_analysis")
    def test_spice_post_echoes_submitted_values_and_units(self, mock_run):
        data = dict(BASE_FIELDS, analysis="spice_tran", amp="0.02",
                    freq="2k", rl="20", rl_unit="ohm")
        for status in ("success", "error"):
            mock_run.return_value = result(
                status=status, analysis="tran",
                series=([{"time": 0, "vin": 0.02, "vout": -0.2},
                         {"time": 0.001, "vin": 0.02, "vout": -0.2}]
                        if status == "success" else None),
                error=None if status == "success" else "stop")
            with self.subTest(status=status):
                html = self.client.post("/", data=data).get_data(as_text=True)
                self.assertIn('value="0.02"', html)
                self.assertIn('value="2k"', html)
                self.assertIn('value="20"', html)
                self.assertIn('<option value="ohm" selected>Ω</option>', html)

    @patch("app.run_analysis")
    def test_ac_success_hides_operating_point_table(self, mock_run):
        mock_run.return_value = result(
            analysis="ac",
            series=[{"freq": 100, "gain_db": -3, "phase_deg": -170},
                    {"freq": 1000, "gain_db": -5, "phase_deg": -180}])
        resp = self.client.post("/", data=dict(BASE_FIELDS, analysis="spice_ac"))
        html = resp.get_data(as_text=True)
        self.assertNotIn("SPICE (.op) operating point", html)
        self.assertIn("Bode plot", html)

    @patch("app.run_analysis")
    def test_spice_post_empty_state_is_analysis_aware(self, mock_run):
        mock_run.return_value = result(status="error", analysis="dc",
                                       error="stop")
        html = self.client.post("/", data=BASE_FIELDS).get_data(as_text=True)
        self.assertNotIn("Calculate DC Bias", html)
        self.assertIn("การวิเคราะห์นี้ใช้ ngspice", html)


CSS_PATH = Path(__file__).resolve().parent.parent / "static" / "style.css"
CAPTION_RE = re.compile(r'<p class="chart-caption">(.*?)</p>', re.S)


def caption_texts(html):
    return CAPTION_RE.findall(html)


class TestMobileChartLegibility(unittest.TestCase):
    def setUp(self):
        app.testing = True
        self.client = app.test_client()

    def test_880px_block_keeps_chart_svg_native_width(self):
        css = CSS_PATH.read_text(encoding="utf-8")
        block = re.search(
            r"@media \(max-width: 880px\)\s*\{(.*?)\n\}", css, re.S)
        self.assertIsNotNone(block, "missing 880px media query")
        mobile = block.group(1)
        self.assertNotRegex(
            mobile, r"\.chart\s+svg\s*\{[^}]*min-width\s*:\s*0")
        widths = re.findall(
            r"\.chart\s+svg\s*\{[^}]*min-width\s*:\s*([0-9.]+)px", mobile)
        self.assertTrue(widths, "mobile rule should set a chart min-width")
        for width in widths:
            self.assertGreaterEqual(float(width), 760)

    def test_mobile_chart_scrolls_inside_panel_without_page_growth(self):
        css = CSS_PATH.read_text(encoding="utf-8")
        block = re.search(r"@media \(max-width: 880px\)\s*\{(.*?)\n\}", css, re.S)
        self.assertIsNotNone(block)
        self.assertRegex(block.group(1), r"\.layout\s*\{[^}]*minmax\(0,\s*1fr\)")
        panel = re.search(r"\.panel\s*\{([^}]*)\}", css)
        self.assertIsNotNone(panel)
        self.assertRegex(panel.group(1), r"min-width\s*:\s*0")
        chart = re.search(r"\.chart\s*\{([^}]*)\}", css)
        self.assertIsNotNone(chart)
        self.assertRegex(chart.group(1), r"overflow-x\s*:\s*auto")
        self.assertRegex(chart.group(1), r"max-width\s*:\s*100%")

    @patch("app.run_analysis")
    def test_bode_caption_only_claims_log_frequency(self, mock_run):
        mock_run.return_value = result(
            analysis="ac",
            series=[{"freq": 100, "gain_db": -3, "phase_deg": -170},
                    {"freq": 1000, "gain_db": -5, "phase_deg": -180}])
        html = self.client.post(
            "/", data=dict(BASE_FIELDS, analysis="spice_ac")).get_data(
                as_text=True)
        captions = caption_texts(html)
        self.assertEqual(len(captions), 1)
        caption = captions[0]
        self.assertIn("ลอการิทึม", caption)
        self.assertIn("10 Hz", caption)
        self.assertIn("1 MHz", caption)
        self.assertNotIn("ms", caption)
        self.assertNotIn("แกนเวลา", caption)

    @patch("app.run_analysis")
    def test_transient_caption_only_claims_ms_time(self, mock_run):
        mock_run.return_value = result(
            analysis="tran",
            series=[{"time": 0, "vin": 0.01, "vout": -0.1},
                    {"time": 0.001, "vin": 0.02, "vout": -0.2}])
        html = self.client.post(
            "/", data=dict(BASE_FIELDS, analysis="spice_tran")).get_data(
                as_text=True)
        captions = caption_texts(html)
        self.assertEqual(len(captions), 1)
        caption = captions[0]
        self.assertIn("ms", caption)
        self.assertNotIn("ลอการิทึม", caption)

    def test_spice_analyses_disable_lab03_only_controls(self):
        # _spice_params() ignores mode/beta/vbe, so the form must not require them.
        for name in SPICE_ANALYSES:
            with self.subTest(analysis=name):
                html = self.client.get(
                    f"/?mode=fixed&analysis={name}"
                ).get_data(as_text=True)
                self.assertIn("ไม่ใช้ใน SPICE", html)
                self.assertRegex(html, r'<select name="mode"[^>]*\bdisabled\b')
                self.assertRegex(html, r'<input id="beta"[^>]*\bdisabled\b')
                self.assertRegex(html, r'<input id="vbe"[^>]*\bdisabled\b')
                self.assertNotRegex(html, r'<input id="beta"[^>]*\brequired\b')
                self.assertNotRegex(html, r'<input id="vbe"[^>]*\brequired\b')

    def test_spice_enables_ce_reference_fields_for_all_modes(self):
        # The SPICE netlist always uses R1/R2/RE; RB from Lab 03 is ignored.
        for name in SPICE_ANALYSES:
            for chosen_mode in ("voltage_divider", "fixed", "emitter"):
                with self.subTest(analysis=name, mode=chosen_mode):
                    html = self.client.get(
                        f"/?mode={chosen_mode}&analysis={name}"
                    ).get_data(as_text=True)
                    for field in ("r1", "r2", "re"):
                        self.assertRegex(
                            html, rf'<input id="{field}"[^>]*\brequired\b'
                        )
                        self.assertNotRegex(
                            html, rf'<input id="{field}"[^>]*\bdisabled\b'
                        )
                    self.assertRegex(html, r'<input id="rb"[^>]*\bdisabled\b')
                    self.assertNotRegex(html, r'<input id="rb"[^>]*\brequired\b')
                    self.assertIn(
                        "R<sub>B</sub> (Base Resistor) · ไม่ใช้ใน SPICE", html
                    )

    def test_spice_uses_ce_reference_schematic_for_all_modes(self):
        # SPICE netlist is always the CE reference circuit, never the Lab 03 mode.
        for chosen_mode in ("voltage_divider", "fixed", "emitter"):
            with self.subTest(mode=chosen_mode):
                html = self.client.get(
                    f"/?mode={chosen_mode}&analysis=spice_dc"
                ).get_data(as_text=True)
                match = re.search(r'<svg class="schematic".*?</svg>', html, re.S)
                self.assertIsNotNone(match)
                svg = match.group(0)
                self.assertIn("[CE Reference]", html)
                self.assertIn(
                    'aria-label="Common-emitter amplifier reference circuit"', html
                )
                # Divider + RE of the reference circuit, not RB or fixed-bias GND.
                self.assertIn(
                    'R<tspan baseline-shift="sub" font-size="10">1</tspan>', svg
                )
                self.assertIn(
                    'R<tspan baseline-shift="sub" font-size="10">E</tspan>', svg
                )
                self.assertNotIn(
                    'R<tspan baseline-shift="sub" font-size="10">B</tspan>', svg
                )
                self.assertNotIn("GND", svg)
                self.assertIn("β = 100 จาก .model", html)
                for marker in ("CIN 10 µF", "COUT 10 µF", "RL 10 kΩ"):
                    self.assertIn(marker, html)

    def test_analytical_mode_keeps_lab03_controls_active(self):
        html = self.client.get("/?mode=fixed&analysis=bias").get_data(as_text=True)
        self.assertRegex(html, r'<select name="mode"[^>]*onchange=')
        self.assertNotRegex(html, r'<select name="mode"[^>]*\bdisabled\b')
        self.assertRegex(html, r'<input id="beta"[^>]*\brequired\b')
        self.assertRegex(html, r'<input id="vbe"[^>]*\brequired\b')
        self.assertNotIn("[CE Reference]", html)

    def test_analytical_mode_keeps_lab03_field_gating(self):
        for chosen_mode, active, idle in (
            ("voltage_divider", ("r1", "r2", "re"), ("rb",)),
            ("fixed", ("rb",), ("r1", "r2", "re")),
            ("emitter", ("rb", "re"), ("r1", "r2")),
        ):
            with self.subTest(mode=chosen_mode):
                html = self.client.get(
                    f"/?mode={chosen_mode}&analysis=bias"
                ).get_data(as_text=True)
                for field in active:
                    self.assertRegex(html, rf'<input id="{field}"[^>]*\brequired\b')
                    self.assertNotRegex(html, rf'<input id="{field}"[^>]*\bdisabled\b')
                for field in idle:
                    self.assertRegex(html, rf'<input id="{field}"[^>]*\bdisabled\b')
                    self.assertNotRegex(html, rf'<input id="{field}"[^>]*\brequired\b')
