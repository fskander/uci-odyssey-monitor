"""Unit tests for state management, persistence, and new drop detection."""

import os
import tempfile
import unittest
from uci_monitor.models import Performance
from uci_monitor.state import StateTracker


class TestStateTracker(unittest.TestCase):

    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        # Remove it so StateTracker starts fresh
        os.remove(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def _create_sample_perf(self, perf_id: str, date: str = "2026-09-10", time: str = "22:30"):
        return Performance(
            performance_id=perf_id,
            film_id="407923",
            film_title="Die Odyssee",
            date=date,
            time=time,
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|omu|2d|465",
            subtext="OmU",
            booking_path=f"/kino-buchung/performanceId/{perf_id}/siteId/82/123",
            booking_url=f"https://www.uci-kinowelt.de/kino-buchung/performanceId/{perf_id}/siteId/82/123",
            direct_booking_url=f"https://buchung.uci-kinowelt.de/?perf_id={perf_id}&site_id=82",
        )

    def test_baseline_first_run(self):
        tracker = StateTracker(self.temp_file.name)
        perfs = [self._create_sample_perf("PERF_1"), self._create_sample_perf("PERF_2")]

        # On initial run with notify_existing=False, it should baseline without drops
        drops = tracker.identify_new_drops(perfs, notify_existing=False)
        self.assertEqual(len(drops), 0)
        self.assertEqual(len(tracker.known_performances), 2)
        self.assertTrue(os.path.exists(self.temp_file.name))

    def test_notify_existing_first_run(self):
        tracker = StateTracker(self.temp_file.name)
        perfs = [self._create_sample_perf("PERF_1"), self._create_sample_perf("PERF_2")]

        # On initial run with notify_existing=True, it should alert on all
        drops = tracker.identify_new_drops(perfs, notify_existing=True)
        self.assertEqual(len(drops), 2)

    def test_detect_new_session_drop(self):
        tracker = StateTracker(self.temp_file.name)
        initial_perfs = [self._create_sample_perf("PERF_1")]
        tracker.identify_new_drops(initial_perfs, notify_existing=False)

        # Second run with a NEW session dropped
        updated_perfs = [self._create_sample_perf("PERF_1"), self._create_sample_perf("PERF_NEW")]
        drops = tracker.identify_new_drops(updated_perfs, notify_existing=False)

        self.assertEqual(len(drops), 1)
        self.assertEqual(drops[0].performance_id, "PERF_NEW")
        self.assertEqual(len(tracker.known_performances), 2)

    def test_reload_from_disk(self):
        tracker1 = StateTracker(self.temp_file.name)
        tracker1.identify_new_drops([self._create_sample_perf("P1")], notify_existing=False)

        # Create new instance pointing to same file
        tracker2 = StateTracker(self.temp_file.name)
        self.assertIn("P1", tracker2.known_performances)

        # Checking same session yields 0 drops
        drops = tracker2.identify_new_drops([self._create_sample_perf("P1")], notify_existing=False)
        self.assertEqual(len(drops), 0)


if __name__ == "__main__":
    unittest.main()
