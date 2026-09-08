"""Unit tests verifying strict format filtering rules."""

import os
import unittest
from uci_monitor.parser import CinemaScheduleParser

SAMPLE_PAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_page.html")


class TestFormatFiltering(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SAMPLE_PAGE_PATH, "r", encoding="utf-8") as f:
            cls.sample_html = f.read()

    def test_all_odyssee_sessions_distribution(self):
        """Verify the exact distribution of format versions across all 40 Odyssee sessions."""
        parser = CinemaScheduleParser()
        all_perfs, matching = parser.parse_all_and_filtered(self.sample_html)

        self.assertEqual(len(all_perfs), 40)

        # Count by format type
        imax_omu = [p for p in all_perfs if p.is_imax and p.is_omu]
        imax_ov = [p for p in all_perfs if p.is_imax and p.is_ov and not p.is_omu]
        imax_de = [p for p in all_perfs if p.is_imax and p.is_german_dub]
        isense_sessions = [p for p in all_perfs if p.is_isense]
        standard_2d = [p for p in all_perfs if not p.is_imax and not p.is_isense]

        self.assertEqual(len(imax_omu), 6, "Must be exactly 6 IMAX OmU sessions")
        self.assertEqual(len(imax_ov), 7, "Must be exactly 7 IMAX OV sessions")
        self.assertEqual(len(imax_de), 6, "Must be exactly 6 IMAX German-dubbed sessions")
        self.assertEqual(len(isense_sessions), 6, "Must be exactly 6 iSense sessions")
        self.assertEqual(len(standard_2d), 15, "Must be exactly 15 standard 2D sessions")
        self.assertEqual(6 + 7 + 6 + 6 + 15, 40)

        # Only the 6 IMAX OmU must pass target filter
        self.assertEqual(len(matching), 6)
        for p in matching:
            self.assertTrue(p.is_imax)
            self.assertTrue(p.is_omu)
            self.assertFalse(p.is_isense)
            self.assertFalse(p.is_german_dub)


if __name__ == "__main__":
    unittest.main()
