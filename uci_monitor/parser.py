"""Parser for UCI Kinowelt cinema schedule and film HTML pages."""

import re
from typing import List, Dict, Set, Tuple, Optional
from uci_monitor.models import Performance


class CinemaScheduleParser:
    """Parses cinema schedule HTML to extract film sessions and filter target formats."""

    def __init__(
        self,
        target_titles: Optional[List[str]] = None,
        target_film_id: Optional[str] = "407923",
        require_imax: bool = True,
        require_omu: bool = True,
        exclude_isense: bool = True,
        exclude_german_dub: bool = True,
    ):
        self.target_titles = target_titles or ["The Odyssey", "Die Odyssee"]
        self.target_film_id = target_film_id
        self.require_imax = require_imax
        self.require_omu = require_omu
        self.exclude_isense = exclude_isense
        self.exclude_german_dub = exclude_german_dub

    def parse(self, html_content: str) -> List[Performance]:
        """Parse HTML content and return only performances matching target format specifications."""
        all_target_perfs, matching_perfs = self.parse_all_and_filtered(html_content)
        return matching_perfs

    def parse_all_and_filtered(
        self, html_content: str
    ) -> Tuple[List[Performance], List[Performance]]:
        """
        Parse HTML content and return two lists:
        1. All performances for the target movie (regardless of format).
        2. Filtered performances meeting the strict IMAX + OmU requirements.
        """
        cinema_name, site_id = self._extract_cinema_info(html_content)
        matching_film_ids, film_title_map = self._extract_matching_film_ids(html_content)

        if self.target_film_id:
            matching_film_ids.add(self.target_film_id)
            if self.target_film_id not in film_title_map:
                film_title_map[self.target_film_id] = "Die Odyssee"

        # Pattern to capture performance badge <a> tag and its inner HTML
        badge_pattern = re.compile(
            r"<a\s+([^>]*class=\"[^\"]*badge-performance[^\"]*\"[^>]*)>(.*?)</a>",
            re.DOTALL | re.IGNORECASE,
        )

        all_target_performances: List[Performance] = []
        matching_performances: List[Performance] = []
        seen_perf_ids: Set[str] = set()

        for match in badge_pattern.finditer(html_content):
            attr_str, inner_html = match.groups()
            attrs = dict(re.findall(r"([a-zA-Z0-9\-_:]+)=\"([^\"]*)\"", attr_str))

            href = attrs.get("href", "").strip()
            # If href doesn't lead to kino-buchung, it is likely a footer/recommendation link
            if not href or "/kino-buchung/" not in href:
                continue

            perf_id_match = re.search(r"performanceId/([^/]+)", href)
            if not perf_id_match:
                continue
            perf_id = perf_id_match.group(1).strip()

            if perf_id in seen_perf_ids:
                continue
            seen_perf_ids.add(perf_id)

            badge_film_id = attrs.get("data-tracking-film-id", "").strip()

            # Check if badge belongs to our target film
            is_target_film = False
            film_title = film_title_map.get(badge_film_id, "Die Odyssee")

            if badge_film_id and badge_film_id in matching_film_ids:
                is_target_film = True
            elif not badge_film_id and self.target_film_id:
                # In direct film page, some badges might rely on page context
                is_target_film = True
                badge_film_id = self.target_film_id

            if not is_target_film:
                continue

            # Parse date: data-tracking-date="2026-09-10" or data-date="20260910"
            date_str = attrs.get("data-tracking-date", "").strip()
            if not date_str:
                raw_date = attrs.get("data-date", "").strip()
                if len(raw_date) == 8 and raw_date.isdigit():
                    date_str = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
                else:
                    date_str = raw_date

            time_str = attrs.get("data-tracking-time") or attrs.get("data-time", "").strip()
            auditorium = attrs.get("data-tracking-auditorium", "").strip()
            badge_cinema = attrs.get("data-tracking-location", "").strip() or cinema_name
            site_id_match = re.search(r"siteId/([^/]+)", href)
            badge_site_id = site_id_match.group(1) if site_id_match else site_id

            version_raw = attrs.get("data-version", "").strip()

            # Extract subtext from inner HTML: e.g. <span class="performance-badge__subtext">OmU</span>
            subtext_match = re.search(
                r"class=\"[^\"]*performance-badge__subtext[^\"]*\">([^<]+)</span>",
                inner_html,
                re.IGNORECASE,
            )
            subtext = subtext_match.group(1).strip() if subtext_match else ""

            # Check if badge classes include specific attributes
            classes = attrs.get("class", "").lower().split()
            version_tokens = [t.strip().lower() for t in version_raw.split("|") if t.strip()]
            if "attribute-imax" in classes and "imax" not in version_tokens:
                version_raw = f"{version_raw}|imax" if version_raw else "imax"
            if "attribute-omu" in classes and "omu" not in version_tokens:
                version_raw = f"{version_raw}|omu" if version_raw else "omu"
            if "attribute-ov" in classes and "ov" not in version_tokens:
                version_raw = f"{version_raw}|ov" if version_raw else "ov"
            if "attribute-isense" in classes and not any("isens" in t for t in version_tokens):
                version_raw = f"{version_raw}|isens" if version_raw else "isens"

            full_booking_url = f"https://www.uci-kinowelt.de{href}" if href.startswith("/") else href
            direct_booking_url = (
                f"https://buchung.uci-kinowelt.de/?perf_id={perf_id}&site_id={badge_site_id}"
            )

            perf = Performance(
                performance_id=perf_id,
                film_id=badge_film_id or self.target_film_id or "",
                film_title=film_title,
                date=date_str,
                time=time_str,
                auditorium=auditorium,
                cinema_name=badge_cinema,
                site_id=badge_site_id,
                version_raw=version_raw,
                subtext=subtext,
                booking_path=href,
                booking_url=full_booking_url,
                direct_booking_url=direct_booking_url,
            )

            all_target_performances.append(perf)

            if perf.matches_target_criteria(
                require_imax=self.require_imax,
                require_omu=self.require_omu,
                exclude_isense=self.exclude_isense,
                exclude_german_dub=self.exclude_german_dub,
            ):
                matching_performances.append(perf)

        # Sort chronologically by date and time
        all_target_performances.sort(key=lambda p: (p.date, p.time))
        matching_performances.sort(key=lambda p: (p.date, p.time))

        return all_target_performances, matching_performances

    def _extract_cinema_info(self, html_content: str) -> Tuple[str, str]:
        """Extract cinema name and site ID from meta tags."""
        cinema_match = re.search(
            r"<meta\s+property=\"uci:cinema\"\s+content=\"([^\"]+)\"", html_content, re.I
        )
        cinema_id_match = re.search(
            r"<meta\s+property=\"uci:cinemaId\"\s+content=\"([^\"]+)\"", html_content, re.I
        )
        cinema_name = cinema_match.group(1).strip() if cinema_match else "Berlin - East Side Gallery | Luxe"
        site_id = cinema_id_match.group(1).strip() if cinema_id_match else "82"
        return cinema_name, site_id

    def _extract_matching_film_ids(self, html_content: str) -> Tuple[Set[str], Dict[str, str]]:
        """Find film IDs and normalized titles matching the configured target movie titles."""
        matching_ids: Set[str] = set()
        title_map: Dict[str, str] = {}

        # 1. Meta tag check (used in film pages)
        meta_title = re.search(
            r"<meta\s+property=\"uci:filmTitle\"\s+content=\"([^\"]+)\"", html_content, re.I
        )
        meta_id = re.search(
            r"<meta\s+property=\"uci:filmId\"\s+content=\"([^\"]+)\"", html_content, re.I
        )
        if meta_title and meta_id:
            title = meta_title.group(1).strip()
            fid = meta_id.group(1).strip()
            if self._is_title_match(title):
                matching_ids.add(fid)
                title_map[fid] = title

        # 2. Trailer buttons with data attributes: data-film-id="407923" data-film-title="Die Odyssee"
        for m in re.finditer(
            r"data-film-id=\"(\d+)\"[^>]*data-film-title=\"([^\"]+)\"", html_content, re.I
        ):
            fid, title = m.group(1).strip(), m.group(2).strip()
            if self._is_title_match(title):
                matching_ids.add(fid)
                title_map[fid] = title

        for m in re.finditer(
            r"data-film-title=\"([^\"]+)\"[^>]*data-film-id=\"(\d+)\"", html_content, re.I
        ):
            title, fid = m.group(1).strip(), m.group(2).strip()
            if self._is_title_match(title):
                matching_ids.add(fid)
                title_map[fid] = title

        # 3. Poster elements: id="poster_407923" data-film-title="Die Odyssee"
        for m in re.finditer(
            r"id=\"poster_(\d+)\"[^>]*data-film-title=\"([^\"]+)\"", html_content, re.I
        ):
            fid, title = m.group(1).strip(), m.group(2).strip()
            if self._is_title_match(title):
                matching_ids.add(fid)
                title_map[fid] = title

        # 4. Links to /film/<slug>/<id>/...
        for m in re.finditer(
            r"href=\"/film/([^/]+)/(\d+)[^\"]*\">([^<]+)</a>", html_content, re.I
        ):
            slug, fid, title = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
            if self._is_title_match(title) or self._is_title_match(slug):
                matching_ids.add(fid)
                title_map[fid] = title

        return matching_ids, title_map

    def _is_title_match(self, title: str) -> bool:
        """Check if candidate title matches any of the target titles."""
        t_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", title).lower()
        t_tokens = set(t_clean.split())

        for target in self.target_titles:
            target_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", target).lower()
            if target_clean in t_clean or t_clean in target_clean:
                return True
            # Keyword matching (e.g. 'odyssey' or 'odyssee')
            target_tokens = set(target_clean.split())
            shared_keywords = {"odyssey", "odyssee"}.intersection(target_tokens)
            if shared_keywords and any(kw in t_tokens for kw in shared_keywords):
                return True

        return False
