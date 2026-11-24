import unittest

from charts import render_bode_svg, render_transient_svg


class TestCharts(unittest.TestCase):
    def test_bode_has_units_and_data_points(self):
        rows = [{"freq": 100, "gain_db": -3, "phase_deg": -170},
                {"freq": 1000, "gain_db": -5, "phase_deg": -180}]
        svg = render_bode_svg(rows)
        self.assertIn("Frequency (Hz)", svg)
        self.assertIn("Gain (dB)", svg)
        self.assertIn("Phase (°)", svg)
        self.assertGreaterEqual(svg.count("L"), 4)

    def test_transient_reflects_input_amplitude(self):
        small = render_transient_svg([{"time": 0, "vin": 0.01, "vout": -0.1},
                                      {"time": 1, "vin": 0.02, "vout": -0.2}])
        large = render_transient_svg([{"time": 0, "vin": 0.1, "vout": -1.0},
                                      {"time": 1, "vin": 0.2, "vout": -2.0}])
        self.assertIn("Time (ms)", small)
        self.assertIn("Voltage (V)", small)
        self.assertNotEqual(small, large)

    def test_empty_series_reports_missing_data_instead_of_fake_trace(self):
        self.assertIn("ไม่มีข้อมูล", render_bode_svg([]))
        self.assertIn("ไม่มีข้อมูล", render_transient_svg([]))
