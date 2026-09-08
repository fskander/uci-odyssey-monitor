"""State management for tracking observed cinema performances across monitor runs."""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Set, Any, Optional
from uci_monitor.models import Performance

logger = logging.getLogger(__name__)


class StateTracker:
    """Manages persistent state of known cinema sessions to identify new drops."""

    def __init__(self, state_file_path: str = "monitor_state.json"):
        self.state_file_path = state_file_path
        self.known_performances: Dict[str, Dict[str, Any]] = {}
        self.last_check_timestamp: Optional[str] = None
        self._is_first_run: bool = True
        self.load()

    def load(self) -> None:
        """Load state from disk if file exists."""
        if os.path.exists(self.state_file_path):
            try:
                with open(self.state_file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.known_performances = data.get("known_performances", {})
                    self.last_check_timestamp = data.get("last_check_timestamp")
                    self._is_first_run = len(self.known_performances) == 0
                    logger.debug(
                        "Loaded %d known performances from state file %s",
                        len(self.known_performances),
                        self.state_file_path,
                    )
            except Exception as e:
                logger.warning("Error reading state file %s, initializing empty state: %s", self.state_file_path, e)
                self.known_performances = {}
                self._is_first_run = True
        else:
            self.known_performances = {}
            self._is_first_run = True

    def save(self) -> None:
        """Atomically persist current state to disk."""
        now_str = datetime.now(timezone.utc).isoformat()
        self.last_check_timestamp = now_str
        payload = {
            "last_check_timestamp": self.last_check_timestamp,
            "total_known_performances": len(self.known_performances),
            "known_performances": self.known_performances,
        }

        temp_path = f"{self.state_file_path}.tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            os.replace(temp_path, self.state_file_path)
            logger.debug("Successfully persisted state to %s", self.state_file_path)
        except Exception as e:
            logger.error("Failed saving state to %s: %s", self.state_file_path, e)
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def identify_new_drops(
        self,
        current_performances: List[Performance],
        notify_existing: bool = False,
    ) -> List[Performance]:
        """
        Compare current performances against known state.
        Returns a list of newly dropped performances.
        
        If it's the very first run and notify_existing is False,
        we baseline all performances into known state without generating alerts.
        """
        new_drops: List[Performance] = []
        now_str = datetime.now(timezone.utc).isoformat()

        if self._is_first_run and not notify_existing:
            logger.info(
                "Initial run: Baseling %d current matching sessions without alerts.",
                len(current_performances),
            )
            for p in current_performances:
                perf_dict = p.to_dict()
                perf_dict["first_seen"] = now_str
                self.known_performances[p.performance_id] = perf_dict
            self._is_first_run = False
            self.save()
            return []

        # Find any performance not currently in known state
        for p in current_performances:
            if p.performance_id not in self.known_performances:
                new_drops.append(p)
                perf_dict = p.to_dict()
                perf_dict["first_seen"] = now_str
                self.known_performances[p.performance_id] = perf_dict
            else:
                # Update existing performance details (e.g. time or link updates)
                perf_dict = p.to_dict()
                perf_dict["first_seen"] = self.known_performances[p.performance_id].get("first_seen", now_str)
                perf_dict["last_seen"] = now_str
                self.known_performances[p.performance_id] = perf_dict

        self._is_first_run = False
        self.save()
        return new_drops

    def reset(self) -> None:
        """Clear all stored performance state."""
        self.known_performances.clear()
        self.last_check_timestamp = None
        self._is_first_run = True
        if os.path.exists(self.state_file_path):
            try:
                os.remove(self.state_file_path)
            except OSError as e:
                logger.warning("Could not remove state file: %s", e)
