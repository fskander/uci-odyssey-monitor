"""HTTP and headless browser fetcher for retrieving cinema schedules from UCI Kinowelt."""

import os
import time
import logging
import subprocess
import urllib.request
import urllib.error
from typing import Optional

logger = logging.getLogger(__name__)

# Check for curl_cffi (Chrome TLS impersonation)
try:
    from curl_cffi import requests as cffi_requests
    HAS_CURL_CFFI = True
except ImportError:
    cffi_requests = None
    HAS_CURL_CFFI = False

# Check for Playwright (real headless Chromium)
try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


class ScheduleFetcher:
    """Fetches cinema schedule HTML from live website, local file, or headless browser."""

    BROWSER_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }

    def __init__(
        self,
        cinema_url: str = "https://www.uci-kinowelt.de/kinoprogramm/berlin-east-side-gallery",
        film_url: Optional[str] = "https://www.uci-kinowelt.de/film/die-odyssee/407923/berlin-east-side-gallery/82",
        user_agent: Optional[str] = None,
        timeout: int = 25,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):
        self.cinema_url = cinema_url
        self.film_url = film_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        if user_agent:
            self.BROWSER_HEADERS["User-Agent"] = user_agent

    def fetch(self, source_url_or_file: Optional[str] = None) -> str:
        """
        Fetch HTML content from a URL or read from a local file path.
        If source_url_or_file is not specified, defaults to cinema_url.
        """
        target = source_url_or_file or self.cinema_url

        # 1. Local file mode
        if not (target.startswith("http://") or target.startswith("https://")):
            logger.info("Reading schedule from local file: %s", target)
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                return f.read()

        logger.info("Fetching schedule from live URL: %s", target)

        # 2. Try curl_cffi if installed (Chrome TLS fingerprint impersonation)
        if HAS_CURL_CFFI:
            try:
                logger.debug("Attempting fetch with curl_cffi (Chrome impersonation)...")
                r = cffi_requests.get(
                    target,
                    impersonate="chrome124",
                    headers=self.BROWSER_HEADERS,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if r.status_code == 200 and len(r.text) > 10000:
                    logger.info("Successfully fetched %d bytes via curl_cffi from %s", len(r.text), target)
                    return r.text
                else:
                    logger.warning("curl_cffi returned status %s (length %d)", r.status_code, len(r.text))
            except Exception as e:
                logger.warning("curl_cffi fetch failed: %s", e)

        # 3. Try standard urllib
        last_exception = None
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(target, headers=self.BROWSER_HEADERS)
                with urllib.request.urlopen(req, timeout=self.timeout) as response:
                    content = response.read().decode("utf-8", errors="replace")
                    logger.info("Successfully fetched %d bytes (HTTP %s) via urllib from %s", len(content), response.status, target)
                    return content
            except urllib.error.HTTPError as e:
                last_exception = e
                body_preview = e.read()[:300].decode("utf-8", errors="replace")
                logger.warning(
                    "urllib HTTP error %d on attempt %d/%d for %s. Preview: %s",
                    e.code,
                    attempt,
                    self.max_retries,
                    target,
                    body_preview.replace("\n", " "),
                )
                if e.code == 403:
                    # Cloudflare block on datacenter IP - break to try fallbacks immediately
                    break
                time.sleep(self.retry_delay * attempt)
            except Exception as e:
                last_exception = e
                logger.warning("urllib network error on attempt %d/%d: %s", attempt, self.max_retries, e)
                time.sleep(self.retry_delay * attempt)

        # 4. Try curl subprocess
        try:
            logger.debug("Attempting fetch with curl CLI subprocess...")
            cmd = [
                "curl",
                "-sL",
                "--max-time", str(self.timeout),
                "-H", f"User-Agent: {self.BROWSER_HEADERS['User-Agent']}",
                "-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: de-DE,de;q=0.9,en-US;q=0.8",
                target,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 5)
            if result.returncode == 0 and len(result.stdout) > 10000 and "<html" in result.stdout.lower():
                logger.info("Successfully fetched %d bytes via curl subprocess from %s", len(result.stdout), target)
                return result.stdout
            else:
                logger.warning("curl subprocess returned %d bytes (code %d)", len(result.stdout), result.returncode)
        except Exception as e:
            logger.warning("curl subprocess fetch failed: %s", e)

        # 5. Try Playwright headless Chromium if available
        if HAS_PLAYWRIGHT:
            try:
                logger.info("Attempting fetch with Playwright headless Chromium to bypass Cloudflare...")
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                    )
                    context = browser.new_context(
                        user_agent=self.BROWSER_HEADERS["User-Agent"],
                        locale="de-DE",
                    )
                    page = context.new_page()
                    page.goto(target, wait_until="domcontentloaded", timeout=self.timeout * 1000)
                    # Wait for cloudflare challenge and schedule badges
                    try:
                        page.wait_for_selector(".badge-performance, [data-film-id], h2", timeout=12000)
                    except Exception:
                        page.wait_for_timeout(5000)
                    content = page.content()
                    browser.close()

                    if len(content) > 10000 and "badge-performance" in content:
                        logger.info("Successfully fetched %d bytes via Playwright from %s", len(content), target)
                        return content
                    else:
                        logger.warning("Playwright fetched page (%d bytes), but badge-performance not found yet", len(content))
                        return content
            except Exception as e:
                logger.warning("Playwright fetch failed: %s", e)

        # 6. Fallback to direct film URL if target was the main cinema schedule
        if self.film_url and target == self.cinema_url and self.film_url != self.cinema_url:
            logger.info("Cinema schedule URL blocked, attempting fallback to direct film page: %s", self.film_url)
            return self.fetch(self.film_url)

        raise RuntimeError(
            f"Failed to fetch cinema schedule after trying urllib, curl, and browser engines: {last_exception}"
        )
