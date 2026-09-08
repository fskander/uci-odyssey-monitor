"""HTTP fetcher for retrieving cinema schedules from UCI Kinowelt."""

import time
import logging
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)


class ScheduleFetcher:
    """Fetches cinema schedule HTML from live website or local file."""

    def __init__(
        self,
        cinema_url: str = "https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery",
        film_url: Optional[str] = "https://www.uci-kinowelt.de/film/die-odyssee/407923/berlin-east-side-gallery/82",
        user_agent: str = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        timeout: int = 20,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.cinema_url = cinema_url
        self.film_url = film_url
        self.user_agent = user_agent
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def fetch(self, source_url_or_file: Optional[str] = None) -> str:
        """
        Fetch HTML content from a URL or read from a local file path.
        If source_url_or_file is not specified, defaults to cinema_url.
        """
        target = source_url_or_file or self.cinema_url

        # Check if target is a local file
        if not (target.startswith("http://") or target.startswith("https://")):
            logger.info("Reading schedule from local file: %s", target)
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        logger.info("Fetching schedule from live URL: %s", target)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(target, headers=headers)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8", errors="replace")
                    logger.info(
                        "Successfully fetched %d bytes (HTTP %s) from %s",
                        len(content),
                        response.status,
                        target,
                    )
                    return content
            except urllib.error.HTTPError as e:
                last_exception = e
                logger.warning(
                    "HTTP error %d on attempt %d/%d for %s",
                    e.code,
                    attempt,
                    self.max_retries,
                    target,
                )
                if e.code >= 500:
                    time.sleep(self.retry_delay * attempt)
                else:
                    # Client errors (4xx) usually should not be retried immediately
                    break
            except urllib.error.URLError as e:
                last_exception = e
                logger.warning(
                    "Network error on attempt %d/%d for %s: %s",
                    attempt,
                    self.max_retries,
                    target,
                    e.reason,
                )
                time.sleep(self.retry_delay * attempt)
            except Exception as e:
                last_exception = e
                logger.warning(
                    "Unexpected error on attempt %d/%d for %s: %s",
                    attempt,
                    self.max_retries,
                    target,
                    e,
                )
                time.sleep(self.retry_delay * attempt)

        # Fallback to film_url if fetching the main cinema URL failed and film_url is different
        if self.film_url and target == self.cinema_url and self.film_url != self.cinema_url:
            logger.info("Main schedule URL failed, attempting fallback to direct film page: %s", self.film_url)
            try:
                return self.fetch(self.film_url)
            except Exception as fallback_e:
                logger.error("Fallback to film URL also failed: %s", fallback_e)

        raise RuntimeError(
            f"Failed to fetch cinema schedule after {self.max_retries} attempts: {last_exception}"
        )
