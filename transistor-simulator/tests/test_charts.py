"""Tests for the dependency-free SVG chart renderers (Lab 04, Task 3)."""

import math
import re
import unittest

from charts import render_bode_svg, render_transient_svg


def _aria_label(svg):
    match = re.search(r'aria-label="([^"]*)"', svg)
    return match.group(1) if match else ""


def _polylines(svg):
    return re.findall(r'points="([^"]*)"', svg)


def _points(polyline):
    return [
        tuple(float(part) for part in pair.split(","))
        for pair in polyline.split()
    ]


def _text_labels(svg):
    return re.findall(r"<text[^>]*>([^<]+)</text>", svg)


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


class TestChartAccessibility(unittest.TestCase):
    def test_both_charts_have_img_role_and_thai_label(self):
        bode = render_bode_svg([{"freq": 100, "gain_db": -3,
                                 "phase_deg": -170}])
        transient = render_transient_svg([{"time": 0, "vin": 0.01,
                                           "vout": -0.1}])
        for svg in (bode, transient):
            self.assertIn('role="img"', svg)
            label = _aria_label(svg)
            self.assertTrue(label)
            self.assertRegex(label, r"[\u0E00-\u0E7F]")

    def test_legend_names_both_series_and_units(self):
        bode = render_bode_svg([{"freq": 100, "gain_db": -3,
                                 "phase_deg": -170}])
        transient = render_transient_svg([{"time": 0, "vin": 0.01,
                                           "vout": -0.1}])
        self.assertIn("อัตราขยาย", bode)
        self.assertIn("เฟส", bode)
        self.assertIn("dB", bode)
        self.assertIn("Vin", transient)
        self.assertIn("Vout", transient)
        self.assertIn("V", transient)


class TestBodeChart(unittest.TestCase):
    def test_one_point_per_row_for_each_series(self):
        rows = [{"freq": 100, "gain_db": -3, "phase_deg": -170},
                {"freq": 500, "gain_db": -4, "phase_deg": -175},
                {"freq": 1000, "gain_db": -5, "phase_deg": -180}]
        polylines = _polylines(render_bode_svg(rows))
        self.assertEqual(len(polylines), 2)
        for points in polylines:
            self.assertEqual(len(points.split()), len(rows))

    def test_gain_y_coordinates_follow_the_data(self):
        rows = [{"freq": 100, "gain_db": -3, "phase_deg": -170},
                {"freq": 1000, "gain_db": -5, "phase_deg": -180}]
        gain_points = _points(_polylines(render_bode_svg(rows))[0])
        # SVG y grows downwards: the higher gain (-3 dB) must be above -5 dB.
        self.assertLess(gain_points[0][1], gain_points[1][1])

    def test_changed_series_changes_the_chart(self):
        first = render_bode_svg([{"freq": 100, "gain_db": -3,
                                  "phase_deg": -170}])
        second = render_bode_svg([{"freq": 100, "gain_db": -13,
                                   "phase_deg": -90}])
        self.assertNotEqual(first, second)

    def test_frequency_axis_is_logarithmic(self):
        rows = [{"freq": freq, "gain_db": 0, "phase_deg": 0}
                for freq in (10, 100, 1000)]
        gain_points = _points(_polylines(render_bode_svg(rows))[0])
        first_gap = gain_points[1][0] - gain_points[0][0]
        second_gap = gain_points[2][0] - gain_points[1][0]
        self.assertAlmostEqual(first_gap, second_gap, delta=0.5)


class TestTransientChart(unittest.TestCase):
    def test_vin_and_vout_are_separate_polylines(self):
        rows = [{"time": 0, "vin": 0.01, "vout": -0.1},
                {"time": 0.001, "vin": 0.02, "vout": -0.2},
                {"time": 0.002, "vin": 0.03, "vout": -0.3}]
        svg = render_transient_svg(rows)
        polylines = _polylines(svg)
        self.assertEqual(len(polylines), 2)
        for points in polylines:
            self.assertEqual(len(points.split()), len(rows))

    def test_time_axis_is_labelled_in_milliseconds(self):
        rows = [{"time": 0, "vin": 0.0, "vout": 0.0},
                {"time": 0.001, "vin": 0.01, "vout": -0.1},
                {"time": 0.002, "vin": 0.02, "vout": -0.2}]
        labels = _text_labels(render_transient_svg(rows))
        # 0.002 s becomes 2 ms, so a "2" tick label must exist.
        self.assertIn("2", labels)


class TestChartEdgeCases(unittest.TestCase):
    def test_empty_series_returns_placeholder_svg(self):
        cases = (
            (render_bode_svg,
             ("Frequency (Hz)", "Gain (dB)", "Phase (°)")),
            (render_transient_svg, ("Time (ms)", "Voltage (V)")),
        )
        for render, labels in cases:
            for empty in ([], None, [{}], [{"freq": 1, "time": 1}]):
                svg = render(empty)
                self.assertIn('role="img"', svg)
                self.assertIn("ไม่มีข้อมูล", svg)
                self.assertNotIn("<polyline", svg)
                for label in labels:
                    self.assertIn(label, svg)

    def test_non_finite_and_malformed_rows_are_ignored(self):
        rows = [
            {"freq": 100, "gain_db": -3, "phase_deg": -170},
            {"freq": math.nan, "gain_db": -4, "phase_deg": -175},
            {"freq": 1000, "gain_db": math.inf, "phase_deg": -180},
            {"freq": "bad", "gain_db": -5, "phase_deg": -180},
        ]
        polylines = _polylines(render_bode_svg(rows))
        self.assertEqual(len(polylines), 2)
        for points in polylines:
            self.assertEqual(len(points.split()), 1)

    def test_constant_values_do_not_divide_by_zero(self):
        rows = [{"freq": 1000, "gain_db": -3, "phase_deg": -180}] * 3
        svg = render_bode_svg(rows)
        self.assertIn("<polyline", svg)
        self.assertIn('role="img"', svg)

    def test_zero_frequency_does_not_break_the_chart(self):
        rows = [{"freq": 0, "gain_db": -3, "phase_deg": -170},
                {"freq": 100, "gain_db": -5, "phase_deg": -180}]
        svg = render_bode_svg(rows)
        self.assertEqual(len(_polylines(svg)), 2)

    def test_input_rows_are_not_mutated(self):
        rows = [{"freq": 1000, "gain_db": -5, "phase_deg": -180},
                {"freq": 100, "gain_db": -3, "phase_deg": -170}]
        before = [dict(row) for row in rows]
        render_bode_svg(rows)
        self.assertEqual(rows, before)


if __name__ == "__main__":
    unittest.main()
