"""Integration unit tests verifying HTML parser against real UCI schedule dumps."""

import os
import unittest
from uci_monitor.parser import CinemaScheduleParser

SAMPLE_PAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "sample_page.html")
FILM_PAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "film_page.html")


class TestCinemaScheduleParser(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(SAMPLE_PAGE_PATH, "r", encoding="utf-8") as f:
            cls.sample_html = f.read()
        with open(FILM_PAGE_PATH, "r", encoding="utf-8") as f:
            cls.film_html = f.read()

    def test_sample_page_extraction(self):
        parser = CinemaScheduleParser(target_titles=["The Odyssey", "Die Odyssee"])
        all_perfs, matching = parser.parse_all_and_filtered(self.sample_html)

        self.assertEqual(len(all_perfs), 40, f"Expected 40 Odyssee sessions, found {len(all_perfs)}")
        self.assertEqual(len(matching), 6, f"Expected 6 IMAX OmU sessions, found {len(matching)}")

        expected_sessions = [
            ("2026-09-10", "22:30", "DC5F1000023ZIQERCX"),
            ("2026-09-11", "22:30", "EC5F1000023ZIQERCX"),
            ("2026-09-12", "14:30", "FC5F1000023ZIQERCX"),
            ("2026-09-13", "13:00", "0D5F1000023ZIQERCX"),
            ("2026-09-14", "15:00", "1D5F1000023ZIQERCX"),
            ("2026-09-16", "14:20", "2D5F1000023ZIQERCX"),
        ]

        for i, (exp_date, exp_time, exp_id) in enumerate(expected_sessions):
            actual = matching[i]
            self.assertEqual(actual.date, exp_date)
            self.assertEqual(actual.time, exp_time)
            self.assertEqual(actual.performance_id, exp_id)
            self.assertEqual(actual.auditorium, "Kino 01 IMAX")
            self.assertTrue(actual.is_imax)
            self.assertTrue(actual.is_omu)
            self.assertFalse(actual.is_isense)
            self.assertFalse(actual.is_german_dub)
            self.assertIn(exp_id, actual.booking_url)
            self.assertIn(exp_id, actual.direct_booking_url)
            self.assertIn("site_id=82", actual.direct_booking_url)

    def test_film_page_extraction(self):
        parser = CinemaScheduleParser(target_titles=["The Odyssey", "Die Odyssee"])
        all_perfs, matching = parser.parse_all_and_filtered(self.film_html)

        self.assertEqual(len(all_perfs), 40)
        self.assertEqual(len(matching), 6)

        expected_perf_ids = {
            "DC5F1000023ZIQERCX",
            "EC5F1000023ZIQERCX",
            "FC5F1000023ZIQERCX",
            "0D5F1000023ZIQERCX",
            "1D5F1000023ZIQERCX",
            "2D5F1000023ZIQERCX",
        }
        actual_perf_ids = {p.performance_id for p in matching}
        self.assertEqual(actual_perf_ids, expected_perf_ids)

    def test_title_matching_variants(self):
        # Match using English title
        parser_en = CinemaScheduleParser(target_titles=["The Odyssey"])
        _, matching_en = parser_en.parse_all_and_filtered(self.sample_html)
        self.assertEqual(len(matching_en), 6)

        # Match using German title
        parser_de = CinemaScheduleParser(target_titles=["Die Odyssee"])
        _, matching_de = parser_de.parse_all_and_filtered(self.sample_html)
        self.assertEqual(len(matching_de), 6)

        # Non-matching title should return 0
        parser_none = CinemaScheduleParser(target_titles=["Random Unrelated Title"], target_film_id=None)
        _, matching_none = parser_none.parse_all_and_filtered(self.sample_html)
        self.assertEqual(len(matching_none), 0)


if __name__ == "__main__":
    unittest.main()
