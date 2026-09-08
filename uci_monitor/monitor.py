"""Core monitor engine orchestrating fetch, parse, state diffing, and notifications."""

import time
import signal
import logging
from datetime import datetime
from typing import List, Optional

from uci_monitor.config import MonitorConfig
from uci_monitor.models import Performance
from uci_monitor.parser import CinemaScheduleParser
from uci_monitor.fetcher import ScheduleFetcher
from uci_monitor.notifier import (
    NtfyNotifier,
    DesktopNotifier,
    ConsoleNotifier,
    NotificationDispatcher,
)
from uci_monitor.state import StateTracker

logger = logging.getLogger(__name__)


class CinemaBookingMonitor:
    """Monitors UCI Kinowelt schedules for specific movie sessions and alerts on new drops."""

    def __init__(
        self,
        config: Optional[MonitorConfig] = None,
        dispatcher: Optional[NotificationDispatcher] = None,
        state_tracker: Optional[StateTracker] = None,
    ):
        self.config = config or MonitorConfig()
        self.fetcher = ScheduleFetcher(
            cinema_url=self.config.cinema_url,
            film_url=self.config.film_page_url,
            user_agent=self.config.user_agent,
            timeout=self.config.request_timeout,
        )
        self.parser = CinemaScheduleParser(
            target_titles=self.config.target_titles,
            target_film_id=self.config.target_film_id,
            require_imax=self.config.require_imax,
            require_omu=self.config.require_omu,
            exclude_isense=self.config.exclude_isense,
            exclude_german_dub=self.config.exclude_german_dub,
        )
        self.state_tracker = state_tracker or StateTracker(self.config.state_file)

        if dispatcher is not None:
            self.dispatcher = dispatcher
        else:
            self.dispatcher = NotificationDispatcher()
            # Always add console notifier
            self.dispatcher.add_notifier(ConsoleNotifier())

            # Add ntfy.sh notifier if topic is provided
            if self.config.ntfy_topic:
                self.dispatcher.add_notifier(
                    NtfyNotifier(
                        topic=self.config.ntfy_topic,
                        server=self.config.ntfy_server,
                    )
                )

            # Add desktop notifier if enabled
            if self.config.enable_desktop_notifications:
                self.dispatcher.add_notifier(DesktopNotifier())

        self._running = False

    def check_once(
        self,
        source: Optional[str] = None,
        dry_run: bool = False,
        notify_existing: bool = False,
    ) -> List[Performance]:
        """
        Execute a single polling cycle.
        Returns newly discovered matching performances.
        """
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info("[%s] Checking cinema schedule for %s...", now_str, self.config.target_titles)

        # 1. Fetch HTML
        html_content = self.fetcher.fetch(source)

        # 2. Parse performances
        all_movie_perfs, matching_perfs = self.parser.parse_all_and_filtered(html_content)

        logger.info(
            "Found %d total performances for target movie, %d strictly matching IMAX OmU.",
            len(all_movie_perfs),
            len(matching_perfs),
        )

        if dry_run:
            logger.info("[Dry Run] Discovered %d matching sessions (no state changes or alerts sent):", len(matching_perfs))
            for p in matching_perfs:
                print(f"  • {p.display_str()}")
                print(f"    Direct: {p.direct_booking_url}")
            return matching_perfs

        # 3. Check for new session drops against state
        notify_flag = notify_existing or self.config.notify_existing
        new_drops = self.state_tracker.identify_new_drops(matching_perfs, notify_existing=notify_flag)

        if new_drops:
            logger.info("🚨 Detected %d NEW session drop(s)! Dispatching notifications...", len(new_drops))
            self.dispatcher.notify_new_sessions(new_drops)
        else:
            logger.info("No new session drops detected. All %d matching sessions already known.", len(matching_perfs))

        return new_drops

    def run_loop(
        self,
        source: Optional[str] = None,
        dry_run: bool = False,
        notify_existing: bool = False,
    ) -> None:
        """Run the monitoring loop continuously with the configured interval."""
        self._running = True

        def handle_signal(sig, frame):
            logger.info("Interrupt received, shutting down gracefully...")
            self._running = False

        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

        logger.info(
            "Starting UCI booking monitor for %s at %s. Polling every %d seconds.",
            self.config.target_titles,
            self.config.cinema_name,
            self.config.polling_interval,
        )

        cycle = 1
        while self._running:
            try:
                logger.info("--- Monitor Cycle #%d ---", cycle)
                self.check_once(source=source, dry_run=dry_run, notify_existing=notify_existing)
                # notify_existing only applies to the first cycle
                notify_existing = False
            except Exception as e:
                logger.error("Error during monitor cycle #%d: %s", cycle, e, exc_info=True)

            if not self._running:
                break

            logger.info("Sleeping for %d seconds until next check...", self.config.polling_interval)
            # Sleep in 1-second chunks to respond quickly to shutdown signals
            for _ in range(self.config.polling_interval):
                if not self._running:
                    break
                time.sleep(1)

            cycle += 1

        logger.info("UCI booking monitor terminated.")
