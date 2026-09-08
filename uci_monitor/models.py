"""Data models for cinema performances, screenings, and notifications."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass(frozen=True)
class Performance:
    """Represents a specific movie screening performance at UCI Kinowelt."""

    performance_id: str
    film_id: str
    film_title: str
    date: str  # Format: YYYY-MM-DD
    time: str  # Format: HH:MM
    auditorium: str
    cinema_name: str
    site_id: str
    version_raw: str
    subtext: str = ""
    booking_path: str = ""
    booking_url: str = ""
    direct_booking_url: str = ""

    @property
    def version_tokens(self) -> List[str]:
        """Return lowercase version tokens split by pipe."""
        return [t.strip().lower() for t in self.version_raw.split("|") if t.strip()]

    @property
    def is_imax(self) -> bool:
        """Check if performance is in IMAX auditorium or marked with IMAX attribute."""
        return "imax" in self.version_tokens or "imax" in self.auditorium.lower()

    @property
    def is_omu(self) -> bool:
        """Check if performance is original version with subtitles (OmU)."""
        return "omu" in self.version_tokens or "omu" in self.subtext.lower()

    @property
    def is_ov(self) -> bool:
        """Check if performance is original version without subtitles (OV)."""
        return "ov" in self.version_tokens or "ov" in self.subtext.lower()

    @property
    def is_isense(self) -> bool:
        """Check if performance is in iSense auditorium or format."""
        return any(t in ("isens", "isense") for t in self.version_tokens) or "isense" in self.auditorium.lower()

    @property
    def is_german_dub(self) -> bool:
        """Check if performance is German-dubbed (neither OmU nor OV)."""
        return not self.is_omu and not self.is_ov

    @property
    def formatted_datetime(self) -> str:
        """Return readable formatted date and time."""
        try:
            dt = datetime.strptime(f"{self.date} {self.time}", "%Y-%m-%d %H:%M")
            return dt.strftime("%a, %d.%m.%Y um %H:%M Uhr")
        except ValueError:
            return f"{self.date} {self.time}"

    def matches_target_criteria(
        self,
        require_imax: bool = True,
        require_omu: bool = True,
        exclude_isense: bool = True,
        exclude_german_dub: bool = True,
    ) -> bool:
        """
        Verify whether the performance matches specific format filtering requirements.
        Specifically: Must match IMAX AND OmU. Exclude standard 2D, iSense, and German-dubbed sessions.
        """
        if require_imax and not self.is_imax:
            return False
        if require_omu and not self.is_omu:
            return False
        if exclude_isense and self.is_isense:
            return False
        if exclude_german_dub and self.is_german_dub:
            return False
        return True

    def display_str(self) -> str:
        """Human-readable one-line representation."""
        badges = []
        if self.is_imax:
            badges.append("IMAX")
        if self.is_omu:
            badges.append("OmU")
        elif self.is_ov:
            badges.append("OV")
        else:
            badges.append("DE")
        if self.is_isense:
            badges.append("iSense")

        badge_str = f"[{' | '.join(badges)}]"
        return (
            f"{self.film_title} | {self.formatted_datetime} | "
            f"{self.auditorium} {badge_str} | ID: {self.performance_id}"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize performance to dictionary for JSON persistence."""
        return {
            "performance_id": self.performance_id,
            "film_id": self.film_id,
            "film_title": self.film_title,
            "date": self.date,
            "time": self.time,
            "auditorium": self.auditorium,
            "cinema_name": self.cinema_name,
            "site_id": self.site_id,
            "version_raw": self.version_raw,
            "subtext": self.subtext,
            "booking_path": self.booking_path,
            "booking_url": self.booking_url,
            "direct_booking_url": self.direct_booking_url,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Performance":
        """Reconstruct performance object from dictionary."""
        return cls(
            performance_id=data["performance_id"],
            film_id=data["film_id"],
            film_title=data["film_title"],
            date=data["date"],
            time=data["time"],
            auditorium=data.get("auditorium", ""),
            cinema_name=data.get("cinema_name", ""),
            site_id=data.get("site_id", ""),
            version_raw=data.get("version_raw", ""),
            subtext=data.get("subtext", ""),
            booking_path=data.get("booking_path", ""),
            booking_url=data.get("booking_url", ""),
            direct_booking_url=data.get("direct_booking_url", ""),
        )


@dataclass
class NotificationMessage:
    """Represents a notification payload ready to dispatch."""

    title: str
    body: str
    click_url: Optional[str] = None
    actions: List[Dict[str, str]] = field(default_factory=list)
    priority: str = "high"
    tags: List[str] = field(default_factory=lambda: ["film_projector", "bell"])
