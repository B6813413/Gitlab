import unittest

from dc_bias import dc_operating_point


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
