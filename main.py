#!/usr/bin/env python3
"""
UCI Kinowelt Booking Monitor & Notifier CLI
Target: Christopher Nolan's "The Odyssey" (Die Odyssee) in IMAX OmU at UCI Luxe East Side Gallery (Berlin).
"""

import sys
import argparse
import logging
from uci_monitor.config import MonitorConfig
from uci_monitor.monitor import CinemaBookingMonitor
from uci_monitor.state import StateTracker
from uci_monitor.notifier import NtfyNotifier, DesktopNotifier, NotificationDispatcher, ConsoleNotifier


def setup_logging(verbose: bool = False):
    """Configure stdout logging format and log levels."""
    log_level = logging.DEBUG if verbose else logging.INFO
    log_format = "%(asctime)s [%(levelname)s] %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    logging.basicConfig(level=log_level, format=log_format, datefmt=date_format)


def build_arg_parser() -> argparse.ArgumentParser:
    """Construct CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Automated booking monitor for UCI Luxe East Side Gallery (Berlin) - Christopher Nolan's 'The Odyssey' (IMAX OmU)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single run against live cinema schedule (dry run mode):
  python3 main.py --once --dry-run

  # Test against local sample file:
  python3 main.py --file sample_page.html --dry-run

  # Send test push notification to verify ntfy.sh setup:
  python3 main.py --test-notify --ntfy-topic my-secret-topic

  # Start continuous monitor polling every 2 minutes with push alerts:
  python3 main.py --ntfy-topic my-secret-topic --interval 120

  # Alert immediately for all current matching sessions:
  python3 main.py --notify-existing --once
        """,
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to JSON configuration file (default: config.json if present)",
    )
    parser.add_argument(
        "--url",
        type=str,
        default=None,
        help="Cinema schedule URL to monitor (default: https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery)",
    )
    parser.add_argument(
        "--film-url",
        type=str,
        default=None,
        help="Direct film page URL fallback",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to local HTML file to parse instead of making network requests (e.g. sample_page.html)",
    )
    parser.add_argument(
        "--ntfy-topic",
        type=str,
        default=None,
        help="ntfy.sh topic for push notifications (e.g. uci-luxe-odyssey-imax)",
    )
    parser.add_argument(
        "--ntfy-server",
        type=str,
        default=None,
        help="ntfy server URL (default: https://ntfy.sh)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Polling interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Perform a single check cycle and exit immediately",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and display matching sessions without updating state or sending push notifications",
    )
    parser.add_argument(
        "--notify-existing",
        action="store_true",
        help="Trigger alerts immediately for existing matching sessions (instead of only new drops)",
    )
    parser.add_argument(
        "--test-notify",
        action="store_true",
        help="Send a test notification to ntfy.sh and desktop, then exit",
    )
    parser.add_argument(
        "--reset-state",
        action="store_true",
        help="Clear persistent monitor state file and exit",
    )
    parser.add_argument(
        "--no-desktop",
        action="store_true",
        help="Disable native desktop notifications",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable detailed debug logging",
    )

    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    # 1. Load configuration
    config = MonitorConfig.load_from_env_and_file(args.config)

    # CLI flag overrides
    if args.url:
        config.cinema_url = args.url
    if args.film_url:
        config.film_page_url = args.film_url
    if args.ntfy_topic:
        config.ntfy_topic = args.ntfy_topic
    if args.ntfy_server:
        config.ntfy_server = args.ntfy_server
    if args.interval:
        config.polling_interval = args.interval
    if args.no_desktop:
        config.enable_desktop_notifications = False
    if args.notify_existing:
        config.notify_existing = True

    # 2. Handle --reset-state
    if args.reset_state:
        tracker = StateTracker(config.state_file)
        tracker.reset()
        print(f"Monitor state cleared ({config.state_file}).")
        sys.exit(0)

    # 3. Handle --test-notify
    if args.test_notify:
        print(f"Sending test notification via ntfy.sh (topic: {config.ntfy_topic}) and desktop...")
        dispatcher = NotificationDispatcher()
        dispatcher.add_notifier(ConsoleNotifier())
        if config.ntfy_topic:
            dispatcher.add_notifier(NtfyNotifier(topic=config.ntfy_topic, server=config.ntfy_server))
        if config.enable_desktop_notifications:
            dispatcher.add_notifier(DesktopNotifier())

        success = dispatcher.send_test_message()
        if success:
            print("✅ Test notification dispatched successfully!")
            print(f"   Subscribe on your phone or browser at: {config.ntfy_server}/{config.ntfy_topic}")
            sys.exit(0)
        else:
            print("❌ Failed to dispatch test notification. Check your network or topic configuration.")
            sys.exit(1)

    # 4. Initialize Monitor
    monitor = CinemaBookingMonitor(config=config)

    # 5. Run monitor
    source = args.file if args.file else config.cinema_url
    if args.once:
        monitor.check_once(source=source, dry_run=args.dry_run, notify_existing=args.notify_existing)
    else:
        monitor.run_loop(source=source, dry_run=args.dry_run, notify_existing=args.notify_existing)


if __name__ == "__main__":
    main()
