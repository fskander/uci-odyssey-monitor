"""Notification dispatchers for ntfy.sh, local desktop alerts, and console logging."""

import os
import sys
import subprocess
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Optional
from uci_monitor.models import Performance, NotificationMessage

logger = logging.getLogger(__name__)


class BaseNotifier(ABC):
    """Abstract base class for notification channels."""

    @abstractmethod
    def notify_new_sessions(self, performances: List[Performance]) -> bool:
        """Send notification alerting about new or released cinema sessions."""
        pass

    @abstractmethod
    def send_test_message(self) -> bool:
        """Send a test verification notification."""
        pass


class NtfyNotifier(BaseNotifier):
    """Sends push notifications via ntfy.sh with direct action buttons."""

    def __init__(
        self,
        topic: str = "uci-luxe-odyssey-imax",
        server: str = "https://ntfy.sh",
        timeout: int = 15,
    ):
        self.topic = topic.strip().lstrip("/")
        self.server = server.rstrip("/")
        self.timeout = timeout

    @property
    def endpoint_url(self) -> str:
        return f"{self.server}/{self.topic}"

    def notify_new_sessions(self, performances: List[Performance]) -> bool:
        if not performances:
            return False

        count = len(performances)
        primary = performances[0]

        if count == 1:
            title = f"🎬 IMAX OmU Drop: {primary.film_title}!"
            body_lines = [
                f"New IMAX OmU session available for {primary.film_title}!",
                f"📅 {primary.formatted_datetime}",
                f"🏛️ Auditorium: {primary.auditorium}",
                f"📍 Cinema: {primary.cinema_name}",
                f"🎟️ Booking: {primary.direct_booking_url or primary.booking_url}",
            ]
        else:
            title = f"🚨 {count} New IMAX OmU Sessions: {primary.film_title}!"
            body_lines = [
                f"{count} new IMAX OmU sessions dropped at {primary.cinema_name} for {primary.film_title}:",
                "",
            ]
            for p in performances:
                body_lines.append(f"• {p.formatted_datetime} | {p.auditorium}")
                body_lines.append(f"  Direct Link: {p.direct_booking_url}")
            body_lines.append("\nBook your seats immediately before they sell out!")

        click_url = primary.direct_booking_url or primary.booking_url

        # Build action buttons for ntfy: open primary booking and cinema schedule
        actions = [f"view, Book Now, {click_url}"]
        if len(performances) > 1:
            actions.append("view, Cinema Schedule, https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery")

        msg = NotificationMessage(
            title=title,
            body="\n".join(body_lines),
            click_url=click_url,
            actions=[{"raw": a} for a in actions],
            priority="urgent",
            tags=["film_projector", "ticket", "popcorn", "bell"],
        )

        return self._send_ntfy(msg)

    def send_test_message(self) -> bool:
        msg = NotificationMessage(
            title="🔔 UCI Monitor: Test Notification",
            body=(
                "This is a test notification from the UCI Luxe Berlin monitor.\n"
                "Target: Christopher Nolan's The Odyssey (Die Odyssee) in IMAX OmU.\n"
                "System is active and listening for new session drops!"
            ),
            click_url="https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery",
            actions=[{"raw": "view, Open UCI Kinoprogramm, https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery"}],
            priority="high",
            tags=["white_check_mark", "cinema"],
        )
        return self._send_ntfy(msg)

    def _send_ntfy(self, msg: NotificationMessage) -> bool:
        try:
            req = urllib.request.Request(
                self.endpoint_url,
                data=msg.body.encode("utf-8"),
                method="POST",
            )
            # ntfy headers with ASCII / UTF-8 fallback
            req.add_header("Title", msg.title.encode("utf-8").decode("latin1", errors="replace"))
            req.add_header("Priority", msg.priority)
            req.add_header("Tags", ",".join(msg.tags))

            if msg.click_url:
                req.add_header("Click", msg.click_url)

            if msg.actions:
                # ntfy supports Actions header format: view, Label, URL; ...
                action_headers = "; ".join(a["raw"] for a in msg.actions if "raw" in a)
                if action_headers:
                    req.add_header("Actions", action_headers)

            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status in (200, 201, 204):
                    logger.info("Successfully sent ntfy.sh notification to topic '%s'", self.topic)
                    return True
                else:
                    logger.warning("ntfy.sh responded with unexpected HTTP %s", resp.status)
                    return False
        except urllib.error.HTTPError as e:
            logger.error("HTTP error sending to ntfy.sh: %s - %s", e.code, e.read().decode(errors="replace"))
            return False
        except Exception as e:
            logger.error("Failed to send ntfy.sh notification: %s", e)
            return False


class DesktopNotifier(BaseNotifier):
    """Sends native desktop notifications via macOS osascript or Linux notify-send."""

    def notify_new_sessions(self, performances: List[Performance]) -> bool:
        if not performances:
            return False

        primary = performances[0]
        count = len(performances)
        title = "UCI Luxe IMAX Alert"
        if count == 1:
            subtitle = f"IMAX OmU Drop: {primary.film_title}"
            message = f"{primary.formatted_datetime} at {primary.auditorium}"
        else:
            subtitle = f"{count} New IMAX OmU Sessions!"
            message = f"{primary.film_title}: First at {primary.formatted_datetime}"

        return self._send_desktop_notification(title, subtitle, message)

    def send_test_message(self) -> bool:
        return self._send_desktop_notification(
            title="UCI Luxe Monitor",
            subtitle="Test Alert",
            message="Monitoring active for Christopher Nolan's The Odyssey (IMAX OmU)",
        )

    def _send_desktop_notification(self, title: str, subtitle: str, message: str) -> bool:
        if sys.platform == "darwin":
            try:
                script = f'display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"'
                subprocess.run(["osascript", "-e", script], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                logger.info("macOS desktop notification displayed.")
                return True
            except Exception as e:
                logger.debug("Could not send macOS notification: %s", e)
                return False
        elif sys.platform.startswith("linux"):
            try:
                subprocess.run(["notify-send", f"{title}: {subtitle}", message], check=True)
                return True
            except Exception as e:
                logger.debug("Could not send Linux notification: %s", e)
                return False
        return False


class ConsoleNotifier(BaseNotifier):
    """Prints colorful, structured session drop banners to terminal stdout."""

    GREEN = "\033[92m"
    CYAN = "\033[96m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def notify_new_sessions(self, performances: List[Performance]) -> bool:
        if not performances:
            return False

        print(f"\n{self.GREEN}{self.BOLD}{'=' * 75}{self.RESET}")
        print(f"{self.GREEN}{self.BOLD}🚨 MATCHING INVENTORY ALERT: {len(performances)} NEW SESSION(S) DROPPED! 🚨{self.RESET}")
        print(f"{self.GREEN}{self.BOLD}{'=' * 75}{self.RESET}")

        for i, p in enumerate(performances, 1):
            print(f"\n{self.BOLD}[{i}] {p.film_title} — IMAX OmU{self.RESET}")
            print(f"    📅 When:       {self.CYAN}{p.formatted_datetime}{self.RESET}")
            print(f"    🏛️  Auditorium: {p.auditorium} (Version: {p.version_raw})")
            print(f"    📍 Cinema:     {p.cinema_name}")
            print(f"    🔗 Direct URL: {self.YELLOW}{p.direct_booking_url}{self.RESET}")
            print(f"    🌐 Page URL:   {p.booking_url}")

        print(f"\n{self.GREEN}{self.BOLD}{'=' * 75}{self.RESET}\n")
        return True

    def send_test_message(self) -> bool:
        print(f"{self.CYAN}[Test Notification] Console output verified.{self.RESET}")
        return True


class NotificationDispatcher(BaseNotifier):
    """Combines multiple notifiers into a unified notification pipeline."""

    def __init__(self, notifiers: Optional[List[BaseNotifier]] = None):
        self.notifiers = notifiers or []

    def add_notifier(self, notifier: BaseNotifier):
        self.notifiers.append(notifier)

    def notify_new_sessions(self, performances: List[Performance]) -> bool:
        success = False
        for n in self.notifiers:
            try:
                if n.notify_new_sessions(performances):
                    success = True
            except Exception as e:
                logger.error("Notifier %s failed: %s", n.__class__.__name__, e)
        return success

    def send_test_message(self) -> bool:
        success = False
        for n in self.notifiers:
            try:
                if n.send_test_message():
                    success = True
            except Exception as e:
                logger.error("Notifier %s test failed: %s", n.__class__.__name__, e)
        return success
