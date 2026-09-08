"""Unit tests for Performance model methods and filtering logic."""

import unittest
from uci_monitor.models import Performance


class TestPerformanceModel(unittest.TestCase):

    def test_imax_omu_matching(self):
        perf = Performance(
            performance_id="TEST001",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-10",
            time="22:30",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|omu|2d|465",
            subtext="OmU",
        )
        self.assertTrue(perf.is_imax)
        self.assertTrue(perf.is_omu)
        self.assertFalse(perf.is_isense)
        self.assertFalse(perf.is_german_dub)
        self.assertTrue(perf.matches_target_criteria())

    def test_german_dub_exclusion(self):
        # IMAX German dubbed (no omu, no ov)
        perf = Performance(
            performance_id="TEST002",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-09",
            time="15:00",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|2d|465",
            subtext="",
        )
        self.assertTrue(perf.is_imax)
        self.assertFalse(perf.is_omu)
        self.assertTrue(perf.is_german_dub)
        self.assertFalse(perf.matches_target_criteria())

    def test_isense_exclusion(self):
        # iSense screening
        perf = Performance(
            performance_id="TEST003",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-11",
            time="20:15",
            auditorium="Kino 02 iSense",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="2d|isens|465|371",
            subtext="",
        )
        self.assertFalse(perf.is_imax)
        self.assertTrue(perf.is_isense)
        self.assertFalse(perf.matches_target_criteria())

    def test_standard_2d_exclusion(self):
        # Standard 2D screening
        perf = Performance(
            performance_id="TEST004",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-09",
            time="16:30",
            auditorium="Kino 05",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="2d|465",
            subtext="",
        )
        self.assertFalse(perf.is_imax)
        self.assertFalse(perf.matches_target_criteria())

    def test_ov_exclusion(self):
        # IMAX OV (without German subtitles)
        perf = Performance(
            performance_id="TEST005",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-09",
            time="19:00",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|ov|2d|465",
            subtext="OV",
        )
        self.assertTrue(perf.is_imax)
        self.assertTrue(perf.is_ov)
        self.assertFalse(perf.is_omu)
        # Target requirement: strictly OmU (must match IMAX AND OmU)
        self.assertFalse(perf.matches_target_criteria(require_omu=True))

    def test_serialization(self):
        perf = Performance(
            performance_id="TEST006",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-10",
            time="22:30",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|omu|2d|465",
            subtext="OmU",
            booking_path="/kino-buchung/performanceId/TEST006/siteId/82/945069",
            booking_url="https://www.uci-kinowelt.de/kino-buchung/performanceId/TEST006/siteId/82/945069",
            direct_booking_url="https://buchung.uci-kinowelt.de/?perf_id=TEST006&site_id=82",
        )
        data = perf.to_dict()
        restored = Performance.from_dict(data)
        self.assertEqual(perf, restored)


if __name__ == "__main__":
    unittest.main()
