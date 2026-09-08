"""Unit tests for ntfy.sh and notification dispatchers."""

import unittest
from unittest.mock import patch, MagicMock
from uci_monitor.models import Performance
from uci_monitor.notifier import NtfyNotifier, NotificationDispatcher, ConsoleNotifier


class TestNotifiers(unittest.TestCase):

    def _sample_perf(self):
        return Performance(
            performance_id="DC5F1000023ZIQERCX",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-10",
            time="22:30",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|omu|2d|465",
            subtext="OmU",
            booking_path="/kino-buchung/performanceId/DC5F1000023ZIQERCX/siteId/82/945069",
            booking_url="https://www.uci-kinowelt.de/kino-buchung/performanceId/DC5F1000023ZIQERCX/siteId/82/945069",
            direct_booking_url="https://buchung.uci-kinowelt.de/?perf_id=DC5F1000023ZIQERCX&site_id=82",
        )

    @patch("urllib.request.urlopen")
    def test_ntfy_single_performance(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        notifier = NtfyNotifier(topic="test-topic-123")
        perf = self._sample_perf()
        success = notifier.notify_new_sessions([perf])

        self.assertTrue(success)
        mock_urlopen.assert_called_once()
        req = mock_urlopen.call_args[0][0]

        self.assertEqual(req.full_url, "https://ntfy.sh/test-topic-123")
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.headers.get("Priority"), "urgent")
        self.assertEqual(req.headers.get("Click"), perf.direct_booking_url)
        self.assertIn("view, Book Now", req.headers.get("Actions"))

        body = req.data.decode("utf-8")
        self.assertIn("Die Odyssee", body)
        self.assertIn("Kino 01 IMAX", body)
        self.assertIn("22:30", body)

    @patch("urllib.request.urlopen")
    def test_ntfy_multiple_performances(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        notifier = NtfyNotifier(topic="test-topic-multi")
        p1 = self._sample_perf()
        p2 = Performance(
            performance_id="EC5F1000023ZIQERCX",
            film_id="407923",
            film_title="Die Odyssee",
            date="2026-09-11",
            time="22:30",
            auditorium="Kino 01 IMAX",
            cinema_name="Berlin - East Side Gallery | Luxe",
            site_id="82",
            version_raw="imax|omu|2d|465",
            subtext="OmU",
            booking_path="/kino-buchung/performanceId/EC5F1000023ZIQERCX/siteId/82/945132",
            booking_url="https://www.uci-kinowelt.de/kino-buchung/performanceId/EC5F1000023ZIQERCX/siteId/82/945132",
            direct_booking_url="https://buchung.uci-kinowelt.de/?perf_id=EC5F1000023ZIQERCX&site_id=82",
        )

        success = notifier.notify_new_sessions([p1, p2])
        self.assertTrue(success)
        req = mock_urlopen.call_args[0][0]
        self.assertIn("2 New IMAX OmU Sessions", req.headers.get("Title"))

    @patch("urllib.request.urlopen")
    def test_ntfy_test_message(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        notifier = NtfyNotifier(topic="test-topic-test")
        success = notifier.send_test_message()
        self.assertTrue(success)
        req = mock_urlopen.call_args[0][0]
        self.assertIn("Test Notification", req.headers.get("Title"))

    def test_dispatcher(self):
        console = ConsoleNotifier()
        dispatcher = NotificationDispatcher([console])
        self.assertTrue(dispatcher.send_test_message())
        self.assertTrue(dispatcher.notify_new_sessions([self._sample_perf()]))


if __name__ == "__main__":
    unittest.main()
