"""Configuration settings and environment loaders for the UCI booking monitor."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MonitorConfig:
    """Configuration options for cinema monitoring and notifications."""

    cinema_url: str = "https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery"
    film_page_url: str = "https://www.uci-kinowelt.de/film/die-odyssee/407923/berlin-east-side-gallery/82"
    cinema_id: str = "82"
    cinema_name: str = "UCI Luxe East Side Gallery, Berlin"
    target_titles: List[str] = field(
        default_factory=lambda: ["The Odyssey", "Die Odyssee"]
    )
    target_film_id: Optional[str] = "407923"
    require_imax: bool = True
    require_omu: bool = True
    exclude_isense: bool = True
    exclude_german_dub: bool = True
    ntfy_server: str = "https://ntfy.sh"
    ntfy_topic: str = "uci-luxe-odyssey-imax"
    polling_interval: int = 300
    state_file: str = "monitor_state.json"
    enable_desktop_notifications: bool = True
    notify_existing: bool = False
    request_timeout: int = 20
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    )

    @classmethod
    def load_from_env_and_file(cls, config_path: Optional[str] = None) -> "MonitorConfig":
        """Load configuration overriding defaults from JSON file and environment variables."""
        cfg = cls()

        # Check config file if specified or default config.json exists
        file_to_check = config_path or os.environ.get("UCI_CONFIG_FILE", "config.json")
        if os.path.exists(file_to_check):
            try:
                with open(file_to_check, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if hasattr(cfg, k):
                            setattr(cfg, k, v)
            except Exception as e:
                print(f"[Warning] Could not load config file {file_to_check}: {e}")

        # Environment variable overrides
        if os.environ.get("UCI_CINEMA_URL"):
            cfg.cinema_url = os.environ["UCI_CINEMA_URL"]
        if os.environ.get("UCI_FILM_URL"):
            cfg.film_page_url = os.environ["UCI_FILM_URL"]
        if os.environ.get("NTFY_TOPIC"):
            cfg.ntfy_topic = os.environ["NTFY_TOPIC"]
        if os.environ.get("NTFY_SERVER"):
            cfg.ntfy_server = os.environ["NTFY_SERVER"]
        if os.environ.get("UCI_POLL_INTERVAL"):
            try:
                cfg.polling_interval = int(os.environ["UCI_POLL_INTERVAL"])
            except ValueError:
                pass
        if os.environ.get("UCI_STATE_FILE"):
            cfg.state_file = os.environ["UCI_STATE_FILE"]
        if os.environ.get("UCI_NOTIFY_EXISTING"):
            cfg.notify_existing = os.environ["UCI_NOTIFY_EXISTING"].lower() in ("1", "true", "yes")

        return cfg
